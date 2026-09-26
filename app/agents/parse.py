"""Parse order-ish fields from free text (deterministic)."""

from __future__ import annotations

import re

_QTY = re.compile(r"\b(\d{1,6})\b")
_SKU_MAP = {
    "laptop": "LAPTOP-PRO-14",
    "laptop pro": "LAPTOP-PRO-14",
    "laptop-pro-14": "LAPTOP-PRO-14",
    "mouse": "MOUSE-ERGO-01",
    "ergo mouse": "MOUSE-ERGO-01",
}


def parse_quantity(text: str, default: int = 1) -> int:
    m = _QTY.search(text or "")
    return int(m.group(1)) if m else default


def parse_sku(text: str, default: str = "LAPTOP-PRO-14") -> str:
    lower = (text or "").lower()
    # explicit sku
    m = re.search(r"\b([A-Z0-9]+-[A-Z0-9-]+)\b", text or "", re.IGNORECASE)
    if m:
        return m.group(1).upper()
    for key, sku in sorted(_SKU_MAP.items(), key=lambda x: -len(x[0])):
        if key in lower:
            return sku
    return default


def parse_customer(text: str, hint: str | None = None, default: str = "ACME") -> str:
    if hint:
        # take first token-ish code
        code = hint.strip().split()[0].upper().rstrip(".,")
        if code:
            return code
    m = re.search(r"\bfor\s+([A-Za-z][A-Za-z0-9_-]*)", text or "", re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return default
