"""Thin Anthropic wrapper shared by every LLM-backed agent.

Domain-specific mock fallbacks (what to say when there's no API key) live in
each agent, not here -- this module only answers two questions: "is a real
key configured?" and "make the call."
"""
from __future__ import annotations

import os
from typing import Optional

MOCK_MODE = not bool(os.environ.get("ANTHROPIC_API_KEY"))
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def complete_or_none(system: str, user_prompt: str, max_tokens: int = 1024) -> Optional[str]:
    """Returns None in mock mode so callers can apply their own deterministic
    fallback instead of silently getting placeholder LLM text."""
    if MOCK_MODE:
        return None
    client = _get_client()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
