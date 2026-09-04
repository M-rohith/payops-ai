from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.integrations.razorpay.schemas import MappedPayment
from app.integrations.razorpay.sync import get_or_create_integration_merchant, upsert_payment
from app.models import Alert, Customer, Merchant, Order, Payment, ReconciliationIssue, Refund, Settlement


def test_demo_investigations_use_existing_evidence_and_stable_priority(client: TestClient) -> None:
    first = client.get("/api/investigations?source=demo")
    second = client.get("/api/investigations?source=demo")

    assert first.status_code == 200
    assert first.json() == second.json()
    items = first.json()
    assert items
    assert {item["source"] for item in items} == {"demo"}
    assert {item["type"] for item in items} >= {"payment_failure_spike", "settlement_variance", "reconciliation_issue"}
    assert [item["severity"] for item in items] == sorted(
        [item["severity"] for item in items], key={"high": 0, "medium": 1, "low": 2}.get
    )

    failure = next(item for item in items if item["type"] == "payment_failure_spike")
    assert failure["title"] == "UPI failure spike"
    assert failure["severity"] == "high"
    assert "UPI" in failure["suggested_question"]
    assert any("UPI_GATEWAY_TIMEOUT" in line for line in failure["evidence"])

    settlement = next(item for item in items if item["type"] == "settlement_variance")
    assert settlement["summary"].startswith("Settlement setl_demo_002")
    assert "setl_demo_002" in settlement["suggested_question"]
    assert settlement["financial_impact"] == 107_500


def test_source_filtering_keeps_razorpay_evidence_isolated(client: TestClient, db: Session) -> None:
    merchant = get_or_create_integration_merchant(db)
    created_at = datetime(2026, 8, 27, 7, 26, tzinfo=UTC)
    for identifier, status in [
        ("pay_queue_success", "captured"),
        ("pay_queue_failed_1", "failed"),
        ("pay_queue_failed_2", "failed"),
    ]:
        upsert_payment(db, merchant, MappedPayment(
            external_payment_id=identifier,
            external_order_id="order_queue_test",
            amount=10_000,
            currency="INR",
            method="card",
            status=status,
            error_code="CARD_DECLINED" if status == "failed" else None,
            error_description="Test decline" if status == "failed" else None,
            captured=status == "captured",
            created_at=created_at,
        ))
    db.commit()

    razorpay = client.get("/api/investigations?source=razorpay").json()
    assert razorpay and {item["source"] for item in razorpay} == {"razorpay"}
    assert {item["type"] for item in razorpay} == {"payment_failure_spike"}
    assert razorpay[0]["severity"] == "medium"
    assert "card payments" in razorpay[0]["suggested_question"]
    assert "CARD_DECLINED" in " ".join(razorpay[0]["evidence"])
    assert all("setl_demo" not in str(item) for item in razorpay)

    combined = client.get("/api/investigations?source=all").json()
    assert {item["source"] for item in combined} == {"demo", "razorpay"}
    assert [item for item in combined if item["source"] == "razorpay"] == razorpay
    assert client.get("/api/investigations?source=unknown").status_code == 422


def test_investigation_endpoint_is_read_only(client: TestClient, db: Session) -> None:
    models = (Merchant, Customer, Order, Payment, Refund, Settlement, Alert, ReconciliationIssue)
    before = {model.__tablename__: db.scalar(select(func.count()).select_from(model)) for model in models}

    assert client.get("/api/investigations?source=all").status_code == 200

    after = {model.__tablename__: db.scalar(select(func.count()).select_from(model)) for model in models}
    assert after == before
    assert client.post("/api/investigations").status_code == 405


def test_investigation_empty_state_returns_no_fabricated_issues(client: TestClient, db: Session) -> None:
    for model in (ReconciliationIssue, Alert, Settlement, Refund, Payment, Order, Customer, Merchant):
        db.execute(delete(model))
    db.commit()

    assert client.get("/api/investigations?source=all").json() == []
    assert client.get("/api/investigations?source=razorpay").json() == []
