"""Balanced, labelled scenario construction independent of engine predictions."""
import random
from dataclasses import replace

from .schemas import Case, Classification as C, Evidence, OrderRecord, PaymentRecord, RefundRecord, SettlementRecord

DATASET_VERSION = "1.0"


def generate(seed: int = 42, per_category: int = 12) -> list[Case]:
    if per_category < 1:
        raise ValueError("per_category must be positive")
    rng = random.Random(seed)
    cases = []
    for label in C:
        for variant in range(per_category):
            index = len(cases) + 1
            amount = rng.randrange(20_000, 500_001, 100)
            order = OrderRecord(f"order_synthetic_{index}", amount)
            payment = PaymentRecord(f"pay_synthetic_{index}", order.id, amount)
            refunded = amount // 4 if variant % 3 == 0 else 0
            refunds = (RefundRecord(f"rfnd_synthetic_{index}", payment.id, refunded),) if refunded else ()
            payment = replace(payment, refunded_amount=refunded)
            fees = amount * 2 // 100
            adjustments = (-100, 0, 100)[variant % 3]
            net = amount - refunded - fees + adjustments
            settlement = SettlementRecord(f"setl_synthetic_{index}", payment.id, net, net)
            records = Evidence(order, payment, refunds, settlement, settlement_due=True, fees=fees, adjustments=adjustments)
            reason = "Paid order and captured payment agree; processed refunds and net settlement reconcile."
            if label == C.PAYMENT_FAILED:
                records = Evidence(replace(order, status="failed"), replace(payment, status="failed", refunded_amount=0))
                reason = "The linked attempt failed; no captured funds, refund or settlement exists."
            elif label == C.AMOUNT_MISMATCH:
                records = replace(records, payment=replace(payment, amount=amount + (100 if variant % 2 else -100)))
                reason = "The captured amount differs from its order by 100 paise."
            elif label == C.ORDER_NOT_CONFIRMED:
                records = replace(records, order=replace(order, status="created" if variant % 2 else "attempted"))
                reason = "Capture succeeded but the linked order has not been marked paid."
            elif label == C.MISSING_PAYMENT:
                records = Evidence(replace(order, status="created"), None)
                reason = "Complete payment lookup for an order returned no attempt."
            elif label == C.MISSING_ORDER:
                records = replace(records, order=None)
                reason = "Capture references an order absent from a complete order lookup."
            elif label == C.REFUND_MISMATCH:
                if variant % 3 == 0:
                    records = replace(records, refunds=(RefundRecord(f"rfnd_synthetic_{index}", payment.id, amount + 100),))
                    reason = "Processed refund exceeds captured payment."
                elif variant % 3 == 1:
                    records = replace(records, payment=replace(payment, refunded_amount=100), refunds=())
                    reason = "Payment reports a refund but complete refund ledger has none."
                else:
                    records = replace(records, payment=replace(payment, refunded_amount=100), refunds=(RefundRecord(f"rfnd_synthetic_{index}", payment.id, 100, "failed"),))
                    reason = "A failed refund is incorrectly counted as refunded by the payment summary."
            elif label == C.MISSING_SETTLEMENT:
                records = replace(records, settlement=None)
                reason = "Settlement is due and the complete settlement lookup contains no allocation."
            elif label == C.SETTLEMENT_VARIANCE:
                delta = rng.choice([-107_500, -100, 100, 2_000])
                records = replace(records, settlement=replace(settlement, actual_amount=max(0, net + delta)))
                reason = "Recorded actual settlement differs from expected net after refunds, fees and signed adjustments."
            elif label == C.UNRESOLVED:
                choices = [
                    (replace(records, payment=None, payments_complete=False), "Payment lookup is incomplete; absence cannot prove a missing payment."),
                    (replace(records, order=None, orders_complete=False), "Order lookup is incomplete; absence cannot prove a missing order."),
                    (replace(records, settlement=None, settlement_due=None), "Settlement eligibility/deadline is unknown."),
                    (replace(records, payment=replace(payment, currency="USD")), "Order and payment currencies contradict; no FX evidence exists."),
                    (replace(records, refunds_complete=False), "Refund ledger is incomplete, so net settlement cannot be established."),
                    (Evidence(replace(order, status="attempted"), replace(payment, status="authorized", refunded_amount=0)), "Authorization has not reached a final capture/failure outcome."),
                    (replace(records, payment=replace(payment, order_id="order_unknown")), "Provided order does not match the payment reference."),
                    (replace(records, settlement=None, settlements_complete=False), "Settlement lookup is incomplete; a missing allocation cannot be established."),
                ]
                records, reason = choices[variant % len(choices)]
            cases.append(Case(f"CASE-{index:04d}", records, label, reason))
    rng.shuffle(cases)
    return cases
