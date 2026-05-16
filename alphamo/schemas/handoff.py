"""Handoff schemas — the structured deliverable produced on run termination.

The handoff is the load-bearing artefact: everything before it is plumbing in
service of producing this document. Skill 4 (implementation-handoff) consumes
the document and packages it for autonomous build.

Sprint 3 redesign: the handoff's `seed_baselines` is now a single-entry
list — the trivial Solo Service Provider baseline that every island was
initialized with at generation 0. This replaces the Sprint 2
"descriptive reference" projection of four curated seeds. Re-harvesting
old DBs that were created under the 4-seed era will produce a 1-entry
baseline section that doesn't reflect what that run actually started
from; this is acceptable legacy drift.

The `no_breakthrough_this_run` flag and `winning_architecture` field are
gated on absolute milestone thresholds (fitness AND robustness clearing
the configured floors), not on seed-relative comparison.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from alphamo.schemas.architecture import Architecture
from alphamo.schemas.findings import StructuralConcern
from alphamo.schemas.scores import Scores


class BaselineSeed(BaseModel):
    """The trivial baseline architecture that every island was initialized
    with at generation 0.

    Sprint 3: the handoff carries this as a single-entry list (the
    Solo Service Provider trivial baseline). It IS a real scored
    candidate in the candidates table (one row per island at gen 0),
    so unlike the Sprint 2 SeedReference projection, this entry
    carries the actual scored fitness — the reader can see what
    "starting from zero" looked like on this run.
    """

    name: str
    summary: str
    capture_mechanism: str
    baseline_fitness: float | None = None
    design_intent: str | None = None


# Backward-compatible alias preserved for any external consumer that
# imported `SeedReference` (the Sprint 2 name). Same shape — only the
# semantics shifted (1 trivial entry vs. 4 reference patterns).
SeedReference = BaselineSeed


class GeneratedDiscovery(BaseModel):
    """A candidate produced by the search loop.

    Sprint 2 redesign: all alive candidates in a run are generated
    discoveries (seeds are not inserted into the DB). `stage4_findings`
    is None for legacy / pre-Stage-4 candidates and an empty list for
    Stage-4-scrutinised candidates that came back clean.
    """

    spec: Architecture
    scores: Scores
    fitness: float
    island_of_origin: int
    generation: int
    lineage: list[int]
    stage4_findings: list[StructuralConcern] | None = None


class VerificationTrail(BaseModel):
    """How the cascade subject was scored, for downstream auditability.

    The cascade subject is the top generated discovery when one exists, or
    nothing at all when the run produced no candidates. In the latter case
    `final_scores` and `adversarial_concerns` are empty / None.

    Sprint 2: `exemplar_comparisons` is retained as an empty list for
    backward-compatible JSON shape but is never populated — Stage 3
    (exemplar similarity) was retired.
    """

    run_id: str
    hyperparameters: dict
    parent_goal_version: str
    verifier_version: str
    final_scores: Scores | None = None
    anchor_used: str
    eval_count: int
    exemplar_comparisons: list[dict] = Field(default_factory=list)
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

    When no candidate exists in the run, this reports `passes=True` with a
    placeholder note.
    """

    passes: bool
    estimated_starting_resources: str
    stage_sequence: list[str]


class Handoff(BaseModel):
    """The complete handoff document.

    Field semantics (Sprint 3):
      - `seed_baselines`: single-entry list — the trivial Solo Service
        Provider baseline every island started from. Carries the actual
        scored fitness of the gen-0 seed copy.
      - `top_generated_discoveries`: top N alive candidates by fitness,
        sorted descending. Excludes gen-0 trivial-seed copies (filtered
        out so the discoveries section reflects what the search produced,
        not what it started from).
      - `no_breakthrough_this_run`: True when no candidate cleared the
        absolute milestone thresholds (fitness AND robustness floors
        from Hyperparameters).
      - `winning_architecture`: the highest-fitness candidate when
        `no_breakthrough_this_run` is False, else null.
    """

    seed_baselines: list[BaselineSeed]
    top_generated_discoveries: list[GeneratedDiscovery]
    no_breakthrough_this_run: bool
    winning_architecture: GeneratedDiscovery | None = None
    verification_trail: VerificationTrail
    drift_log: list[DriftLogEntry]
    parent_goal_alignment: str
    middle_class_entry_check: MiddleClassEntryCheck
    coverage_residual: str
