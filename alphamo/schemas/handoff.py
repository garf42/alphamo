"""Handoff schemas — the structured deliverable produced on run termination.

The handoff is the load-bearing artefact: everything before it is plumbing in
service of producing this document. Skill 4 (implementation-handoff) consumes
the document and packages it for autonomous build.

Sprint 2 redesign: seeds appear only as descriptive references (mechanism /
structural insight / known fragilities), without fitness numbers. The
`no_breakthrough_this_run` flag and `winning_architecture` field are gated
on absolute milestone thresholds (fitness AND robustness clearing the
configured floors), not on seed-relative comparison.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from alphamo.schemas.architecture import Architecture
from alphamo.schemas.findings import StructuralConcern
from alphamo.schemas.scores import Scores


class SeedReference(BaseModel):
    """One reference exemplar's descriptive entry.

    Listed in the handoff so the reader sees the structural patterns the
    search was anchored against, without any fitness number suggesting the
    seed itself was a candidate. Seeds are not scored in the Sprint 2
    redesign — they appear in proposer prompts as patterns, and here as
    descriptive reference, and nowhere else in the pipeline.
    """

    name: str
    summary: str
    capture_mechanism: str
    structural_insight: str | None = None
    known_fragilities: str | None = None


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

    Field semantics (Sprint 2):
      - `seed_baselines`: descriptive reference. One entry per seed in
        `SEED_REFERENCES`. NO fitness number — seeds aren't scored.
      - `top_generated_discoveries`: research output. Top N alive
        candidates by fitness, sorted descending.
      - `no_breakthrough_this_run`: True when no candidate cleared the
        absolute milestone thresholds (fitness AND robustness floors
        from Hyperparameters). Honest summary flag.
      - `winning_architecture`: the highest-fitness candidate when
        `no_breakthrough_this_run` is False, else null.
    """

    seed_baselines: list[SeedReference]
    top_generated_discoveries: list[GeneratedDiscovery]
    no_breakthrough_this_run: bool
    winning_architecture: GeneratedDiscovery | None = None
    verification_trail: VerificationTrail
    drift_log: list[DriftLogEntry]
    parent_goal_alignment: str
    middle_class_entry_check: MiddleClassEntryCheck
    coverage_residual: str
