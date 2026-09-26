"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.logging_setup import setup_logging
from app.routes.api_led import (
    experience_router,
    process_router,
    sap_router,
    system_router,
)
from app.routes.approvals import router as approvals_router
from app.routes.enterprise import router as enterprise_router
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
        yield

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
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
    return app


app = create_app()
