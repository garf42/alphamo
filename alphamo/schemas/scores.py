"""Pydantic schema for evaluator output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scores(BaseModel):
    """Multi-objective evaluator output.

    Phase 01 stores the raw stage outputs verbatim. The evaluator cascade
    (phase 02) will fill these in; here we accept hand-set values.
    """

    feasibility: float = Field(ge=0.0, le=1.0)
    structural: float = Field(ge=0.0, le=1.0)
    exemplar_similarity: float = Field(ge=0.0, le=1.0)
    middle_class_accessible: bool
