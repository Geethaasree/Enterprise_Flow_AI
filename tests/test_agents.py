"""Phase 7 specialist agent / order workflow tests."""

from __future__ import annotations

import os
import re

import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import text

from app import models  # noqa: F401
from app.db import Base, reset_engine, session_scope
from app.graph import build_graph, run_workflow
from app.graph.supervisor import classify_intent
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
        seed_enterprise(s, reset=True)
        s.execute(text("DELETE FROM policy_chunks"))
        s.execute(text("DELETE FROM policy_documents"))
        ingest_directory(s)
    yield
    reset_engine()


def test_classify_order_and_policy():
    intent, route, agents, cust = classify_intent(
        "Create an order for 10 Laptop Pro 14 units for ACME."
    )
    assert intent == "create_order"
    assert route == "order"
    assert "customer" in agents
    assert cust and "ACME" in cust

    _, route2, _, _ = classify_intent("What is the return policy window?")
    assert route2 == "policy"


def test_full_order_workflow():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Create an order for 10 Laptop Pro 14 units for ACME.",
        workflow_id="wf_phase7_order",
        graph=graph,
    )
    assert state.get("error") is None
    steps = state["steps"]
    assert steps[0] == "supervisor"
    for name in ("customer_agent", "inventory_agent", "pricing_agent", "order_agent", "policy_agent", "finalize"):
        assert name in steps
    assert state["context"].get("order", {}).get("ok") is True
    assert "ORD-" in (state["final_response"] or "")
    assert "ACME" in (state["final_response"] or "")


def test_inventory_shortage():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Create an order for 500 Laptop Pro 14 units for ACME.",
        workflow_id="wf_phase7_short",
        graph=graph,
    )
    assert state.get("error")
    assert "Insufficient" in (state.get("final_response") or state["error"])


def test_inventory_check_path():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Check inventory stock for LAPTOP-PRO-14",
        workflow_id="wf_phase7_inv",
        graph=graph,
    )
    assert "available" in (state["final_response"] or "").lower() or "on_hand" in (state["final_response"] or "")


def test_workflows_api_order():
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    r = client.post(
        "/workflows/run",
        json={"message": "Create an order for 2 Laptop Pro 14 units for ACME."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["intent"] == "create_order"
    assert re.search(r"ORD-", body.get("final_response") or "")
