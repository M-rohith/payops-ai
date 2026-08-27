from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Merchant, Order, Payment, ReconciliationIssue, Settlement
from app.schemas.dashboard import AlertResponse
from app.schemas.operations import PaymentDetail, PaymentListResponse, ReconciliationIssueResponse, SettlementResponse
from app.services.payments import get_payment, list_payments

router = APIRouter(prefix="/api")


@router.get("/payments", response_model=PaymentListResponse, tags=["payments"])
def payments(source: Literal["demo", "razorpay", "all"] = "all", status: Literal["authorized", "captured", "failed", "refunded"] | None = None, method: Literal["upi", "card", "netbanking", "wallet"] | None = None, search: str | None = Query(None, max_length=100), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)) -> PaymentListResponse:
    return list_payments(db, source, status, method, search, limit, offset)


@router.get("/payments/{payment_identifier}", response_model=PaymentDetail, tags=["payments"])
def payment_detail(payment_identifier: str, source: Literal["demo", "razorpay", "all"] = "all", db: Session = Depends(get_db)) -> PaymentDetail:
    payment = get_payment(db, payment_identifier, source)
    if payment is None: raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/settlements", response_model=list[SettlementResponse], tags=["settlements"])
def settlements(source: Literal["demo", "razorpay", "all"] = "all", db: Session = Depends(get_db)) -> list[SettlementResponse]:
    statement = select(Settlement).join(Merchant, Settlement.merchant_id == Merchant.id)
    if source != "all": statement = statement.where(Merchant.source == source)
    rows = db.scalars(statement.order_by(Settlement.created_at.desc())).all()
    return [SettlementResponse(id=s.id, external_settlement_id=s.external_settlement_id, expected_amount=s.expected_amount, actual_amount=s.actual_amount, difference=s.actual_amount - s.expected_amount, fees=s.fees, adjustments=s.adjustments, status=s.status, settled_at=s.settled_at, created_at=s.created_at) for s in rows]


@router.get("/reconciliation/issues", response_model=list[ReconciliationIssueResponse], tags=["reconciliation"])
def reconciliation_issues(source: Literal["demo", "razorpay", "all"] = "all", db: Session = Depends(get_db)) -> list[ReconciliationIssueResponse]:
    statement = select(ReconciliationIssue, Order, Payment).select_from(ReconciliationIssue).join(Merchant, ReconciliationIssue.merchant_id == Merchant.id).outerjoin(Order, ReconciliationIssue.order_id == Order.id).outerjoin(Payment, ReconciliationIssue.payment_id == Payment.id)
    if source != "all": statement = statement.where(Merchant.source == source)
    rows = db.execute(statement.order_by(ReconciliationIssue.created_at.desc())).all()
    return [ReconciliationIssueResponse(id=i.id, issue_type=i.issue_type, description=i.description, status=i.status, order_id=i.order_id, external_order_id=o.external_order_id if o else None, payment_id=i.payment_id, external_payment_id=p.external_payment_id if p else None, amount=p.amount if p else (o.amount if o else None), created_at=i.created_at) for i, o, p in rows]


@router.get("/alerts", response_model=list[AlertResponse], tags=["alerts"])
def alerts(source: Literal["demo", "razorpay", "all"] = "all", status: Literal["open", "resolved"] | None = None, db: Session = Depends(get_db)) -> list[Alert]:
    statement = select(Alert).join(Merchant, Alert.merchant_id == Merchant.id)
    if source != "all": statement = statement.where(Merchant.source == source)
    if status: statement = statement.where(Alert.status == status)
    return list(db.scalars(statement.order_by(Alert.created_at.desc())).all())
