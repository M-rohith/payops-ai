from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["all", "demo", "razorpay"]
TimeRange = Literal["1D", "7D", "30D"]
PaymentMethod = Literal["upi", "card", "netbanking", "wallet"]


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SummaryArgs(ToolArguments):
    source: Source
    time_range: TimeRange


class FailureStatsArgs(ToolArguments):
    source: Source
    method: PaymentMethod | None
    time_range: TimeRange


class FailureReasonsArgs(FailureStatsArgs):
    pass


class CompareFailureRatesArgs(ToolArguments):
    source: Source
    method: PaymentMethod | None
    current_period: TimeRange
    comparison_period: TimeRange


class FailedPaymentsArgs(ToolArguments):
    source: Source
    method: PaymentMethod | None
    minimum_amount: int | None = Field(ge=0)
    limit: int = Field(ge=1, le=25)


class SettlementVarianceArgs(ToolArguments):
    source: Source
    settlement_id: str | None


class ReconciliationArgs(ToolArguments):
    source: Source
    issue_type: str | None = Field(max_length=80)
    limit: int = Field(ge=1, le=25)


class AlertsArgs(ToolArguments):
    source: Source
    severity: Literal["high", "medium", "low"] | None
    limit: int = Field(ge=1, le=25)


class PaymentDetailsArgs(ToolArguments):
    payment_id: str = Field(min_length=1, max_length=100)


TOOL_MODELS: dict[str, type[ToolArguments]] = {
    "get_dashboard_summary": SummaryArgs,
    "get_payment_failure_stats": FailureStatsArgs,
    "get_failure_reason_breakdown": FailureReasonsArgs,
    "compare_failure_rates": CompareFailureRatesArgs,
    "get_failed_payments": FailedPaymentsArgs,
    "get_settlement_variance": SettlementVarianceArgs,
    "get_reconciliation_issues": ReconciliationArgs,
    "get_alerts": AlertsArgs,
    "get_payment_details": PaymentDetailsArgs,
}

TOOL_DESCRIPTIONS = {
    "get_dashboard_summary": "Get top-level payment, refund, settlement, and alert metrics for a source and time range.",
    "get_payment_failure_stats": "Get attempts, failures, success count, failure rate, and failed amount, optionally for one payment method.",
    "get_failure_reason_breakdown": "Break failed payments down by recorded error code, count, percentage, and affected amount.",
    "compare_failure_rates": "Compare a current failure window with the immediately preceding comparison window.",
    "get_failed_payments": "Return a bounded list of normalized failed payment facts and customer names without contact details.",
    "get_settlement_variance": "Return recorded settlement expected/actual variance, fees, adjustments, and status.",
    "get_reconciliation_issues": "Return bounded recorded reconciliation issues and related payment/order context.",
    "get_alerts": "Return bounded recorded operational alerts, optionally filtered by severity.",
    "get_payment_details": "Return normalized details for one local or external payment identifier.",
}


def _strict_schema(model: type[ToolArguments]) -> dict:
    schema = model.model_json_schema()
    schema["additionalProperties"] = False
    schema["required"] = list(schema.get("properties", {}).keys())
    return schema


OPENAI_TOOLS = [{"type": "function", "name": name, "description": TOOL_DESCRIPTIONS[name], "parameters": _strict_schema(model), "strict": True} for name, model in TOOL_MODELS.items()]
