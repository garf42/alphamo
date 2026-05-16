"""Adversarial framings used by Stage 4 of the cascade.

Phase 2 (Stage 4) supersedes the standalone red-team agent. Each framing
is a separate adversarial lens — different adversaries surface different
failure modes (AlphaEvolve §2.4). Findings carry falsification conditions
so the curator can distinguish blocking issues from notes.

8 framings, all run in parallel per candidate that reaches Stage 4:

  Legacy carryovers from the standalone red-team:
    - regulatory           : licensing / regulator-shutdown / compliance risk
    - economic             : margins, commoditization, competitive erosion
    - operational          : SPOF, hidden labor, one-person violations

  Added in Phase 2:
    - mechanism_robustness : does the mechanism require a specific
                             cultural/regulatory/technological moment that may
                             have closed
    - hidden_dependencies  : un-listed resources, networks, credentials,
                             capital implied by the architecture
    - scaling_cliffs       : non-linear path-to-$1B barriers distinct from
                             general scaling failure modes
    - legal_exposure       : concrete enforcement risks (state AG, IRS, UPL,
                             FDA, class action) that could collapse the
                             architecture

  Added in Sprint 2 (replaced the legacy `scaling` framing, whose coverage
  is preserved by scaling_cliffs + mechanism_robustness):
    - timeline_plausibility: gap between stated timeline and mechanism floor,
                             plus middle-class cash-flow viability during
                             buildup

Sprint 2 (Bug 3) reframed every framing toward yes/no evaluation, anchored
severity to the parent goal, and promoted "default to empty concerns lists"
to the most prominent rule. The previous "examine for X failure modes"
phrasing produced 22-41 concerns per seed regardless of seed quality; the
new phrasing targets 3-10 per candidate, varying with actual structural
strength.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.schemas import Architecture

FRAMINGS: dict[str, str] = {
    "regulatory": (
        "Evaluate whether this candidate has structural regulatory exposure. "
        "If the architecture's value capture and operation don't trigger "
        "material regulatory risk, return an empty concerns list. Empty "
        "results are correct when there is no real regulatory concern under "
        "this framing.\n\n"
        "If real exposure exists, identify the specific risks: which "
        "regulatory regime, which specific provision, what the enforcement "
        "action would look like, what the structural consequence is. "
        "Probes: regulator-shutdown risk, licensing requirements that block "
        "middle-class entry, compliance review failure in a major "
        "jurisdiction."
    ),
    "economic": (
        "Evaluate whether this candidate has a structural economic flaw — "
        "unrealistic margins at scale, a commoditization trap, or "
        "competitive erosion of the capture mechanism before $1B. If unit "
        "economics and the competitive position are sound, return an empty "
        "concerns list. Empty results are correct when there is no real "
        "economic concern under this framing.\n\n"
        "If a flaw exists, identify it concretely: which assumption breaks "
        "at scale, what the resulting margin compression looks like, which "
        "competitor structure erodes the capture mechanism, and over what "
        "timeframe."
    ),
    "operational": (
        "Evaluate whether this candidate has a structural operational flaw "
        "— single points of failure, fragile dependencies, hidden labor "
        "requirements that violate the labor-separation constraint, or "
        "organizational complexity that breaks the one-person threshold. "
        "If operations are clean and the one-person constraint actually "
        "holds, return an empty concerns list. Empty results are correct "
        "when there is no real operational concern under this framing.\n\n"
        "If a flaw exists, identify the specific dependency or labor "
        "requirement, why it's structurally required (not optional), and "
        "how it violates the constraint."
    ),
    "timeline_plausibility": (
        "Evaluate whether this candidate has timeline problems that would "
        "make middle-class execution implausible. If the architecture's "
        "timeline is appropriate to its mechanism and the path to capture "
        "is compatible with middle-class financial constraints, return an "
        "empty concerns list. Empty results are correct when the timeline "
        "is tight for the mechanism and the cash-flow path is realistic "
        "for a middle-class operator.\n\n"
        "For each candidate, assess two coupled timeline questions:\n\n"
        "1. UNNECESSARY SLOWNESS. What timeline does the architecture's "
        "stage-sequence imply from middle-class entry to $1B+ value "
        "capture? Given the mechanism's nature, what's the shortest "
        "reasonable duration this architecture could plausibly compress "
        "to? Some mechanisms have hard floors that aren't penalizable: "
        "biological cycles (breeding, growth — years per cycle), "
        "regulatory/legal processes (months to years for approvals), "
        "cultural adoption (typical curves measured in years), "
        "compounding mathematics (minimum periods for given returns), "
        "network bootstrap (characteristic time-to-critical-mass). The "
        "concern is the gap between stated timeline and mechanism floor "
        "— not absolute duration, but unnecessary delay.\n\n"
        "2. MIDDLE-CLASS FINANCIAL VIABILITY. Can a middle-class operator "
        "sustain the path? A middle-class person needs to eat, pay rent, "
        "and meet other obligations throughout the buildup. The "
        "architecture must either: produce revenue early enough to sustain "
        "the operator, OR be operable as a side-pursuit alongside primary "
        "income, OR reach a self-sustaining point before middle-class "
        "savings are exhausted (typically 12-24 months of savings runway "
        "for a determined middle-class operator). Architectures requiring "
        "multi-year zero-revenue operation from middle-class entry have a "
        "structural problem regardless of mechanism timeline — the parent "
        "goal specifies middle-class entry, and a path that violates "
        "middle-class financial constraints during buildup isn't actually "
        "achievable from middle-class start.\n\n"
        "Examples:\n"
        "- Cultivar IP at 7-15 years, evenings-and-weekends alongside day "
        "job: clean (matches breeding cycle floor; cash flow compatible "
        "with middle-class via primary income).\n"
        "- SaaS product portfolio at 8 years, with revenue from year 1: "
        "clean (timeline appropriate for mechanism; cash flow positive "
        "early).\n"
        "- Software business at 5 years to $1B with zero revenue until "
        "year 4: MEDIUM concern (cash flow requires 4 years of "
        "zero-revenue operation, inconsistent with middle-class survival "
        "unless side-pursuit, and the architecture doesn't describe it "
        "as a side-pursuit).\n"
        "- Patent licensing requiring 15 years of legal infrastructure "
        "buildup before first royalty: MEDIUM concern (long buildup with "
        "no revenue is middle-class-implausible).\n"
        "- Index investing for 150 years to $1B: HIGH concern (extreme "
        "timeline implausibility; no realistic path within a "
        "human-relevant duration; even if mechanism floor matches, the "
        "architecture is incompatible with the parent goal's middle-class "
        "achievability).\n"
        "- 'Buy and hold S&P 500 for 1000 years': HIGH concern (timeline "
        "fundamentally implausible; mechanism's required duration "
        "conflicts with the parent goal's framing of achievability).\n"
        "- Network bootstrap claiming '$1B in 2 years from middle-class "
        "entry through viral content': LOW or MEDIUM concern (assess "
        "whether the architecture's mechanism actually supports the "
        "asserted compressed timeline, or whether the timeline is "
        "hand-waved relative to the mechanism's bootstrap floor).\n\n"
        "Severity calibration for this framing:\n"
        "- HIGH: either (a) timeline is dramatically longer than mechanism "
        "requires (3x+ the floor) AND no clear cash-flow path for "
        "middle-class operator, OR (b) timeline is fundamentally "
        "inconsistent with the parent goal's human-relevant achievability "
        "(centuries-long compounding, etc.).\n"
        "- MEDIUM: either (a) timeline is meaningfully longer than "
        "mechanism requires (1.5-3x floor) with cash-flow concerns, OR "
        "(b) timeline reasonable for mechanism but multi-year zero-revenue "
        "buildup creates middle-class survival problems, OR (c) timeline "
        "is long but bounded (20-50 years) without clear cash-flow "
        "workability.\n"
        "- LOW: some unnecessary slack in timeline (1.1-1.5x mechanism "
        "floor), or minor cash-flow concerns during buildup, but the "
        "architecture is broadly workable.\n\n"
        "The goal is balanced selection pressure: shorter timelines win "
        "over longer for similar mechanisms, AND middle-class cash-flow "
        "realism is enforced, without rigid cutoffs that would prevent "
        "legitimately-long-timeline mechanisms (like cultivar IP) from "
        "winning when they're appropriate."
    ),
    "mechanism_robustness": (
        "Evaluate whether the value-capture mechanism works as a structural "
        "pattern OR depends on a specific historical moment that may have "
        "closed (cultural, regulatory, or technological window). If the "
        "mechanism is genuinely structural — works under current "
        "conditions, not just historical ones — return an empty concerns "
        "list. Empty results are correct when there is no real "
        "moment-dependence concern under this framing.\n\n"
        "If real moment-dependence exists, identify the specific window: "
        "pre-regulation gap, first-mover cultural moment, technology-"
        "adoption inflection point, spectrum / domain / namespace "
        "allocation window that has since filled — and explain why it "
        "cannot be reproduced today. A configuration that only worked "
        "because of an unreproducible moment is fragile even if it "
        "succeeded once."
    ),
    "hidden_dependencies": (
        "Evaluate whether the architecture relies on resources, networks, "
        "credentials, or capital NOT listed in its entry_resources "
        "description. If the description is honest about what the "
        "architecture needs, return an empty concerns list. Empty results "
        "are correct when there is no real hidden-dependency concern under "
        "this framing.\n\n"
        "If hidden dependencies exist, identify the unstated prerequisite "
        "(industry network, specific credential, prior reputation, family "
        "guarantor capital, insider regulatory knowledge) and explain why "
        "the architecture cannot function without it. A candidate that "
        "says 'modest savings and skill' but tacitly assumes any of these "
        "violates the middle-class-accessible constraint even if it "
        "formally passed Stage 1."
    ),
    "scaling_cliffs": (
        "Evaluate whether the path from current scale to $1B+ contains a "
        "non-linear barrier distinct from generic scaling-cost issues. If "
        "the path to $1B is structurally smooth — no cold-start cliff, no "
        "capital wall, no regulatory-threshold trip, no platform-dependency "
        "collapse, no attention ceiling — return an empty concerns list. "
        "Empty results are correct when there is no real cliff under this "
        "framing.\n\n"
        "If a cliff exists, identify it concretely: network-effect "
        "cold-start failure, capital-intensity wall that requires outside "
        "funding (breaking the single-individual constraint at scale), "
        "regulatory-threshold trip (AUM rules, employee-count rules, "
        "revenue-based licensure), platform-dependency collapse, or "
        "attention-ceiling exhaustion. A configuration that grows smoothly "
        "to $10M but hits a wall at $100M doesn't reach $1B."
    ),
    "legal_exposure": (
        "Evaluate whether this candidate has concrete regulatory "
        "enforcement risk that could collapse the architecture suddenly "
        "rather than gradually. If the architecture doesn't sit in any of "
        "the known high-exposure shapes (UPL/UPM, state-AG action, IRS "
        "classification, FTC unfairness/deception, FDA jurisdiction, "
        "state-by-state licensure, class-action exposure on consumer-"
        "facing terms), return an empty concerns list. Empty results are "
        "correct when there is no real enforcement-risk concern under this "
        "framing.\n\n"
        "If enforcement risk exists, identify the specific risk: "
        "unauthorized practice of law (UPL), unauthorized practice of "
        "medicine, state attorney-general consumer-protection action, IRS "
        "partnership/employee classification challenges, FTC unfairness or "
        "deception claims, FDA jurisdiction over health-adjacent claims, "
        "state-by-state licensure exposure, class-action exposure on "
        "consumer-facing terms. The Medvi-class navigation-layer pattern "
        "is a known high-exposure shape; if the candidate is shaped that "
        "way, scrutinize hard for these risks."
    ),
}

DEFAULT_FRAMINGS: list[str] = list(FRAMINGS.keys())


def stage4_system(framing: str) -> str:
    """System prompt for one Stage 4 adversarial framing pass.

    The model emits concerns; the stage aggregates them and computes a
    deterministic robustness score from the aggregate severity. The model
    is NOT asked to produce a robustness scalar — its job is to surface
    well-formed concerns under this specific lens, OR explicitly return an
    empty list when no concern exists.
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
1. Default to empty concerns lists unless you can identify a specific \
structural issue with clear evidence from the architecture's own \
description. The architecture being scrutinized is one of multiple \
candidates being compared; not every framing applies to every candidate. \
Empty results when no concern exists are correct.
2. Every concern MUST include a falsification_condition — a concrete fact \
that, if true, would make the concern NOT a problem. Concerns without a \
falsifier are filtered out at validation time. This is non-negotiable.
3. Surface flaws are not concerns — only structural ones. A typo is not a \
concern; a missing capture mechanism IS.
4. Severity is your judgment of how badly this concern would degrade the \
architecture if it materialized — calibrated against the parent goal \
(see "Severity calibration" below).
5. Do NOT emit a robustness score. The stage computes that deterministically \
from the aggregate severity of concerns across all framings.

