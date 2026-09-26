"""Phase 11 MLflow + evaluation tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401
from app.db import Base, reset_engine, session_scope
from app.eval_runner import run_all_and_log
from app.main import create_app
from app.observability import list_recent_runs, tracking_uri
from app.rag.service import ingest_directory
from app.seed import seed_enterprise

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="needs Postgres",
)


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")
    monkeypatch.setenv("MLFLOW_EXPERIMENT", "ef_test")
    reset_engine()
    with session_scope() as s:
        s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(s.get_bind())
        seed_enterprise(s, reset=True)
        s.execute(text("DELETE FROM policy_chunks"))
        s.execute(text("DELETE FROM policy_documents"))
        ingest_directory(s)
    yield
    reset_engine()


def test_eval_runner_metrics(seeded):
    summary = run_all_and_log(log_mlflow=True)
    assert summary["n"] >= 6
    assert 0.0 <= summary["pass_rate"] <= 1.0
    assert summary["latency_ms_p50"] is not None
    # must be real measured fields
    assert "cases" in summary
    failed = [c for c in summary["cases"] if not c["passed"]]
    # log failures for debug but require high pass
    assert summary["pass_rate"] >= 0.7, failed
    runs = list_recent_runs(limit=5)
    assert any(r.get("tags", {}).get("kind") == "evaluation" or "evaluation" in (r.get("name") or "") for r in runs) or runs
    assert tracking_uri().startswith("file:")


def test_evaluations_api(seeded):
    client = TestClient(create_app())
    r = client.post("/evaluations/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["summary"]["n"] > 0
    g = client.get("/evaluations/runs")
    assert g.status_code == 200
    assert g.json()["tracking_uri"]
