"""Read-only judge presentation for deterministic evaluation results."""
from functools import lru_cache

from fastapi import APIRouter

from app.evaluation.evaluator import run_benchmark

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

BENCHMARK_NAMES = {
    "specification": "Specification Benchmark",
    "robustness": "Robustness Suite",
}


def _money(value: int) -> str:
    return f"INR {value / 100:,.2f}"


def _evidence_summary(evidence: dict) -> list[str]:
    snapshot = evidence.get("snapshot", evidence)
    facts: list[str] = []
    for kind in ("order", "payment", "settlement"):
        record = snapshot.get(kind)
        if not record:
            facts.append(f"{kind.title()}: not present")
            continue
        identifier = record.get("id", "unknown")
        detail = [identifier]
        if "status" in record:
            detail.append(str(record["status"]))
        if "amount" in record:
            detail.append(_money(record["amount"]))
        elif "actual_amount" in record:
            detail.append(f"actual {_money(record['actual_amount'])}")
            detail.append(f"expected {_money(record['expected_amount'])}")
        facts.append(f"{kind.title()}: " + " · ".join(detail))
    refunds = snapshot.get("refunds", [])
    if refunds:
        processed = sum(r["amount"] for r in refunds if r.get("status") == "processed")
        facts.append(f"Refunds: {len(refunds)} record(s) · processed {_money(processed)}")
    other_attempts = evidence.get("other_attempts", [])
    if other_attempts:
        states = ", ".join(f"{p['id']} ({p['status']}, {_money(p['amount'])})" for p in other_attempts)
        facts.append(f"Other payment attempts: {states}")
    if snapshot.get("fees"):
        facts.append(f"Documented fees: {_money(snapshot['fees'])}")
    if snapshot.get("adjustments"):
        facts.append(f"Documented adjustments: {_money(snapshot['adjustments'])}")
    if not snapshot.get("orders_complete", True) or not snapshot.get("payments_complete", True):
        facts.append("Order or payment lookup is incomplete")
    if not snapshot.get("refunds_complete", True) or not snapshot.get("settlements_complete", True):
        facts.append("Refund or settlement lookup is incomplete")
    return facts


def _case(row: dict, benchmark: str) -> dict:
    expected = str(row["expected_classification"])
    predicted = str(row["predicted_classification"])
    if row["correct"] and predicted == "UNRESOLVED":
        display_status = "safe_unresolved"
    elif not row["correct"] and predicted == "UNRESOLVED":
        display_status = "incorrect_unresolved"
    elif row["correct"]:
        display_status = "correct"
    else:
        display_status = "mismatch"
    scenario = row["ground_truth_reason"].split(":", 1)[0] if benchmark == "robustness" else expected
    return {
        "case_id": row["case_id"], "benchmark": benchmark, "benchmark_name": BENCHMARK_NAMES[benchmark],
        "scenario": scenario, "expected": expected, "predicted": predicted,
        "correct": row["correct"], "display_status": display_status,
        "ground_truth_reason": row["ground_truth_reason"], "engine_reason": row["reason"],
        "evidence_summary": _evidence_summary(row["evidence"]),
    }


def _benchmark(key: str) -> dict:
    report = run_benchmark(benchmark=key)
    metadata, metrics = report["metadata"], report["metrics"]
    cases = [_case(row, key) for row in report["case_results"]]
    scenario_distribution: dict[str, int] = {}
    for case in cases:
        scenario_distribution[case["scenario"]] = scenario_distribution.get(case["scenario"], 0) + 1
    return {
        "key": key, "name": BENCHMARK_NAMES[key], "seed": metadata["seed"],
        "dataset_version": metadata["dataset_version"], "dataset_sha256": metadata["dataset_sha256"],
        "synthetic": metadata["synthetic"], "metrics": metrics,
        "runtime_seconds": report["runtime_seconds"],
        "throughput_cases_per_second": report["throughput_cases_per_second"],
        "scenario_distribution": scenario_distribution, "cases": cases,
        "known_mismatches": [case for case in cases if not case["correct"]],
    }


@lru_cache(maxsize=1)
def evaluation_payload() -> dict:
    return {
        "generated_from": "cached deterministic in-memory evaluation",
        "disclaimer": "Synthetic benchmark · developer-authored · not production validation",
        "benchmarks": [_benchmark("specification"), _benchmark("robustness")],
        "known_limitation": {
            "title": "Safe failure cases",
            "summary": "2 robustness cases expected MATCHED but returned UNRESOLVED.",
            "detail": "Both involve split-capture aggregation, which the current reconciliation engine does not support. The engine refused to guess rather than incorrectly declaring a match or exception.",
        },
    }


@router.get("")
def evaluation() -> dict:
    return evaluation_payload()
