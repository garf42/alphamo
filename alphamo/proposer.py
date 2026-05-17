"""LLM proposer: generates a candidate Architecture from k island-drawn seeds.

Sprint 3 redesign: empty seed lists are an invariant violation. Bootstrap
inserts the trivial seed into every island at gen 0; reset reseeds wiped
islands with a copy of a surviving island's best — so the sampler always
has at least one alive row to return. `propose([])` raises ValueError.

Sprint 9 model routing: defaults to OPUS_MODEL. Sprint 7 had routed the
proposer to Sonnet on the rationale that Sprint 6's component-synthesis
prompt structure would constrain the task enough for Sonnet to perform
comparably at lower cost. Sprint 9 reverts to Opus because:

  (a) Research is architecturally isolated from the proposer (research
      output goes only to the meta-curator; see research.py docstring),
      so the proposer's only source of current-moment grounding is the
      model's own training data.
  (b) Opus 4.7's reliable knowledge cutoff is Jan 2026; Sonnet 4.6's
      is Aug 2025 — a 5-month gap covering late-2025 agentic AI
      pattern maturation that's load-bearing for the proposer's
      reasoning about novel value-capture configurations.
  (c) Prompt caching is already wired on the proposer (cached_system
      on the 1268-token system prefix, above Anthropic's 1024-token
      Sonnet/Opus cache minimum). Cache hits drop input cost to 0.1×
      base, making the Opus premium ~25% at scale rather than the
      naive 5× you'd see without caching.

Curator and Research stay on SONNET_MODEL (Sprint 7 routing for those
unchanged — structured classification and information-gathering tasks
where Sonnet's reasoning is sufficient).

Sprint 10 thinking config: adaptive on Opus 4.7.

  thinking = {"type": "adaptive"}

Sprint 9 attempted to bound the thinking budget with
`{"type": "enabled", "budget_tokens": 6000}` — Opus 4.7 rejects this
shape with HTTP 400: "thinking.type.enabled is not supported for this
model. Use thinking.type.adaptive and output_config.effort to control
thinking behavior." The integer-budget thinking config was a Sonnet-
era pattern; Opus 4.7 requires adaptive.

The Sonnet-specific failure mode that motivated Sprint 9's bounded
budget (run-551c7c42: thinking consuming the entire 16384 token cap
before JSON output reached parse_response) was empirically a Sonnet
issue. Stage 3 has been running adaptive Opus thinking across 9
framings per candidate for many runs without that failure mode
surfacing — Opus 4.7's adaptive scheduler handles the output budget
correctly.

If proposer failures do emerge on Opus 4.7's adaptive mode, dial in
`output_config={"effort": "medium"}` (or "low") for more conservative
thinking. Defaulting to no output_config = high effort, the
Anthropic-documented recommendation for Opus 4.7.

Sprint 7 token cap: max_tokens stays at MAX_TOKENS_XLONG (16384).
The Research module uses the same cap for similar reasoning-heavy
work.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import (
    ProposerOutputError,
    TelemetryContext,
    parse_or_raise,
)
from alphamo.evaluator._common import (
    MAX_TOKENS_XLONG,
    OPUS_MODEL,
    cached_system,
)
from alphamo.prompts.proposer_prompt import (
    PROPOSER_SYSTEM,
    render_seeds,
    render_seeds_from_architectures,
)
from alphamo.sampler import Seed
from alphamo.schemas import Architecture


class Proposer:
    """Calls Opus with k island-drawn candidates and parses the response
    as a new Architecture.

    The proposer sees ONLY candidates from the current island (Sprint 3 /
    FunSearch §A.1 alignment) — no global reference library. Sprint 9
    reverted the default model from Sonnet back to Opus 4.7 (see module
    docstring for the late-2025-cutoff + caching rationale). Sprint 10
    reverted the Sprint 9 bounded-thinking config to adaptive because
    Opus 4.7 doesn't support the `{"type": "enabled", "budget_tokens":
    N}` shape — see module docstring.
    """

    def __init__(self, client: Any, model: str = OPUS_MODEL) -> None:
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
            # Sprint 10: Opus 4.7 requires adaptive thinking; the
            # budget_tokens form is deprecated and the API rejects it
            # with HTTP 400. Stage 3 uses the same adaptive Opus
            # thinking config and runs without failures. If proposer
            # failures emerge, dial in output_config.effort
            # (medium/low) for more conservative thinking.
            thinking={"type": "adaptive"},
            system=cached_system(PROPOSER_SYSTEM),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )

