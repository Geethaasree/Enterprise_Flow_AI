"""Human approval service (HITL)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.repositories import AuditRepo

logger = logging.getLogger(__name__)

# Auto-approve under these ceilings; above → HITL
DISCOUNT_AUTO_LIMIT_PCT = Decimal("10.00")
ORDER_AMOUNT_AUTO_LIMIT = Decimal("50000.00")

APPROVER_ROLES = frozenset({"admin", "manager", "finance"})


@dataclass
class ApprovalView:
    id: str
    workflow_id: str | None
    status: str
    approval_type: str
    reason: str | None
    payload: dict[str, Any]
    requested_by: str | None
    decided_by: str | None
    order_id: str | None


class ApprovalError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _to_view(row: m.Approval) -> ApprovalView:
    payload: dict[str, Any] = {}
    if row.payload_json:
        try:
            payload = json.loads(row.payload_json)
        except json.JSONDecodeError:
            payload = {"raw": row.payload_json}
    return ApprovalView(
        id=row.id,
        workflow_id=row.workflow_id,
        status=row.status,
        approval_type=row.approval_type or "general",
        reason=row.reason,
        payload=payload,
        requested_by=row.requested_by,
        decided_by=row.decided_by,
        order_id=row.order_id,
    )


class ApprovalService:
    def __init__(self, session: Session):
        self.s = session
        self.audit = AuditRepo(session)

    def ensure_pending(
        self,
        *,
        workflow_id: str,
        approval_type: str,
        reason: str,
        payload: dict[str, Any] | None = None,
        requested_by: str = "sales",
        request_id: str | None = None,
    ) -> ApprovalView:
        existing = self.s.scalar(
            select(m.Approval).where(
                m.Approval.workflow_id == workflow_id,
                m.Approval.status == "pending",
            )
        )
        if existing:
            return _to_view(existing)

        row = m.Approval(
            workflow_id=workflow_id,
            status="pending",
            approval_type=approval_type,
            reason=reason,
            payload_json=json.dumps(payload or {}, default=str),
            requested_by=requested_by,
        )
        self.s.add(row)
        self.s.flush()
        self.audit.write(
            action="approval.created",
            actor=requested_by,
            entity_type="approval",
            entity_id=row.id,
            request_id=request_id,
            workflow_id=workflow_id,
            detail=reason,
        )
        return _to_view(row)

    def get(self, approval_id: str) -> ApprovalView:
        row = self.s.get(m.Approval, approval_id)
        if not row:
            raise ApprovalError("NOT_FOUND", f"Approval {approval_id} not found")
        return _to_view(row)

    def get_by_workflow(self, workflow_id: str) -> ApprovalView | None:
        row = self.s.scalar(
            select(m.Approval)
            .where(m.Approval.workflow_id == workflow_id)
            .order_by(m.Approval.created_at.desc())
        )
        return _to_view(row) if row else None

    def list_pending(self, *, limit: int = 50) -> list[ApprovalView]:
        rows = self.s.scalars(
            select(m.Approval)
            .where(m.Approval.status == "pending")
            .order_by(m.Approval.created_at.asc())
            .limit(limit)
        ).all()
        return [_to_view(r) for r in rows]

    def decide(
        self,
        approval_id: str,
        *,
        action: str,
        decided_by: str,
        role: str = "admin",
        note: str | None = None,
        request_id: str | None = None,
    ) -> ApprovalView:
        if role not in APPROVER_ROLES:
            raise ApprovalError("UNAUTHORIZED", f"Role {role!r} cannot decide approvals")
        action = action.lower().strip()
        if action not in {"approve", "reject"}:
            raise ApprovalError("INVALID", "action must be approve or reject")

        row = self.s.get(m.Approval, approval_id)
        if not row:
            raise ApprovalError("NOT_FOUND", f"Approval {approval_id} not found")
        if row.status != "pending":
            raise ApprovalError("ALREADY_DECIDED", f"Approval already {row.status}")

        row.status = "approved" if action == "approve" else "rejected"
        row.decided_by = decided_by
        row.decided_at = datetime.now(UTC)
        if note:
            row.reason = f"{row.reason or ''} | decision: {note}".strip(" |")
        self.s.flush()
        self.audit.write(
            action=f"approval.{row.status}",
            actor=decided_by,
            entity_type="approval",
            entity_id=row.id,
            request_id=request_id,
            workflow_id=row.workflow_id,
            detail=note or action,
        )
        return _to_view(row)


def evaluate_approval_need(
    *,
    discount_pct: Decimal | float | str,
    line_total: Decimal | float | str,
    credit_approved: bool,
) -> tuple[bool, str, str]:
    """Return (needs_approval, type, reason)."""
    disc = Decimal(str(discount_pct))
    total = Decimal(str(line_total))
    reasons: list[str] = []
    atype = "general"
    if disc > DISCOUNT_AUTO_LIMIT_PCT:
        reasons.append(f"discount {disc}% exceeds auto-limit {DISCOUNT_AUTO_LIMIT_PCT}%")
        atype = "discount_exception"
    if total > ORDER_AMOUNT_AUTO_LIMIT:
        reasons.append(f"order total {total} exceeds {ORDER_AMOUNT_AUTO_LIMIT}")
        atype = "high_value" if atype == "general" else atype
    if not credit_approved:
        reasons.append("credit check failed")
        atype = "credit_exception" if atype == "general" else atype
    if not reasons:
        return False, "none", ""
    return True, atype, "; ".join(reasons)
