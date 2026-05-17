"""LLM proposer: generates a candidate Architecture from k island-drawn seeds.

Sprint 3 redesign: empty seed lists are an invariant violation. Bootstrap
inserts the trivial seed into every island at gen 0; reset reseeds wiped
islands with a copy of a surviving island's best — so the sampler always
has at least one alive row to return. `propose([])` raises ValueError.

Sprint 7 model routing: defaults to SONNET_MODEL (was OPUS_MODEL).
Sprint 6's component-synthesis prompt provides enough structural
scaffolding (3-step decomposition / diagnosis / synthesis with a fixed
component vocabulary) that Sonnet should perform comparably to Opus on
the proposer task at ~60% of Opus cost. Stage 3 adversarial scrutiny
stays on Opus because the cascade's value depends on substantive
falsifiable critique with statute citations — empirically observed in
run-ed6e72e1 gen-12 §203(b)(4) finding that required reasoning depth
Sonnet wouldn't produce reliably.

Sprint 7 token cap: max_tokens bumped from MAX_TOKENS_LONG (8192) to
MAX_TOKENS_XLONG (16384). Empirical evidence from run-c8b5144e showed
11 of 30 generations silently dropping at the 8192 cap due to JSON
truncation when adaptive-thinking budget plus structured-output JSON
exceeded the limit. Sprint 6's longer prompt (component-synthesis
reasoning steps plus per-candidate concerns blocks up to 4000 chars
each) made the 8192 cap borderline. The Research module already uses
XLONG for similar reasoning-heavy work; aligning the proposer with that.
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
    SONNET_MODEL,
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
    """Calls Sonnet with k island-drawn candidates and parses the response
    as a new Architecture.

    The proposer sees ONLY candidates from the current island (Sprint 3 /
    FunSearch §A.1 alignment) — no global reference library. Sprint 7
    moved the default model from Opus to Sonnet on the rationale that
    Sprint 6's component-synthesis prompt structure (fixed component
    vocabulary, explicit 3-step reasoning) constrains the task enough
    for Sonnet to perform comparably at lower cost.
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
            thinking={"type": "adaptive"},
            system=cached_system(PROPOSER_SYSTEM),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )
