"""Inner-loop sampler: softmax-weighted draw of k seed candidates from an island."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphamo.database import ProgramsDB

from alphamo.schemas import Architecture


def _softmax(values: list[float], temperature: float) -> list[float]:
    scaled = [v / temperature for v in values]
    max_v = max(scaled)
    exps = [math.exp(v - max_v) for v in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def _weighted_sample_without_replacement(
    weights: list[float],
    k: int,
    rng: random.Random | None = None,
) -> list[int]:
    if rng is None:
        rng = random.Random()
    remaining = list(enumerate(weights))
    result: list[int] = []
    for _ in range(min(k, len(remaining))):
        total = sum(w for _, w in remaining)
        threshold = rng.random() * total
        cumulative = 0.0
        for pos, (idx, w) in enumerate(remaining):
            cumulative += w
            if cumulative >= threshold:
                result.append(idx)
                remaining.pop(pos)
                break
    return result


class Sampler:
    """Softmax-weighted draw of k seed candidates from a Programs DB island.

    Zero-fitness candidates (those that failed the middle-class filter) are
    excluded before weighting so they can never seed a new generation. When
    `run_id` is set, sampling is restricted to that run's candidates — the
    sampler will not draw a seed from a prior run's population.
    """

    def __init__(
        self,
        db: "ProgramsDB",
        temperature: float = 1.0,
        pool_size: int = 8,
        rng: random.Random | None = None,
        run_id: str | None = None,
    ) -> None:
        self.db = db
        self.temperature = temperature
        self.pool_size = pool_size
        self.rng = rng or random.Random()
        self.run_id = run_id

    def draw(self, island_id: int, k: int = 2) -> list[Architecture]:
        """Return k architectures sampled by fitness-weighted softmax."""
        rows = self.db.top_k_in_island(
            island_id=island_id, k=self.pool_size, run_id=self.run_id
        )
        rows = [r for r in rows if r.fitness > 0.0]
        if not rows:
            return []
        if len(rows) <= k:
            return [Architecture(**r.architecture_spec) for r in rows]
        weights = _softmax([r.fitness for r in rows], self.temperature)
        indices = _weighted_sample_without_replacement(weights, k, rng=self.rng)
        return [Architecture(**rows[i].architecture_spec) for i in indices]