Severity calibration:

HIGH: Would prevent the architecture from reaching $1B+ value capture \
entirely. Examples:
- The legal mechanism does not actually grant exclusivity (e.g., the \
  patent is unenforceable, the trademark is generic, the copyright \
  doesn't cover the claimed scope).
- The value-capture step requires a regulatory regime that doesn't \
  exist or has been struck down.
- The single-person constraint is violated by the architecture's stated \
  operations (e.g., the architecture actually requires 10+ employees to \
  function).
- The capture mechanism is structurally impossible (e.g., the asymmetry \
  the architecture relies on doesn't actually exist in the relevant \
  market).

MEDIUM: Would cap upside well below $1B or require structural redesign. \
Examples:
- Scaling limits at a specific size (e.g., the addressable market caps \
  at $200M).
- Competitive dynamics that erode margins over time (e.g., the \
  asymmetric position is replicable by competitors within 3-5 years).
- Entry cost dependencies that grow with adoption (e.g., customer \
  acquisition costs scale faster than revenue).
- Regulatory regime change risk that materially affects the capture \
  mechanism.

LOW: Worth noting but the architecture survives. Examples:
- Minor optimization opportunities (e.g., the timing could be improved \
  by 6 months).
- Surface-level concerns that don't affect the structural mechanism \
  (e.g., the named example could be replaced with a more current one).
- Issues that are addressable through normal operational iteration.

When in doubt between HIGH and MEDIUM, ask: does this concern prevent \
$1B capture entirely, or does it cap upside below $1B? The first is \
HIGH, the second is MEDIUM.

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
