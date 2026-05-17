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

Sprint 9 thinking budget: explicit budget cap replaces adaptive.

  thinking = {"type": "enabled", "budget_tokens": 6000}

Sprint 7's max_tokens=16384 bump was insufficient on its own. Adaptive
thinking scales with task complexity, and Sprint 6's component-
synthesis prompt is sufficiently complex (3-step decomposition /
diagnosis / synthesis with per-candidate concerns context) to trigger
the thinking budget consuming the entire token cap before the JSON
output is produced. Empirical evidence from run-551c7c42 (Sonnet
diagnostic): 20% of generations on island 5 failed with
stop_reason=max_tokens and content_blocks=['thinking'] only — no
JSON output reached.

Bounded thinking gives a hard ceiling: 6000 tokens for reasoning,
~10K for the JSON output, eliminating the failure mode by design.
Sprint 4's SDK retry layer continues to absorb transient API
failures independently.

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


# Sprint 9: explicit thinking budget on the proposer. Adaptive scaling
# under Sprint 6's component-synthesis prompt consumed the whole token
# cap on the harder islands; bounded thinking gives a deterministic
# ceiling. 6000 leaves ~10K for the JSON output within the 16384 cap.
PROPOSER_THINKING_BUDGET_TOKENS = 6000


class Proposer:
    """Calls Opus with k island-drawn candidates and parses the response
    as a new Architecture.

    The proposer sees ONLY candidates from the current island (Sprint 3 /
    FunSearch §A.1 alignment) — no global reference library. Sprint 9
    reverted the default model from Sonnet back to Opus 4.7 (see module
    docstring for the late-2025-cutoff + caching rationale).
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
            # Sprint 9: bounded thinking. Replaces Sprint 6+7's adaptive.
            # See module docstring + run-551c7c42 diagnostic for why
            # adaptive failed; bounded budget eliminates the
            # thinking-eats-the-whole-cap failure mode by design.
            thinking={
                "type": "enabled",
                "budget_tokens": PROPOSER_THINKING_BUDGET_TOKENS,
            },
            system=cached_system(PROPOSER_SYSTEM),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )
