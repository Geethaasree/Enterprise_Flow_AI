"""RAG HTTP API."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import session_scope
from app.rag.service import ingest_directory, retrieve_dict

router = APIRouter(prefix="/rag", tags=["rag"])


class SearchBody(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)
    min_score: float = Field(default=0.12, ge=0.0, le=1.0)


@router.post("/ingest")
def rag_ingest():
    from sqlalchemy import text

    with session_scope() as s:
        s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        result = ingest_directory(s)
    return {"status": "ok", **result}


@router.post("/search")
def rag_search(body: SearchBody):
    with session_scope() as s:
        out = retrieve_dict(s, body.query, top_k=body.top_k, min_score=body.min_score)
    if out["count"] == 0:
        return JSONResponse(
            {"status": "ok", "message": "no relevant policy found", **out},
            status_code=200,
        )
    return {"status": "ok", **out}
