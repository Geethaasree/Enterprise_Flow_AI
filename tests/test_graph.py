"""LangGraph foundation tests."""

from __future__ import annotations

import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.graph import build_graph, get_checkpoint_state, run_workflow
from app.graph.state import new_request_id, new_workflow_id
from app.graph.supervisor import classify_intent, route_after_supervisor

needs_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="agent graph needs Postgres/MCP data",
)


def test_ids_unique():
    assert new_request_id() != new_request_id()
    assert new_workflow_id().startswith("wf_")


def test_classify_order():
    intent, route, agents, cust = classify_intent("Create an order for 100 laptops for ACME.")
    assert intent == "create_order"
    assert route == "order"
    assert "order" in agents
    assert cust and "ACME" in cust


def test_classify_inventory():
    intent, route, agents, _ = classify_intent("Check inventory stock for widgets")
    assert intent == "check_inventory"
    assert route == "inventory"
    assert agents == ["inventory"]


def test_classify_general():
    intent, route, agents, _ = classify_intent("What can you do?")
    assert intent == "general"
    assert route == "general"
    assert agents == []


def test_route_after_supervisor():
    assert route_after_supervisor({"route": "order"}) == "order"
    assert route_after_supervisor({"route": "policy"}) == "policy"
    assert route_after_supervisor({"route": "nope"}) == "general"


@needs_db
def test_graph_execution_order():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Create an order for 10 laptops for ACME.",
        workflow_id="wf_test_order_1",
        request_id="req_test_1",
        graph=graph,
    )
    assert state["intent"] == "create_order"
    assert state["steps"][0] == "supervisor"
    assert "customer_agent" in state["steps"]
    assert "order_agent" in state["steps"]
    assert state["steps"][-1] == "finalize"
    assert state["final_response"]
    assert "ACME" in (state.get("customer_hint") or "")


@needs_db
def test_graph_execution_inventory():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Check stock availability for LAPTOP-PRO-14",
        workflow_id="wf_inv_1",
        graph=graph,
    )
    assert state["intent"] == "check_inventory"
    assert "inventory_agent" in state["steps"]


@needs_db
def test_checkpoint_persists():
    saver = MemorySaver()
    graph = build_graph(saver)
    wid = "wf_ckpt_1"
    run_workflow("Create an order for 1 laptop for ACME", workflow_id=wid, graph=graph)
    ckpt = get_checkpoint_state(wid, graph=graph)
    assert ckpt is not None
    assert ckpt["workflow_id"] == wid
    assert ckpt["intent"] == "create_order"
    assert ckpt.get("final_response")


@needs_db
def test_workflows_api():
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    r = client.post(
        "/workflows/run",
        json={"message": "Create an order for 2 laptops for ACME."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["intent"] == "create_order"
    assert body["workflow_id"]
    wid = body["workflow_id"]

    g = client.get(f"/workflows/{wid}")
    assert g.status_code == 200
    assert g.json()["state"]["intent"] == "create_order"
