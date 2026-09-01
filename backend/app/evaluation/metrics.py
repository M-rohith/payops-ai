"""Metrics use explicit denominators; undefined ratios are None, not perfect scores."""
from collections import Counter

from .schemas import Classification as C, status_for


def divide(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def calculate(pairs: list[tuple[C, C]]) -> dict:
    actual_exceptions = sum(status_for(e) == "exception" for e, _ in pairs)
    predicted_exceptions = sum(status_for(p) == "exception" for _, p in pairs)
    tp = sum(status_for(e) == status_for(p) == "exception" for e, p in pairs)
    fp = predicted_exceptions - tp
    missed = actual_exceptions - tp
    exact_exceptions = sum(e == p and status_for(e) == "exception" for e, p in pairs)
    correct = sum(e == p for e, p in pairs)
    clean = sum(e == C.MATCHED for e, _ in pairs)
    correctly_clean = sum(e == p == C.MATCHED for e, p in pairs)
    expected_unresolved = sum(e == C.UNRESOLVED for e, _ in pairs)
    unresolved = sum(p == C.UNRESOLVED for _, p in pairs)
    correctly_unresolved = sum(e == p == C.UNRESOLVED for e, p in pairs)
    matrix = Counter((str(e), str(p)) for e, p in pairs)
    return {
        "cases_processed": len(pairs), "total_correct": correct, "total_incorrect": len(pairs) - correct,
        "actual_exception_count": actual_exceptions, "predicted_exception_count": predicted_exceptions,
        "true_exception_detections": tp, "false_positive_exceptions": fp, "missed_exceptions": missed,
        "misclassified_exception_types": tp - exact_exceptions,
        "actual_clean_count": clean, "correctly_matched": correctly_clean,
        "clean_match_recall": divide(correctly_clean, clean),
        "exception_precision": divide(tp, predicted_exceptions),
        "exception_recall": divide(tp, actual_exceptions),
        "exception_f1": divide(2 * tp, 2 * tp + fp + missed),
        "exception_classification_accuracy": divide(exact_exceptions, actual_exceptions),
        "overall_correctness": divide(correct, len(pairs)),
        "unresolved_count": unresolved, "unresolved_rate": divide(unresolved, len(pairs)),
        "expected_unresolved": expected_unresolved, "correctly_unresolved": correctly_unresolved,
        "incorrectly_unresolved": unresolved - correctly_unresolved,
        "unresolved_precision": divide(correctly_unresolved, unresolved),
        "unresolved_recall": divide(correctly_unresolved, expected_unresolved),
        "confusion_matrix": {e: {p: matrix[e, p] for p in sorted({str(p) for _, p in pairs})} for e in sorted({str(e) for e, _ in pairs})},
    }
