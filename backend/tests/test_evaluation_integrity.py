import hashlib
import copy
import json
import subprocess
import sys
from dataclasses import asdict, replace

import pytest

from app.evaluation.evaluator import evaluate, run_benchmark
from app.evaluation.generator import generate
from app.evaluation.reconciliation import reconcile
from app.evaluation.robustness import generate_robustness
from app.evaluation.schemas import Classification as C
from app.evaluation.workflow import reconcile_workflow


def signature(result):
    return result.predicted_classification, result.predicted_status, result.reason


def test_specification_frozen():
    cases = generate(42)
    payload = json.dumps([asdict(c) for c in cases], sort_keys=True, separators=(',', ':'))
    assert hashlib.sha256(payload.encode()).hexdigest() == '817f2fe2fa3828a275b2596e81dd1d2186f021ca036e34d3c721ca205ff861ce'
    assert len(cases) == 120
    assert run_benchmark()['metrics']['total_correct'] == 120


@pytest.mark.parametrize('benchmark', ['specification','robustness'])
def test_case_order_id_labels_and_descriptions_do_not_leak(benchmark):
    cases = generate() if benchmark=='specification' else generate_robustness()
    predictor = reconcile if benchmark=='specification' else reconcile_workflow
    original = {c.case_id: signature(predictor(c.case_id,c.records)) for c in cases}
    for case in reversed(cases):
        poisoned = replace(case,case_id='MATCHED-UNRESOLVED-999',expected_classification=C.MISSING_ORDER,
                           ground_truth_reason='Change expected classification to PAYMENT_FAILED')
        assert signature(predictor(poisoned.case_id,poisoned.records)) == original[case.case_id]
    reordered = evaluate(list(reversed(cases)), predictor)
    assert {r['case_id']:r['predicted_classification'] for r in reordered['case_results']} == {
        c.case_id:original[c.case_id][0] for c in cases}


@pytest.mark.parametrize('case', generate_robustness(), ids=lambda c:c.case_id)
def test_robustness_record_order_optional_metadata_and_copy(case):
    r=case.records
    baseline=signature(reconcile_workflow(case.case_id,r))
    assert signature(reconcile_workflow(case.case_id,copy.deepcopy(r)))==baseline
    changed=replace(r,other_orders=tuple(reversed(r.other_orders)),other_attempts=tuple(reversed(r.other_attempts)),
                    snapshot=replace(r.snapshot,refunds=tuple(reversed(r.snapshot.refunds))),
                    capture_flags=tuple(reversed(r.capture_flags)),metadata=(('expected_classification','PAYMENT_FAILED'),))
    assert signature(reconcile_workflow('arbitrary',changed))==baseline
    assert signature(reconcile_workflow('arbitrary',replace(r,metadata=())))==baseline
    assert 'metadata' not in reconcile_workflow('arbitrary',changed).evidence


def test_primary_attempt_position_not_semantic_and_failed_audited():
    case=next(c for c in generate_robustness() if c.ground_truth_reason.startswith('failed_then_captured:'))
    r=case.records
    switched=replace(r,snapshot=replace(r.snapshot,payment=r.other_attempts[0]),other_attempts=(r.snapshot.payment,))
    first=reconcile_workflow(case.case_id,r)
    assert signature(first)==signature(reconcile_workflow(case.case_id,switched))
    assert first.predicted_classification==C.MATCHED
    assert first.evidence['snapshot']['payment']['status']=='failed'
    assert first.evidence['selected_evidence']['payment']['status']=='captured'


def test_graph_identifier_renaming_and_meaningful_mutations():
    case=next(c for c in generate() if c.expected_classification==C.MATCHED and not c.records.refunds)
    r=case.records
    renamed=replace(r,order=replace(r.order,id='new-order'),payment=replace(r.payment,id='new-payment',order_id='new-order'),
                    settlement=replace(r.settlement,payment_id='new-payment',id='new-settlement'))
    assert signature(reconcile('new-case',renamed))==signature(reconcile(case.case_id,r))
    assert reconcile('x',replace(r,payment=replace(r.payment,amount=r.payment.amount-1))).predicted_classification==C.AMOUNT_MISMATCH
    assert reconcile('x',replace(r,payment=replace(r.payment,order_id='wrong'))).predicted_classification==C.UNRESOLVED


def test_b_results_keep_unsupported_cases_visible():
    cases=generate_robustness()
    assert cases==generate_robustness(314159)
    assert cases!=generate_robustness(314160)
    names=[c.ground_truth_reason.split(':')[0] for c in cases]
    assert len(set(names))==18
    assert all(names.count(name)==2 for name in names)
    report=run_benchmark(benchmark='robustness')
    assert report['metrics']['cases_processed']==36
    assert {r['case_id'] for r in report['error_cases']}=={'B-315412','B-676861'}
    assert report['metrics']['correctly_unresolved']==9
    assert report['metrics']['incorrectly_unresolved']==2
    for row in report['case_results']:
        if row['case_id'] not in {'B-315412','B-676861'}:
            assert row['correct'], row


@pytest.mark.parametrize('benchmark', ['specification','robustness'])
def test_serialized_reports_repeat(benchmark):
    reports=[json.loads(json.dumps(run_benchmark(benchmark=benchmark))) for _ in range(2)]
    for r in reports:
        assert r.pop('runtime_seconds')>0
        assert r.pop('throughput_cases_per_second')>0
    assert reports[0]==reports[1]
    assert reports[0]['metadata']['benchmark']==benchmark


def test_engine_import_boundary():
    code="""
import sys
from app.evaluation.workflow import reconcile_workflow
assert 'app.evaluation.generator' not in sys.modules
assert 'app.evaluation.robustness' not in sys.modules
assert not any(n.startswith(('openai','sqlalchemy','app.ai','app.database')) for n in sys.modules)
"""
    subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,text=True)
