"""xAI Grok provider (OpenAI-compatible chat completions)."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.llm.base import (
    ChatMessage,
    LLMError,
    LLMProvider,
    LLMResponse,
    LLMTimeoutError,
    TokenUsage,
)
from app.llm.credentials import resolve_xai_api_key

logger = logging.getLogger(__name__)


class XAIProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.x.ai/v1",
        model: str = "grok-4.5",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        key, source = resolve_xai_api_key(api_key)
        self._api_key = key
        self._credential_source = source
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

    @property
    def credential_source(self) -> str:
        return self._credential_source

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = 512,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [_message_to_dict(m) for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format

        data = self._request_json("POST", "/chat/completions", payload)
        resp = _parse_chat_response(data)
        try:
            from app.observability import record_tokens, span

            with span("llm.chat", kind="llm", attrs={"model": resp.model or self.model}):
                record_tokens(
                    prompt=resp.usage.prompt_tokens,
                    completion=resp.usage.completion_tokens,
                    total=resp.usage.total_tokens,
                )
        except Exception:
            pass
        return resp

    def _request_json(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.request(method, url, headers=headers, json=payload)
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise LLMError(
                        f"xAI transient error HTTP {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                        retryable=True,
                    )
                if resp.status_code >= 400:
                    raise LLMError(
                        f"xAI error HTTP {resp.status_code}: {resp.text[:300]}",
                        status_code=resp.status_code,
                        retryable=False,
                    )
                return resp.json()
            except httpx.TimeoutException as exc:
                last_error = LLMTimeoutError(str(exc) or "timeout")
            except LLMError as exc:
                last_error = exc
                if not exc.retryable:
                    raise
            except httpx.HTTPError as exc:
                last_error = LLMError(str(exc), retryable=True)

            if attempt + 1 >= attempts:
                break
            sleep_for = self.retry_backoff_seconds * (2**attempt)
            logger.warning(
                "xai_retry attempt=%s sleep=%.2f err=%s",
                attempt + 1,
                sleep_for,
                type(last_error).__name__,
            )
            time.sleep(sleep_for)

        assert last_error is not None
        raise last_error


def _message_to_dict(message: ChatMessage) -> dict[str, Any]:
    body: dict[str, Any] = {"role": message.role}
    if message.content is not None:
        body["content"] = message.content
    if message.name:
        body["name"] = message.name
    if message.tool_call_id:
        body["tool_call_id"] = message.tool_call_id
    if message.tool_calls:
        body["tool_calls"] = message.tool_calls
    return body


def _parse_chat_response(data: dict[str, Any]) -> LLMResponse:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage_raw = data.get("usage") or {}
    usage = TokenUsage(
        prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
        completion_tokens=int(usage_raw.get("completion_tokens") or 0),
        total_tokens=int(usage_raw.get("total_tokens") or 0),
    )
    return LLMResponse(
        content=message.get("content"),
        model=str(data.get("model") or ""),
        usage=usage,
        tool_calls=list(message.get("tool_calls") or []),
        raw=data,
        finish_reason=choice.get("finish_reason"),
    )
