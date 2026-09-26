"""Compile and run the EnterpriseFlow LangGraph with specialist agents."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents import (
    customer_agent,
    finalize_agent,
    general_agent,
    inventory_agent,
    order_agent,
    policy_agent,
    pricing_agent,
)
from app.graph.state import GraphState, new_request_id, new_workflow_id
from app.graph.supervisor import route_after_supervisor, supervisor_node

_checkpointer = MemorySaver()


def _order_continue(state: GraphState) -> str:
    """Stop pipeline early on error."""
    if state.get("error") or state.get("route") == "done":
        return "finalize"
    return "continue"


def build_graph(checkpointer: MemorySaver | None = None):
    g = StateGraph(GraphState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("customer_agent", customer_agent)
    g.add_node("inventory_agent", inventory_agent)
    g.add_node("pricing_agent", pricing_agent)
    g.add_node("order_agent", order_agent)
    g.add_node("policy_agent", policy_agent)
    g.add_node("general_agent", general_agent)
    g.add_node("finalize", finalize_agent)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "order": "customer_agent",
            "inventory": "inventory_agent",
            "policy": "policy_agent",
            "general": "general_agent",
        },
    )

    # order pipeline: customer → inventory → pricing → order → policy → finalize
    def _gate(next_node: str):
        def _inner(state: GraphState) -> str:
            if state.get("error") or state.get("route") == "done":
                return "finalize"
            return next_node

        return _inner

    g.add_conditional_edges(
        "customer_agent",
        _gate("inventory_agent"),
        {"inventory_agent": "inventory_agent", "finalize": "finalize"},
    )
    g.add_conditional_edges(
        "inventory_agent",
        _gate("pricing_agent"),
        {"pricing_agent": "pricing_agent", "finalize": "finalize"},
    )
    g.add_conditional_edges(
        "pricing_agent",
        _gate("order_agent"),
        {"order_agent": "order_agent", "finalize": "finalize"},
    )
    g.add_conditional_edges(
        "order_agent",
        _gate("policy_agent"),
        {"policy_agent": "policy_agent", "finalize": "finalize"},
    )
    g.add_edge("policy_agent", "finalize")
    g.add_edge("general_agent", "finalize")
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
