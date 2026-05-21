"""LLM proposer: generates a candidate Architecture from k island-drawn seeds.

Sprint 14: routed through `BaseProvider.parse(...)`. Production default
is the Fireworks provider with DeepSeek V4 Flash. The Anthropic path
remains available for per-component routing (set
`hp.provider_proposer = "anthropic"`).

Sprint 14 thinking config:
  Anthropic — `thinking={"type": "enabled", "budget_tokens": 6000}`
              (the Sprint 11 bounded-thinking design that Sonnet 4.6
              accepts; Opus 4.7 had rejected it, forcing Sprint 10's
              adaptive revert)
  Fireworks — `reasoning_effort="high"` (DeepSeek V4 has three modes:
              Non-think / Think High / Think Max; the Sprint 14 audit
              decision was to default to High, not Max, until empirical
              evidence justifies Max)

Both are passed on every call; each provider reads what it needs and
ignores the other. The Sprint 9 → Sprint 10 → Sprint 11 model-routing
arc converged on bounded thinking as the run-551c7c42-style failure
mode prevention; on Fireworks there's no budget_tokens equivalent, so
the deterministic ceiling property is lost. The smoke test must catch
any regression there.

Sprint 7 token cap: max_tokens stays at MAX_TOKENS_XLONG (16384).
Sprint 3 redesign: empty seed lists are an invariant violation —
bootstrap inserts the trivial seed into every island at gen 0.

PROPOSER_VERSION bumped v7 → v8 in Sprint 14 because the proposer sees
materially different input (provider-translated cache structure, no
budget_tokens ceiling on Fireworks) and the model class changed
(Sonnet 4.6 → DeepSeek V4 Flash).
"""

from __future__ import annotations

from typing import Any

from alphamo.corpus import load_proposer_subset
from alphamo.errors import (
    ProposerOutputError,
    TelemetryContext,
)
from alphamo.evaluator._common import (
    MAX_TOKENS_XLONG,
    SONNET_MODEL,
    prepare_cached_blocks,
)
from alphamo.prompts.proposer_prompt import (
    PROPOSER_SYSTEM,
    render_seeds,
    render_seeds_from_architectures,
)
from alphamo.providers.base import ensure_provider
from alphamo.sampler import Seed
from alphamo.schemas import Architecture

# Sprint 11: bounded thinking budget on the Anthropic proposer. Kept as
# the Anthropic-side knob; Fireworks uses `reasoning_effort` instead.
# 6000 leaves ~10K for the JSON output within the 16384 cap.
PROPOSER_THINKING_BUDGET_TOKENS = 6000


class Proposer:
    """Calls an LLM with k island-drawn candidates and parses the response
    as a new Architecture.

    The proposer sees ONLY candidates from the current island (Sprint 3 /
    FunSearch §A.1 alignment) — no global reference library. Sprint 14
    moved the default routing to Fireworks/DeepSeek V4 Flash for cost.
    """

    def __init__(
        self,
        client: Any,
        model: str = SONNET_MODEL,
        reasoning_effort: str | None = "high",
    ) -> None:
        # ensure_provider auto-wraps an Anthropic-shaped client / MagicMock
        # into AnthropicProvider — preserves the Sprint 8 mock pattern.
        self.provider = ensure_provider(client)
        self.model = model
        self.reasoning_effort = reasoning_effort

    def propose(
        self,
        seeds: list[Seed] | list[Architecture],
        telemetry: TelemetryContext | None = None,
    ) -> Architecture:
        if not seeds:
            raise ValueError(
                "propose() requires at least one seed — empty islands are an "
                "invariant violation post-bootstrap"
            )
        if isinstance(seeds[0], Seed):
            user_content = render_seeds(seeds)  # type: ignore[arg-type]
        else:
            user_content = render_seeds_from_architectures(seeds)  # type: ignore[arg-type]
        return self.provider.parse(
            error_cls=ProposerOutputError,
            component="proposer",
            telemetry=telemetry,
            model=self.model,
            max_tokens=MAX_TOKENS_XLONG,
            thinking={
                "type": "enabled",
                "budget_tokens": PROPOSER_THINKING_BUDGET_TOKENS,
            },
            reasoning_effort=self.reasoning_effort,
            system=prepare_cached_blocks(
                [load_proposer_subset(), PROPOSER_SYSTEM]
            ),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )
