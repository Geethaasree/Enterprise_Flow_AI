"""LangGraph workflow state and ID helpers."""

from __future__ import annotations

import uuid
from typing import Any, Literal, TypedDict


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def new_workflow_id() -> str:
    return f"wf_{uuid.uuid4().hex[:16]}"


class GraphState(TypedDict, total=False):
    """Shared graph state for Phase 3 foundation.

    Specialist agents (Phase 7+) extend fields; keep this the single source of truth.
    """

    request_id: str
    workflow_id: str
    user_request: str
    intent: str
    route: str
    required_agents: list[str]
    customer_hint: str | None
    notes: list[str]
    steps: list[str]
    final_response: str | None
    error: str | None
    # free-form bag for later phases (memory, tool results, etc.)
    context: dict[str, Any]


RouteName = Literal["order", "inventory", "general", "done"]
