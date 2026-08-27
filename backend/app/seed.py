import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Alert, Customer, Merchant, Order, Payment, ReconciliationIssue, Refund, Settlement

DEMO_MERCHANT_NAME = "Acme Commerce Demo"


def seed_database(session: Session, reference_time: datetime | None = None) -> dict[str, int]:
    """Replace the demo merchant dataset so repeated runs never duplicate it."""
    now = (reference_time or datetime.now(UTC)).replace(minute=0, second=0, microsecond=0)
    existing = session.scalar(select(Merchant).where(Merchant.name == DEMO_MERCHANT_NAME))
    if existing:
        merchant_id = existing.id
        for model in (ReconciliationIssue, Alert, Settlement, Refund, Payment, Order, Customer):
            session.execute(delete(model).where(model.merchant_id == merchant_id))
        session.delete(existing)
        session.flush()

    rng = random.Random(20260826)
    merchant = Merchant(name=DEMO_MERCHANT_NAME, source="demo", created_at=now - timedelta(days=90))
    session.add(merchant); session.flush()
    customers = [Customer(merchant_id=merchant.id, name=f"Demo Customer {i:02d}", email=f"customer{i:02d}@example.test", phone=f"+9198000{i:05d}", created_at=now - timedelta(days=60 - i)) for i in range(1, 41)]
    session.add_all(customers); session.flush()

    payments: list[Payment] = []
    orders: list[Order] = []
    for index in range(220):
        customer = customers[index % len(customers)]
        amount = rng.randrange(19900, 189900, 100)
        created_at = now - timedelta(hours=rng.randint(25, 30 * 24), minutes=rng.randint(0, 59))
        method = rng.choices(["upi", "card", "netbanking", "wallet"], weights=[0.48, 0.31, 0.13, 0.08], k=1)[0]
        status = rng.choices(["captured", "failed", "authorized"], weights=[0.90, 0.06, 0.04], k=1)[0]
        order_status = "paid" if status == "captured" else ("failed" if status == "failed" else "created")
        order = Order(merchant_id=merchant.id, customer_id=customer.id, external_order_id=f"order_demo_{index + 1:04d}", amount=amount, currency="INR", status=order_status, created_at=created_at - timedelta(minutes=2))
        session.add(order); session.flush(); orders.append(order)
        payment = Payment(merchant_id=merchant.id, order_id=order.id, external_payment_id=f"pay_demo_{index + 1:04d}", amount=amount, currency="INR", method=method, status=status, error_code="PAYMENT_DECLINED" if status == "failed" else None, error_description="Payment was declined by the issuing institution" if status == "failed" else None, captured=status == "captured", created_at=created_at)
        session.add(payment); payments.append(payment)

    # Scenario A: concentrated recent UPI timeout failures.
    for spike_index in range(28):
        index = 220 + spike_index
        customer = customers[index % len(customers)]
        amount = rng.randrange(24900, 149900, 100)
        created_at = now - timedelta(hours=spike_index % 20, minutes=(spike_index * 7) % 60)
        order = Order(merchant_id=merchant.id, customer_id=customer.id, external_order_id=f"order_demo_{index + 1:04d}", amount=amount, currency="INR", status="failed", created_at=created_at - timedelta(minutes=2))
        session.add(order); session.flush(); orders.append(order)
        payment = Payment(merchant_id=merchant.id, order_id=order.id, external_payment_id=f"pay_demo_{index + 1:04d}", amount=amount, currency="INR", method="upi", status="failed", error_code="UPI_GATEWAY_TIMEOUT", error_description="UPI provider did not respond within the allowed time", captured=False, created_at=created_at)
        session.add(payment); payments.append(payment)

    session.flush()
    captured = [p for p in payments if p.status == "captured"]
    for index, payment in enumerate(captured[:10], start=1):
        amount = min(payment.amount, rng.randrange(9900, 39900, 100))
        session.add(Refund(merchant_id=merchant.id, payment_id=payment.id, external_refund_id=f"rfnd_demo_{index:03d}", amount=amount, status="processed", created_at=now - timedelta(hours=index * 5)))
        if index <= 3: payment.status = "refunded"

    settlements = [
        Settlement(merchant_id=merchant.id, external_settlement_id="setl_demo_001", expected_amount=2_460_000, actual_amount=2_460_000, fees=49_200, adjustments=0, status="processed", settled_at=now - timedelta(days=3), created_at=now - timedelta(days=4)),
        Settlement(merchant_id=merchant.id, external_settlement_id="setl_demo_002", expected_amount=3_180_000, actual_amount=3_072_500, fees=63_600, adjustments=-43_900, status="processed", settled_at=now - timedelta(days=1), created_at=now - timedelta(days=2)),
        Settlement(merchant_id=merchant.id, external_settlement_id="setl_demo_003", expected_amount=1_840_000, actual_amount=1_840_000, fees=36_800, adjustments=0, status="pending", settled_at=None, created_at=now - timedelta(hours=8)),
    ]
    session.add_all(settlements)
    mismatch = captured[15]; mismatch.order.status = "created"
    session.add_all([
        ReconciliationIssue(merchant_id=merchant.id, order_id=mismatch.order_id, payment_id=mismatch.id, issue_type="order_payment_status_mismatch", description="Payment is captured but the associated order is still marked created.", status="open", created_at=now - timedelta(hours=3)),
        ReconciliationIssue(merchant_id=merchant.id, order_id=captured[22].order_id, payment_id=captured[22].id, issue_type="settlement_pending_investigation", description="Captured payment is eligible for settlement but is not included in the expected batch.", status="investigating", created_at=now - timedelta(hours=7)),
        ReconciliationIssue(merchant_id=merchant.id, order_id=captured[31].order_id, payment_id=captured[31].id, issue_type="amount_verification", description="Payment amount requires verification against the settlement report.", status="open", created_at=now - timedelta(days=1)),
    ])
    session.add_all([
        Alert(merchant_id=merchant.id, type="payment_failure_spike", severity="high", title="UPI failure rate increased", description="UPI timeout failures are significantly above the previous comparison period.", metric_value=28.0, baseline_value=4.0, status="open", created_at=now - timedelta(hours=1)),
        Alert(merchant_id=merchant.id, type="settlement_discrepancy", severity="medium", title="Settlement lower than expected", description="Settlement setl_demo_002 is ₹1,075 lower than expected after fees and adjustments.", metric_value=107500.0, baseline_value=0.0, status="open", created_at=now - timedelta(hours=5)),
        Alert(merchant_id=merchant.id, type="refund_activity", severity="medium", title="Refund activity requires review", description="Recent refund volume is above the normal development baseline.", metric_value=10.0, baseline_value=4.0, status="open", created_at=now - timedelta(hours=9)),
    ])
    session.commit()
    return {"merchants": 1, "customers": 40, "orders": len(orders), "payments": len(payments), "refunds": 10, "settlements": 3, "alerts": 3, "reconciliation_issues": 3}


def main() -> None:
    with SessionLocal() as session: counts = seed_database(session)
    print("Seed complete: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__": main()
