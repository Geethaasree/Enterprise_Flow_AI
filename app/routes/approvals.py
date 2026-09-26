"""Human approval HTTP API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.approvals import APPROVER_ROLES, ApprovalError, ApprovalService
from app.db import session_scope
from app.graph import resume_workflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecideBody(BaseModel):
    action: str = Field(description="approve or reject")
    decided_by: str = Field(default="manager", min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)
    role: str | None = Field(default=None, max_length=32)


def _view_dict(v) -> dict:
    return {
        "id": v.id,
        "workflow_id": v.workflow_id,
        "status": v.status,
        "approval_type": v.approval_type,
        "reason": v.reason,
        "payload": v.payload,
        "requested_by": v.requested_by,
        "decided_by": v.decided_by,
        "order_id": v.order_id,
    }


@router.get("")
def list_approvals(status: str = "pending") -> JSONResponse:
    with session_scope() as s:
        svc = ApprovalService(s)
        if status == "pending":
            rows = svc.list_pending()
        else:
            # ponytail: only pending list fully supported
            rows = [r for r in svc.list_pending(limit=200)]
            rows = [r for r in rows if r.status == status] if status != "all" else rows
        return JSONResponse({"status": "ok", "count": len(rows), "approvals": [_view_dict(r) for r in rows]})


@router.get("/{approval_id}")
def get_approval(approval_id: str) -> JSONResponse:
    try:
        with session_scope() as s:
            v = ApprovalService(s).get(approval_id)
            return JSONResponse({"status": "ok", "approval": _view_dict(v)})
    except ApprovalError as e:
        code = 404 if e.code == "NOT_FOUND" else 400
        return JSONResponse({"status": "error", "code": e.code, "detail": e.message}, status_code=code)


@router.post("/{approval_id}/decide")
def decide_approval(
    approval_id: str,
    body: DecideBody,
    x_role: str | None = Header(default="admin", alias="X-Role"),
) -> JSONResponse:
    role = (body.role or x_role or "admin").lower()
    if role not in APPROVER_ROLES:
        return JSONResponse(
            {"status": "error", "code": "UNAUTHORIZED", "detail": f"Role {role!r} cannot approve"},
            status_code=403,
        )
    try:
        with session_scope() as s:
            svc = ApprovalService(s)
            before = svc.get(approval_id)
            workflow_id = before.workflow_id
            # decide in DB first when still pending; resume may also decide
            if before.status == "pending":
                # leave pending for graph decide on resume — or decide now and resume with same action
                pass
    except ApprovalError as e:
        code = 404 if e.code == "NOT_FOUND" else 400
        return JSONResponse({"status": "error", "code": e.code, "detail": e.message}, status_code=code)

    if not workflow_id:
        return JSONResponse(
            {"status": "error", "code": "NO_WORKFLOW", "detail": "Approval has no workflow_id"},
            status_code=400,
        )

    decision = {
        "action": body.action.lower(),
        "decided_by": body.decided_by,
        "role": role,
        "note": body.note,
        "approval_id": approval_id,
    }
    try:
        state = resume_workflow(workflow_id, decision)
    except Exception as exc:
        logger.exception("resume_failed")
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)

    # refresh approval row
    with session_scope() as s:
        try:
            appr = ApprovalService(s).get(approval_id)
            appr_d = _view_dict(appr)
        except ApprovalError:
            appr_d = None

    return JSONResponse(
        {
            "status": state.get("status") or "ok",
            "approval": appr_d,
            "workflow_id": workflow_id,
            "intent": state.get("intent"),
            "steps": state.get("steps"),
            "final_response": state.get("final_response"),
            "error": state.get("error"),
        }
    )
