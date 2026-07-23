"""Thin Anthropic wrapper shared by every LLM-backed agent.

Domain-specific mock fallbacks (what to say when there's no API key) live in
each agent, not here -- this module only answers two questions: "is a real
key configured?" and "make the call."
"""
from __future__ import annotations

import logging
import os
from typing import Optional

MOCK_MODE = not bool(os.environ.get("ANTHROPIC_API_KEY"))
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("ANTHROPIC_TIMEOUT_SECONDS", "20"))

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], timeout=REQUEST_TIMEOUT_SECONDS
        )
    return _client


async def complete_or_none(system: str, user_prompt: str, max_tokens: int = 1024) -> Optional[str]:
    """Returns None in mock mode -- or if a real call is configured but fails
    at runtime (timeout, rate limit, network error) -- so callers always
    have to define their own deterministic fallback rather than assuming
    "key present" means "a response is guaranteed." Without this, a real key
    that starts failing at runtime would surface as an unhandled 500 instead
    of the same graceful degradation mock mode already provides."""
    if MOCK_MODE:
        return None
    client = _get_client()
    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception:
        logger.warning("Anthropic call failed; falling back to caller's deterministic template", exc_info=True)
        return None
    return "".join(block.text for block in response.content if block.type == "text")
