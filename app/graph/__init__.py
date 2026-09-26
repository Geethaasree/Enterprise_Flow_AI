"""Compile and run the EnterpriseFlow LangGraph with specialist agents + HITL."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents import (
    approval_agent,
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


def build_graph(checkpointer: MemorySaver | None = None):
    g = StateGraph(GraphState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("customer_agent", customer_agent)
    g.add_node("inventory_agent", inventory_agent)
    g.add_node("pricing_agent", pricing_agent)
    g.add_node("approval_agent", approval_agent)
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

    def _gate(next_node: str):
        def _inner(state: GraphState) -> str:
            if state.get("error") or state.get("route") == "done":
                return "finalize"
            return next_node

        return _inner

    # order: customer → inventory → pricing → approval → order → policy → finalize
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
        _gate("approval_agent"),
        {"approval_agent": "approval_agent", "finalize": "finalize"},
    )
    g.add_conditional_edges(
        "approval_agent",
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


def _interrupted_payload(compiled, config: dict) -> dict[str, Any] | None:
    snap = compiled.get_state(config)
    if not snap or not snap.next:
        return None
    # tasks may hold interrupt values
    interrupts = []
    for task in getattr(snap, "tasks", ()) or ():
        for intr in getattr(task, "interrupts", ()) or ():
            val = getattr(intr, "value", intr)
            interrupts.append(val)
    return {
        "status": "awaiting_approval",
        "next": list(snap.next),
        "interrupts": interrupts,
        "values": dict(snap.values) if snap.values else {},
    }


def run_workflow(
    user_request: str,
    *,
    request_id: str | None = None,
    workflow_id: str | None = None,
    session_id: str | None = None,
    graph=None,
) -> dict[str, Any]:
    rid = request_id or new_request_id()
    wid = workflow_id or new_workflow_id()
    compiled = graph or get_compiled_graph()

    memory_bundle: dict[str, Any] = {}
    if session_id:
        try:
            from app.memory import build_context_bundle

            memory_bundle = build_context_bundle(session_id)
        except Exception:
            memory_bundle = {"session_id": session_id}

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
        "context": {
            "session_id": session_id,
            "memory_bundle": memory_bundle,
        },
    }
    config = {"configurable": {"thread_id": wid}}
    result = compiled.invoke(initial, config=config)  # type: ignore[arg-type]
    out = dict(result)

    paused = _interrupted_payload(compiled, config)
    if paused:
        vals = paused.get("values") or {}
        ctx = vals.get("context") or out.get("context") or {}
        interrupt_info = (paused.get("interrupts") or [None])[0] or {}
        out["status"] = "awaiting_approval"
        out["workflow_id"] = wid
        out["request_id"] = rid
        out["intent"] = vals.get("intent") or out.get("intent")
        out["steps"] = vals.get("steps") or out.get("steps")
        out["notes"] = vals.get("notes") or out.get("notes")
        out["context"] = ctx
        out["approval"] = interrupt_info
        out["final_response"] = (
            f"Approval required ({interrupt_info.get('approval_type') or 'review'}): "
            f"{interrupt_info.get('reason') or 'pending human decision'}. "
            f"approval_id={interrupt_info.get('approval_id')}"
        )
        return out

    out.setdefault("status", "ok")
    return out


def resume_workflow(
    workflow_id: str,
    decision: dict[str, Any],
    *,
    graph=None,
) -> dict[str, Any]:
    """Resume a paused approval workflow with approve/reject decision."""
    compiled = graph or get_compiled_graph()
    config = {"configurable": {"thread_id": workflow_id}}
    result = compiled.invoke(Command(resume=decision), config=config)  # type: ignore[arg-type]
    out = dict(result)
    paused = _interrupted_payload(compiled, config)
    if paused:
        out["status"] = "awaiting_approval"
        out["approval"] = (paused.get("interrupts") or [None])[0]
        return out
    out.setdefault("status", "ok")
    out.setdefault("workflow_id", workflow_id)
    return out


def get_checkpoint_state(workflow_id: str, *, graph=None) -> dict[str, Any] | None:
    compiled = graph or get_compiled_graph()
    config = {"configurable": {"thread_id": workflow_id}}
    snap = compiled.get_state(config)  # type: ignore[arg-type]
    if snap is None or snap.values is None:
        return None
    data = dict(snap.values)
    if snap.next:
        data["_paused"] = True
        data["_next"] = list(snap.next)
    return data
