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
_DISC = re.compile(r"(?:with|at|@)?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*(?:discount|off)?", re.IGNORECASE)
_DISC2 = re.compile(r"(?:discount|exception)\s*(?:of\s*)?(\d{1,2}(?:\.\d+)?)\s*%", re.IGNORECASE)


def parse_quantity(text: str, default: int = 1) -> int:
    m = _QTY.search(text or "")
    return int(m.group(1)) if m else default


def parse_sku(text: str, default: str = "LAPTOP-PRO-14") -> str:
    lower = (text or "").lower()
    m = re.search(r"\b([A-Z0-9]+-[A-Z0-9-]+)\b", text or "", re.IGNORECASE)
    if m:
        return m.group(1).upper()
    for key, sku in sorted(_SKU_MAP.items(), key=lambda x: -len(x[0])):
        if key in lower:
            return sku
    return default


def parse_discount_pct(text: str) -> float | None:
    """Optional requested discount exception from free text."""
    for rx in (_DISC2, _DISC):
        m = rx.search(text or "")
        if m:
            return float(m.group(1))
    return None


def parse_customer(text: str, hint: str | None = None, default: str = "ACME") -> str:
    if hint:
        code = hint.strip().split()[0].upper().rstrip(".,")
        if code:
            return code
    m = re.search(r"\bfor\s+([A-Za-z][A-Za-z0-9_-]*)", text or "", re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return default
