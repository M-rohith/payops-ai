from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.dashboard import get_dashboard_summary, get_payment_method_breakdown, get_volume_series
from app.integrations.razorpay.schemas import MappedPayment
from app.integrations.razorpay.sync import get_or_create_integration_merchant, upsert_payment
from app.models import Merchant, Payment
from app.seed import seed_database


def test_analytics_ranges_and_methods(db: Session) -> None:
    now = datetime(2026, 8, 26, 12, tzinfo=UTC)
    day = get_dashboard_summary(db, "demo", "1D", now); month = get_dashboard_summary(db, "demo", "30D", now)
    assert day.failed_payments >= 28 and month.payment_volume >= day.payment_volume
    assert len(get_volume_series(db, "demo", "7D", now)) == 8
    assert {item.method for item in get_payment_method_breakdown(db, "demo", "30D", now)} == {"upi", "card", "netbanking", "wallet"}


def test_seed_is_idempotent(db: Session) -> None:
    now = datetime(2026, 8, 26, 12, tzinfo=UTC)
    seed_database(db, now); seed_database(db, now)
    assert db.scalar(select(func.count(Payment.id))) == 248
    assert db.scalar(select(func.count(Merchant.id))) == 1


def test_monetary_calculation_uses_exact_minor_units(db: Session) -> None:
    merchant_id = db.scalar(select(Merchant.id).where(Merchant.source == "demo")); now = datetime(2026, 8, 26, 12, tzinfo=UTC)
    expected = db.scalar(select(func.sum(Payment.amount)).where(Payment.merchant_id == merchant_id, Payment.status.in_(["captured", "refunded"]), Payment.created_at >= datetime(2026, 7, 27, 12, tzinfo=UTC)))
    assert get_dashboard_summary(db, "demo", "30D", now).payment_volume == expected


def test_source_aware_razorpay_and_combined_analytics(db: Session) -> None:
    now = datetime(2026, 8, 26, 12, tzinfo=UTC); merchant = get_or_create_integration_merchant(db)
    for identifier, status in [("pay_source_captured", "captured"), ("pay_source_failed_1", "failed"), ("pay_source_failed_2", "failed")]:
        upsert_payment(db, merchant, MappedPayment(external_payment_id=identifier, external_order_id="order_source_test", amount=10_000, currency="INR", method="card", status=status, error_code="DECLINED" if status == "failed" else None, error_description=None, captured=status == "captured", created_at=now))
    db.commit()

    demo = get_dashboard_summary(db, "demo", "30D", now); razorpay = get_dashboard_summary(db, "razorpay", "30D", now); combined = get_dashboard_summary(db, "all", "30D", now)
    assert razorpay.payment_volume == 10_000 and razorpay.failed_payments == 2 and razorpay.success_rate == 33.3
    assert razorpay.settlement_amount == razorpay.refund_amount == razorpay.open_alerts == 0
    assert combined.payment_volume == demo.payment_volume + razorpay.payment_volume
    assert combined.failed_payments == demo.failed_payments + razorpay.failed_payments
    assert sum(point.amount for point in get_volume_series(db, "razorpay", "1D", now)) == 10_000
    methods = get_payment_method_breakdown(db, "razorpay", "30D", now)
    assert len(methods) == 1 and methods[0].method == "card" and methods[0].payment_count == 3
