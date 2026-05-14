"""Structured per-stage evaluator output and meta-layer findings.

Phase 02 added Stage{1,2,3}Finding for the evaluator cascade.
Phase 05 adds RawFinding (LLM output) → MetaFinding (Python-side, tagged
with source and framing) → ClassifiedFinding → CuratorDecision.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Stage1Finding(BaseModel):
    """Stage 1 — cheap feasibility + middle-class accessibility filter."""

    feasibility: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How plausible is this architecture as a value-capture configuration? "
            "1.0 = clearly coherent; 0.0 = malformed or contradictory."
        ),
    )
    middle_class_accessible: bool = Field(
        description=(
            "True iff the entry_resources describe a starting position reachable "
            "from middle-class personal resources with no privileged starting "
            "conditions (no family wealth, no institutional backing, no pre-existing "
            "industry network, no bespoke legal structuring)."
        ),
    )
    reasoning: str = Field(
        description="One or two sentences. Why this score and accessibility verdict.",
    )


class Stage2Finding(BaseModel):
    """Stage 2 — structured criteria evaluation against the parent goal."""

    one_person_threshold: float = Field(
        ge=0.0,
        le=1.0,
        description="How well does this satisfy the single-individual constraint?",
    )
    billion_dollar_potential: float = Field(
        ge=0.0,
        le=1.0,
        description="How plausibly does this configuration reach $1B+ in capture?",
    )
    labor_separation: float = Field(
        ge=0.0,
        le=1.0,
        description="How clean is the separation between value capture and operational labor?",
    )
    structural: float = Field(
        ge=0.0,
        le=1.0,
        description="Aggregate structural fit, weighing the three sub-criteria.",
    )
    reasoning: str = Field(
        description="Two to four sentences justifying the structural score.",
    )


class Stage3Finding(BaseModel):
    """Stage 3 — deep comparison against the exemplar library."""

    closest_exemplar: str = Field(
        description="Name of the exemplar (Satoshi / Rowling / Levels) the candidate most resembles structurally.",
    )
    similarity: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How structurally similar is the candidate to its closest exemplar? "
            "1.0 = same structural pattern (not the same surface details); "
            "0.0 = no structural relationship."
        ),
    )
    reasoning: str = Field(
        description="Two to four sentences justifying the similarity score and exemplar choice.",
    )


class Severity(str, Enum):
    """Per-finding severity tag from the research/red-team agents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RawFinding(BaseModel):
    """LLM-facing schema for a single research or red-team finding.

    `source` and `framing` are NOT part of the LLM output — the Python
    wrapper sets them when promoting a RawFinding to a MetaFinding.
    """

    claim: str = Field(description="The finding itself, one or two sentences.")
    evidence: str = Field(
        description=(
            "Direct citation, URL, or concise reasoning supporting the claim."
        ),
    )
    falsification_condition: str = Field(
        description=(
            "A concrete fact that, if true, would make this finding NOT a "
            "problem. Required — empty strings will be dropped at validation."
        ),
    )
    severity: Severity = Field(
        description="low / medium / high. High = blocks the parent goal as stated."
    )


class RawFindingsBatch(BaseModel):
    """LLM-facing schema for an entire research or red-team pass."""

    findings: list[RawFinding] = Field(
        description=(
            "Zero or more findings. Empty list is a first-class output — emit "
            "it when an honest pass surfaces nothing material."
        ),
    )


class MetaFinding(BaseModel):
    """Python-side finding: a RawFinding tagged with its source and framing."""

    source: str = Field(description='"research" or "redteam".')
    framing: str | None = Field(
        default=None,
        description="Red-team framing tag (regulatory, economic, …) or None.",
    )
    claim: str
    evidence: str
    falsification_condition: str
    severity: Severity


class Classification(str, Enum):
    """Curator's verdict on a single finding."""

    STRUCTURAL = "structural"
    COSMETIC = "cosmetic"


class ClassificationVerdict(BaseModel):
    """LLM output for one classification decision."""

    classification: Classification = Field(
        description=(
            "STRUCTURAL = warrants pausing the build / updating context. "
            "COSMETIC = note and continue. Default cosmetic unless clearly structural."
        ),
    )
    rationale: str = Field(
        description="One or two sentences justifying the classification."
    )


class ClassifiedFinding(BaseModel):
    """A finding paired with the curator's classification."""

    finding: MetaFinding
    classification: Classification
    rationale: str


class CuratorAction(str, Enum):
    """The action returned by Curator.curate()."""

    CONTINUE = "continue"
    RECALIBRATE_VERIFIER = "recalibrate_verifier"
    REFRAME_PARENT_GOAL = "reframe_parent_goal"
    PAUSE_FOR_HUMAN = "pause_for_human"


class CuratorDecision(BaseModel):
    """Final output of the curator for one batch of findings."""

    action: CuratorAction
    classified: list[ClassifiedFinding]
    rationale: str
