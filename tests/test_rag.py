"""RAG / pgvector tests."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app import models  # noqa: F401
from app.db import Base, reset_engine, session_scope
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_text
from app.rag.service import ingest_directory, retrieve
from app.seed import seed_enterprise

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="needs Postgres+pgvector",
)


@pytest.fixture()
def session():
    reset_engine()
    with session_scope() as s:
        try:
            s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"pgvector unavailable: {e}")
        Base.metadata.create_all(s.get_bind())
        seed_enterprise(s, reset=False)
        # wipe policy tables for clean ingest
        s.execute(text("DELETE FROM policy_chunks"))
        s.execute(text("DELETE FROM policy_documents"))
        ingest_directory(s)
        s.commit()
    with session_scope() as s:
        yield s
    reset_engine()


def test_embed_normalized():
    v = embed_text("credit limit approval policy")
    assert len(v) == 384
    assert abs(sum(x * x for x in v) - 1.0) < 1e-6


def test_chunking():
    chunks = chunk_text("Para one.\n\nPara two is here.\n\nPara three follows.")
    assert len(chunks) >= 1
    assert chunks[0].text


def test_ingest_and_retrieve(session):
    hits = retrieve(session, "What is the credit limit policy for large orders?", top_k=3)
    assert hits, "expected credit policy hit"
    assert any("credit" in h.document_title.lower() or "credit" in h.source_file for h in hits)
    assert hits[0].score > 0
    assert hits[0].text
    assert hits[0].source_file.endswith(".md")


def test_irrelevant_query(session):
    hits = retrieve(session, "xyzzy quantum banana recipe", top_k=3, min_score=0.35)
    assert hits == []


def test_rag_http():
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    r = client.post("/rag/search", json={"query": "return window for defective items"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert body["citations"][0]["source"]
