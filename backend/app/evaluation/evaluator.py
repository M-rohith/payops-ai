import hashlib
import json
import time
from collections import Counter
from dataclasses import asdict

from .generator import DATASET_VERSION, generate
from .metrics import calculate
from .reconciliation import ENGINE_VERSION, reconcile
from .schemas import Case


def evaluate(cases: list[Case], predictor=reconcile) -> dict:
    if len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Case identifiers must be unique")
    rows = []
    pairs = []
    for case in cases:
        prediction = predictor(case.case_id, case.records)
        pairs.append((case.expected_classification, prediction.predicted_classification))
        rows.append({
            "case_id": case.case_id, "expected_classification": case.expected_classification,
            "expected_status": case.expected_status, "ground_truth_reason": case.ground_truth_reason,
            "predicted_classification": prediction.predicted_classification,
            "predicted_status": prediction.predicted_status,
            "correct": case.expected_classification == prediction.predicted_classification,
            "reason": prediction.reason, "evidence": prediction.evidence,
        })
    return {"metrics": calculate(pairs), "case_results": rows,
            "error_cases": [r for r in rows if not r["correct"]],
            "unresolved_cases": [r for r in rows if r["predicted_status"] == "unresolved"]}


def run_benchmark(seed: int | None = None, per_category: int = 12, benchmark: str = "specification") -> dict:
    if benchmark == "robustness":
        from .robustness import generate_robustness, ROBUSTNESS_SEED
        from .workflow import reconcile_workflow, WORKFLOW_VERSION
    started = time.perf_counter()
    if benchmark == "specification":
        seed = 42 if seed is None else seed
        cases = generate(seed, per_category)
        predictor = reconcile
        dataset_version, engine_version = DATASET_VERSION, ENGINE_VERSION
    elif benchmark == "robustness":
        seed = ROBUSTNESS_SEED if seed is None else seed
        cases = generate_robustness(seed)
        predictor = reconcile_workflow
        dataset_version, engine_version = "B-1.0", ENGINE_VERSION + "+workflow-" + WORKFLOW_VERSION
    else:
        raise ValueError("Unknown benchmark")
    payload = json.dumps([asdict(c) for c in cases], sort_keys=True, separators=(",", ":"))
    report = evaluate(cases, predictor)
    report["metadata"] = {
        "benchmark": benchmark,
        "seed": seed, "dataset_version": dataset_version, "engine_version": engine_version,
        "dataset_sha256": hashlib.sha256(payload.encode()).hexdigest(), "synthetic": True,
        "scenario_distribution": dict(sorted(Counter(c.expected_classification for c in cases).items())),
        "runtime_scope": "in-memory generation, dataset hashing, reconciliation, metrics and report assembly; excludes imports, console and file I/O",
    }
    elapsed = time.perf_counter() - started
    report["runtime_seconds"] = elapsed
    report["throughput_cases_per_second"] = len(cases) / elapsed if elapsed > 0 else None
    return report
