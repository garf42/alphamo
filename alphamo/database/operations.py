"""Programs DB operations.

Phase 01 implemented insert / top_k_in_island / get.
Phase 04 fills in reset_island / fitness_history / diversity_metric and
adds the helpers the islands manager needs.
"""

from __future__ import annotations

import itertools
import re
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from alphamo.database.schema import Base, Candidate
from alphamo.schemas import Architecture, Scores


def aggregate_fitness(scores: Scores) -> float:
    """Average of the three stage scores, zeroed when the middle-class filter fails.

    The modal's evaluator node calls the middle-class constraint a *filter, not a
    penalty* — candidates that fail it must not appear above accessible
    candidates regardless of how well they score elsewhere. Phase 02's cascade
    evaluator will replace this with its own aggregator.
    """
    if not scores.middle_class_accessible:
        return 0.0
    return (scores.feasibility + scores.structural + scores.exemplar_similarity) / 3.0


class ProgramsDB:
    """Append-only store of every candidate ever generated."""

    def __init__(self, url: str = "sqlite:///alphamo.db") -> None:
        self.url = url
        self.engine = create_engine(url, future=True)
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def insert(
        self,
        architecture: Architecture,
        scores: Scores,
        island_id: int = 0,
        generation: int = 0,
        parent_ids: list[int] | None = None,
        status: str = "alive",
    ) -> int:
        """Insert one candidate. Returns the new row id."""
        candidate = Candidate(
            architecture_spec=architecture.model_dump(),
            scores=scores.model_dump(),
            fitness=aggregate_fitness(scores),
            island_id=island_id,
            generation=generation,
            parent_ids=parent_ids,
            status=status,
        )
        with self._session() as session:
            session.add(candidate)
            session.flush()
            return candidate.id

    def get(self, candidate_id: int) -> Candidate:
        with self._session() as session:
            row = session.get(Candidate, candidate_id)
            if row is None:
                raise KeyError(f"no candidate with id={candidate_id}")
            session.expunge(row)
            return row

    def top_k_in_island(self, island_id: int, k: int) -> list[Candidate]:
        """Return the k highest-fitness *alive* candidates in the given island.

        Reset / failed rows are filtered out so they cannot seed new generations.
        """
        stmt = (
            select(Candidate)
            .where(Candidate.island_id == island_id)
            .where(Candidate.status == "alive")
            .order_by(Candidate.fitness.desc())
            .limit(k)
        )
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def top_programs_from_islands(
        self, island_ids: list[int], n: int
    ) -> list[Candidate]:
        """Return the top n alive programs across the given islands by fitness."""
        if not island_ids:
            return []
        stmt = (
            select(Candidate)
            .where(Candidate.island_id.in_(island_ids))
            .where(Candidate.status == "alive")
            .order_by(Candidate.fitness.desc())
            .limit(n)
        )
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def mean_fitness_per_island(self, num_islands: int) -> dict[int, float]:
        """Mean fitness of alive candidates per island. Empty islands map to 0.0."""
        stmt = (
            select(Candidate.island_id, func.avg(Candidate.fitness))
            .where(Candidate.status == "alive")
            .group_by(Candidate.island_id)
        )
        means: dict[int, float] = {i: 0.0 for i in range(num_islands)}
        with self._session() as session:
            for island_id, avg in session.execute(stmt):
                means[island_id] = float(avg) if avg is not None else 0.0
        return means

    def reset_island(self, island_id: int, seed_programs: list[int]) -> None:
        """Mark every alive row in `island_id` as 'reset', then copy the seed
        programs into the island as fresh alive entries.

        The copies retain the source architecture / scores / fitness so the new
        island starts from a calibrated population. Each copy's `parent_ids`
        points back to the source program for lineage tracking.
        """
        with self._session() as session:
            session.execute(
                update(Candidate)
                .where(Candidate.island_id == island_id)
                .where(Candidate.status == "alive")
                .values(status="reset")
            )
            sources = list(
                session.scalars(
                    select(Candidate).where(Candidate.id.in_(seed_programs))
                )
            )
            for source in sources:
                session.add(
                    Candidate(
                        architecture_spec=source.architecture_spec,
                        scores=source.scores,
                        fitness=source.fitness,
                        island_id=island_id,
                        generation=source.generation,
                        parent_ids=[source.id],
                        status="alive",
                    )
                )

    def fitness_history(self, generations: int) -> list[float]:
        """Max fitness per generation for the last N generations, chronological.

        Generations with no alive rows are filled with 0.0 so the caller can
        detect flat stretches as stalls without a special-case loop.
        """
        stmt = (
            select(Candidate.generation, func.max(Candidate.fitness))
            .where(Candidate.status == "alive")
            .group_by(Candidate.generation)
            .order_by(Candidate.generation.desc())
            .limit(generations)
        )
        with self._session() as session:
            pairs = list(session.execute(stmt))
        if not pairs:
            return []
        observed = {int(g): float(f) for g, f in pairs}
        latest = max(observed)
        window = range(max(0, latest - generations + 1), latest + 1)
        return [observed.get(g, 0.0) for g in window]

    def diversity_metric(self, island_id: int) -> float:
        """Average pairwise Jaccard distance over alive candidates' word bags.

        Bag = lowercase word tokens of `value_chain + capture_mechanism`.
        Returns 0.0 when every alive candidate has identical content, 1.0 when
        no candidates share any tokens. Islands with fewer than two alive
        candidates return 0.0 (no diversity to measure).
        """
        stmt = (
            select(Candidate.architecture_spec)
            .where(Candidate.island_id == island_id)
            .where(Candidate.status == "alive")
        )
        with self._session() as session:
            specs = [row for row in session.scalars(stmt)]
        if len(specs) < 2:
            return 0.0
        bags: list[set[str]] = []
        for spec in specs:
            text = f"{spec.get('value_chain', '')} {spec.get('capture_mechanism', '')}".lower()
            bags.append(set(re.findall(r"\w+", text)))
        distances: list[float] = []
        for a, b in itertools.combinations(bags, 2):
            union = len(a | b)
            if union == 0:
                continue
            distances.append(1.0 - len(a & b) / union)
        return sum(distances) / len(distances) if distances else 0.0
