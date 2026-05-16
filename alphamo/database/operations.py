"""Programs DB operations.

Phase 01 implemented insert / top_k_in_island / get.
Phase 04 added reset_island / fitness_history / diversity_metric and the
helpers the islands manager needs.
Phase-run-boundaries adds first-class `runs` and threads `run_id` through
every read filter and write path. Migration on init backfills legacy
candidates that pre-date the column.
"""

from __future__ import annotations

import itertools
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import create_engine, func, inspect, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from alphamo.database.schema import Base, Candidate, Run
from alphamo.schemas import Architecture, Scores

LEGACY_RUN_ID = "run_legacy"


def aggregate_fitness(scores: Scores) -> float:
    """Average of present score dimensions, zeroed when the middle-class filter fails.

    The middle-class constraint is a *filter, not a penalty* — candidates
    that fail it must not appear above accessible candidates regardless of
    how well they score elsewhere.

    Aggregation rule (Phase 2):
      - middle_class_accessible=False ⇒ fitness = 0.0 (filter)
      - else: average over dimensions actually evaluated. `robustness` is
        included when present and skipped when None. This preserves
        backward compatibility with pre-Stage-4 candidates (which average
        over 3 dimensions, matching the original behavior) and gives
        Stage-4-scrutinised candidates a true 4-way average.
    """
    if not scores.middle_class_accessible:
        return 0.0
    dims: list[float] = [
        scores.feasibility,
        scores.structural,
        scores.exemplar_similarity,
    ]
    if scores.robustness is not None:
        dims.append(scores.robustness)
    return sum(dims) / len(dims)


def _generate_run_id() -> str:
    """8-hex-char short id, prefixed for readability in CLI output."""
    return f"run_{secrets.token_hex(4)}"


