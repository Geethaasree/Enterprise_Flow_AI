"""Specialist stub nodes — real agents arrive in Phase 7."""

from __future__ import annotations

from app.graph.state import GraphState


def order_stub_node(state: GraphState) -> dict:
    steps = list(state.get("steps") or [])
    steps.append("order_stub")
    notes = list(state.get("notes") or [])
    cust = state.get("customer_hint") or "unknown customer"
    notes.append(f"order_path customer={cust}")
    return {
        "steps": steps,
        "notes": notes,
        "final_response": (
            f"Order workflow accepted for {cust}. "
            "Specialist agents not yet wired (Phase 7)."
        ),
        "route": "done",
    }


def inventory_stub_node(state: GraphState) -> dict:
    steps = list(state.get("steps") or [])
    steps.append("inventory_stub")
    notes = list(state.get("notes") or [])
    notes.append("inventory_path")
    return {
        "steps": steps,
        "notes": notes,
        "final_response": "Inventory check workflow accepted. Specialist not yet wired (Phase 7).",
        "route": "done",
    }


def general_node(state: GraphState) -> dict:
    steps = list(state.get("steps") or [])
    steps.append("general")
    return {
        "steps": steps,
        "final_response": (
            "I can help with enterprise order and inventory requests. "
            f"Received: {state.get('user_request', '')!r}"
        ),
        "route": "done",
    }


def finalize_node(state: GraphState) -> dict:
    steps = list(state.get("steps") or [])
    steps.append("finalize")
    response = state.get("final_response") or "Workflow completed with no response."
    return {"steps": steps, "final_response": response}
