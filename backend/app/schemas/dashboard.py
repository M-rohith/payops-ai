from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DashboardSummary(BaseModel):
    payment_volume: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)
    failed_payments: int = Field(ge=0)
    refund_amount: int = Field(ge=0)
    settlement_amount: int = Field(ge=0)
    open_alerts: int = Field(ge=0)


class VolumePoint(BaseModel):
    timestamp: datetime
    amount: int
    payment_count: int


class PaymentMethodMetric(BaseModel):
    method: str
    payment_count: int
    amount: int


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    severity: str
    title: str
    description: str
    metric_value: float | None
    baseline_value: float | None
    status: str
    created_at: datetime
