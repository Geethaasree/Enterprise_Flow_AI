"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_setup import setup_logging
from app.routes.api_led import (
    experience_router,
    process_router,
    sap_router,
    system_router,
)
from app.routes.approvals import router as approvals_router
from app.routes.auth import router as auth_router
from app.routes.enterprise import router as enterprise_router
from app.routes.evaluations import router as evaluations_router
from app.routes.health import router as health_router
from app.routes.llm import router as llm_router
from app.routes.mcp import router as mcp_router
from app.routes.rag import router as rag_router
from app.routes.workflows import router as workflows_router

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        logger.info("application_started env=%s", settings.app_env)
        secret = os.environ.get("EF_JWT_SECRET", "")
        if settings.app_env == "production" and (
            not secret or secret == "enterpriseflow-dev-secret-change-me"
        ):
            logger.warning("EF_JWT_SECRET is default/empty in production — set a strong secret")
        yield

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    # # ponytail: open CORS for interview UI; tighten origins in prod
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(llm_router)
    app.include_router(workflows_router)
    app.include_router(enterprise_router)
    app.include_router(mcp_router)
    app.include_router(rag_router)
    app.include_router(approvals_router)
    app.include_router(sap_router)
    app.include_router(system_router)
    app.include_router(process_router)
    app.include_router(experience_router)
    app.include_router(evaluations_router)
    return app


app = create_app()
