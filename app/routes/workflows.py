"""Workflow execution HTTP API with session memory."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.graph import get_checkpoint_state, run_workflow
from app.memory import (
    append_turn,
    build_context_bundle,
    clear_session,
    get_business_memory,
    get_summary,
    get_turns,
    rate_limit_allow,
)
from app.security import (
    client_id_from_request,
    redact_pii,
    sanitize_user_message,
    scan_prompt_injection,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


class RunWorkflowRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    workflow_id: str | None = None
    request_id: str | None = None
    session_id: str | None = None


@router.post("/run")
def workflows_run(
    body: RunWorkflowRequest,
    request: Request,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
) -> JSONResponse:
    # rate limit per client
    client = client_id_from_request(request, x_client_id)
    allowed, rate_meta = rate_limit_allow(f"wf:{client}", limit=60, window=60)
    if not allowed:
        return JSONResponse(
            {"status": "error", "code": "RATE_LIMITED", "detail": "Too many requests", "rate": rate_meta},
            status_code=429,
        )

    blocked, reason = scan_prompt_injection(body.message)
    if blocked:
        return JSONResponse(
            {
                "status": "error",
                "code": "PROMPT_INJECTION",
                "detail": "Message rejected by security policy",
                "reason": reason,
            },
            status_code=400,
        )

    message = sanitize_user_message(body.message)
    session_id = body.session_id or x_session_id or f"sess_{uuid.uuid4().hex[:12]}"
    try:
        append_turn(session_id, "user", redact_pii(message))
    except Exception:
        logger.warning("session_append_failed", exc_info=True)

    try:
        state = run_workflow(
            message,
            request_id=body.request_id,
            workflow_id=body.workflow_id,
            session_id=session_id,
        )
        final = redact_pii(state.get("final_response") or "")
        try:
            append_turn(
                session_id,
                "assistant",
                final,
                meta={"workflow_id": state.get("workflow_id"), "intent": state.get("intent")},
            )
        except Exception:
            logger.warning("session_append_assistant_failed", exc_info=True)

        return JSONResponse(
            {
                "status": state.get("status") or "ok",
                "request_id": state.get("request_id"),
                "workflow_id": state.get("workflow_id"),
                "session_id": session_id,
                "intent": state.get("intent"),
                "route": state.get("route"),
                "required_agents": state.get("required_agents"),
                "customer_hint": state.get("customer_hint"),
                "steps": state.get("steps"),
                "final_response": final,
                "approval": state.get("approval"),
                "context_used": bool((state.get("context") or {}).get("memory_bundle")),
                "rate": rate_meta,
            }
        )
    except Exception as exc:
        logger.exception("workflow_run_failed")
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)


@router.get("/session/{session_id}")
def session_get(session_id: str) -> JSONResponse:
    try:
        turns = get_turns(session_id)
        summary = get_summary(session_id)
        bundle = build_context_bundle(session_id)
        return JSONResponse(
            {
                "status": "ok",
                "session_id": session_id,
                "turns": turns,
                "summary": summary,
                "bundle": bundle,
            }
        )
    except Exception as exc:
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)


@router.delete("/session/{session_id}")
def session_delete(session_id: str) -> JSONResponse:
    clear_session(session_id)
    return JSONResponse({"status": "ok", "session_id": session_id, "cleared": True})


@router.get("/memory/business/{customer_code}")
def business_memory_get(customer_code: str) -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "customer_code": customer_code.upper(), "memory": get_business_memory(customer_code)}
    )


@router.get("/{workflow_id}")
def workflows_get(workflow_id: str) -> JSONResponse:
    state = get_checkpoint_state(workflow_id)
    if not state:
        return JSONResponse({"status": "not_found", "workflow_id": workflow_id}, status_code=404)
    return JSONResponse(
        {
            "status": "ok",
            "workflow_id": workflow_id,
            "state": {
                "request_id": state.get("request_id"),
                "intent": state.get("intent"),
                "route": state.get("route"),
                "steps": state.get("steps"),
                "final_response": state.get("final_response"),
                "session_id": (state.get("context") or {}).get("session_id"),
            },
        }
    )
