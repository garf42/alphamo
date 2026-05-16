"""LLM proposer: generates a candidate Architecture from k island-drawn seeds.

Sprint 3 redesign: empty seed lists are an invariant violation. Bootstrap
inserts the trivial seed into every island at gen 0; reset reseeds wiped
islands with a copy of a surviving island's best — so the sampler always
has at least one alive row to return. `propose([])` raises ValueError.
"""

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
    """Calls Opus with k island-drawn candidates and parses the response
    as a new Architecture.

    The proposer sees ONLY candidates from the current island (Sprint 3 /
    FunSearch §A.1 alignment) — no global reference library.
    """

    def __init__(self, client: Any, model: str = OPUS_MODEL) -> None:
        self.client = client
        self.model = model

    def propose(self, seeds: list[Seed] | list[Architecture]) -> Architecture:
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
            model=self.model,
            max_tokens=MAX_TOKENS_LONG,
            thinking={"type": "adaptive"},
            system=cached_system(PROPOSER_SYSTEM),
            messages=[{"role": "user", "content": user_content}],
            output_format=Architecture,
        )
