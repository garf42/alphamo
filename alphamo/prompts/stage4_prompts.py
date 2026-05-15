"""Adversarial framings used by Stage 4 of the cascade.

Phase 2 (Stage 4) supersedes the standalone red-team agent. Each framing
is a separate adversarial lens — different adversaries surface different
failure modes (AlphaEvolve §2.4). Findings carry falsification conditions
so the curator can distinguish blocking issues from notes.

8 framings, all run in parallel per candidate that reaches Stage 4:

  Original four (kept from the legacy red-team):
    - regulatory          : licensing / regulator-shutdown / compliance risk
    - economic            : margins, commoditization, competitive erosion
    - operational         : SPOF, hidden labor, one-person violations
    - scaling             : superlinear costs, mechanism degradation at scale

  Four new (added in Phase 2):
    - mechanism_robustness: does the mechanism require a specific
                            cultural/regulatory/technological moment that may
                            have closed
    - hidden_dependencies : un-listed resources, networks, credentials,
                            capital implied by the architecture
    - scaling_cliffs      : non-linear path-to-$1B barriers distinct from
                            general scaling failure modes
    - legal_exposure      : concrete enforcement risks (state AG, IRS, UPL,
                            FDA, class action) that could collapse the
                            architecture
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.schemas import Architecture

FRAMINGS: dict[str, str] = {
    "regulatory": (
        "Examine the candidate for regulatory and legal failure modes the "
        "evaluator might have missed. Could a regulator shut it down? Are "
        "there licensing requirements that block middle-class entry? Could the "
        "structure fail compliance review in a major jurisdiction?"
    ),
    "economic": (
        "Examine the candidate for economic and unit-economics failure modes. "
        "Are assumed margins realistic at scale? Is there a commoditization "
        "trap? Does competition erode the capture mechanism before it reaches "
        "$1B?"
    ),
    "operational": (
        "Examine the candidate for operational failure modes. Single points of "
        "failure, fragile dependencies, hidden labor requirements that would "
        "violate the labor-separation constraint, organizational complexity "
        "that breaks the one-person threshold."
    ),
    "scaling": (
        "Examine the candidate for scaling failure modes. Does the capture "
        "mechanism degrade at scale? Are there hidden costs that grow "
        "superlinearly? Does the architecture force the single individual to "
        "do more work as it scales (violating labor separation)?"
    ),
    "mechanism_robustness": (
        "Examine whether the value-capture mechanism works as a structural "
        "pattern OR depends on a specific historical moment that may have "
        "closed. Identify cultural, regulatory, or technological windows the "
        "architecture implicitly assumes. A configuration that only works "
        "because of an unreproducible moment is fragile even if it succeeded "
        "once. Concrete examples to probe for: pre-regulation windows, "
        "first-mover cultural moments, technology-adoption inflection points, "
        "spectrum / domain / namespace allocation windows that have since "
        "filled. If the mechanism is genuinely structural (works under "
        "current conditions, not just historical ones), say so."
    ),
    "hidden_dependencies": (
        "Examine whether the architecture relies on resources, networks, "
        "credentials, or capital NOT listed in its entry_resources description. "
        "A description that says 'modest savings and skill' but tacitly assumes "
        "an industry network, a specific credential, prior reputation, family "
        "guarantor capital, or insider regulatory knowledge violates the "
        "middle-class-accessible constraint even if the formal description "
        "passes Stage 1. Identify the unstated prerequisites. If there are "
        "none — the description is honest about what the architecture needs — "
        "say so explicitly."
    ),
    "scaling_cliffs": (
        "Examine the path from current scale to $1B+ for non-linear barriers "
        "distinct from generic scaling-cost issues. Concrete probes: network-"
        "effect cold-start failure, capital-intensity walls that require "
        "outside funding (breaking the single-individual constraint at scale), "
        "regulatory-threshold trips (AUM rules, employee-count rules, "
        "revenue-based licensure), platform-dependency collapse, attention-"
        "ceiling exhaustion. A configuration that grows smoothly to $10M but "
        "hits a wall at $100M doesn't reach $1B."
    ),
    "legal_exposure": (
        "Examine for specific regulatory enforcement risks that could collapse "
        "the architecture suddenly rather than gradually. Concrete probes: "
        "unauthorized practice of law (UPL), unauthorized practice of "
        "medicine, state attorney-general consumer-protection action, "
        "IRS partnership/employee classification challenges, FTC unfairness "
        "or deception claims, FDA jurisdiction over health-adjacent claims, "
        "state-by-state licensure exposure, class-action exposure on consumer-"
        "facing terms. The Medvi-class navigation-layer pattern is a known "
        "high-exposure shape and should be scrutinized hard for these risks."
    ),
}

DEFAULT_FRAMINGS: list[str] = list(FRAMINGS.keys())


def stage4_system(framing: str) -> str:
    """System prompt for one Stage 4 adversarial framing pass.

    The model emits concerns; the stage aggregates them and computes a
    deterministic robustness score from the aggregate severity. The model
    is NOT asked to produce a robustness scalar — its job is to surface
    well-formed concerns under this specific lens.
    """
    if framing not in FRAMINGS:
        raise KeyError(f"unknown Stage 4 framing: {framing!r}")
    return f"""\
You are the Stage 4 adversarial evaluator for an evolutionary search over \
value-capture architectures. Your job is to find STRUCTURAL flaws the \
upstream cascade (feasibility, structural-criteria, exemplar-similarity) \
might have missed.

Framing for this pass: {FRAMINGS[framing]}

Discipline:
1. Every concern MUST include a falsification_condition — a concrete fact \
that, if true, would make the concern NOT a problem. Concerns without a \
falsifier are filtered out at validation time. This is non-negotiable.
2. Empty results are first-class outputs. "No significant structural flaws \
under this framing" is the correct answer when you find none; do NOT \
manufacture concerns to look thorough.
3. Surface flaws are not concerns — only structural ones. A typo is not a \
concern; a missing capture mechanism IS.
4. Severity is your judgment of how badly this concern would degrade the \
architecture if it materialized. HIGH = collapses the architecture; \
MEDIUM = significant degradation but plausibly survivable; LOW = note worth \
mentioning that probably doesn't move the dial.
5. Do NOT emit a robustness score. The stage computes that deterministically \
from the aggregate severity of concerns across all framings.

The parent goal you are scrutinizing against:

{PARENT_GOAL}\
"""


def render_candidate(architecture: Architecture) -> str:
    """Render the candidate as the user-turn payload for any framing."""
    return (
        f"Candidate under adversarial review:\n\n"
        f"Name: {architecture.name}\n"
        f"Summary: {architecture.summary}\n"
        f"Value chain: {architecture.value_chain}\n"
        f"Capture mechanism: {architecture.capture_mechanism}\n"
        f"Entry resources: {architecture.entry_resources}"
    )
