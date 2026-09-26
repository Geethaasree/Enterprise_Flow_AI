"""Lightweight deterministic embeddings (no external model required).

# ponytail: hashed n-gram bag; swap for OpenAI/xAI/sentence-transformers when quality needs it.
"""

from __future__ import annotations

import hashlib
import math
import re
from itertools import pairwise

EMBED_DIM = 384


def embed_text(text: str, dim: int = EMBED_DIM) -> list[float]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        return [0.0] * dim
    vec = [0.0] * dim
    for tok in tokens:
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    for a, b in pairwise(tokens):
        h = int(hashlib.sha256(f"{a}_{b}".encode()).hexdigest(), 16)
        vec[h % dim] += 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
