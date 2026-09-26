"""Policy RAG ingestion + retrieval with pgvector."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import models as m
from app.rag.chunking import chunk_text
from app.rag.embeddings import cosine, embed_text

logger = logging.getLogger(__name__)

DEFAULT_POLICY_DIR = Path(__file__).resolve().parents[2] / "data" / "policies"


@dataclass
class Citation:
    document_id: str
    document_title: str
    source_file: str
    chunk_index: int
    score: float
    text: str


def ensure_pgvector(session: Session) -> None:
    session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    session.commit()


def ingest_file(session: Session, path: Path, *, title: str | None = None) -> m.PolicyDocument:
    raw = path.read_text(encoding="utf-8")
    doc_title = title or path.stem.replace("_", " ").title()
    existing = session.scalar(select(m.PolicyDocument).where(m.PolicyDocument.source_file == path.name))
    if existing:
        # replace chunks
        for ch in list(existing.chunks):
            session.delete(ch)
        session.flush()
        doc = existing
        doc.title = doc_title
        doc.body = raw
    else:
        doc = m.PolicyDocument(title=doc_title, source_file=path.name, body=raw)
        session.add(doc)
        session.flush()

    for ch in chunk_text(raw):
        emb = embed_text(ch.text)
        session.add(
            m.PolicyChunk(
                document_id=doc.id,
                chunk_index=ch.index,
                content=ch.text,
                start_char=ch.start_char,
                end_char=ch.end_char,
                embedding=emb,
            )
        )
    session.flush()
    logger.info("ingested policy file=%s chunks=%s", path.name, len(doc.chunks) if doc.chunks else "?")
    return doc


def ingest_directory(session: Session, directory: Path | None = None) -> dict[str, Any]:
    d = directory or DEFAULT_POLICY_DIR
    if not d.exists():
        return {"ingested": 0, "error": f"missing {d}"}
    count = 0
    files = []
    for path in sorted(d.glob("*.md")) + sorted(d.glob("*.txt")):
        ingest_file(session, path)
        count += 1
        files.append(path.name)
    return {"ingested": count, "files": files}


def retrieve(
    session: Session,
    query: str,
    *,
    top_k: int = 4,
    min_score: float = 0.12,
) -> list[Citation]:
    from app.observability import span

    with span("rag.retrieve", kind="rag", attrs={"top_k": top_k}):
        q_emb = embed_text(query)
        # fetch candidates — ponytail: full scan OK for small policy corpus; IVF index later
        rows = session.scalars(select(m.PolicyChunk)).all()
        scored: list[tuple[float, m.PolicyChunk]] = []
        for row in rows:
            if not row.embedding:
                continue
            score = cosine(q_emb, list(row.embedding))
            if score >= min_score:
                scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[Citation] = []
        for score, row in scored[:top_k]:
            doc = row.document
            out.append(
                Citation(
                    document_id=doc.id if doc else row.document_id,
                    document_title=doc.title if doc else "",
                    source_file=doc.source_file if doc else "",
                    chunk_index=row.chunk_index,
                    score=round(float(score), 4),
                    text=row.content,
                )
            )
        return out


def retrieve_dict(session: Session, query: str, **kwargs) -> dict[str, Any]:
    hits = retrieve(session, query, **kwargs)
    return {
        "query": query,
        "count": len(hits),
        "citations": [
            {
                "document_id": c.document_id,
                "title": c.document_title,
                "source": c.source_file,
                "chunk_index": c.chunk_index,
                "score": c.score,
                "text": c.text,
            }
            for c in hits
        ],
        "answer_context": "\n\n---\n\n".join(c.text for c in hits) if hits else "",
    }
