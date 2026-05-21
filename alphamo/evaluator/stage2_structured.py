"""Stage 2 — structured criteria evaluation against the parent goal.

Sprint 14: routed through `BaseProvider.parse(...)`. Production default
is Fireworks/DeepSeek V4 Flash. No reasoning config — Stage 2 is
structured-classification work that doesn't benefit from extended
thinking. Caching is via `cached_system(...)`.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import Stage2OutputError, TelemetryContext
from alphamo.evaluator._common import (
    MAX_TOKENS_MEDIUM,
    SONNET_MODEL,
    cached_system,
)
from alphamo.prompts.evaluator_prompts import STAGE2_SYSTEM, render_candidate
from alphamo.providers.base import ensure_provider
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Stage2Finding


def stage2_structured(
    architecture: Architecture,
    client: Any,
    telemetry: TelemetryContext | None = None,
    model: str = SONNET_MODEL,
) -> Stage2Finding:
    """Score the candidate against the parent goal's structural criteria."""
    provider = ensure_provider(client)
    return provider.parse(
        error_cls=Stage2OutputError,
        component="stage2",
        telemetry=telemetry,
        model=model,
        max_tokens=MAX_TOKENS_MEDIUM,
        system=cached_system(STAGE2_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage2Finding,
    )
