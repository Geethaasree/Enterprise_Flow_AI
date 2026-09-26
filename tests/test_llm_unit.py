"""LLM provider unit tests (mocked HTTP)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.llm import ChatMessage, LLMError, LLMTimeoutError, XAIProvider
from app.llm.credentials import resolve_xai_api_key


def test_resolve_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY", "env-key-123")
    key, source = resolve_xai_api_key(hermes_auth_path=tmp_path / "missing.json")
    assert key == "env-key-123"
    assert source == "env"


def test_resolve_hermes_oauth(monkeypatch, tmp_path):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    auth = tmp_path / "auth.json"
    auth.write_text(
        json.dumps({"providers": {"xai-oauth": {"tokens": {"access_token": "oauth-token"}}}})
    )
    key, source = resolve_xai_api_key(hermes_auth_path=auth)
    assert key == "oauth-token"
    assert source == "hermes-xai-oauth"


def test_resolve_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        resolve_xai_api_key(hermes_auth_path=tmp_path / "nope.json")


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(payload or {})

    def json(self):
        return self._payload


def test_chat_success(monkeypatch):
    calls = {"n": 0}

    def fake_request(self, method, url, headers=None, json=None):
        calls["n"] += 1
        assert method == "POST"
        assert url.endswith("/chat/completions")
        assert headers["Authorization"].startswith("Bearer ")
        return _FakeResponse(
            200,
            {
                "model": "grok-4.5",
                "choices": [
                    {
                        "message": {"content": "hello", "tool_calls": []},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            },
        )

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    p = XAIProvider(api_key="test-key", max_retries=0)
    out = p.chat([ChatMessage(role="user", content="hi")])
    assert out.content == "hello"
    assert out.usage.total_tokens == 4
    assert calls["n"] == 1


def test_retry_on_500(monkeypatch):
    calls = {"n": 0}

    def fake_request(self, method, url, headers=None, json=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResponse(500, text="boom")
        return _FakeResponse(
            200,
            {
                "model": "grok-4.5",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {},
            },
        )

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    monkeypatch.setattr("app.llm.xai.time.sleep", lambda *_: None)
    p = XAIProvider(api_key="test-key", max_retries=2, retry_backoff_seconds=0)
    out = p.chat([ChatMessage(role="user", content="hi")])
    assert out.content == "ok"
    assert calls["n"] == 2


def test_timeout_raises(monkeypatch):
    def fake_request(self, method, url, headers=None, json=None):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    monkeypatch.setattr("app.llm.xai.time.sleep", lambda *_: None)
    p = XAIProvider(api_key="test-key", max_retries=1, retry_backoff_seconds=0)
    with pytest.raises(LLMTimeoutError):
        p.chat([ChatMessage(role="user", content="hi")])


def test_non_retryable_4xx(monkeypatch):
    def fake_request(self, method, url, headers=None, json=None):
        return _FakeResponse(401, text="nope")

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    p = XAIProvider(api_key="bad", max_retries=3)
    with pytest.raises(LLMError) as ei:
        p.chat([ChatMessage(role="user", content="hi")])
    assert ei.value.status_code == 401
    assert ei.value.retryable is False


def test_tool_calling_payload(monkeypatch):
    captured = {}

    def fake_request(self, method, url, headers=None, json=None):
        captured["json"] = json
        return _FakeResponse(
            200,
            {
                "model": "grok-4.5",
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "ping", "arguments": "{}"},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {},
            },
        )

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "ping",
                "description": "ping",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    p = XAIProvider(api_key="test-key", max_retries=0)
    out = p.chat([ChatMessage(role="user", content="ping")], tools=tools, tool_choice="auto")
    assert captured["json"]["tools"] == tools
    assert out.tool_calls[0]["function"]["name"] == "ping"


def test_llm_status_endpoint(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("XAI_API_KEY", "status-key")
    get_settings.cache_clear()
    client = TestClient(create_app())
    r = client.get("/llm/status")
    assert r.status_code == 200
    assert r.json()["status"] == "configured"
    get_settings.cache_clear()
