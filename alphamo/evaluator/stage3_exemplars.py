"""Stage 3 — deep structural comparison against the exemplar library.

Backed by Opus 4.7 with adaptive thinking. The exemplar library is part of
the cached system prompt, so the only volatile bytes per call are the
candidate description in the user turn.
"""

from __future__ import annotations

import anthropic

from alphamo.errors import Stage3OutputError, parse_or_raise
from alphamo.evaluator._common import MAX_TOKENS_LONG, OPUS_MODEL, cached_system
from alphamo.prompts.evaluator_prompts import STAGE3_SYSTEM, render_candidate
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Stage3Finding


def stage3_exemplars(
    architecture: Architecture, client: anthropic.Anthropic
) -> Stage3Finding:
    """Score the candidate's structural similarity to its closest exemplar."""
    return parse_or_raise(
        client,
        Stage3OutputError,
        model=OPUS_MODEL,
        max_tokens=MAX_TOKENS_LONG,
        thinking={"type": "adaptive"},
        system=cached_system(STAGE3_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage3Finding,
    )
