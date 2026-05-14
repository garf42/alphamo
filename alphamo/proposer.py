"""LLM proposer: generates a candidate Architecture as a variation on k seeds."""

from __future__ import annotations

from typing import Any

from alphamo.errors import ProposerOutputError, parse_or_raise
from alphamo.evaluator._common import MAX_TOKENS_LONG, OPUS_MODEL, cached_system
from alphamo.prompts.proposer_prompt import PROPOSER_SYSTEM, render_seeds
from alphamo.schemas import Architecture


class Proposer:
    """Calls Opus with k seed architectures and parses the response as a new Architecture."""

    def __init__(self, client: Any, model: str = OPUS_MODEL) -> None:
        self.client = client
        self.model = model

    def propose(self, seeds: list[Architecture]) -> Architecture:
        return parse_or_raise(
            self.client,
            ProposerOutputError,
            model=self.model,
            max_tokens=MAX_TOKENS_LONG,
            thinking={"type": "adaptive"},
            system=cached_system(PROPOSER_SYSTEM),
            messages=[{"role": "user", "content": render_seeds(seeds)}],
            output_format=Architecture,
        )
