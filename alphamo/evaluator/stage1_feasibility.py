"""Stage 1 — cheap LLM feasibility + middle-class accessibility filter.

Sprint 14: routed through `BaseProvider.parse(...)` (provider abstraction).
Production default is the Fireworks provider with DeepSeek V4 Flash —
the orchestrator constructs one provider per component from
Hyperparameters and passes it in via `EvaluatorCascade`.

Stage 1 does not use reasoning (cheap-tier — no thinking config on
either provider). Caching is via `cached_system(...)` — Anthropic
emits the ephemeral marker; Fireworks concatenates the text and lets
its automatic-prefix matcher do the rest.

Sprint 8: accepts an optional `telemetry` kwarg (TelemetryContext) so
the call emits an `llm_usage` audit event with input/output/cache
token counts. None on legacy / test call sites that don't supply one.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import Stage1OutputError, TelemetryContext
from alphamo.evaluator._common import HAIKU_MODEL, MAX_TOKENS_SHORT, cached_system
from alphamo.prompts.evaluator_prompts import STAGE1_SYSTEM, render_candidate
from alphamo.providers.base import ensure_provider
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Stage1Finding


def stage1_feasibility(
    architecture: Architecture,
    client: Any,
    telemetry: TelemetryContext | None = None,
    model: str = HAIKU_MODEL,
) -> Stage1Finding:
    """Score the candidate's feasibility and middle-class accessibility.

    `client` accepts a BaseProvider directly (production path) or an
    Anthropic-shaped SDK client / MagicMock (auto-wrapped). The
    auto-wrap path is what keeps the Sprint 8 MagicMock test pattern
    working unchanged after Sprint 14's migration.
    """
    provider = ensure_provider(client)
    return provider.parse(
        error_cls=Stage1OutputError,
        component="stage1",
        telemetry=telemetry,
        model=model,
        max_tokens=MAX_TOKENS_SHORT,
        system=cached_system(STAGE1_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage1Finding,
    )
