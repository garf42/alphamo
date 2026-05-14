"""Handoff schemas — the structured deliverable produced on run termination.

The handoff is the load-bearing artefact: everything before it is plumbing in
service of producing this document. Skill 4 (implementation-handoff) consumes
the document and packages it for autonomous build.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from alphamo.schemas.architecture import Architecture
from alphamo.schemas.scores import Scores


class WinningArchitecture(BaseModel):
    """The top candidate at harvest time."""

    spec: Architecture
    scores: Scores
    island_of_origin: int
    generation: int
    lineage: list[int]


class AlternateCandidate(BaseModel):
    """A diverse runner-up from another island."""

    spec: Architecture
    scores: Scores
    island_of_origin: int
    generation: int


class ExemplarComparison(BaseModel):
    """One stage-3 comparison record for the verification trail."""

    closest_exemplar: str
    similarity: float
    reasoning: str


class VerificationTrail(BaseModel):
    """How the winner was scored, for downstream auditability."""

    final_scores: Scores
    anchor_used: str
    eval_count: int
    exemplar_comparisons: list[ExemplarComparison]


class DriftLogEntry(BaseModel):
    """One row from the curator's drift log, projected for the handoff."""

    iter: int
    type: str = Field(description='"structural" | "cosmetic" | "no_action"')
    source: str = Field(description='"research" | "redteam" | "" if unknown')
    action: str
    rationale: str


class MiddleClassEntryCheck(BaseModel):
    """Explicit confirmation the hard constraint held on the winner."""

    passes: bool
    estimated_starting_resources: str
    stage_sequence: list[str]


class Handoff(BaseModel):
    """The complete handoff document."""

    winning_architecture: WinningArchitecture
    alternates: list[AlternateCandidate]
    verification_trail: VerificationTrail
    drift_log: list[DriftLogEntry]
    parent_goal_alignment: str
    middle_class_entry_check: MiddleClassEntryCheck
    coverage_residual: str
