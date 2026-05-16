"""Islands manager: m sub-populations with periodic FunSearch-style reset.

The FunSearch trick (Nature 2023, §A.1 Methods):
  "Every 4 h, we discard all the programs from the m/2 islands whose
   best instances have the lowest score. Each of these islands is then
   seeded with a single program, obtained by first choosing one of the
   surviving m/2 islands uniformly at random and then retrieving the
   best program from it."

Three things to note about FunSearch's spec, all observed by Sprint 3's
implementation:
  - PER-WEAK-ISLAND INDEPENDENT DRAW. Each dying island independently
    samples one surviving island uniformly. Two dying islands can reseed
    from the same surviving island or from different ones; the draws are
    independent. Pre-Sprint-3 code pulled a shared top-k across all
    surviving islands and copied that fixed set to every dying island —
    a divergence from the spec that propagated the surviving population's
    centroid rather than allowing genuinely independent reseed paths.
  - SINGLE PROGRAM, not top-k. One program copied per dying island.
  - BEST OF THE CHOSEN ISLAND, not best across the surviving half.

Sprint 3 redesign: islands are bootstrapped with a copy of the trivial
seed (`exemplar_library.TRIVIAL_SEED`) at gen 0 by the orchestrator's
`_bootstrap_islands()`. From gen 1 onward the sampler always has at
least one alive row to return; the sampler's empty-list safety net
remains as a defence-in-depth invariant but should never fire in
normal flow.

Every DB operation is scoped to a single `run_id` so two runs against
the same database stay isolated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphamo.database import ProgramsDB


@dataclass(frozen=True)
class ResetEvent:
    """Audit record of one island-reset cycle.

    `source_islands[i]` is the surviving island that supplied
    `seed_program_ids[i]` for `weak_islands[i]`. The three lists are
    parallel: index i across all three describes a single weak-island
    reseed action.
    """

    weak_islands: list[int]
    strong_islands: list[int]
    source_islands: list[int]
    seed_program_ids: list[int]


class IslandsManager:
    """Wraps a ProgramsDB with m islands, FunSearch-style periodic reset,
    and uniform sampling."""

    def __init__(
        self,
        db: "ProgramsDB",
        run_id: str,
        num_islands: int = 8,
        reset_every_generations: int = 10,
        top_seed_count: int = 1,
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
        # `top_seed_count` is retained for backward-compat with persisted
        # HP from pre-Sprint-3 runs (default was 5). FunSearch-correct
        # reset always copies one program per weak-island; the field is
        # not consulted by `maybe_reset`.
        self.top_seed_count = top_seed_count
        self.rng = rng or random.Random()

    def pick_island(self) -> int:
        """Uniform-random island id for the next inner-loop step."""
        return self.rng.randrange(self.num_islands)

    def rank_by_mean_fitness(self) -> list[int]:
        """Island ids sorted by mean alive fitness in this run, highest first."""
        means = self.db.mean_fitness_per_island(self.num_islands, run_id=self.run_id)
        return sorted(range(self.num_islands), key=lambda i: means[i], reverse=True)

    def maybe_reset(self, current_generation: int) -> ResetEvent | None:
        """At reset cadence, wipe bottom m/2 islands and reseed each one
        with a single program drawn FunSearch-style.

        For each weak island independently:
          1. Sample one surviving island uniformly at random.
          2. Retrieve that island's single best alive program.
          3. Copy it as the sole reseed program for the weak island.

        Returns None (no reset performed) when:
          - generation <= 0
          - generation not at the reset cadence
          - no surviving island has any alive program (degenerate: no
            sources to reseed from).
        """
        if current_generation <= 0:
            return None
        if current_generation % self.reset_every_generations != 0:
            return None

        ranked = self.rank_by_mean_fitness()
        half = self.num_islands // 2
        strong = ranked[:half]
        weak = ranked[half:]

        # Per-weak-island independent uniform draw over surviving islands.
        # FunSearch (Nature 2023, §A.1): "Each of these islands is then
        # seeded with a single program, obtained by first choosing one of
        # the surviving m/2 islands uniformly at random and then retrieving
        # the best program from it."
        source_islands: list[int] = []
        seed_program_ids: list[int] = []
        actual_weak: list[int] = []
        for weak_island in weak:
            source_island = self.rng.choice(strong)
            top = self.db.top_k_in_island(
                island_id=source_island, k=1, run_id=self.run_id
            )
            if not top:
                # Source island has no alive candidates — skip this weak
                # island this cycle. Loop continues so other weak islands
                # may still reseed from other surviving sources.
                continue
            best = top[0]
            self.db.reset_island(weak_island, [best.id], run_id=self.run_id)
            source_islands.append(source_island)
            seed_program_ids.append(best.id)
            actual_weak.append(weak_island)

        if not actual_weak:
            return None

        return ResetEvent(
            weak_islands=actual_weak,
            strong_islands=strong,
            source_islands=source_islands,
            seed_program_ids=seed_program_ids,
        )

    def diversity_summary(self) -> dict[int, float]:
        """Per-island diversity metric for this run, keyed by island id."""
        return {
            i: self.db.diversity_metric(i, run_id=self.run_id)
            for i in range(self.num_islands)
        }
