"""Auth token endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.security import KNOWN_ROLES, issue_jwt

router = APIRouter(prefix="/auth", tags=["auth"])

# # ponytail: demo users only; real IdP when enterprise SSO lands
_USERS = {
    "demo": {"password": "demo", "role": "sales", "sub": "user_demo"},
    "admin": {"password": "admin", "role": "admin", "sub": "user_admin"},
    "viewer": {"password": "viewer", "role": "viewer", "sub": "user_viewer"},
    "manager": {"password": "manager", "role": "manager", "sub": "user_manager"},
}


class TokenRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)


@router.post("/token")
def auth_token(body: TokenRequest):
    user = _USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = user["role"]
    if role not in KNOWN_ROLES:
        raise HTTPException(status_code=500, detail="Misconfigured user role")
    token = issue_jwt(sub=user["sub"], role=role, ttl_seconds=body.ttl_seconds)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "expires_in": body.ttl_seconds,
    }
