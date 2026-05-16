"""Handoff schemas — the structured deliverable produced on run termination.

The handoff is the load-bearing artefact: everything before it is plumbing in
service of producing this document. Skill 4 (implementation-handoff) consumes
the document and packages it for autonomous build.

The structure honestly separates seeds (what the run started with) from
generated discoveries (what the search actually produced). A seed never
"wins" — `winning_architecture` is null whenever no generated candidate
exceeded a seed baseline, and `no_breakthrough_this_run` flags that case
explicitly so a human reading the handoff knows the search did not exceed
its starting baseline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from alphamo.schemas.architecture import Architecture
from alphamo.schemas.findings import StructuralConcern
from alphamo.schemas.scores import Scores


class SeedBaseline(BaseModel):
    """One STARTER's canonical baseline. Informational — NOT a winner.

    Listed in the handoff so the reader sees what the run started with and
    can interpret `top_generated_discoveries` against it. The fitness here
    is computed from the canonical scores in `exemplar_library.py`, not from
    DB rows, so the baseline is stable even if a reseed copy of this seed
    has been killed off the alive set.
    """

    name: str
    scores: Scores
    fitness: float
    island_of_origin: int


class GeneratedDiscovery(BaseModel):
    """A non-seed candidate produced by the search loop.

    `stage4_findings` is None for legacy / pre-Stage-4 candidates and an
    empty list for Stage-4-scrutinised candidates that came back clean.
    """

    spec: Architecture
    scores: Scores
    fitness: float
    island_of_origin: int
    generation: int
    lineage: list[int]
    stage4_findings: list[StructuralConcern] | None = None


class ExemplarComparison(BaseModel):
    """One stage-3 comparison record for the verification trail."""

    closest_exemplar: str
    similarity: float
    reasoning: str


class VerificationTrail(BaseModel):
    """How the cascade subject was scored, for downstream auditability.

    The cascade subject is the top generated discovery when one exists, or
    nothing at all when the run produced only seeds. In the latter case
    `final_scores`, `exemplar_comparisons`, and `adversarial_concerns` are
    empty / None — there's nothing to verify because nothing was generated.
    """

    run_id: str
    hyperparameters: dict
    parent_goal_version: str
    verifier_version: str
    final_scores: Scores | None = None
    anchor_used: str
    eval_count: int
    exemplar_comparisons: list[ExemplarComparison]
    adversarial_concerns: list[StructuralConcern] = Field(default_factory=list)


class DriftLogEntry(BaseModel):
    """One row from the curator's drift log, projected for the handoff."""

    iter: int
    type: str = Field(description='"structural" | "cosmetic" | "no_action"')
    source: str = Field(description='"research" | "redteam" | "" if unknown')
    action: str
    rationale: str


class MiddleClassEntryCheck(BaseModel):
    """Explicit confirmation the hard constraint held on the cascade subject.

    When no generated candidate exists, this reports `passes=True` with a
    placeholder note — seeds always pass the filter and there's no subject
    to check otherwise.
    """

    passes: bool
    estimated_starting_resources: str
    stage_sequence: list[str]


class Handoff(BaseModel):
    """The complete handoff document.

    Field semantics:
      - `seed_baselines`: informational. One entry per STARTER. NOT a winner.
      - `top_generated_discoveries`: research output. Top N generated
        candidates by fitness, sorted descending. Empty when the run
        produced only seeds.
      - `no_breakthrough_this_run`: True when no generated candidate's
        fitness exceeds `min(seed_baselines.fitness)`. Honest summary flag.
      - `winning_architecture`: the highest-fitness generated candidate
        when `no_breakthrough_this_run` is False, else null. Never a seed.
    """

    seed_baselines: list[SeedBaseline]
    top_generated_discoveries: list[GeneratedDiscovery]
    no_breakthrough_this_run: bool
    winning_architecture: GeneratedDiscovery | None = None
    verification_trail: VerificationTrail
    drift_log: list[DriftLogEntry]
    parent_goal_alignment: str
    middle_class_entry_check: MiddleClassEntryCheck
    coverage_residual: str
