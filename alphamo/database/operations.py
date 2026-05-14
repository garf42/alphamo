"""Programs DB operations.

Phase 01 implements:
  - insert(architecture, scores, ...) -> int
  - top_k_in_island(island_id, k) -> list[Candidate]
  - get(candidate_id) -> Candidate

Phase 04 will fill in reset_island / fitness_history / diversity_metric;
they are declared here so the interface is visible.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, select
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
        """Return the k highest-fitness candidates in the given island."""
        stmt = (
            select(Candidate)
            .where(Candidate.island_id == island_id)
            .order_by(Candidate.fitness.desc())
            .limit(k)
        )
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def reset_island(self, island_id: int, seed_programs: list[int]) -> None:
        raise NotImplementedError("phase 04 (islands manager)")

    def fitness_history(self, generations: int) -> list[float]:
        raise NotImplementedError("phase 04 (stall detection)")

    def diversity_metric(self, island_id: int) -> float:
        raise NotImplementedError("phase 04 (islands manager)")