class ProgramsDB:
    """Append-only store of every candidate ever generated, scoped by run_id."""

    def __init__(self, url: str = "sqlite:///alphamo.db") -> None:
        self.url = url
        self.engine = create_engine(url, future=True)
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(self.engine, expire_on_commit=False)
        self._migrate_legacy_candidates()

    # ------------------------------------------------------------------ session

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

    # ------------------------------------------------------------------ migration

    def _migrate_legacy_candidates(self) -> None:
        """One-shot migration: add run_id and stage4_findings columns; backfill any NULL run_ids.

        Idempotent. Runs on every ProgramsDB construction.
          - Pre-Phase-1 candidates lack run_id; assigned to the LEGACY_RUN_ID
            run, lazily created.
          - Pre-Sprint-1 candidates lack stage4_findings; the column is added
            but rows stay NULL. Backfill from the audit log is a separate
            operation (`backfill_stage4_from_audit`).
        """
        inspector = inspect(self.engine)
        if "candidates" not in inspector.get_table_names():
            return

        column_names = {col["name"] for col in inspector.get_columns("candidates")}
        if "run_id" not in column_names:
            with self.engine.begin() as conn:
                conn.execute(text("ALTER TABLE candidates ADD COLUMN run_id TEXT"))
        if "stage4_findings" not in column_names:
            with self.engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE candidates ADD COLUMN stage4_findings JSON")
                )

        with self._session() as session:
            null_count = session.scalar(
                select(func.count())
                .select_from(Candidate)
                .where(Candidate.run_id.is_(None))
            )
            if not null_count:
                return

            legacy = session.get(Run, LEGACY_RUN_ID)
            if legacy is None:
                session.add(
                    Run(
                        run_id=LEGACY_RUN_ID,
                        created_at=datetime.now(timezone.utc),
                        hyperparameters={},
                        parent_goal_version="unknown",
                        verifier_version="unknown",
                        stopped_reason="migrated",
                        completed_at=datetime.now(timezone.utc),
                        notes=(
                            "pre-run-boundaries data (auto-migrated). Hyperparameters and "
                            "versions are unknown because these rows pre-date the runs table."
                        ),
                    )
                )
                session.flush()
            session.execute(
                update(Candidate)
                .where(Candidate.run_id.is_(None))
                .values(run_id=LEGACY_RUN_ID)
            )

    # ------------------------------------------------------------------ runs

    def create_run(
        self,
        hyperparameters: dict[str, Any],
        parent_goal_version: str,
        verifier_version: str,
        notes: str | None = None,
    ) -> str:
        """Create a new run row and return its id."""
        run_id = _generate_run_id()
        with self._session() as session:
            session.add(
                Run(
                    run_id=run_id,
                    created_at=datetime.now(timezone.utc),
                    hyperparameters=hyperparameters,
                    parent_goal_version=parent_goal_version,
                    verifier_version=verifier_version,
                    notes=notes,
                )
            )
        return run_id

    def get_run(self, run_id: str) -> Run:
        with self._session() as session:
            row = session.get(Run, run_id)
            if row is None:
                raise KeyError(f"no run with run_id={run_id!r}")
            session.expunge(row)
            return row

    def list_runs(self) -> list[Run]:
        stmt = select(Run).order_by(Run.created_at.desc())
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def latest_run_id(self) -> str | None:
        with self._session() as session:
            return session.scalar(
                select(Run.run_id).order_by(Run.created_at.desc()).limit(1)
            )

    def complete_run(self, run_id: str, stopped_reason: str) -> None:
        with self._session() as session:
            result = session.execute(
                update(Run)
                .where(Run.run_id == run_id)
                .values(
                    stopped_reason=stopped_reason,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount == 0:
                raise KeyError(f"no run with run_id={run_id!r}")

    def mark_run_resumed(self, run_id: str) -> None:
        with self._session() as session:
            result = session.execute(
                update(Run)
                .where(Run.run_id == run_id)
                .values(last_resumed_at=datetime.now(timezone.utc))
            )
            if result.rowcount == 0:
                raise KeyError(f"no run with run_id={run_id!r}")

    def backfill_stage4_from_audit(
        self,
        audit_events: "list[Any]",
        decay_k: float = 0.15,
    ) -> dict[str, int]:
        """One-shot migration: populate stage4_findings on existing candidates
        from `trigger='stage4_routine'` events in the audit log.

        For each event:
          - Extract `payload.candidate_id` and `payload.concerns`.
          - Skip if the candidate already has a non-NULL stage4_findings
            (the operation is idempotent — re-running is safe).
          - Skip if no candidate with that id exists (audit and DB drifted).
          - Else: write the concerns list, recompute robustness via the
            current `compute_robustness` formula, recompute fitness via
            `aggregate_fitness`, update all three columns in one row.

        Returns a stats dict: {"updated": N, "skipped_existing": N,
        "skipped_missing": N, "skipped_non_stage4": N}.

        Importing the audit log live here would pull in alphamo.meta — we
        keep the DB module dependency-light by taking already-loaded events.
        """
        from alphamo.evaluator.stage4_adversarial import compute_robustness
        from alphamo.schemas import Scores
        from alphamo.schemas.findings import StructuralConcern

        stats = {
            "updated": 0,
            "skipped_existing": 0,
            "skipped_missing": 0,
            "skipped_non_stage4": 0,
        }
        with self._session() as session:
            for event in audit_events:
                if event.trigger != "stage4_routine":
                    stats["skipped_non_stage4"] += 1
                    continue
                payload = event.payload or {}
                candidate_id = payload.get("candidate_id")
                concerns_data = payload.get("concerns")
                if candidate_id is None or concerns_data is None:
                    stats["skipped_non_stage4"] += 1
                    continue

                row = session.get(Candidate, candidate_id)
                if row is None:
                    stats["skipped_missing"] += 1
                    continue
                if row.stage4_findings is not None:
                    stats["skipped_existing"] += 1
                    continue

                concerns = [StructuralConcern(**c) for c in concerns_data]
                new_robustness = compute_robustness(concerns, decay_k=decay_k)

                merged_scores = dict(row.scores)
                merged_scores["robustness"] = new_robustness
                new_fitness = aggregate_fitness(Scores(**merged_scores))

                row.stage4_findings = concerns_data
                row.scores = merged_scores
                row.fitness = new_fitness
                stats["updated"] += 1
        return stats

    def patch_run_hyperparameters(
        self, run_id: str, patch: dict[str, Any]
    ) -> None:
        """Merge `patch` into the run's hyperparameters JSON.

        Used by the orchestrator to persist derived run-start constants
        (e.g. `seed_baseline_fitness`) alongside the user-set Hyperparameters
        config. The Pydantic Hyperparameters model ignores unknown keys, so
        these extras survive a resume_run() roundtrip cleanly.
        """
        with self._session() as session:
            row = session.get(Run, run_id)
            if row is None:
                raise KeyError(f"no run with run_id={run_id!r}")
            merged = dict(row.hyperparameters)
            merged.update(patch)
            row.hyperparameters = merged

    # ------------------------------------------------------------------ inserts

    def insert(
        self,
        architecture: Architecture,
        scores: Scores,
        *,
        run_id: str,
        island_id: int = 0,
        generation: int = 0,
        parent_ids: list[int] | None = None,
        status: str = "alive",
        stage4_findings: list[dict[str, Any]] | None = None,
    ) -> int:
        """Insert one candidate. Returns the new row id. `run_id` is required.

        `stage4_findings` is an optional list of StructuralConcern dicts (the
        Pydantic model_dump form). Pass it when Stage 4 ran on this candidate
        and produced concerns; leave None for short-circuit-exit candidates
        or for ad-hoc inserts that bypass the cascade.
        """
        if not run_id:
            raise ValueError("run_id is required on insert")
        candidate = Candidate(
            run_id=run_id,
            architecture_spec=architecture.model_dump(),
            scores=scores.model_dump(),
            stage4_findings=stage4_findings,
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

    # ------------------------------------------------------------------ reads

    def get(self, candidate_id: int) -> Candidate:
        with self._session() as session:
            row = session.get(Candidate, candidate_id)
            if row is None:
                raise KeyError(f"no candidate with id={candidate_id}")
            session.expunge(row)
            return row

    def count_candidates(
        self, status: str | None = None, run_id: str | None = None
    ) -> int:
        """Total candidate rows, optionally filtered by status and/or run_id."""
        stmt = select(func.count()).select_from(Candidate)
        if status is not None:
            stmt = stmt.where(Candidate.status == status)
        if run_id is not None:
            stmt = stmt.where(Candidate.run_id == run_id)
        with self._session() as session:
            return int(session.scalar(stmt) or 0)

    def count_candidates_in_run(
        self, run_id: str, status: str | None = None
    ) -> int:
        return self.count_candidates(status=status, run_id=run_id)

    def top_k_in_island(
        self, island_id: int, k: int, run_id: str | None = None
    ) -> list[Candidate]:
        """Return the k highest-fitness *alive* candidates in the given island.

        Reset / failed rows are filtered out so they cannot seed new generations.
        When `run_id` is supplied the population is restricted to that run.
        """
        stmt = (
            select(Candidate)
            .where(Candidate.island_id == island_id)
            .where(Candidate.status == "alive")
            .order_by(Candidate.fitness.desc())
            .limit(k)
        )
        if run_id is not None:
            stmt = stmt.where(Candidate.run_id == run_id)
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def top_programs_from_islands(
        self, island_ids: list[int], n: int, run_id: str | None = None
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
        if run_id is not None:
            stmt = stmt.where(Candidate.run_id == run_id)
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def mean_fitness_per_island(
        self, num_islands: int, run_id: str | None = None
    ) -> dict[int, float]:
        """Mean fitness of alive candidates per island. Empty islands map to 0.0."""
        stmt = (
            select(Candidate.island_id, func.avg(Candidate.fitness))
            .where(Candidate.status == "alive")
            .group_by(Candidate.island_id)
        )
        if run_id is not None:
            stmt = stmt.where(Candidate.run_id == run_id)
        means: dict[int, float] = {i: 0.0 for i in range(num_islands)}
        with self._session() as session:
            for island_id, avg in session.execute(stmt):
                means[island_id] = float(avg) if avg is not None else 0.0
        return means

    def alive_in_run(self, run_id: str) -> list[Candidate]:
        """All alive candidates for `run_id`, sorted by fitness descending.

        Used by the harvest builder to partition seeds vs generated discoveries
        and pick top-N. The whole alive set is intentional — runs are bounded
        by max_generations * num_islands and capped at low thousands of rows.
        """
        stmt = (
            select(Candidate)
            .where(Candidate.run_id == run_id)
            .where(Candidate.status == "alive")
            .order_by(Candidate.fitness.desc())
        )
        with self._session() as session:
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def fitness_history(
        self, generations: int, run_id: str | None = None
    ) -> list[float]:
        """Max fitness per generation for the last N generations, chronological."""
        stmt = (
            select(Candidate.generation, func.max(Candidate.fitness))
            .where(Candidate.status == "alive")
            .group_by(Candidate.generation)
            .order_by(Candidate.generation.desc())
            .limit(generations)
        )
        if run_id is not None:
            stmt = stmt.where(Candidate.run_id == run_id)
        with self._session() as session:
            pairs = list(session.execute(stmt))
        if not pairs:
            return []
        observed = {int(g): float(f) for g, f in pairs}
        latest = max(observed)
        window = range(max(0, latest - generations + 1), latest + 1)
        return [observed.get(g, 0.0) for g in window]

    def diversity_metric(
        self, island_id: int, run_id: str | None = None
    ) -> float:
        """Average pairwise Jaccard distance over alive candidates' word bags."""
        stmt = (
            select(Candidate.architecture_spec)
            .where(Candidate.island_id == island_id)
            .where(Candidate.status == "alive")
        )
        if run_id is not None:
            stmt = stmt.where(Candidate.run_id == run_id)
        with self._session() as session:
            specs = [row for row in session.scalars(stmt)]
        if len(specs) < 2:
            return 0.0
        bags: list[set[str]] = []
        for spec in specs:
            text_blob = (
                f"{spec.get('value_chain', '')} {spec.get('capture_mechanism', '')}"
            ).lower()
            bags.append(set(re.findall(r"\w+", text_blob)))
        distances: list[float] = []
        for a, b in itertools.combinations(bags, 2):
            union = len(a | b)
            if union == 0:
                continue
            distances.append(1.0 - len(a & b) / union)
        return sum(distances) / len(distances) if distances else 0.0

    # ------------------------------------------------------------------ reset

    def reset_island(
        self,
        island_id: int,
        seed_programs: list[int],
        *,
        run_id: str,
    ) -> None:
        """Mark every alive row in `island_id` for this run as 'reset', then copy
        the seed programs into the island as fresh alive entries.

        The copies retain the source architecture / scores / fitness so the new
        island starts from a calibrated population. Each copy's `parent_ids`
        points back to the source program for lineage tracking. The copies are
        tagged with the current run_id so the reset stays scoped to this run.
        """
        if not run_id:
            raise ValueError("run_id is required on reset_island")
        with self._session() as session:
            session.execute(
                update(Candidate)
                .where(Candidate.run_id == run_id)
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
                        run_id=run_id,
                        architecture_spec=source.architecture_spec,
                        scores=source.scores,
                        stage4_findings=source.stage4_findings,
                        fitness=source.fitness,
                        island_id=island_id,
                        generation=source.generation,
                        parent_ids=[source.id],
                        status="alive",
                    )
                )
