"""LLM proposer: generates a candidate Architecture as a variation on k seeds."""

from __future__ import annotations

from typing import Any

from alphamo.errors import ProposerOutputError, parse_or_raise
from alphamo.evaluator._common import MAX_TOKENS_LONG, OPUS_MODEL, cached_system
from alphamo.prompts.proposer_prompt import (
    PROPOSER_SYSTEM,
    render_seeds,
    render_seeds_from_architectures,
)
from alphamo.sampler import Seed
from alphamo.schemas import Architecture


class Proposer:
    """Calls Opus with k seed architectures and parses the response as a new Architecture.

    Phase 2 (per AlphaEvolve §2.2): seeds carry their per-dimension scores so
    the prompt can render score headers above each prior program. Callers
    pass `list[Seed]`. A back-compat overload also accepts `list[Architecture]`
    for ad-hoc usage that doesn't have score data.
    """

    def __init__(self, client: Any, model: str = OPUS_MODEL) -> None:
        self.client = client
        self.model = model

    def propose(self, seeds: list[Seed] | list[Architecture]) -> Architecture:
        if not seeds:
            raise ValueError("propose() requires at least one seed")
        if isinstance(seeds[0], Seed):
            user_content = render_seeds(seeds)  # type: ignore[arg-type]
        else:
            user_content = render_seeds_from_architectures(seeds)  # type: ignore[arg-type]
        return parse_or_raise(
            self.client,
            ProposerOutputError,
            model=self.model,
            max_tokens=MAX_TOKENS_LONG,
            thinking={"type": "adaptive"},
            system=cached_system(PROPOSER_SYSTEM),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )
