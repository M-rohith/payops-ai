import json

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session


def test_evaluation_endpoint_exposes_separate_frozen_results(client: TestClient):
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["disclaimer"] == "Synthetic benchmark · developer-authored · not production validation"
    assert [b["key"] for b in payload["benchmarks"]] == ["specification", "robustness"]
    a, b = payload["benchmarks"]
    assert a["seed"] == 42 and a["metrics"]["cases_processed"] == 120
    assert a["metrics"]["total_correct"] == 120 and a["metrics"]["correctly_unresolved"] == 12
    assert len(a["scenario_distribution"]) == 10 and set(a["scenario_distribution"].values()) == {12}
    assert b["seed"] == 314159 and b["metrics"]["cases_processed"] == 36
    assert b["metrics"]["total_correct"] == 34
    assert b["metrics"]["clean_match_recall"] == 15 / 17
    assert b["metrics"]["unresolved_count"] == 11
    assert b["metrics"]["correctly_unresolved"] == 9
    assert b["metrics"]["incorrectly_unresolved"] == 2
    assert len(b["scenario_distribution"]) == 18 and set(b["scenario_distribution"].values()) == {2}
    assert {row["case_id"] for row in b["known_mismatches"]} == {"B-315412", "B-676861"}
    assert all(row["display_status"] == "incorrect_unresolved" for row in b["known_mismatches"])
    assert all(isinstance(row["evidence_summary"], list) for benchmark in (a, b) for row in benchmark["cases"])


def test_evaluation_endpoint_is_cached_deterministic_and_read_only(client: TestClient, db: Session):
    statements = []
    engine = db.get_bind()
    def record_sql(*args):
        statements.append(args[2])
    event.listen(engine, "before_cursor_execute", record_sql)
    try:
        first = client.get("/api/evaluation")
        second = client.get("/api/evaluation")
    finally:
        event.remove(engine, "before_cursor_execute", record_sql)
    assert first.content == second.content
    assert statements == []
    assert json.loads(first.content)["generated_from"] == "cached deterministic in-memory evaluation"


def test_evaluation_has_no_mutation_routes(client: TestClient):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/evaluation").status_code == 405
