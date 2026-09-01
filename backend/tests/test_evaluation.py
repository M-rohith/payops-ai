import json
import subprocess
import sys
from dataclasses import asdict, replace

import pytest
from sqlalchemy import event, select

from app.evaluation.evaluator import evaluate, run_benchmark
from app.evaluation.generator import generate
from app.evaluation.metrics import calculate
from app.evaluation.reconciliation import reconcile
from app.evaluation.schemas import Classification as C, Evidence


def test_deterministic_balanced_dataset():
    cases = generate()
    assert cases == generate(42)
    assert cases != generate(43)
    assert len(cases) == len({c.case_id for c in cases}) == 120
    assert {c.expected_classification for c in cases} == set(C)
    assert all(sum(c.expected_classification == label for c in cases) == 12 for label in C)
    with pytest.raises(ValueError):
        generate(per_category=0)


@pytest.mark.parametrize("label", list(C))
def test_every_scenario_and_variant(label):
    for case in generate():
        if case.expected_classification == label:
            actual = reconcile(case.case_id, case.records)
            assert actual.predicted_classification == label, (case, actual)
            assert actual.predicted_status == case.expected_status
            assert actual.evidence and actual.reason


def test_ground_truth_cannot_influence_engine():
    case = next(c for c in generate() if c.expected_classification == C.MATCHED)
    poisoned = replace(case, expected_classification=C.PAYMENT_FAILED, ground_truth_reason="wrong label")
    report = evaluate([poisoned])
    assert report["metrics"]["total_incorrect"] == 1
    assert report["error_cases"][0]["predicted_classification"] == C.MATCHED
    with pytest.raises(ValueError):
        evaluate([case, case])


def test_independent_metric_confusion_fixture():
    pairs = [(C.MATCHED,C.MATCHED), (C.MATCHED,C.PAYMENT_FAILED),
             (C.PAYMENT_FAILED,C.PAYMENT_FAILED), (C.AMOUNT_MISMATCH,C.PAYMENT_FAILED),
             (C.MISSING_ORDER,C.MATCHED), (C.REFUND_MISMATCH,C.UNRESOLVED),
             (C.UNRESOLVED,C.UNRESOLVED), (C.UNRESOLVED,C.MISSING_ORDER)]
    m = calculate(pairs)
    assert m["exception_precision"] == m["exception_recall"] == m["exception_f1"] == 0.5
    assert m["exception_classification_accuracy"] == 0.25
    assert m["clean_match_recall"] == 0.5
    assert m["overall_correctness"] == 3/8
    assert m["false_positive_exceptions"] == m["missed_exceptions"] == 2
    assert m["misclassified_exception_types"] == 1
    assert m["expected_unresolved"] == 2
    assert m["correctly_unresolved"] == m["incorrectly_unresolved"] == 1


def test_metric_zero_denominators():
    empty = calculate([])
    assert empty["exception_precision"] is None
    assert empty["exception_recall"] is None
    assert empty["exception_f1"] is None
    assert empty["overall_correctness"] is None
    no_detection = calculate([(C.PAYMENT_FAILED,C.MATCHED)])
    assert no_detection["exception_precision"] is None
    assert no_detection["exception_recall"] == no_detection["exception_f1"] == 0
    false_alarm = calculate([(C.MATCHED,C.PAYMENT_FAILED)])
    assert false_alarm["exception_recall"] is None
    assert false_alarm["exception_precision"] == false_alarm["exception_f1"] == 0


def test_report_reproducibility_and_runtime():
    first, second = run_benchmark(), run_benchmark()
    for report in (first, second):
        elapsed = report.pop("runtime_seconds")
        throughput = report.pop("throughput_cases_per_second")
        assert elapsed > 0 and throughput == pytest.approx(120 / elapsed)
        assert len(report["unresolved_cases"]) == 12
        assert json.loads(json.dumps(report))["metadata"]["synthetic"] is True
    assert first == second
    assert json.loads(json.dumps(first)) == json.loads(json.dumps(second))


def test_cli_reports_expected_unresolved_and_no_mismatches():
    result = subprocess.run([sys.executable, "-m", "app.evaluation.run", "--seed", "42"],
                            check=True, capture_output=True, text=True)
    assert "Cases: 120" in result.stdout
    assert "No classification mismatches occurred." in result.stdout
    assert "UNRESOLVED CASES" in result.stdout
    assert result.stdout.count("expected UNRESOLVED;") == 12


def test_no_database_or_openai_imports_in_fresh_process():
    code = """
import sys
from app.evaluation.evaluator import run_benchmark
assert run_benchmark()['metrics']['cases_processed'] == 120
assert not any(name.startswith(('openai', 'sqlalchemy', 'app.ai', 'app.database', 'app.config')) for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)


def test_evaluation_does_not_touch_operational_records(db):
    from app.database import Base
    tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)
    def snapshot():
        return {t.name: [dict(row) for row in db.execute(select(t).order_by(t.c.id)).mappings()] for t in tables}
    before = snapshot()
    statements = []
    def record_sql(*args):
        statements.append(args[2])
    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", record_sql)
    try:
        run_benchmark()
        run_benchmark(benchmark="robustness")
    finally:
        event.remove(engine, "before_cursor_execute", record_sql)
    assert statements == []
    assert snapshot() == before


def test_safe_failure_and_no_input_mutation():
    case = next(c for c in generate() if c.expected_classification == C.MATCHED and c.records.refunds)
    r = case.records
    before = asdict(r)
    mutations = [replace(r, settlement=replace(r.settlement, expected_amount=1)),
                 replace(r, refunds=r.refunds + r.refunds),
                 replace(r, refunds=(replace(r.refunds[0], status="pending"),)),
                 replace(r, settlement=replace(r.settlement, payment_id="wrong")),
                 replace(r, payment=replace(r.payment, status="failed")),
                 Evidence(None,None)]
    for records in mutations:
        assert reconcile("independent-case",records).predicted_classification == C.UNRESOLVED
    assert asdict(r) == before
    not_due = replace(r, settlement=None, settlement_due=False)
    assert reconcile("not-due",not_due).predicted_classification == C.MATCHED
