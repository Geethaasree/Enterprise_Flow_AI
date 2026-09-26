"""Health check routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.db import check_db
from app.redis_client import check_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
        "env": settings.app_env,
    }


@router.get("/health/db")
def health_db() -> JSONResponse:
    try:
        check_db()
        return JSONResponse({"status": "ok", "dependency": "postgresql"})
    except Exception as exc:
        logger.exception("database health check failed")
        return JSONResponse(
            {"status": "error", "dependency": "postgresql", "detail": str(exc)},
            status_code=503,
        )


@router.get("/health/redis")
def health_redis() -> JSONResponse:
    try:
        check_redis()
        return JSONResponse({"status": "ok", "dependency": "redis"})
    except Exception as exc:
        logger.exception("redis health check failed")
        return JSONResponse(
            {"status": "error", "dependency": "redis", "detail": str(exc)},
            status_code=503,
        )
