from datetime import datetime

from pydantic import BaseModel


class PaymentListItem(BaseModel):
    id: int
    external_payment_id: str
    external_order_id: str
    customer_name: str
    source: str
    amount: int
    currency: str
    method: str
    status: str
    error_code: str | None
    error_description: str | None
    captured: bool
    created_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentListItem]
    total: int
    limit: int
    offset: int


class PaymentDetail(PaymentListItem):
    customer_email: str
    customer_phone: str | None
    order_status: str


class SettlementResponse(BaseModel):
    id: int
    external_settlement_id: str
    expected_amount: int
    actual_amount: int
    difference: int
    fees: int
    adjustments: int
    status: str
    settled_at: datetime | None
    created_at: datetime


class ReconciliationIssueResponse(BaseModel):
    id: int
    issue_type: str
    description: str
    status: str
    order_id: int | None
    external_order_id: str | None
    payment_id: int | None
    external_payment_id: str | None
    amount: int | None
    created_at: datetime
