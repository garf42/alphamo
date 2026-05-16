"""LLM proposer: generates a candidate Architecture from reference exemplars +
optional island-drawn seeds.

Sprint 2 redesign: empty seed lists are valid. When the island is empty
(fresh run, or just post-reset), the proposer bootstraps from the
reference exemplar set alone — see `render_seeds([])`.
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
    """Calls Opus with k island seeds (or zero, for bootstrap) and parses the
    response as a new Architecture.

    Reference exemplars are baked into the prompt template — the caller
    passes only the island-drawn candidates (which may be empty for the
    bootstrap case).
    """

    def __init__(self, client: Any, model: str = OPUS_MODEL) -> None:
        self.client = client
        self.model = model

    def propose(self, seeds: list[Seed] | list[Architecture]) -> Architecture:
        # Empty list is valid: bootstrap from reference exemplars alone.
        if seeds and isinstance(seeds[0], Seed):
            user_content = render_seeds(seeds)  # type: ignore[arg-type]
        elif seeds:
            user_content = render_seeds_from_architectures(seeds)  # type: ignore[arg-type]
        else:
            user_content = render_seeds([])
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
