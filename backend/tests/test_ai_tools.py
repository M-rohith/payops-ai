import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.ai.agent import PayOpsAgent
from app.ai.dispatcher import dispatch_tool
from app.ai.exceptions import AIConfigurationError, AIProviderError, AIToolError, AIToolRoundLimitError
from app.ai.prompts import PAYOPS_INSTRUCTIONS
from app.ai.tool_schemas import OPENAI_TOOLS
from app.ai.tools import alerts, failure_reason_breakdown, payment_failure_stats, reconciliation_issues, settlement_variance
from app.config import Settings
from app.integrations.razorpay.schemas import MappedPayment
from app.integrations.razorpay.sync import get_or_create_integration_merchant, upsert_payment


def add_razorpay_attempts(db: Session) -> None:
    merchant = get_or_create_integration_merchant(db); now = datetime.now(UTC)
    for identifier, status in [("pay_ai_captured", "captured"), ("pay_ai_failed_1", "failed"), ("pay_ai_failed_2", "failed")]:
        upsert_payment(db, merchant, MappedPayment(external_payment_id=identifier, external_order_id="order_ai_test", amount=10_000, currency="INR", method="card", status=status, error_code="CARD_DECLINED" if status == "failed" else None, error_description=None, captured=status == "captured", created_at=now))
    db.commit()


def test_tool_schemas_are_strict_and_dispatch_validates(db: Session) -> None:
    assert len(OPENAI_TOOLS) == 9
    assert all(tool["strict"] and tool["parameters"]["additionalProperties"] is False for tool in OPENAI_TOOLS)
    result = dispatch_tool(db, "get_dashboard_summary", {"source": "demo", "time_range": "30D"}, "demo")
    assert result["payment_volume"] > 0
    with pytest.raises(AIToolError): dispatch_tool(db, "unknown_tool", {}, "demo")
    with pytest.raises(AIToolError): dispatch_tool(db, "get_failed_payments", {"source": "demo", "method": None, "minimum_amount": None, "limit": 1000}, "demo")
    with pytest.raises(AIToolError): dispatch_tool(db, "get_dashboard_summary", "not-json", "demo")


def test_dispatch_enforces_selected_source(db: Session) -> None:
    add_razorpay_attempts(db)
    result = dispatch_tool(db, "get_dashboard_summary", {"source": "razorpay", "time_range": "30D"}, "demo")
    assert result["payment_volume"] > 10_000


def test_demo_failure_settlement_and_attention_scenarios(db: Session) -> None:
    stats = payment_failure_stats(db, "demo", "upi", "30D")
    reasons = failure_reason_breakdown(db, "demo", "upi", "30D")
    settlements = settlement_variance(db, "demo", None)
    assert stats["failed_attempts"] >= 28 and stats["failure_rate"] > 0
    assert any(reason["error_code"] == "UPI_GATEWAY_TIMEOUT" and reason["count"] >= 28 for reason in reasons["reasons"])
    assert any(item["difference"] == -107_500 for item in settlements["settlements"])
    assert alerts(db, "demo", None, 10)["count"] == 3
    issues = reconciliation_issues(db, "demo", None, 10)
    assert issues["count"] == 3 and any(item["customer_name"] for item in issues["issues"])


def test_razorpay_recent_payments_and_empty_settlements(db: Session) -> None:
    add_razorpay_attempts(db)
    stats = payment_failure_stats(db, "razorpay", "card", "30D")
    assert stats == {"source": "razorpay", "method": "card", "time_range": "30D", "total_attempts": 3, "failed_attempts": 2, "successful_attempts": 1, "failure_rate": 66.7, "affected_amount": 20_000}
    assert settlement_variance(db, "razorpay", None) == {"source": "razorpay", "found": False, "settlements": []}


class FakeResponses:
    def __init__(self, responses): self.queue = list(responses); self.requests = []
    def create(self, **kwargs): self.requests.append(kwargs); response = self.queue.pop(0); return response() if callable(response) else response


class FakeClient:
    def __init__(self, responses): self.responses = FakeResponses(responses)


def function_call(name: str, arguments: dict, call_id: str):
    return SimpleNamespace(type="function_call", name=name, arguments=json.dumps(arguments), call_id=call_id)


def model_response(output, text=""):
    return SimpleNamespace(output=output, output_text=text)


def ai_settings(key: str = "test-key") -> Settings:
    return Settings(openai_api_key=SecretStr(key), openai_model="test-model", openai_max_output_tokens=200)


def test_agent_supports_multiple_tool_rounds_and_evidence(db: Session) -> None:
    fake = FakeClient([model_response([function_call("get_dashboard_summary", {"source": "razorpay", "time_range": "30D"}, "call_1")]), model_response([function_call("get_failure_reason_breakdown", {"source": "razorpay", "method": "upi", "time_range": "30D"}, "call_2")]), model_response([], "The recorded evidence shows a UPI timeout spike. No action was performed.")])
    result = PayOpsAgent(ai_settings(), fake).query(db, "Why are UPI payments failing?", "demo")
    assert result.source == "demo" and result.advisory
    assert result.tools_used == ["get_dashboard_summary", "get_failure_reason_breakdown"]
    outputs = [item for request in fake.responses.requests for item in request["input"] if item.get("type") == "function_call_output"]
    assert outputs and any("payment_volume" in item["output"] for item in outputs)
    assert all(request["store"] is False and request["parallel_tool_calls"] is False for request in fake.responses.requests)


def test_agent_max_round_and_provider_failure(db: Session) -> None:
    calls = [model_response([function_call("get_dashboard_summary", {"source": "demo", "time_range": "30D"}, f"call_{index}")]) for index in range(2)]
    with pytest.raises(AIToolRoundLimitError): PayOpsAgent(ai_settings(), FakeClient(calls), max_tool_rounds=2).query(db, "Summarize payments", "demo")
    with pytest.raises(AIProviderError): PayOpsAgent(ai_settings(), FakeClient([lambda: (_ for _ in ()).throw(RuntimeError("provider internals"))])).query(db, "Summarize payments", "demo")


def test_missing_key_and_read_only_prompt() -> None:
    with pytest.raises(AIConfigurationError): PayOpsAgent(ai_settings(""))
    assert "read-only" in PAYOPS_INSTRUCTIONS and "cannot capture" in PAYOPS_INSTRUCTIONS
    assert not any(any(word in tool["name"] for word in ["refund_payment", "capture", "resolve_alert", "execute"]) for tool in OPENAI_TOOLS)
