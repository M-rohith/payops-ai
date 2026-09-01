from dataclasses import dataclass

from .schemas import Evidence, OrderRecord, PaymentRecord


@dataclass(frozen=True)
class WorkflowEvidence:
    snapshot: Evidence
    other_orders: tuple[OrderRecord, ...] = ()
    other_attempts: tuple[PaymentRecord, ...] = ()
    capture_flags: tuple[tuple[str, bool], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()
