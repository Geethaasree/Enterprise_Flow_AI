"""Resolve xAI credentials without printing secrets."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_xai_api_key(
    explicit: str | None = None,
    *,
    hermes_auth_path: Path | None = None,
) -> tuple[str, str]:
    """
    Return (api_key, source).

    Order:
      1. explicit argument
      2. XAI_API_KEY env
      3. Hermes SuperGrok OAuth access_token (~/.hermes/auth.json)
    """
    if explicit and explicit.strip():
        return explicit.strip(), "explicit"

    env = os.getenv("XAI_API_KEY", "").strip()
    if env:
        return env, "env"

    path = hermes_auth_path or Path.home() / ".hermes" / "auth.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            token = (
                data.get("providers", {})
                .get("xai-oauth", {})
                .get("tokens", {})
                .get("access_token")
            )
            if isinstance(token, str) and token.strip():
                return token.strip(), "hermes-xai-oauth"
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("failed reading hermes xai oauth credentials: %s", type(exc).__name__)

    raise RuntimeError(
        "No xAI credentials. Set XAI_API_KEY or configure Hermes xai-oauth (hermes auth)."
    )
