from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from app.models import Alert, Merchant, Payment, Refund, Settlement
from app.schemas.dashboard import DashboardSummary, PaymentMethodMetric, VolumePoint

RANGE_DAYS = {"1D": 1, "7D": 7, "30D": 30}
SOURCES = {"demo", "razorpay", "all"}


def range_start(time_range: str, now: datetime | None = None) -> datetime:
    if time_range not in RANGE_DAYS:
        raise ValueError("time_range must be one of 1D, 7D, or 30D")
    return (now or datetime.now(UTC)) - timedelta(days=RANGE_DAYS[time_range])


def source_condition(source: str):
    if source not in SOURCES: raise ValueError("source must be one of demo, razorpay, or all")
    return true() if source == "all" else Merchant.source == source


def normalized_timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def get_dashboard_summary(session: Session, source: str = "all", time_range: str = "30D", now: datetime | None = None) -> DashboardSummary:
    start = range_start(time_range, now)
    payment_base = lambda expression: select(expression).select_from(Payment).join(Merchant, Payment.merchant_id == Merchant.id).where(source_condition(source), Payment.created_at >= start)
    terminal = session.scalar(payment_base(func.count(Payment.id)).where(Payment.status.in_(["captured", "refunded", "failed"]))) or 0
    successful = session.scalar(payment_base(func.count(Payment.id)).where(Payment.status.in_(["captured", "refunded"]))) or 0
    volume = session.scalar(payment_base(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status.in_(["captured", "refunded"]))) or 0
    failed = session.scalar(payment_base(func.count(Payment.id)).where(Payment.status == "failed")) or 0
    refunds = session.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).select_from(Refund).join(Merchant, Refund.merchant_id == Merchant.id).where(source_condition(source), Refund.created_at >= start, Refund.status == "processed")) or 0
    settlements = session.scalar(select(func.coalesce(func.sum(Settlement.actual_amount), 0)).select_from(Settlement).join(Merchant, Settlement.merchant_id == Merchant.id).where(source_condition(source), Settlement.created_at >= start, Settlement.status == "processed")) or 0
    alerts = session.scalar(select(func.count(Alert.id)).select_from(Alert).join(Merchant, Alert.merchant_id == Merchant.id).where(source_condition(source), Alert.status == "open")) or 0
    return DashboardSummary(payment_volume=int(volume), success_rate=round(successful / terminal * 100, 1) if terminal else 0.0, failed_payments=failed, refund_amount=int(refunds), settlement_amount=int(settlements), open_alerts=alerts)


def get_volume_series(session: Session, source: str, time_range: str, now: datetime | None = None) -> list[VolumePoint]:
    start = range_start(time_range, now); end = now or datetime.now(UTC); hourly = time_range == "1D"
    payments = session.scalars(select(Payment).join(Merchant, Payment.merchant_id == Merchant.id).where(source_condition(source), Payment.created_at >= start, Payment.status.in_(["captured", "refunded"])).order_by(Payment.created_at)).all()
    buckets: dict[datetime, list[int]] = defaultdict(lambda: [0, 0])
    for payment in payments:
        created_at = normalized_timestamp(payment.created_at)
        stamp = created_at.replace(minute=0, second=0, microsecond=0) if hourly else created_at.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets[stamp][0] += payment.amount; buckets[stamp][1] += 1
    step = timedelta(hours=1) if hourly else timedelta(days=1)
    cursor = start.replace(minute=0, second=0, microsecond=0) if hourly else start.replace(hour=0, minute=0, second=0, microsecond=0)
    points = []
    while cursor <= end:
        amount, count = buckets[cursor]; points.append(VolumePoint(timestamp=cursor, amount=amount, payment_count=count)); cursor += step
    return points


def get_payment_method_breakdown(session: Session, source: str, time_range: str, now: datetime | None = None) -> list[PaymentMethodMetric]:
    start = range_start(time_range, now)
    rows = session.execute(select(Payment.method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)).select_from(Payment).join(Merchant, Payment.merchant_id == Merchant.id).where(source_condition(source), Payment.created_at >= start).group_by(Payment.method).order_by(Payment.method)).all()
    return [PaymentMethodMetric(method=method, payment_count=count, amount=int(amount)) for method, count, amount in rows]
