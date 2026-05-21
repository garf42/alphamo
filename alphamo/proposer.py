"""LLM proposer: generates a candidate Architecture from k island-drawn seeds.

Sprint 3 redesign: empty seed lists are an invariant violation. Bootstrap
inserts the trivial seed into every island at gen 0; reset reseeds wiped
islands with a copy of a surviving island's best — so the sampler always
has at least one alive row to return. `propose([])` raises ValueError.

Sprint 11 routing: SONNET_MODEL. The Sprint 9 → Sprint 10 cycle landed on
Opus 4.7 with adaptive thinking because Opus rejected the
`{"type": "enabled", "budget_tokens": N}` shape. Sprint 11 removes Opus
entirely (cost-driven: $115-135 per 200-gen run on Sonnet vs ~$190 on
Opus). Cost loss from the 200-gen target was unaffordable on Opus.

Sonnet 4.6 ACCEPTS the bounded thinking form that Sprint 9 attempted —
the rejection was Opus-specific. Sprint 11 lands what Sprint 9 wanted
all along: bounded thinking on a Sonnet-based proposer.

Tradeoffs accepted:
  - Sonnet's reliable knowledge cutoff is Aug 2025 (vs Opus's Jan 2026).
    The current-moment grounding gap concentrates on the
    `current_moment_dependency` Stage 3 framing; proposer reasoning is
    less cutoff-sensitive (structural component synthesis, not
    current-event recall).
  - Empirically untested at 200-gen scale. The smoke test (5 gens × 2
    islands) validates the routing + thinking config before any longer
    run commits the budget.

Sprint 11 thinking config: bounded.

  thinking = {"type": "enabled", "budget_tokens": 6000}

6000 thinking + ~10000 for output within the 16384 max_tokens cap.
Eliminates the run-551c7c42-style failure mode (Sonnet adaptive
thinking consuming the entire token cap before JSON output reached
parse_response) by design. The Sprint 9 design intent was structurally
correct; it just couldn't be tested on Opus 4.7.

Sprint 7 token cap: max_tokens stays at MAX_TOKENS_XLONG (16384).
"""

from __future__ import annotations

from typing import Any

from alphamo.corpus import load_proposer_subset
from alphamo.errors import (
    ProposerOutputError,
    TelemetryContext,
    parse_or_raise,
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
from alphamo.sampler import Seed
from alphamo.schemas import Architecture


# Sprint 11: bounded thinking budget on the proposer. The Sprint 9
# design intent (deterministic ceiling on reasoning) lands now that
# the model is Sonnet (Opus 4.7 had rejected the `enabled` form).
# 6000 leaves ~10K for the JSON output within the 16384 cap.
PROPOSER_THINKING_BUDGET_TOKENS = 6000


class Proposer:
    """Calls Sonnet with k island-drawn candidates and parses the response
    as a new Architecture.

    The proposer sees ONLY candidates from the current island (Sprint 3 /
    FunSearch §A.1 alignment) — no global reference library. Sprint 11
    moved the default model from Opus 4.7 (Sprint 9/10) to Sonnet 4.6
    as part of the no-Opus cost-reduction directive. Sprint 9's bounded
    thinking config — rejected by Opus 4.7's API and reverted to
    adaptive in Sprint 10 — is the intended config here; Sonnet 4.6
    accepts it.
    """

    def __init__(self, client: Any, model: str = SONNET_MODEL) -> None:
        self.client = client
        self.model = model

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
        return parse_or_raise(
            self.client,
            ProposerOutputError,
            component="proposer",
            telemetry=telemetry,
            model=self.model,
            # Sprint 7: bumped from MAX_TOKENS_LONG (8192) to
            # MAX_TOKENS_XLONG (16384). See module docstring for the
            # empirical rationale (run-c8b5144e silent drops).
            max_tokens=MAX_TOKENS_XLONG,
            # Sprint 11: bounded thinking on Sonnet 4.6 — the Sprint 9
            # design intent now that Opus 4.7's API rejection no
            # longer constrains the config. Prevents the
            # run-551c7c42-style failure (Sonnet adaptive thinking
            # consuming the entire token cap before JSON output) by
            # design. Sonnet 4.6 accepts this shape (unlike Opus 4.7,
            # which forced the Sprint 10 revert to adaptive).
            thinking={
                "type": "enabled",
                "budget_tokens": PROPOSER_THINKING_BUDGET_TOKENS,
            },
            # Sprint 12: layered cached system prompt — corpus subset
            # (compositional substrate, ~44K tokens) before the
            # existing PROPOSER_SYSTEM block. Two cache breakpoints;
            # corpus block is byte-stable across the run, PROPOSER_
            # SYSTEM is byte-stable within a PROPOSER_VERSION epoch,
            # so each layer caches independently and revisions to
            # either layer don't invalidate the other.
            system=prepare_cached_blocks(
                [load_proposer_subset(), PROPOSER_SYSTEM]
            ),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )


