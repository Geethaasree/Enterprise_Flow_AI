"""Auth, RBAC helpers, PII redaction, prompt-injection guards.

# ponytail: HS256 JWT via stdlib hmac — no PyJWT until key rotation/JWKS needed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException, Request

# Elevated roles must come from JWT or X-Role header — never request body alone.
ELEVATED_ROLES = frozenset({"admin", "manager", "finance"})
KNOWN_ROLES = frozenset({"admin", "manager", "finance", "sales", "viewer"})

_JWT_SECRET = os.environ.get("EF_JWT_SECRET", "enterpriseflow-dev-secret-change-me")
_AUTH_REQUIRED = os.environ.get("EF_AUTH_REQUIRED", "0").lower() in {"1", "true", "yes"}

_INJECTION_RE = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions"
    r"|disregard\s+(all\s+)?(previous|safety)"
    r"|you\s+are\s+now\s+(an?\s+)?admin"
    r"|system\s*:\s*"
    r"|<\s*/?\s*system\s*>"
    r"|role\s*=\s*admin"
    r"|x-role\s*:\s*admin"
    r"|grant\s+(yourself|me)\s+(admin|root)"
    r"|bypass\s+(auth|approval|rbac|permission)"
    r"|do\s+not\s+call\s+tools"
    r"|exfiltrate|dump\s+(secrets|keys|tokens))",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_jwt(
    *,
    sub: str,
    role: str,
    ttl_seconds: int = 3600,
    extra: dict[str, Any] | None = None,
) -> str:
    if role not in KNOWN_ROLES:
        raise ValueError(f"unknown role {role}")
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_obj = {
        "sub": sub,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + int(ttl_seconds),
        **(extra or {}),
    }
    payload = _b64url_encode(json.dumps(payload_obj, separators=(",", ":")).encode())
    sig = _b64url_encode(
        hmac.new(_JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


def verify_jwt(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Malformed token") from e
    expect = _b64url_encode(
        hmac.new(_JWT_SECRET.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expect, sig_b64):
        raise HTTPException(status_code=401, detail="Invalid token signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token payload") from e
    if int(payload.get("exp") or 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")
    role = payload.get("role") or "viewer"
    if role not in KNOWN_ROLES:
        raise HTTPException(status_code=401, detail="Invalid role in token")
    return payload


@dataclass
class Principal:
    subject: str
    role: str
    auth_via: str  # jwt | header | body | anon


def resolve_principal(
    *,
    authorization: str | None = None,
    x_role: str | None = None,
    body_role: str | None = None,
    default_role: str = "sales",
) -> Principal:
    """Resolve caller identity. Elevated roles never accepted from body alone."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        claims = verify_jwt(token)
        return Principal(subject=str(claims.get("sub") or "user"), role=str(claims["role"]), auth_via="jwt")

    if x_role:
        role = x_role.strip().lower()
        if role not in KNOWN_ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role {x_role!r}")
        return Principal(subject="header-user", role=role, auth_via="header")

    if _AUTH_REQUIRED:
        raise HTTPException(status_code=401, detail="Authorization required")

    # body role: clamp elevated
    role = (body_role or default_role).strip().lower()
    if role not in KNOWN_ROLES:
        role = default_role
    if role in ELEVATED_ROLES:
        # # ponytail: silent downgrade prevents body.role=admin privilege escalation
        role = default_role if default_role not in ELEVATED_ROLES else "sales"
        return Principal(subject="body-user", role=role, auth_via="body_clamped")
    return Principal(subject="body-user", role=role, auth_via="body")


def require_roles(*allowed: str):
    allowed_set = {a.lower() for a in allowed}

    async def _dep(
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_role: str | None = Header(default=None, alias="X-Role"),
    ) -> Principal:
        p = resolve_principal(authorization=authorization, x_role=x_role, body_role=None, default_role="viewer")
        if p.role not in allowed_set:
            raise HTTPException(status_code=403, detail=f"Role {p.role!r} not permitted")
        return p

    return _dep


def scan_prompt_injection(text: str) -> tuple[bool, str | None]:
    """Return (blocked, reason)."""
    if not text or not text.strip():
        return False, None
    if len(text) > 8000:
        return True, "input_too_long"
    m = _INJECTION_RE.search(text)
    if m:
        return True, f"injection_pattern:{m.group(0)[:40]}"
    # null bytes / control spam
    if "\x00" in text:
        return True, "null_byte"
    return False, None


def redact_pii(text: str) -> str:
    if not text:
        return text
    # preserve order numbers (digit runs otherwise look like phones)
    saved: list[str] = []

    def _park_ord(m: re.Match[str]) -> str:
        saved.append(m.group(0))
        return f"\x00ORD{len(saved) - 1}\x00"

    out = re.sub(r"\bORD-[A-Za-z0-9_-]+\b", _park_ord, text)
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    out = _PHONE_RE.sub("[REDACTED_PHONE]", out)
    out = _SSN_RE.sub("[REDACTED_SSN]", out)
    for i, val in enumerate(saved):
        out = out.replace(f"\x00ORD{i}\x00", val)
    return out


def sanitize_user_message(text: str) -> str:
    """Strip common injection wrappers without blocking benign text."""
    cleaned = text.replace("\x00", "")
    # neutralize system spoof tags
    cleaned = re.sub(r"<\s*/?\s*system\s*>", " ", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def client_id_from_request(request: Request, x_client_id: str | None = None) -> str:
    if x_client_id:
        return x_client_id[:128]
    if request.client and request.client.host:
        return request.client.host
    return "anon"
