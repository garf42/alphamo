"""Structured per-stage evaluator output.

The evaluator stages emit these as structured-output payloads parsed by
`client.messages.parse()`. The cascade composes them into the system-wide
`Scores` shape stored on each candidate.
"""

from __future__ import annotations

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
