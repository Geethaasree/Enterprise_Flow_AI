"""LangGraph foundation tests."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.graph import build_graph, get_checkpoint_state, run_workflow
from app.graph.state import new_request_id, new_workflow_id
from app.graph.supervisor import classify_intent, route_after_supervisor


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
    assert route_after_supervisor({"route": "nope"}) == "general"


def test_graph_execution_order():
    graph = build_graph(MemorySaver())
    state = run_workflow(
        "Create an order for 100 laptops for ACME.",
        workflow_id="wf_test_order_1",
        request_id="req_test_1",
        graph=graph,
    )
    assert state["intent"] == "create_order"
    assert state["steps"][0] == "supervisor"
    assert "order_stub" in state["steps"]
    assert state["steps"][-1] == "finalize"
    assert state["final_response"]
    assert "ACME" in (state.get("customer_hint") or "")


def test_graph_execution_inventory():
    graph = build_graph(MemorySaver())
    state = run_workflow("Check stock availability", workflow_id="wf_inv_1", graph=graph)
    assert state["intent"] == "check_inventory"
    assert "inventory_stub" in state["steps"]


def test_checkpoint_persists():
    saver = MemorySaver()
    graph = build_graph(saver)
    wid = "wf_ckpt_1"
    run_workflow("Create an order for ACME", workflow_id=wid, graph=graph)
    ckpt = get_checkpoint_state(wid, graph=graph)
    assert ckpt is not None
    assert ckpt["workflow_id"] == wid
    assert ckpt["intent"] == "create_order"
    assert ckpt.get("final_response")


def test_workflows_api(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    r = client.post(
        "/workflows/run",
        json={"message": "Create an order for 10 laptops for ACME."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["intent"] == "create_order"
    assert body["workflow_id"]
    wid = body["workflow_id"]

    g = client.get(f"/workflows/{wid}")
    # default app uses process MemorySaver — same process TestClient shares it
    assert g.status_code == 200
    assert g.json()["state"]["intent"] == "create_order"
