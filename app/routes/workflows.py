"""Workflow execution HTTP API (Phase 3)."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.graph import get_checkpoint_state, run_workflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


class RunWorkflowRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    workflow_id: str | None = None
    request_id: str | None = None


@router.post("/run")
def workflows_run(body: RunWorkflowRequest) -> JSONResponse:
    try:
        state = run_workflow(
            body.message,
            request_id=body.request_id,
            workflow_id=body.workflow_id,
        )
        return JSONResponse(
            {
                "status": "ok",
                "request_id": state.get("request_id"),
                "workflow_id": state.get("workflow_id"),
                "intent": state.get("intent"),
                "route": state.get("route"),
                "required_agents": state.get("required_agents"),
                "customer_hint": state.get("customer_hint"),
                "steps": state.get("steps"),
                "final_response": state.get("final_response"),
            }
        )
    except Exception as exc:
        logger.exception("workflow_run_failed")
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)


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
            },
        }
    )
