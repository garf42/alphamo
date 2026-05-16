"""Pydantic schema for evaluator output.

Phase 2 (Stage 4) added `robustness`. Legacy candidates persisted before
Stage 4 existed have `robustness=None`; `aggregate_fitness` handles this
by averaging over present dimensions, which keeps legacy fitness values
stable.

Sprint 2 redesign: `exemplar_similarity` is now optional (None) too. It
was retired when seeds stopped being scored candidates and similarity
stopped contributing to fitness — keeping novel architectures from being
punished for not looking like the four reference seeds. Old DB rows that
carry an `exemplar_similarity` float load fine and the value is silently
ignored when computing new aggregates.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scores(BaseModel):
    """Multi-objective evaluator output.

    Dimensions actively used in fitness:
      - feasibility           : stage 1 (Haiku) — does this hang together
      - structural            : stage 2 (Sonnet) — one-person/billion/labor
      - robustness            : stage 3 (Opus, adversarial scrutiny under
                                multiple framings) — survives scrutiny
      - middle_class_accessible : stage 1 boolean filter, NOT a fitness term

    Retired but persisted:
      - exemplar_similarity   : retired Sprint 2. Was the exemplar
                                comparison stage — "looks like a known
                                proof". Now Optional; None on all new
                                candidates. Kept in the schema so old run
                                DBs still read.

    `robustness` is None when adversarial scrutiny did not run on this
    candidate — early-exit, pre-Stage-4 legacy, or seed reference. The
    `aggregate_fitness` helper in alphamo/database/operations.py averages
    over whichever dimensions are present (non-None).
    """

    feasibility: float = Field(ge=0.0, le=1.0)
    structural: float = Field(ge=0.0, le=1.0)
    exemplar_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    robustness: float | None = Field(default=None, ge=0.0, le=1.0)
    middle_class_accessible: bool
