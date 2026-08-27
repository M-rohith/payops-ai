from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Customer, Merchant, Order, Payment
from app.schemas.operations import PaymentDetail, PaymentListItem, PaymentListResponse


def list_payments(session: Session, source: str, status: str | None, method: str | None, search: str | None, limit: int, offset: int) -> PaymentListResponse:
    conditions = []
    if source != "all": conditions.append(Merchant.source == source)
    if status: conditions.append(Payment.status == status)
    if method: conditions.append(Payment.method == method)
    if search:
        token = f"%{search}%"; conditions.append(or_(Payment.external_payment_id.ilike(token), Order.external_order_id.ilike(token), Customer.name.ilike(token)))
    base = select(Payment, Order, Customer, Merchant).select_from(Payment).join(Order, Payment.order_id == Order.id).join(Customer, Order.customer_id == Customer.id).join(Merchant, Payment.merchant_id == Merchant.id).where(*conditions)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(base.order_by(Payment.created_at.desc()).limit(limit).offset(offset)).all()
    items = [PaymentListItem(id=p.id, external_payment_id=p.external_payment_id, external_order_id=o.external_order_id, customer_name=c.name, source=m.source, amount=p.amount, currency=p.currency, method=p.method, status=p.status, error_code=p.error_code, error_description=p.error_description, captured=p.captured, created_at=p.created_at) for p, o, c, m in rows]
    return PaymentListResponse(items=items, total=total, limit=limit, offset=offset)


def get_payment(session: Session, payment_identifier: str, source: str = "all") -> PaymentDetail | None:
    conditions = [Payment.id == int(payment_identifier)] if payment_identifier.isdigit() else [Payment.external_payment_id == payment_identifier]
    if source != "all": conditions.append(Merchant.source == source)
    row = session.execute(select(Payment, Order, Customer, Merchant).select_from(Payment).join(Order, Payment.order_id == Order.id).join(Customer, Order.customer_id == Customer.id).join(Merchant, Payment.merchant_id == Merchant.id).where(*conditions)).one_or_none()
    if not row: return None
    p, o, c, m = row
    return PaymentDetail(id=p.id, external_payment_id=p.external_payment_id, external_order_id=o.external_order_id, customer_name=c.name, source=m.source, customer_email=c.email, customer_phone=c.phone, order_status=o.status, amount=p.amount, currency=p.currency, method=p.method, status=p.status, error_code=p.error_code, error_description=p.error_description, captured=p.captured, created_at=p.created_at)
