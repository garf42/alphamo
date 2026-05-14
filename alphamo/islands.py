"""Islands manager: m sub-populations with periodic reset of weakest m/2.

The FunSearch trick: split the population into m islands, evolve each
independently, and periodically wipe the bottom half — reseeding them with
copies of the top programs from the surviving islands. This prevents global
mode collapse without losing the discoveries the strong islands have made.

Every DB operation is scoped to a single `run_id` so two runs against the
same database stay isolated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphamo.database import ProgramsDB

from alphamo.schemas import Architecture, Scores


@dataclass(frozen=True)
class ResetEvent:
    """Audit record of one island-reset cycle."""

    weak_islands: list[int]
    strong_islands: list[int]
    seed_program_ids: list[int]


class IslandsManager:
    """Wraps a ProgramsDB with m islands, periodic resets, and uniform sampling."""

    def __init__(
        self,
        db: "ProgramsDB",
        run_id: str,
        num_islands: int = 8,
        reset_every_generations: int = 20,
        top_seed_count: int = 5,
        rng: random.Random | None = None,
    ) -> None:
        if num_islands < 2:
            raise ValueError("need at least 2 islands for reset to make sense")
        if not run_id:
            raise ValueError("run_id is required for IslandsManager")
        self.db = db
        self.run_id = run_id
        self.num_islands = num_islands
        self.reset_every_generations = reset_every_generations
        self.top_seed_count = top_seed_count
        self.rng = rng or random.Random()

    def seed_all_islands(self, starters: list[tuple[Architecture, Scores]]) -> None:
        """Insert each starter into every island as generation-0 alive candidates."""
        for island_id in range(self.num_islands):
            for architecture, scores in starters:
                self.db.insert(
                    architecture,
                    scores,
                    run_id=self.run_id,
                    island_id=island_id,
                    generation=0,
                )

    def pick_island(self) -> int:
        """Uniform-random island id for the next inner-loop step."""
        return self.rng.randrange(self.num_islands)

    def rank_by_mean_fitness(self) -> list[int]:
        """Island ids sorted by mean alive fitness in this run, highest first."""
        means = self.db.mean_fitness_per_island(self.num_islands, run_id=self.run_id)
        return sorted(range(self.num_islands), key=lambda i: means[i], reverse=True)

    def maybe_reset(self, current_generation: int) -> ResetEvent | None:
        """At the reset cadence, wipe the bottom m/2 islands and reseed from the top."""
        if current_generation <= 0:
            return None
        if current_generation % self.reset_every_generations != 0:
            return None

        ranked = self.rank_by_mean_fitness()
        half = self.num_islands // 2
        strong = ranked[:half]
        weak = ranked[half:]

        seeds = self.db.top_programs_from_islands(
            strong, self.top_seed_count, run_id=self.run_id
        )
        seed_ids = [s.id for s in seeds]
        if not seed_ids:
            return None

        for island_id in weak:
            self.db.reset_island(island_id, seed_ids, run_id=self.run_id)

        return ResetEvent(
            weak_islands=weak, strong_islands=strong, seed_program_ids=seed_ids
        )

    def diversity_summary(self) -> dict[int, float]:
        """Per-island diversity metric for this run, keyed by island id."""
        return {
            i: self.db.diversity_metric(i, run_id=self.run_id)
            for i in range(self.num_islands)
        }
