"""Evidence-only attempt selection, before the unchanged single-payment rules."""
from dataclasses import asdict, replace

from .reconciliation import reconcile
from .workflow_schemas import WorkflowEvidence
from .schemas import Classification as C, Result

WORKFLOW_VERSION = "1.0"


def reconcile_workflow(case_id: str, records: WorkflowEvidence) -> Result:
    facts = asdict(records)
    facts.pop("metadata")
    snapshot = records.snapshot
    def unresolved(reason):
        return Result(case_id,C.UNRESOLVED,reason,facts)
    orders = records.other_orders + ((snapshot.order,) if snapshot.order else ())
    attempts = records.other_attempts + ((snapshot.payment,) if snapshot.payment else ())
    for items in (orders,attempts):
        if len({item.id for item in items}) != len(items):
            return unresolved("Duplicate record identity requires snapshot deduplication/version evidence.")
    flags = dict(records.capture_flags)
    if len(flags) != len(records.capture_flags):
        return unresolved("Repeated capture flags require consistent source evidence.")
    if any(identifier not in {p.id for p in attempts} for identifier in flags):
        return unresolved("Capture flag references an unknown payment.")
    for p in attempts:
        if p.id in flags and flags[p.id] != (p.status in ('captured','refunded')):
            return unresolved("Payment status contradicts explicit capture evidence.")
    if snapshot.order is None:
        if records.other_orders or records.other_attempts:
            return unresolved("Target order identity is absent from a multi-record workflow.")
        prediction = reconcile(case_id,snapshot)
    else:
        relevant = [p for p in attempts if p.order_id == snapshot.order.id]
        if not relevant and attempts:
            return unresolved("Available payments reference other orders; amount is not identity evidence.")
        successful = [p for p in relevant if p.status in ('captured','refunded')]
        if len(successful)>1:
            return unresolved("Multiple captures require unsupported split-payment/allocation aggregation.")
        if successful:
            selected = successful[0]
            if any(p.status not in ('captured','refunded','failed') for p in relevant):
                return unresolved("Another attempt is not final; duplicate funding risk cannot be excluded.")
        elif len(relevant)>1:
            if any(p.status != 'failed' for p in relevant):
                return unresolved("Multiple non-final attempts have no definitive payment outcome.")
            selected = min(relevant,key=lambda p:p.id)
        else:
            selected = relevant[0] if relevant else None
        prediction = reconcile(case_id,replace(snapshot,payment=selected))
    facts["selected_evidence"] = prediction.evidence
    return Result(case_id,prediction.predicted_classification,prediction.reason,facts)
