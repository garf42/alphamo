"""Stage 1 — cheap LLM feasibility + middle-class accessibility filter.

Backed by Haiku 4.5. Uses prompt caching on the parent-goal system prompt
so the per-call cost on a hot cache lands in the ~$0.01 range the
architecture doc targets.

Sprint 8: accepts an optional `telemetry` kwarg (TelemetryContext) so
the call emits an `llm_usage` audit event with input/output/cache
token counts. None on legacy / test call sites that don't supply one.
"""

from __future__ import annotations

import anthropic

from alphamo.errors import Stage1OutputError, TelemetryContext, parse_or_raise
from alphamo.evaluator._common import HAIKU_MODEL, MAX_TOKENS_SHORT, cached_system
from alphamo.prompts.evaluator_prompts import STAGE1_SYSTEM, render_candidate
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Stage1Finding


def stage1_feasibility(
    architecture: Architecture,
    client: anthropic.Anthropic,
    telemetry: TelemetryContext | None = None,
) -> Stage1Finding:
    """Score the candidate's feasibility and middle-class accessibility."""
    return parse_or_raise(
        client,
        Stage1OutputError,
        component="stage1",
        telemetry=telemetry,
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS_SHORT,
        system=cached_system(STAGE1_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage1Finding,
    )
