"""Run with python -m app.evaluation.run [--seed 42] [--json]."""
import argparse
import json
from pathlib import Path

from .evaluator import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--benchmark", choices=("specification", "robustness"), default="specification")
    parser.add_argument("--json", action="store_true", help="Write ignored generated/evaluation/latest.json (A) or robustness.json (B)")
    args = parser.parse_args()
    report = run_benchmark(args.seed, benchmark=args.benchmark)
    metrics = report["metrics"]
    print("PAYOPS AI RECONCILIATION BENCHMARK\n")
    print(f"Benchmark: {args.benchmark}\nSeed: {report['metadata']['seed']}\nCases: {metrics['cases_processed']}\nRESULTS")
    for key, value in metrics.items():
        if key == "confusion_matrix":
            continue
        shown = "N/A" if value is None else f"{value:.2%}" if isinstance(value, float) else str(value)
        print(f"{key}: {shown}")
    print(f"Runtime: {report['runtime_seconds']:.6f} s")
    print(f"Throughput: {report['throughput_cases_per_second']:.1f} cases/sec (local in-memory benchmark)")
    print("ERRORS")
    if not report["error_cases"]:
        print("No classification mismatches occurred.")
    for row in report["error_cases"]:
        print(f"{row['case_id']}: expected {row['expected_classification']}; predicted {row['predicted_classification']}; {row['reason']}")
    print("UNRESOLVED CASES (including expected safe failures)")
    for row in report["unresolved_cases"]:
        print(f"{row['case_id']}: expected {row['expected_classification']}; {row['reason']}")
    if args.json:
        filename = "latest.json" if args.benchmark == "specification" else "robustness.json"
        path = Path(__file__).resolve().parents[2] / "generated" / "evaluation" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON: {path}")


if __name__ == "__main__":
    main()
