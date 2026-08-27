from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.dashboard import get_dashboard_summary, get_payment_method_breakdown, get_volume_series
from app.database import get_db
from app.models import Alert, Merchant
from app.schemas.dashboard import AlertResponse, DashboardSummary, PaymentMethodMetric, VolumePoint

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


TimeRange = Literal["1D", "7D", "30D"]
DataSource = Literal["demo", "razorpay", "all"]


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(source: DataSource = Query("all"), time_range: TimeRange = Query("30D"), db: Session = Depends(get_db)) -> DashboardSummary:
    return get_dashboard_summary(db, source, time_range)


@router.get("/volume", response_model=list[VolumePoint])
def volume(source: DataSource = Query("all"), time_range: TimeRange = Query("7D"), db: Session = Depends(get_db)) -> list[VolumePoint]:
    return get_volume_series(db, source, time_range)


@router.get("/payment-methods", response_model=list[PaymentMethodMetric])
def payment_methods(source: DataSource = Query("all"), time_range: TimeRange = Query("30D"), db: Session = Depends(get_db)) -> list[PaymentMethodMetric]:
    return get_payment_method_breakdown(db, source, time_range)


@router.get("/issues", response_model=list[AlertResponse])
def recent_issues(source: DataSource = Query("all"), limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)) -> list[Alert]:
    statement = select(Alert).join(Merchant, Alert.merchant_id == Merchant.id).where(Alert.status == "open")
    if source != "all": statement = statement.where(Merchant.source == source)
    return list(db.scalars(statement.order_by(Alert.created_at.desc()).limit(limit)).all())
