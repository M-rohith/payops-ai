"""Immutable input records and separately held ground truth. Money is integer paise."""
from dataclasses import dataclass
from enum import StrEnum


class Classification(StrEnum):
    MATCHED = "MATCHED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    ORDER_NOT_CONFIRMED = "ORDER_NOT_CONFIRMED"
    MISSING_PAYMENT = "MISSING_PAYMENT"
    MISSING_ORDER = "MISSING_ORDER"
    REFUND_MISMATCH = "REFUND_MISMATCH"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    SETTLEMENT_VARIANCE = "SETTLEMENT_VARIANCE"
    UNRESOLVED = "UNRESOLVED"


def status_for(label: Classification) -> str:
    return "matched" if label == Classification.MATCHED else "unresolved" if label == Classification.UNRESOLVED else "exception"


@dataclass(frozen=True)
class OrderRecord:
    id: str
    amount: int
    status: str = "paid"
    currency: str = "INR"


@dataclass(frozen=True)
class PaymentRecord:
    id: str
    order_id: str
    amount: int
    status: str = "captured"
    currency: str = "INR"
    refunded_amount: int = 0


@dataclass(frozen=True)
class RefundRecord:
    id: str
    payment_id: str
    amount: int
    status: str = "processed"


@dataclass(frozen=True)
class SettlementRecord:
    id: str
    payment_id: str
    expected_amount: int
    actual_amount: int
    status: str = "processed"


@dataclass(frozen=True)
class Evidence:
    order: OrderRecord | None
    payment: PaymentRecord | None
    refunds: tuple[RefundRecord, ...] = ()
    settlement: SettlementRecord | None = None
    # Explicit snapshot guarantees, not inferred from absence of a record.
    orders_complete: bool = True
    payments_complete: bool = True
    refunds_complete: bool = True
    settlements_complete: bool = True
    settlement_due: bool | None = False
    fees: int = 0
    adjustments: int = 0


@dataclass(frozen=True)
class Case:
    case_id: str
    records: Evidence
    expected_classification: Classification
    ground_truth_reason: str

    @property
    def expected_status(self) -> str:
        return status_for(self.expected_classification)


@dataclass(frozen=True)
class Result:
    case_id: str
    predicted_classification: Classification
    reason: str
    evidence: dict

    @property
    def predicted_status(self) -> str:
        return status_for(self.predicted_classification)
