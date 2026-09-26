"""Phase 9 human approval tests."""

from __future__ import annotations

import os
import uuid

import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import text

from app import models  # noqa: F401
from app.approvals import DISCOUNT_AUTO_LIMIT_PCT, evaluate_approval_need
from app.db import Base, reset_engine, session_scope
from app.graph import build_graph, resume_workflow, run_workflow
from app.rag.service import ingest_directory
from app.seed import seed_enterprise

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="needs Postgres",
)


@pytest.fixture(autouse=True)
def _seed():
    reset_engine()
    with session_scope() as s:
        s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(s.get_bind())
        # add approval columns if missing on old DB
        for stmt in (
            "ALTER TABLE approvals ADD COLUMN IF NOT EXISTS approval_type VARCHAR(64) DEFAULT 'general'",
            "ALTER TABLE approvals ADD COLUMN IF NOT EXISTS payload_json TEXT",
        ):
            try:
                s.execute(text(stmt))
            except Exception:
                pass
        seed_enterprise(s, reset=True)
        s.execute(text("DELETE FROM policy_chunks"))
        s.execute(text("DELETE FROM policy_documents"))
        ingest_directory(s)
    yield
    reset_engine()


def test_evaluate_thresholds():
    need, atype, reason = evaluate_approval_need(
        discount_pct=15, line_total=1000, credit_approved=True
    )
    assert need and atype == "discount_exception"
    assert str(DISCOUNT_AUTO_LIMIT_PCT) in reason or "10" in reason

    need2, _, _ = evaluate_approval_need(discount_pct=5, line_total=1000, credit_approved=True)
    assert not need2


def test_discount_exception_pauses_then_approves():
    graph = build_graph(MemorySaver())
    wid = f"wf_appr_{uuid.uuid4().hex[:8]}"
    state = run_workflow(
        "Create an order for 2 Laptop Pro 14 units for ACME with 15% discount exception",
        workflow_id=wid,
        graph=graph,
    )
    assert state.get("status") == "awaiting_approval"
    appr = state.get("approval") or {}
    assert appr.get("approval_id")
    assert "discount" in (appr.get("reason") or "").lower() or appr.get("approval_type") == "discount_exception"

    # unauthorized role
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    bad = client.post(
        f"/approvals/{appr['approval_id']}/decide",
        json={"action": "approve", "decided_by": "bob", "role": "sales"},
        headers={"X-Role": "sales"},
    )
    assert bad.status_code == 403

    # approve via graph resume (same checkpointer as pause)
    done = resume_workflow(
        wid,
        {"action": "approve", "decided_by": "mgr1", "role": "admin", "note": "ok exception"},
        graph=graph,
    )
    assert done.get("status") != "awaiting_approval"
    assert done.get("error") is None
    assert "ORD-" in (done.get("final_response") or "")
    assert "approval_agent" in (done.get("steps") or [])


def test_discount_exception_reject_releases():
    graph = build_graph(MemorySaver())
    wid = f"wf_rej_{uuid.uuid4().hex[:8]}"
    state = run_workflow(
        "Create an order for 1 Laptop Pro 14 units for ACME with 20% discount",
        workflow_id=wid,
        graph=graph,
    )
    assert state.get("status") == "awaiting_approval"
    done = resume_workflow(
        wid,
        {"action": "reject", "decided_by": "mgr1", "role": "admin", "note": "too high"},
        graph=graph,
    )
    assert done.get("error") or "reject" in (done.get("final_response") or "").lower()
    assert "ORD-" not in (done.get("final_response") or "")


def test_normal_order_skips_approval():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Create an order for 1 Laptop Pro 14 units for ACME.",
        workflow_id=f"wf_norm_{uuid.uuid4().hex[:8]}",
        graph=graph,
    )
    assert state.get("status") != "awaiting_approval"
    assert "ORD-" in (state.get("final_response") or "")
    notes = " ".join(state.get("notes") or [])
    assert "approval_not_required" in notes or "approval_skipped" in notes
