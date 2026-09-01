"""Deterministic single-primary-explanation rules; never accepts ground truth."""
from dataclasses import asdict

from .schemas import Classification as C, Evidence, Result

ENGINE_VERSION = "1.0"


def reconcile(case_id: str, records: Evidence) -> Result:
    facts = asdict(records)

    def result(label: C, reason: str) -> Result:
        return Result(case_id, label, reason, facts)

    order, payment = records.order, records.payment
    if not records.orders_complete or not records.payments_complete:
        return result(C.UNRESOLVED, "Order/payment snapshot is incomplete.")
    if order is None and payment is None:
        return result(C.UNRESOLVED, "Neither an order nor a payment is present.")
    if payment is None:
        if records.refunds or records.settlement:
            return result(C.UNRESOLVED, "Downstream financial records exist without the payment needed to validate them.")
        return result(C.MISSING_PAYMENT, "Complete payment lookup has no corresponding payment.")
    if order is None:
        return result(C.MISSING_ORDER, "Payment references an order absent from the complete lookup.")
    if payment.order_id != order.id or payment.currency != order.currency:
        return result(C.UNRESOLVED, "Order reference or currency contradicts the payment; no safe comparison is possible.")
    if min(order.amount, payment.amount) <= 0 or payment.refunded_amount < 0 or records.fees < 0:
        return result(C.UNRESOLVED, "Invalid monetary evidence.")
    if payment.status == "failed":
        if order.status == "paid" or records.refunds or records.settlement or payment.refunded_amount:
            return result(C.UNRESOLVED, "Failed payment contradicts paid order or downstream financial evidence.")
        return result(C.PAYMENT_FAILED, "Linked payment attempt has a terminal failed status.")
    if payment.status not in ("captured", "refunded"):
        return result(C.UNRESOLVED, "Payment has no supported final captured/failed outcome.")
    if payment.amount != order.amount:
        return result(C.AMOUNT_MISMATCH, "Captured amount differs from the order amount.")
    if order.status in ("created", "attempted", "pending"):
        return result(C.ORDER_NOT_CONFIRMED, "Payment was captured but order is not confirmed paid.")
    if order.status != "paid":
        return result(C.UNRESOLVED, "Order status contradicts capture or is unsupported.")
    if not records.refunds_complete:
        return result(C.UNRESOLVED, "Incomplete refund ledger prevents reliable reconciliation.")
    if len({r.id for r in records.refunds}) != len(records.refunds):
        return result(C.UNRESOLVED, "Duplicate refund identifiers prevent reliable summation.")
    if any(r.payment_id != payment.id or r.status not in ("processed", "failed", "pending") for r in records.refunds):
        return result(C.UNRESOLVED, "Refund reference/status is unsupported or contradictory.")
    if any(r.status == "pending" for r in records.refunds):
        return result(C.UNRESOLVED, "Refund outcome is still pending.")
    total = sum(r.amount for r in records.refunds if r.status == "processed")
    facts["processed_refund_total"] = total
    if any(r.amount <= 0 for r in records.refunds) or total > payment.amount or total != payment.refunded_amount or (payment.status == "refunded" and total == 0):
        return result(C.REFUND_MISMATCH, "Processed refund total/status disagrees with captured funds or payment refund summary.")
    if records.settlement_due is None or not records.settlements_complete:
        return result(C.UNRESOLVED, "Settlement deadline or complete settlement evidence is unavailable.")
    settlement = records.settlement
    if settlement is None:
        if records.settlement_due:
            return result(C.MISSING_SETTLEMENT, "Settlement is due but no allocation exists in the complete lookup.")
        return result(C.MATCHED, "Order/payment/refunds agree; settlement is not yet due.")
    if settlement.payment_id != payment.id or settlement.status != "processed":
        return result(C.UNRESOLVED, "Settlement reference is contradictory or settlement is not final.")
    net = payment.amount - total - records.fees + records.adjustments
    facts["calculated_net_amount"] = net
    facts["settlement_difference"] = settlement.actual_amount - settlement.expected_amount
    if net < 0 or settlement.actual_amount < 0:
        return result(C.UNRESOLVED, "Negative settlement requires an unsupported carry-forward/debit allocation.")
    if settlement.expected_amount != net:
        return result(C.UNRESOLVED, "Declared expected net conflicts with the supporting ledger calculation.")
    if settlement.actual_amount != net:
        return result(C.SETTLEMENT_VARIANCE, "Actual settlement differs from independently calculated expected net.")
    return result(C.MATCHED, "Order, capture, processed refunds and net settlement agree.")
