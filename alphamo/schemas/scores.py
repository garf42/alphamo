"""Pydantic schema for evaluator output.

Phase 2 (Stage 4) added `robustness`. Legacy candidates persisted before
Stage 4 existed have `robustness=None`; `aggregate_fitness` handles this by
averaging over present dimensions, which keeps legacy fitness values stable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scores(BaseModel):
    """Multi-objective evaluator output.

    Dimensions:
      - feasibility           : stage 1 (Haiku) — does this hang together
      - structural            : stage 2 (Sonnet) — one-person/billion/labor
      - exemplar_similarity   : stage 3 (Opus) — looks like a known proof
      - robustness            : stage 4 (Opus, 8 framings) — survives scrutiny
      - middle_class_accessible : stage 1 boolean filter, NOT a fitness term

    `robustness` is None when Stage 4 did not run on this candidate — either
    because the candidate exited the cascade early, because it pre-dates
    Stage 4, or because it was hand-seeded without scrutiny. The
    `aggregate_fitness` helper in alphamo/database/operations.py averages
    over whichever dimensions are present.
    """

    feasibility: float = Field(ge=0.0, le=1.0)
    structural: float = Field(ge=0.0, le=1.0)
    exemplar_similarity: float = Field(ge=0.0, le=1.0)
    robustness: float | None = Field(default=None, ge=0.0, le=1.0)
    middle_class_accessible: bool
