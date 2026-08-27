import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.exceptions import RazorpayAPIError
from app.integrations.razorpay.mapper import map_order, map_payment, map_refund, map_settlement
from app.integrations.razorpay.schemas import MappedOrder, MappedPayment, MappedRefund, MappedSettlement, SyncSummary
from app.models import Customer, Merchant, Order, Payment, Refund, Settlement

logger = logging.getLogger(__name__)
ORDER_RANK = {"created": 1, "failed": 2, "cancelled": 2, "paid": 3}
PAYMENT_RANK = {"authorized": 1, "failed": 2, "captured": 3, "refunded": 4}


def get_or_create_integration_merchant(session: Session) -> Merchant:
    merchant = session.scalar(select(Merchant).where(Merchant.source == "razorpay"))
    if merchant is None:
        merchant = Merchant(name="Razorpay Test Integration", source="razorpay", created_at=datetime.now(UTC)); session.add(merchant); session.flush()
    return merchant


def get_or_create_integration_customer(session: Session, merchant: Merchant) -> Customer:
    customer = session.scalar(select(Customer).where(Customer.merchant_id == merchant.id, Customer.email == "razorpay-integration@example.test"))
    if customer is None:
        customer = Customer(merchant_id=merchant.id, name="Razorpay Customer", email="razorpay-integration@example.test", phone=None, created_at=datetime.now(UTC)); session.add(customer); session.flush()
    return customer


def upsert_order(session: Session, merchant: Merchant, data: MappedOrder) -> tuple[Order, str]:
    order = session.scalar(select(Order).where(Order.external_order_id == data.external_order_id))
    action = "updated"
    if order is None:
        customer = get_or_create_integration_customer(session, merchant)
        order = Order(merchant_id=merchant.id, customer_id=customer.id, external_order_id=data.external_order_id, amount=data.amount, currency=data.currency, status=data.status, created_at=data.created_at); session.add(order); action = "created"
    elif order.merchant_id != merchant.id:
        raise RazorpayAPIError("External order ID conflicts with a non-Razorpay record")
    else:
        order.amount = data.amount; order.currency = data.currency
        if ORDER_RANK.get(data.status, 0) >= ORDER_RANK.get(order.status, 0): order.status = data.status
    session.flush(); return order, action


def _placeholder_order(session: Session, merchant: Merchant, external_order_id: str, amount: int, currency: str, created_at: datetime) -> Order:
    mapped = MappedOrder(external_order_id=external_order_id, amount=amount, currency=currency, status="created", created_at=created_at)
    return upsert_order(session, merchant, mapped)[0]


def upsert_payment(session: Session, merchant: Merchant, data: MappedPayment) -> tuple[Payment, str]:
    payment = session.scalar(select(Payment).where(Payment.external_payment_id == data.external_payment_id))
    order_external_id = data.external_order_id or f"razorpay_unlinked_{data.external_payment_id}"
    order = _placeholder_order(session, merchant, order_external_id, data.amount, data.currency, data.created_at)
    action = "updated"
    if payment is None:
        payment = Payment(merchant_id=merchant.id, order_id=order.id, external_payment_id=data.external_payment_id, amount=data.amount, currency=data.currency, method=data.method, status=data.status, error_code=data.error_code, error_description=data.error_description, captured=data.captured, created_at=data.created_at); session.add(payment); action = "created"
    elif payment.merchant_id != merchant.id:
        raise RazorpayAPIError("External payment ID conflicts with a non-Razorpay record")
    else:
        payment.order_id = order.id; payment.amount = data.amount; payment.currency = data.currency; payment.method = data.method
        if PAYMENT_RANK.get(data.status, 0) >= PAYMENT_RANK.get(payment.status, 0):
            payment.status = data.status; payment.captured = data.captured; payment.error_code = data.error_code; payment.error_description = data.error_description
    if payment.status in {"captured", "refunded"} and ORDER_RANK.get(order.status, 0) < ORDER_RANK["paid"]: order.status = "paid"
    session.flush(); return payment, action


def upsert_refund(session: Session, merchant: Merchant, data: MappedRefund) -> tuple[Refund, str]:
    refund = session.scalar(select(Refund).where(Refund.external_refund_id == data.external_refund_id)); action = "updated"
    payment = session.scalar(select(Payment).where(Payment.external_payment_id == data.external_payment_id, Payment.merchant_id == merchant.id))
    if payment is None:
        placeholder = MappedPayment(external_payment_id=data.external_payment_id, external_order_id=None, amount=data.amount, currency="INR", method="unknown", status="captured", error_code=None, error_description=None, captured=True, created_at=data.created_at)
        payment = upsert_payment(session, merchant, placeholder)[0]
    if refund is None:
        refund = Refund(merchant_id=merchant.id, payment_id=payment.id, external_refund_id=data.external_refund_id, amount=data.amount, status=data.status, created_at=data.created_at); session.add(refund); action = "created"
    elif refund.merchant_id != merchant.id: raise RazorpayAPIError("External refund ID conflicts with a non-Razorpay record")
    else: refund.payment_id = payment.id; refund.amount = data.amount; refund.status = data.status
    if data.status == "processed": payment.status = "refunded"
    session.flush(); return refund, action


def upsert_settlement(session: Session, merchant: Merchant, data: MappedSettlement) -> tuple[Settlement, str]:
    settlement = session.scalar(select(Settlement).where(Settlement.external_settlement_id == data.external_settlement_id)); action = "updated"
    if settlement is None:
        settlement = Settlement(merchant_id=merchant.id, external_settlement_id=data.external_settlement_id, expected_amount=data.amount, actual_amount=data.amount, fees=data.fees, adjustments=0, status=data.status, settled_at=data.settled_at, created_at=data.created_at); session.add(settlement); action = "created"
    elif settlement.merchant_id != merchant.id: raise RazorpayAPIError("External settlement ID conflicts with a non-Razorpay record")
    else: settlement.expected_amount = data.amount; settlement.actual_amount = data.amount; settlement.fees = data.fees; settlement.status = data.status; settlement.settled_at = data.settled_at
    session.flush(); return settlement, action


def synchronize(session: Session, client: RazorpayClient, count: int = 25) -> SyncSummary:
    summary = SyncSummary(); merchant = get_or_create_integration_merchant(session)
    orders = client.list_orders(count); summary.orders_fetched = len(orders)
    for raw in orders:
        _, action = upsert_order(session, merchant, map_order(raw)); setattr(summary, f"orders_{action}", getattr(summary, f"orders_{action}") + 1)
    payments = client.list_payments(count); summary.payments_fetched = len(payments)
    for raw in payments:
        _, action = upsert_payment(session, merchant, map_payment(raw)); setattr(summary, f"payments_{action}", getattr(summary, f"payments_{action}") + 1)
    refunds = client.list_refunds(count); summary.refunds_fetched = len(refunds)
    for raw in refunds:
        _, action = upsert_refund(session, merchant, map_refund(raw)); setattr(summary, f"refunds_{action}", getattr(summary, f"refunds_{action}") + 1)
    try: settlements = client.list_settlements(count)
    except RazorpayAPIError:
        settlements = []; summary.settlements_unavailable = True
    summary.settlements_fetched = len(settlements)
    for raw in settlements:
        _, action = upsert_settlement(session, merchant, map_settlement(raw)); setattr(summary, f"settlements_{action}", getattr(summary, f"settlements_{action}") + 1)
    session.commit()
    logger.info("Razorpay sync completed: orders=%s payments=%s refunds=%s settlements=%s", summary.orders_fetched, summary.payments_fetched, summary.refunds_fetched, summary.settlements_fetched)
    return summary
