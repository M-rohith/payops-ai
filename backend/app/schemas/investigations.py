from typing import Literal

from pydantic import BaseModel, Field


class InvestigationMetric(BaseModel):
    label: str
    value: int | float
    format: Literal["count", "money", "percent", "percentage_points"]


class InvestigationItem(BaseModel):
    id: str
    type: Literal["payment_failure_spike", "settlement_variance", "reconciliation_issue", "alert"]
    title: str
    severity: Literal["high", "medium", "low"]
    source: Literal["demo", "razorpay"]
    summary: str
    metrics: list[InvestigationMetric]
    evidence: list[str]
    financial_impact: int = Field(ge=0)
    suggested_question: str
