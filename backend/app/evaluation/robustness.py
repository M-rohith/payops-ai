"""Independent, hand-authored robustness cases; never imports specification generator."""
import random
from dataclasses import replace

from .schemas import Case, Classification as C, Evidence, OrderRecord, PaymentRecord, RefundRecord, SettlementRecord
from .workflow_schemas import WorkflowEvidence

ROBUSTNESS_SEED = 314159


def generate_robustness(seed: int = ROBUSTNESS_SEED) -> list[Case]:
    rng = random.Random(seed)
    cases = []
    ids = rng.sample(range(100000, 999999), 36)
    for variant in range(2):
        amount = (10000, 100)[variant]
        order = OrderRecord(f"ord-{rng.getrandbits(48):012x}", amount)
        payment = PaymentRecord(f"pay-{rng.getrandbits(48):012x}", order.id, amount)
        base = Evidence(order, payment)
        failed = replace(payment, id=payment.id + "-prior", status="failed")
        wrong = replace(order, id=order.id + "-other")
        def add(name, snapshot, expected, reason, **kwargs):
            index = len(cases)
            records = WorkflowEvidence(snapshot, **kwargs)
            cases.append(Case(f"B-{ids[index]}", records, expected, name + ": " + reason))
        add("failed_then_captured", replace(base, payment=failed), C.MATCHED,
            "Failed attempt must not override the later successful capture.", other_attempts=(payment,))
        add("similar_records", base, C.MATCHED, "Equal amounts do not join unrelated records.",
            other_orders=(wrong,), other_attempts=(replace(payment,id=payment.id+'-other',order_id=wrong.id), failed),
            metadata=(("timestamp", "2026-08-01T12:00:00Z"),))
        add("wrong_reference", replace(base,payment=replace(payment,order_id=wrong.id)), C.UNRESOLVED,
            "Payment belongs to the other order despite identical amounts.", other_orders=(wrong,))
        partial = amount * 3 // 10
        refund = RefundRecord("refund-a",payment.id,partial)
        add("partial_refund", replace(base,payment=replace(payment,refunded_amount=partial),refunds=(refund,)), C.MATCHED,
            "A processed partial refund is valid.")
        second = amount // 5
        add("multiple_refunds", replace(base,payment=replace(payment,refunded_amount=partial+second),
            refunds=(RefundRecord('refund-b',payment.id,second),refund)), C.MATCHED, "Sum both processed refunds exactly once.")
        add("refund_overflow_with_variance", replace(base,payment=replace(payment,refunded_amount=amount+1),
            refunds=(replace(refund,amount=amount+1),),settlement=SettlementRecord('settle',payment.id,amount,amount-1)),
            C.REFUND_MISMATCH, "Refund above capture is primary before downstream variance.")
        fee = (199,1)[variant]
        net = amount-fee
        add("documented_fees", replace(base,fees=fee,settlement_due=True,
            settlement=SettlementRecord('settle',payment.id,net,net)), C.MATCHED, "Documented integer fee explains gross/net difference.")
        adjustment = (-17,1)[variant]
        net += adjustment
        add("documented_adjustment", replace(base,fees=fee,adjustments=adjustment,settlement_due=True,
            settlement=SettlementRecord('settle',payment.id,net,net)), C.MATCHED, "Signed documented adjustment explains net.")
        add("unexplained_one_paise", replace(base,fees=fee,adjustments=adjustment,settlement_due=True,
            settlement=SettlementRecord('settle',payment.id,net,net+1)), C.SETTLEMENT_VARIANCE, "One unexplained paise is still variance.")
        add("optional_metadata", base, C.MATCHED, "No optional timestamp, method or description is required.",
            metadata=() if variant else (("description","human-readable label"),("method","card")))
        add("missing_relationship", replace(base,payment=replace(payment,order_id='')), C.UNRESOLVED,
            "Absent essential order reference cannot be guessed from amount.")
        add("contradictory_capture", base, C.UNRESOLVED, "Captured status conflicts with an explicit false capture flag.",
            capture_flags=((payment.id,False),))
        add("missing_payment_and_settlement", replace(base,order=replace(order,status='created'),payment=None,settlement_due=True),
            C.MISSING_PAYMENT, "No payment is primary; settlement cannot be reconciled yet.")
        add("failed_pending_amount", replace(base,order=replace(order,status='created'),payment=replace(failed,amount=amount-1)),
            C.PAYMENT_FAILED, "Failed attempt precedes order confirmation and amount matching.")
        boundary = (0,100_000_000)[variant]
        add("boundary_amount", replace(base,order=replace(order,amount=boundary),payment=replace(payment,amount=boundary)),
            C.UNRESOLVED if boundary==0 else C.MATCHED, "Zero-value capture is invalid; INR 10 lakh is a valid exact match.")
        add("amount_before_settlement", replace(base,payment=replace(payment,amount=amount-1),settlement_due=True),
            C.AMOUNT_MISMATCH, "One-paise capture mismatch precedes missing settlement.")
        split = amount // 2
        add("split_capture", replace(base,payment=replace(payment,amount=split)), C.MATCHED,
            "Two distinct partial captures sum to the paid order; requires multi-capture aggregation.",
            other_attempts=(replace(payment,id=payment.id+'-second',amount=amount-split),))
        add("duplicate_capture_identity", base, C.UNRESOLVED, "Conflicting snapshots share the same payment ID.",
            other_attempts=(replace(payment,amount=amount-1),))
    rng.shuffle(cases)
    return cases
