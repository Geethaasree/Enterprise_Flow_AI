"""LLM demo / smoke routes (Phase 2)."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm import ChatMessage, LLMError, XAIProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["llm"])


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str | None = None
    json_mode: bool = False


@router.get("/status")
def llm_status() -> dict:
    settings = get_settings()
    try:
        provider = XAIProvider(
            api_key=settings.xai_api_key or None,
            base_url=settings.xai_base_url,
            model=settings.xai_model,
            timeout_seconds=settings.xai_timeout_seconds,
            max_retries=settings.xai_max_retries,
        )
        return {
            "status": "configured",
            "provider": "xai",
            "model": provider.model,
            "credential_source": provider.credential_source,
            "base_url": settings.xai_base_url,
        }
    except RuntimeError as exc:
        return {"status": "unconfigured", "detail": str(exc)}


@router.post("/chat")
def llm_chat(body: ChatRequest) -> JSONResponse:
    settings = get_settings()
    try:
        provider = XAIProvider(
            api_key=settings.xai_api_key or None,
            base_url=settings.xai_base_url,
            model=settings.xai_model,
            timeout_seconds=settings.xai_timeout_seconds,
            max_retries=settings.xai_max_retries,
        )
        messages = [
            ChatMessage(role="system", content="You are a concise enterprise assistant."),
            ChatMessage(role="user", content=body.prompt),
        ]
        if body.json_mode:
            messages[0] = ChatMessage(
                role="system",
                content="Reply with a single JSON object only. Include keys summary and ok.",
            )
            result = provider.chat_json(messages, model=body.model)
            # validate JSON parse
            if result.content:
                json.loads(result.content)
        else:
            result = provider.chat(messages, model=body.model, max_tokens=256)

        return JSONResponse(
            {
                "status": "ok",
                "model": result.model,
                "content": result.content,
                "finish_reason": result.finish_reason,
                "usage": {
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                    "total_tokens": result.usage.total_tokens,
                },
                "tool_calls": result.tool_calls,
                "credential_source": provider.credential_source,
            }
        )
    except LLMError as exc:
        logger.exception("llm_chat failed")
        return JSONResponse(
            {"status": "error", "detail": str(exc), "retryable": exc.retryable},
            status_code=502,
        )
    except RuntimeError as exc:
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=503)
    except json.JSONDecodeError as exc:
        return JSONResponse(
            {"status": "error", "detail": f"model returned non-JSON: {exc}"},
            status_code=502,
        )
