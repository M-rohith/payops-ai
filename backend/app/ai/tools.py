from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.dashboard import RANGE_DAYS, get_dashboard_summary, source_condition
from app.models import Alert, Customer, Merchant, Order, Payment, ReconciliationIssue, Settlement
from app.services.payments import get_payment


def _start(time_range: str, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) - timedelta(days=RANGE_DAYS[time_range])


def _payment_conditions(source: str, method: str | None, start: datetime, end: datetime | None = None):
    conditions = [source_condition(source), Payment.created_at >= start]
    if end is not None: conditions.append(Payment.created_at < end)
    if method is not None: conditions.append(Payment.method == method)
    return conditions


def dashboard_summary(session: Session, source: str, time_range: str) -> dict:
    return get_dashboard_summary(session, source, time_range).model_dump()


def payment_failure_stats(session: Session, source: str, method: str | None, time_range: str, *, start: datetime | None = None, end: datetime | None = None) -> dict:
    window_start = start or _start(time_range)
    conditions = _payment_conditions(source, method, window_start, end)
    row = session.execute(select(func.count(Payment.id), func.count(Payment.id).filter(Payment.status == "failed"), func.count(Payment.id).filter(Payment.status.in_(["captured", "refunded"])), func.coalesce(func.sum(Payment.amount).filter(Payment.status == "failed"), 0)).select_from(Payment).join(Merchant, Payment.merchant_id == Merchant.id).where(*conditions)).one()
    total, failed, successful, failed_amount = (int(value or 0) for value in row)
    return {"source": source, "method": method, "time_range": time_range, "total_attempts": total, "failed_attempts": failed, "successful_attempts": successful, "failure_rate": round(failed / total * 100, 1) if total else 0.0, "affected_amount": failed_amount}


def failure_reason_breakdown(session: Session, source: str, method: str | None, time_range: str) -> dict:
    start = _start(time_range)
    conditions = _payment_conditions(source, method, start) + [Payment.status == "failed"]
    rows = session.execute(select(func.coalesce(Payment.error_code, "UNKNOWN"), func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)).select_from(Payment).join(Merchant, Payment.merchant_id == Merchant.id).where(*conditions).group_by(Payment.error_code).order_by(func.count(Payment.id).desc())).all()
    total = sum(int(row[1]) for row in rows)
    return {"source": source, "method": method, "time_range": time_range, "total_failures": total, "reasons": [{"error_code": code, "count": int(count), "percentage": round(int(count) / total * 100, 1) if total else 0.0, "affected_amount": int(amount)} for code, count, amount in rows]}


def compare_failure_rates(session: Session, source: str, method: str | None, current_period: str, comparison_period: str) -> dict:
    now = datetime.now(UTC); current_start = now - timedelta(days=RANGE_DAYS[current_period]); comparison_start = current_start - timedelta(days=RANGE_DAYS[comparison_period])
    current = payment_failure_stats(session, source, method, current_period, start=current_start, end=now)
    previous = payment_failure_stats(session, source, method, comparison_period, start=comparison_start, end=current_start)
    absolute = round(current["failure_rate"] - previous["failure_rate"], 1)
    relative = round(absolute / previous["failure_rate"] * 100, 1) if previous["failure_rate"] else None
    return {"source": source, "method": method, "current_period": current_period, "comparison_period": comparison_period, "current_rate": current["failure_rate"], "comparison_rate": previous["failure_rate"], "absolute_change": absolute, "relative_percentage_change": relative, "current_sample": current["total_attempts"], "comparison_sample": previous["total_attempts"]}


def failed_payments(session: Session, source: str, method: str | None, minimum_amount: int | None, limit: int) -> dict:
    conditions = [source_condition(source), Payment.status == "failed"]
    if method is not None: conditions.append(Payment.method == method)
    if minimum_amount is not None: conditions.append(Payment.amount >= minimum_amount)
    rows = session.execute(select(Payment, Order, Customer).select_from(Payment).join(Merchant, Payment.merchant_id == Merchant.id).join(Order, Payment.order_id == Order.id).join(Customer, Order.customer_id == Customer.id).where(*conditions).order_by(Payment.created_at.desc()).limit(limit)).all()
    return {"source": source, "count": len(rows), "payments": [{"payment_id": p.external_payment_id, "order_id": o.external_order_id, "amount": p.amount, "currency": p.currency, "method": p.method, "status": p.status, "error_code": p.error_code, "timestamp": p.created_at.isoformat(), "customer_name": c.name} for p, o, c in rows]}


def settlement_variance(session: Session, source: str, settlement_id: str | None) -> dict:
    statement = select(Settlement).join(Merchant, Settlement.merchant_id == Merchant.id).where(source_condition(source))
    if settlement_id: statement = statement.where(Settlement.external_settlement_id == settlement_id)
    rows = session.scalars(statement.order_by(Settlement.created_at.desc()).limit(10 if settlement_id is None else 1)).all()
    return {"source": source, "found": bool(rows), "settlements": [{"settlement_id": item.external_settlement_id, "expected_amount": item.expected_amount, "actual_amount": item.actual_amount, "difference": item.actual_amount - item.expected_amount, "fees": item.fees, "adjustments": item.adjustments, "status": item.status} for item in rows]}


def reconciliation_issues(session: Session, source: str, issue_type: str | None, limit: int) -> dict:
    statement = select(ReconciliationIssue, Order, Payment, Customer).select_from(ReconciliationIssue).join(Merchant, ReconciliationIssue.merchant_id == Merchant.id).outerjoin(Order, ReconciliationIssue.order_id == Order.id).outerjoin(Payment, ReconciliationIssue.payment_id == Payment.id).outerjoin(Customer, Order.customer_id == Customer.id).where(source_condition(source))
    if issue_type: statement = statement.where(ReconciliationIssue.issue_type == issue_type)
    rows = session.execute(statement.order_by(ReconciliationIssue.created_at.desc()).limit(limit)).all()
    return {"source": source, "count": len(rows), "issues": [{"issue_type": issue.issue_type, "order_id": order.external_order_id if order else None, "payment_id": payment.external_payment_id if payment else None, "amount": payment.amount if payment else (order.amount if order else None), "customer_name": customer.name if customer else None, "description": issue.description, "status": issue.status} for issue, order, payment, customer in rows]}


def alerts(session: Session, source: str, severity: str | None, limit: int) -> dict:
    statement = select(Alert).join(Merchant, Alert.merchant_id == Merchant.id).where(source_condition(source))
    if severity: statement = statement.where(Alert.severity == severity)
    rows = session.scalars(statement.order_by(Alert.created_at.desc()).limit(limit)).all()
    return {"source": source, "count": len(rows), "alerts": [{"type": item.type, "severity": item.severity, "title": item.title, "description": item.description, "metric_value": item.metric_value, "baseline_value": item.baseline_value, "status": item.status} for item in rows]}


def payment_details(session: Session, source: str, payment_id: str) -> dict:
    payment = get_payment(session, payment_id, source)
    if payment is None: return {"source": source, "found": False, "payment": None}
    data = payment.model_dump(); data.pop("customer_email", None); data.pop("customer_phone", None)
    return {"source": source, "found": True, "payment": data}
