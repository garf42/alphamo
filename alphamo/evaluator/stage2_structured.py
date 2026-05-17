"""Stage 2 — structured criteria evaluation against the parent goal.

Backed by Sonnet 4.6. Scores three sub-criteria (one-person threshold,
billion-dollar potential, labor separation) and aggregates them.
"""

from __future__ import annotations

import anthropic

from alphamo.errors import Stage2OutputError, TelemetryContext, parse_or_raise
from alphamo.evaluator._common import (
    MAX_TOKENS_MEDIUM,
    SONNET_MODEL,
    cached_system,
)
from alphamo.prompts.evaluator_prompts import STAGE2_SYSTEM, render_candidate
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Stage2Finding


def stage2_structured(
    architecture: Architecture,
    client: anthropic.Anthropic,
    telemetry: TelemetryContext | None = None,
) -> Stage2Finding:
    """Score the candidate against the parent goal's structural criteria."""
    return parse_or_raise(
        client,
        Stage2OutputError,
        component="stage2",
        telemetry=telemetry,
        model=SONNET_MODEL,
        max_tokens=MAX_TOKENS_MEDIUM,
        system=cached_system(STAGE2_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage2Finding,
    )
