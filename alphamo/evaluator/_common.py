"""Shared constants and helpers for the cascade stages.

Model IDs are picked to match the architecture doc's cost gradient
($0.01 / $0.05 / $0.20 per stage). Override by injecting a different model
into the cascade if you prefer all-Opus or all-Sonnet.

Token caps are sized for adaptive thinking. Opus 4.7 with adaptive can
spend substantial budget on internal reasoning; the cap must cover BOTH
the reasoning tokens AND the structured-output JSON. A too-tight cap
truncates the JSON mid-string and surfaces as a Pydantic ValidationError
from inside the SDK's parse_response.
"""

from __future__ import annotations

from typing import Any

HAIKU_MODEL = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"

MAX_TOKENS_SHORT = 2048
MAX_TOKENS_MEDIUM = 4096
MAX_TOKENS_LONG = 8192
MAX_TOKENS_XLONG = 16384


def cached_system(text: str) -> list[dict[str, Any]]:
    """Render a single system text block with an ephemeral cache breakpoint.

    Parent-goal context is byte-stable across every call, so caching it
    drops the per-call cost to ~10% of base input price after the first
    request.
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def prepare_cached_blocks(texts: list[str]) -> list[dict[str, Any]]:
    """Render multiple text blocks as a layered cached system prompt.

    Each non-empty text becomes its own system text block with an
    `ephemeral` cache_control marker, producing one cache breakpoint
    per block. Anthropic caches up to 4 breakpoints per request;
    Sprint 12's two-block design (corpus + existing system) uses 2 of
    those 4 slots with comfortable headroom.

    Why layered rather than concatenated:
      - Corpus revisions invalidate only the corpus block's cache,
        not the existing PROPOSER_SYSTEM cache (and vice versa).
        Important during development when one layer iterates faster
        than the other.
      - Stage 3's 9 framings share the SAME corpus block bytes (one
        cache write, 9 reads) but each has its OWN per-framing
        system block. Two independent cache layers per framing.

    Empty strings are filtered out — passing an empty corpus subset
    (e.g., when the corpus directory is missing in a test sandbox)
    degrades gracefully to a single-block prompt rather than failing.

    Sprint 12: model-agnostic by design. The `cache_control` shape
    is Anthropic-specific; if a future model migration requires a
    different cache mechanism, this is the only file that needs
    updating.
    """
    return [
        {
            "type": "text",
            "text": text,
            "cache_control": {"type": "ephemeral"},
        }
        for text in texts
        if text
    ]
