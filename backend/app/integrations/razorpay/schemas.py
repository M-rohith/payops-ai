from datetime import datetime

from pydantic import BaseModel


class MappedOrder(BaseModel):
    external_order_id: str
    amount: int
    currency: str
    status: str
    created_at: datetime


class MappedPayment(BaseModel):
    external_payment_id: str
    external_order_id: str | None
    amount: int
    currency: str
    method: str
    status: str
    error_code: str | None
    error_description: str | None
    captured: bool
    created_at: datetime


class MappedRefund(BaseModel):
    external_refund_id: str
    external_payment_id: str
    amount: int
    status: str
    created_at: datetime


class MappedSettlement(BaseModel):
    external_settlement_id: str
    amount: int
    fees: int
    status: str
    settled_at: datetime | None
    created_at: datetime


class ConnectionStatus(BaseModel):
    configured: bool
    reachable: bool
    mode: str
    entities_returned: int = 0
    detail: str | None = None


class SyncSummary(BaseModel):
    orders_fetched: int = 0
    orders_created: int = 0
    orders_updated: int = 0
    payments_fetched: int = 0
    payments_created: int = 0
    payments_updated: int = 0
    refunds_fetched: int = 0
    refunds_created: int = 0
    refunds_updated: int = 0
    settlements_fetched: int = 0
    settlements_created: int = 0
    settlements_updated: int = 0
    settlements_unavailable: bool = False
