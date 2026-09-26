"""Supervisor node — intent + routing (deterministic foundation)."""

from __future__ import annotations

import re

from app.graph.state import GraphState


def classify_intent(user_request: str) -> tuple[str, str, list[str], str | None]:
    """Return (intent, route, required_agents, customer_hint)."""
    text = (user_request or "").strip()
    lower = text.lower()
    customer = _extract_customer(text)

    if any(k in lower for k in ("policy", "return window", "approval rule", "what is the")):
        if any(k in lower for k in ("order", "buy", "purchase")) and "policy" not in lower:
            pass  # fall through to order if primarily order
        elif any(
            k in lower
            for k in ("policy", "return", "credit limit policy", "discount policy", "shipping policy")
        ):
            return "policy", "policy", ["policy"], customer

    if any(k in lower for k in ("order", "purchase", "buy", "procure", "units for")):
        return "create_order", "order", ["customer", "inventory", "pricing", "order", "policy"], customer
    if any(k in lower for k in ("inventory", "stock", "availability", "on hand", "how many")):
        return "check_inventory", "inventory", ["inventory"], customer
    if any(k in lower for k in ("policy", "return", "approval", "discount rules")):
        return "policy", "policy", ["policy"], customer
    return "general", "general", [], customer


_CUSTOMER_RE = re.compile(
    r"\b(?:for|customer)\s+([A-Za-z][A-Za-z0-9 ._-]{1,40})",
    re.IGNORECASE,
)


def _extract_customer(text: str) -> str | None:
    m = _CUSTOMER_RE.search(text)
    if not m:
        return None
    return m.group(1).strip(" .,")


def supervisor_node(state: GraphState) -> dict:
    intent, route, agents, customer = classify_intent(state.get("user_request", ""))
    steps = list(state.get("steps") or [])
    steps.append("supervisor")
    notes = list(state.get("notes") or [])
    notes.append(f"intent={intent} route={route}")
    return {
        "intent": intent,
        "route": route,
        "required_agents": agents,
        "customer_hint": customer,
        "steps": steps,
        "notes": notes,
    }


def route_after_supervisor(state: GraphState) -> str:
    route = state.get("route") or "general"
    if route in {"order", "inventory", "policy", "general"}:
        return route
    return "general"
