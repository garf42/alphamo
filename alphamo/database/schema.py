"""SQLAlchemy schema for the Programs DB.

Mirrors the schema sketch from the Programs DB modal:

    CREATE TABLE candidates (
      id INTEGER PRIMARY KEY,
      architecture_spec JSON NOT NULL,
      scores JSON NOT NULL,
      fitness REAL NOT NULL,
      island_id INTEGER,
      generation INTEGER,
      parent_ids JSON,
      status TEXT,
      created_at TIMESTAMP
    );
    CREATE INDEX idx_island_fitness ON candidates(island_id, fitness DESC);
    CREATE INDEX idx_generation ON candidates(generation);
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    architecture_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
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
    )

    def __repr__(self) -> str:
        name = self.architecture_spec.get("name", "?") if self.architecture_spec else "?"
        return f"Candidate(id={self.id}, name={name!r}, fitness={self.fitness:.3f})"
