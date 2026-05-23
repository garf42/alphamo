"""Stage 2 — evidence extraction + deterministic structural score.

Sprint 14: routed through `BaseProvider.parse(...)`. Production default
is Fireworks/DeepSeek V4 Flash. No reasoning config — Stage 2 is
structured-classification work that doesn't benefit from extended
thinking. Caching is via `cached_system(...)`.

Sprint Stage 2 PAJAMA: the LLM call returns evidence (categoricals +
booleans + lists), not a structural-score float. `compute_structural`
maps the evidence to a deterministic scalar — mirroring Stage 3's
`compute_robustness`. Pre-PAJAMA the model produced four floats
(one_person_threshold, billion_dollar_potential, labor_separation,
structural) and the cascade trusted the model's aggregate `structural`
directly; the variance test (commit bcdb86c, 3 candidates × 5 trials)
showed stdev 0.406-0.457 on that aggregate. Under PAJAMA the model's
freedom is constrained to enum / boolean / list shapes the
json_schema response_format enforces; the aggregation moves to a
fixed Python function with auditable constants.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import Stage2OutputError, TelemetryContext
from alphamo.evaluator._common import (
    MAX_TOKENS_MEDIUM,
    SONNET_MODEL,
    cached_system,
)
from alphamo.prompts.evaluator_prompts import STAGE2_SYSTEM, render_candidate
from alphamo.providers.base import ensure_provider
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    AutomationPlausibility,
    Stage2Finding,
    TAMEstimate,
)


# --------------------------------------------------------------------- compute_structural

# Per-category weight for the automation-plausibility scalar input to
# the ops-component of the structural score. Calibration intent:
# "already_automated" pegs the ops component at 1.0 absent labor
# penalties; "requires_human_judgment" tops out at 0.1 even with zero
# labor points (a fundamentally human-judgment-required architecture
# can't be one-person-operable at $1B+ scale).
_AUTOMATION_SCORES: dict[AutomationPlausibility, float] = {
    AutomationPlausibility.ALREADY_AUTOMATED: 1.0,
    AutomationPlausibility.AUTOMATABLE_WITH_EXISTING_TOOLS: 0.75,
    AutomationPlausibility.REQUIRES_CUSTOM_ENGINEERING: 0.4,
    AutomationPlausibility.REQUIRES_HUMAN_JUDGMENT: 0.1,
}

# Per-bucket weight for the TAM categorical input to the market-component
# of the structural score. Calibration: ">$100B" comfortably exceeds the
# $1B parent goal (1.0); "$10B-$100B" gives 10-100× headroom (0.7);
# "$1B-$10B" is plausible but at the floor (0.4); below $1B fails the
# parent goal outright (0.0); "unquantifiable" is the honest-vagueness
# bucket — small score so the proposer is incentivized to pin a market
# down rather than claim breadth.
_TAM_SCORES: dict[TAMEstimate, float] = {
    TAMEstimate.SUB_1B: 0.0,
    TAMEstimate.ONE_TO_10B: 0.4,
    TAMEstimate.TEN_TO_100B: 0.7,
    TAMEstimate.OVER_100B: 1.0,
    TAMEstimate.UNQUANTIFIABLE: 0.2,
}

# Per-labor-dependency-point penalty on the ops component. With auto
# score 1.0, 12.5 labor points zeros the ops component entirely; with
# auto score 0.4 (REQUIRES_CUSTOM_ENGINEERING), 5 labor points zero it.
# The intent: incremental penalty proportional to how many discrete
# human-touch operations the architecture stacks. Already additive
# and well-behaved pre-PAJAMA-stabilization; preserved unchanged.
_PER_LABOR_POINT_PENALTY = 0.08

# Sprint PAJAMA-stabilization: bottom-line-judgement penalties are now
# ADDITIVE rather than multiplicative. Pre-stabilization the formula
# used `× 0.3 / × 0.4 / × 0.5` boolean gates, which produced 50-70%
# structural-score swings when the LLM flipped a single bool between
# extractions (Proptax stdev 0.213, TaxVeritas 0.095 in the variance
# test). The new shape mirrors `compute_feasibility`'s additive
# pattern (max single-field swing ≤ 0.15 on the Stage 1 score, stdev
# 0.011-0.038). The constraint here: max single-field swing on the
# final structural score ≤ 0.20, achieved by bounding each penalty
# at ≤ 0.20 on its respective sub-component (sub-component / 3 = the
# final-score impact per flip).
_ONE_PERSON_FAIL_PENALTY = 0.20      # one_person_operable=False
_NO_MARKET_NAMED_PENALTY = 0.15      # target_market_named=False
_NO_CAPTURE_MECHANISM_PENALTY = 0.15 # capture_mechanism_identified=False
_NO_SEPARATION_PENALTY = 0.20        # separation_achieved=False

# Sprint PAJAMA-stabilization: additive bonus replaces the
# `× 1.3 capped at 1.0` boost. Bonus is applied to market_score and
# the dimension is still capped at 1.0 (a candidate at the dimension
# ceiling can't go above it).
_NONLINEAR_SCALING_BONUS = 0.10

# Baseline when the model populates BOTH autonomous_value_sources and
# active_labor_requirements as empty lists — no evidence either way.
# Centered low-ish so an absence of evidence isn't a free pass.
# Preserved unchanged.
_SEPARATION_NO_EVIDENCE = 0.25


def compute_structural(finding: Stage2Finding) -> float:
    """Deterministic structural score from Stage 2 evidence fields.

    Range: [0.0, 1.0]. Analogous to `compute_robustness` for Stage 3 —
    the LLM provides categorical / boolean / list evidence, this
    function maps it to a scalar via fixed constants. No randomness,
    no LLM calls, no state-dependent inputs.

    Sprint PAJAMA-stabilization: rewritten with ADDITIVE penalties to
    cap single-field-flip variance. Pre-stabilization the formula used
    multiplicative gates (`× 0.3` for one_person_operable=False, `× 0.5`
    for separation_achieved=False, etc.) which produced 50-70% structural
    swings when the LLM flipped a single bool. The variance test
    (commit 0da8f2c) showed Proptax stdev 0.213 and TaxVeritas 0.095 —
    the dominant remaining noise source after Stage 1 PAJAMA. Stage 1's
    additive `compute_feasibility` produced stdev 0.011-0.038 on the
    same variance test; this rewrite applies the same pattern.

    Aggregation: equal-weighted arithmetic mean of three sub-component
    scores (ops, market, separation). Each sub-component is bounded
    [0, 1] before averaging via `max(0, ...)` / `min(1.0, ...)` clamps.

    Sub-component formulas:

      ops_score
        = max(0, AUTOMATION_SCORES[automation_plausibility]
               - 0.08 * len(labor_dependency_points))
        - (0.20 if not one_person_operable else 0.0)
        # clamped to [0, 1]

      market_score
        = TAM_SCORES[tam_estimate]
        - (0.15 if not target_market_named else 0.0)
        - (0.15 if not capture_mechanism_identified else 0.0)
        + (0.10 if nonlinear_scaling_path else 0.0)
        # clamped to [0, 1]

      sep_score
        = (if no lists: 0.25; else n_autonomous / (n_autonomous + n_active))
        - (0.20 if not separation_achieved else 0.0)
        # clamped to [0, 1]

      structural = (ops_score + market_score + sep_score) / 3
        # rounded to 3 decimal places

    Each sub-criterion contributes independently — no cross-criterion
    interaction. Maximum single-field-flip impact on final structural:
      - one_person_operable flip:   up to 0.20 on ops   → 0.067 on structural
      - target_market_named flip:   up to 0.15 on mkt   → 0.050 on structural
      - capture_mechanism flip:     up to 0.15 on mkt   → 0.050 on structural
      - nonlinear_scaling flip:     up to 0.10 on mkt   → 0.033 on structural
      - separation_achieved flip:   up to 0.20 on sep   → 0.067 on structural
      - per_labor_point flip (Δ1):  0.08 on ops         → 0.027 on structural
    Worst single-field swing: 0.067, well under the design cap of 0.20.
    """
    # one-person-threshold component
    labor_count = len(finding.labor_dependency_points)
    auto_score = _AUTOMATION_SCORES[finding.automation_plausibility]
    ops_score = max(0.0, auto_score - _PER_LABOR_POINT_PENALTY * labor_count)
    if not finding.one_person_operable:
        ops_score = max(0.0, ops_score - _ONE_PERSON_FAIL_PENALTY)

    # billion-dollar-potential component
    market_score = _TAM_SCORES[finding.tam_estimate]
    if not finding.target_market_named:
        market_score = max(0.0, market_score - _NO_MARKET_NAMED_PENALTY)
    if not finding.capture_mechanism_identified:
        market_score = max(0.0, market_score - _NO_CAPTURE_MECHANISM_PENALTY)
    if finding.nonlinear_scaling_path:
        market_score = min(1.0, market_score + _NONLINEAR_SCALING_BONUS)

    # labor-separation component
    n_auto = len(finding.autonomous_value_sources)
    n_active = len(finding.active_labor_requirements)
    if n_auto + n_active == 0:
        sep_score = _SEPARATION_NO_EVIDENCE
    else:
        sep_score = n_auto / (n_auto + n_active)
    if not finding.separation_achieved:
        sep_score = max(0.0, sep_score - _NO_SEPARATION_PENALTY)

    return round((ops_score + market_score + sep_score) / 3.0, 3)


# --------------------------------------------------------------------- LLM call


def stage2_structured(
    architecture: Architecture,
    client: Any,
    telemetry: TelemetryContext | None = None,
    model: str = SONNET_MODEL,
) -> Stage2Finding:
    """Score the candidate against the parent goal's structural criteria."""
    provider = ensure_provider(client)
    return provider.parse(
        error_cls=Stage2OutputError,
        component="stage2",
        telemetry=telemetry,
        model=model,
        max_tokens=MAX_TOKENS_MEDIUM,
        system=cached_system(STAGE2_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage2Finding,
    )
