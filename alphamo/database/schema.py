"""SQLAlchemy schema for the Programs DB.

Mirrors the schema sketch from the Programs DB modal:

    CREATE TABLE candidates (
      id INTEGER PRIMARY KEY,
      run_id TEXT,                          -- FK to runs.run_id (phase-run-boundaries)
      architecture_spec JSON NOT NULL,
      scores JSON NOT NULL,
      stage4_findings JSON,                 -- list of StructuralConcern dicts; NULL for legacy / pre-Stage-4 / Stage-1-or-2-exit candidates
      fitness REAL NOT NULL,
      island_id INTEGER,
      generation INTEGER,
      parent_ids JSON,
      status TEXT,
      created_at TIMESTAMP
    );
    CREATE INDEX idx_island_fitness ON candidates(island_id, fitness DESC);
    CREATE INDEX idx_generation ON candidates(generation);
    CREATE INDEX idx_run_id ON candidates(run_id);

    CREATE TABLE runs (
      run_id TEXT PRIMARY KEY,
      created_at TIMESTAMP NOT NULL,
      hyperparameters JSON NOT NULL,
      parent_goal_version TEXT NOT NULL,
      verifier_version TEXT NOT NULL,
      stopped_reason TEXT,
      completed_at TIMESTAMP,
      last_resumed_at TIMESTAMP,
      notes TEXT
    );
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Run(Base):
    """One AlphaMo run. Created at orchestrator construction; updated on termination."""

    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    parent_goal_version: Mapped[str] = mapped_column(String, nullable=False)
    verifier_version: Mapped[str] = mapped_column(String, nullable=False)
    stopped_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_resumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"Run(run_id={self.run_id!r}, "
            f"parent_goal_version={self.parent_goal_version!r}, "
            f"verifier_version={self.verifier_version!r}, "
            f"completed_at={self.completed_at!r})"
        )


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # run_id is schema-nullable so the auto-migration can backfill legacy rows;
    # application code enforces NOT NULL on insert via ProgramsDB.insert().
    run_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("runs.run_id"), nullable=True
    )
    architecture_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # stage4_findings: list of StructuralConcern dicts (claim, evidence,
    # falsification_condition, severity, framing). NULL for legacy candidates
    # from pre-Sprint-1 runs, and for candidates that exit the cascade
    # before Stage 4 runs.
    stage4_findings: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    # Sprint 15 (Q2): per-framing "no identifiable vulnerability"
    # explanation text from clean framings on this candidate.
    # `{framing_name: assessment_text, ...}` — empty dict (or NULL on
    # legacy rows) when no framing came back clean or when Stage 3 didn't
    # run. The closed-RL-loop signal complement to stage4_findings:
    # findings carry concerns the cascade raised, assessments carry
    # the reasoning behind framings that found nothing.
    stage4_assessments: Mapped[dict[str, str] | None] = mapped_column(
        JSON, nullable=True
    )
    # Sprint Stage 2 PAJAMA: the full Stage 2 evidence dict
    # (categoricals + booleans + lists + reasoning string) for
    # candidates that reached Stage 2. NULL when Stage 1 short-
    # circuited (middle-class filter exit or stage1_threshold exit).
    # The persisted scalar `scores.structural` is derived from this
    # evidence via `evaluator.stage2_structured.compute_structural` —
    # the evidence is the audit trail behind the scalar, queryable
    # via SQL (e.g. find every alive candidate with
    # `automation_plausibility = 'requires_human_judgment'`).
    stage2_evidence: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    fitness: Mapped[float] = mapped_column(Float, nullable=False)
    island_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_island_fitness", "island_id", fitness.desc()),
        Index("idx_generation", "generation"),
        Index("idx_run_id", "run_id"),
    )

    def __repr__(self) -> str:
        name = self.architecture_spec.get("name", "?") if self.architecture_spec else "?"
        return (
            f"Candidate(id={self.id}, run_id={self.run_id!r}, "
            f"name={name!r}, fitness={self.fitness:.3f})"
        )
