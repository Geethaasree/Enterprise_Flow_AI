"""Live Grok call (requires SuperGrok OAuth or XAI_API_KEY)."""

from __future__ import annotations

import os

import pytest

from app.llm import ChatMessage, XAIProvider

pytestmark = pytest.mark.skipif(
    os.getenv("EF_LIVE_LLM") != "1",
    reason="Set EF_LIVE_LLM=1 to run live xAI calls",
)


def test_live_generation():
    p = XAIProvider(model=os.getenv("XAI_MODEL", "grok-4.5"), max_retries=1, timeout_seconds=90)
    out = p.chat(
        [
            ChatMessage(role="system", content="Reply with exactly one short word."),
            ChatMessage(role="user", content="Say pong"),
        ],
        max_tokens=16,
        temperature=0,
    )
    assert out.content
    assert out.usage.total_tokens >= 0
    assert out.model


def test_live_json_mode():
    p = XAIProvider(model=os.getenv("XAI_MODEL", "grok-4.5"), max_retries=1, timeout_seconds=90)
    out = p.chat_json(
        [
            ChatMessage(
                role="system",
                content='Return JSON with keys "ok" (boolean true) and "echo" (string).',
            ),
            ChatMessage(role="user", content="echo=enterprise"),
        ],
        max_tokens=64,
    )
    assert out.content
    import json

    data = json.loads(out.content)
    assert data.get("ok") is True
