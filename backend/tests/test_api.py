from fastapi.testclient import TestClient
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.razorpay.schemas import MappedPayment
from app.integrations.razorpay.sync import get_or_create_integration_merchant, upsert_payment
from app.models import Payment


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_database_backed_dashboard_summary(client: TestClient) -> None:
    response = client.get("/api/dashboard/summary?time_range=30D")
    assert response.status_code == 200
    data = response.json()
    assert data["payment_volume"] > 0
    assert 70 < data["success_rate"] < 100
    assert data["failed_payments"] >= 28
    assert data["refund_amount"] > 0
    assert data["settlement_amount"] == 5_532_500
    assert data["open_alerts"] == 3


def test_payment_filters_and_search(client: TestClient) -> None:
    failed_upi = client.get("/api/payments?status=failed&method=upi&limit=100").json()
    assert failed_upi["total"] >= 28
    assert all(item["status"] == "failed" and item["method"] == "upi" for item in failed_upi["items"])
    assert any(item["error_code"] == "UPI_GATEWAY_TIMEOUT" for item in failed_upi["items"])
    assert client.get("/api/payments?search=pay_demo_0248").json()["total"] == 1


def test_reconciliation_and_settlement_scenarios(client: TestClient) -> None:
    issues = client.get("/api/reconciliation/issues")
    assert issues.status_code == 200 and len(issues.json()) == 3
    assert any(issue["issue_type"] == "order_payment_status_mismatch" for issue in issues.json())
    settlements = client.get("/api/settlements").json()
    discrepancy = next(item for item in settlements if item["external_settlement_id"] == "setl_demo_002")
    assert discrepancy["difference"] == -107_500


def test_demo_and_razorpay_payment_visibility_and_detail(client: TestClient, db: Session) -> None:
    merchant = get_or_create_integration_merchant(db)
    razorpay_payment, _ = upsert_payment(db, merchant, MappedPayment(external_payment_id="pay_visibility_test", external_order_id="order_visibility_test", amount=10_000, currency="INR", method="card", status="captured", error_code=None, error_description=None, captured=True, created_at=datetime(2026, 8, 27, 7, 26, tzinfo=UTC)))
    db.commit()

    default_result = client.get("/api/payments?search=pay_visibility_test").json()
    assert default_result["total"] == 1 and default_result["items"][0]["source"] == "razorpay"
    assert client.get("/api/payments?source=razorpay&search=pay_visibility_test").json()["total"] == 1
    assert client.get("/api/payments?source=demo&search=pay_visibility_test").json()["total"] == 0

    demo_result = client.get("/api/payments?source=demo&search=pay_demo_0001").json()
    assert demo_result["total"] == 1 and demo_result["items"][0]["source"] == "demo"
    assert client.get("/api/payments?source=all&limit=100").json()["total"] == 249

    by_local_id = client.get(f"/api/payments/{razorpay_payment.id}")
    by_external_id = client.get("/api/payments/pay_visibility_test")
    assert by_local_id.status_code == by_external_id.status_code == 200
    assert by_local_id.json()["external_payment_id"] == by_external_id.json()["external_payment_id"] == "pay_visibility_test"
    assert client.get("/api/payments/pay_visibility_test?source=demo").status_code == 404
    assert db.scalar(select(func.count(Payment.id)).where(Payment.external_payment_id == "pay_visibility_test")) == 1

    razorpay_summary = client.get("/api/dashboard/summary?source=razorpay").json()
    demo_summary = client.get("/api/dashboard/summary?source=demo").json()
    all_summary = client.get("/api/dashboard/summary?source=all").json()
    assert razorpay_summary["payment_volume"] == 10_000
    assert all_summary["payment_volume"] == demo_summary["payment_volume"] + 10_000
    assert client.get("/api/dashboard/issues?source=razorpay").json() == []
    assert client.get("/api/settlements?source=razorpay").json() == []
    assert client.get("/api/reconciliation/issues?source=razorpay").json() == []
