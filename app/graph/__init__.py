"""Compile and run the EnterpriseFlow LangGraph."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import finalize_node, general_node, inventory_stub_node, order_stub_node
from app.graph.state import GraphState, new_request_id, new_workflow_id
from app.graph.supervisor import route_after_supervisor, supervisor_node

# Process-local checkpointer foundation (Phase 8 may move to Redis/Postgres).
_checkpointer = MemorySaver()


def build_graph(checkpointer: MemorySaver | None = None):
    g = StateGraph(GraphState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("order", order_stub_node)
    g.add_node("inventory", inventory_stub_node)
    g.add_node("general", general_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "order": "order",
            "inventory": "inventory",
            "general": "general",
        },
    )
    g.add_edge("order", "finalize")
    g.add_edge("inventory", "finalize")
    g.add_edge("general", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer or _checkpointer)


@lru_cache
def get_compiled_graph():
    return build_graph()


def run_workflow(
    user_request: str,
    *,
    request_id: str | None = None,
    workflow_id: str | None = None,
    graph=None,
) -> dict[str, Any]:
    """Execute one workflow turn and return structured state."""
    rid = request_id or new_request_id()
    wid = workflow_id or new_workflow_id()
    compiled = graph or get_compiled_graph()

    initial: GraphState = {
        "request_id": rid,
        "workflow_id": wid,
        "user_request": user_request,
        "intent": "",
        "route": "",
        "required_agents": [],
        "customer_hint": None,
        "notes": [],
        "steps": [],
        "final_response": None,
        "error": None,
        "context": {},
    }
    config = {"configurable": {"thread_id": wid}}
    result = compiled.invoke(initial, config=config)  # type: ignore[arg-type]
    return dict(result)


def get_checkpoint_state(workflow_id: str, *, graph=None) -> dict[str, Any] | None:
    compiled = graph or get_compiled_graph()
    config = {"configurable": {"thread_id": workflow_id}}
    snap = compiled.get_state(config)  # type: ignore[arg-type]
    if snap is None or snap.values is None:
        return None
    return dict(snap.values)
