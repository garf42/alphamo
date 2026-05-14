"""Shared constants and helpers for the cascade stages.

Model IDs are picked to match the architecture doc's cost gradient
($0.01 / $0.05 / $0.20 per stage). Override by injecting a different model
into the cascade if you prefer all-Opus or all-Sonnet.
"""

from __future__ import annotations

from typing import Any

HAIKU_MODEL = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"

MAX_TOKENS_SHORT = 1024
MAX_TOKENS_MEDIUM = 2048
MAX_TOKENS_LONG = 4096


def cached_system(text: str) -> list[dict[str, Any]]:
    """Render a single system text block with an ephemeral cache breakpoint.

    Parent-goal context is byte-stable across every call, so caching it
    drops the per-call cost to ~10% of base input price after the first
    request.
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
