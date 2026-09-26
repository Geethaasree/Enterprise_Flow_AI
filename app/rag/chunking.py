"""Chunk plain text / markdown into overlapping windows."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str
    start_char: int
    end_char: int


def chunk_text(text: str, *, size: int = 500, overlap: int = 80) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []
    # prefer paragraph boundaries
    parts = re.split(r"\n\s*\n", text)
    chunks: list[Chunk] = []
    buf = ""
    buf_start = 0
    pos = 0
    idx = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # find part in original-ish stream
        if buf and len(buf) + 1 + len(part) > size:
            chunks.append(Chunk(index=idx, text=buf.strip(), start_char=buf_start, end_char=buf_start + len(buf)))
            idx += 1
            # overlap tail
            tail = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = (tail + "\n\n" + part).strip() if tail else part
            buf_start = max(0, buf_start + len(buf) - len(buf))  # approximate
            # better start: keep simple sequential
            buf_start = pos - len(tail) if tail else pos
        else:
            if not buf:
                buf_start = pos
            buf = f"{buf}\n\n{part}".strip() if buf else part
        pos += len(part) + 2
    if buf.strip():
        chunks.append(Chunk(index=idx, text=buf.strip(), start_char=buf_start, end_char=buf_start + len(buf)))
    # hard-split any oversize chunk
    final: list[Chunk] = []
    for c in chunks:
        if len(c.text) <= size * 2:
            final.append(c)
            continue
        start = 0
        sub = 0
        while start < len(c.text):
            end = min(len(c.text), start + size)
            final.append(
                Chunk(
                    index=len(final),
                    text=c.text[start:end],
                    start_char=c.start_char + start,
                    end_char=c.start_char + end,
                )
            )
            if end >= len(c.text):
                break
            start = max(end - overlap, start + 1)
            sub += 1
    # reindex
    for i, c in enumerate(final):
        c.index = i
    return final
