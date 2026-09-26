"""MCP HTTP surface — list + call tools."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.mcp_tools import ToolError, call_tool, list_tools
from app.memory import rate_limit_allow
from app.security import client_id_from_request, resolve_principal

router = APIRouter(prefix="/mcp", tags=["mcp"])


class CallBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    arguments: dict = Field(default_factory=dict)
    role: str = "sales"
    request_id: str | None = None


@router.get("/tools")
def mcp_list_tools():
    return {"tools": list_tools()}


@router.post("/call")
def mcp_call(
    body: CallBody,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_role: str | None = Header(default=None, alias="X-Role"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
):
    client = client_id_from_request(request, x_client_id)
    allowed, rate_meta = rate_limit_allow(f"mcp:{client}", limit=120, window=60)
    if not allowed:
        return JSONResponse(
            {"status": "error", "code": "RATE_LIMITED", "rate": rate_meta},
            status_code=429,
        )

    principal = resolve_principal(
        authorization=authorization,
        x_role=x_role,
        body_role=body.role,
        default_role="sales",
    )
    request_id = x_request_id or body.request_id or f"req_{uuid.uuid4().hex[:12]}"
    try:
        result = call_tool(body.name, body.arguments, role=principal.role, request_id=request_id)
        result["auth"] = {"role": principal.role, "via": principal.auth_via, "sub": principal.subject}
        return result
    except ToolError as e:
        return JSONResponse(
            {
                "tool": body.name,
                "status": "error",
                "code": e.code,
                "message": e.message,
                "request_id": request_id,
                "auth": {"role": principal.role, "via": principal.auth_via},
            },
            status_code=e.http_status,
        )
