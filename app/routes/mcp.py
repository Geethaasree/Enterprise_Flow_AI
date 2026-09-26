"""MCP HTTP surface — list + call tools."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.mcp_tools import ToolError, call_tool, list_tools

router = APIRouter(prefix="/mcp", tags=["mcp"])


class CallBody(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    role: str = "sales"
    request_id: str | None = None


@router.get("/tools")
def mcp_list_tools():
    return {"tools": list_tools()}


@router.post("/call")
def mcp_call(
    body: CallBody,
    x_role: str | None = Header(default=None, alias="X-Role"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
):
    role = x_role or body.role or "sales"
    request_id = x_request_id or body.request_id or f"req_{uuid.uuid4().hex[:12]}"
    try:
        return call_tool(body.name, body.arguments, role=role, request_id=request_id)
    except ToolError as e:
        return JSONResponse(
            {
                "tool": body.name,
                "status": "error",
                "code": e.code,
                "message": e.message,
                "request_id": request_id,
            },
            status_code=e.http_status,
        )
