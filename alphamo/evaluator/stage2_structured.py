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
# human-touch operations the architecture stacks.
_PER_LABOR_POINT_PENALTY = 0.08

# Bottom-line-judgement penalty multipliers. Each is "heavy but not
# zero" — preserves gradient so the proposer gets "wrong direction"
# signal instead of a hard zero that erases the dimension.
_ONE_PERSON_FAIL_FACTOR = 0.3        # one_person_operable=False
_NO_MARKET_NAMED_FACTOR = 0.3        # target_market_named=False
_NO_CAPTURE_MECHANISM_FACTOR = 0.4   # capture_mechanism_identified=False
_NO_SEPARATION_FACTOR = 0.5          # separation_achieved=False

# Boost applied to the market component when nonlinear_scaling_path=True.
# Capped at 1.0 in the formula — a candidate that already scores 1.0 on
# every market input can't go above the dimension's ceiling.
_NONLINEAR_SCALING_BOOST = 1.3

# Baseline when the model populates BOTH autonomous_value_sources and
# active_labor_requirements as empty lists — no evidence either way.
# Centered low-ish so an absence of evidence isn't a free pass.
_SEPARATION_NO_EVIDENCE = 0.25


def compute_structural(finding: Stage2Finding) -> float:
    """Deterministic structural score from Stage 2 evidence fields.

    Range: [0.0, 1.0]. Analogous to `compute_robustness` for Stage 3 —
    the LLM provides categorical / boolean / list evidence, this
    function maps it to a scalar via fixed constants. No randomness,
    no LLM calls, no state-dependent inputs.

    Aggregation: equal-weighted arithmetic mean of three sub-component
    scores (ops, market, separation). Each sub-component is bounded
    [0, 1] before averaging.

    Sub-component formulas:

      ops_score
        = max(0, AUTOMATION_SCORES[automation_plausibility]
               - 0.08 * len(labor_dependency_points))
        × (1.0 if one_person_operable else 0.3)

      market_score
        = TAM_SCORES[tam_estimate]
        × (1.0 if target_market_named else 0.3)
        × (1.0 if capture_mechanism_identified else 0.4)
        × (1.3 if nonlinear_scaling_path else 1.0)
        # capped at 1.0

      sep_score
        = if no labor lists at all: 0.25
          else: n_autonomous / (n_autonomous + n_active)
        × (1.0 if separation_achieved else 0.5)

      structural = (ops_score + market_score + sep_score) / 3
        # rounded to 3 decimal places

    Each sub-criterion contributes independently — no cross-criterion
    interaction in v1. The constants above are explicit and auditable;
    if a future calibration finds them wrong, the bend is one edit
    here, not a re-ranking of every persisted candidate (their
    Stage 2 evidence is persisted in `candidates.stage2_evidence`
    starting this sprint).
    """
    # one-person-threshold component
    labor_count = len(finding.labor_dependency_points)
    auto_score = _AUTOMATION_SCORES[finding.automation_plausibility]
    ops_score = max(0.0, auto_score - _PER_LABOR_POINT_PENALTY * labor_count)
    if not finding.one_person_operable:
        ops_score *= _ONE_PERSON_FAIL_FACTOR

    # billion-dollar-potential component
    market_score = _TAM_SCORES[finding.tam_estimate]
    if not finding.target_market_named:
        market_score *= _NO_MARKET_NAMED_FACTOR
    if not finding.capture_mechanism_identified:
        market_score *= _NO_CAPTURE_MECHANISM_FACTOR
    if finding.nonlinear_scaling_path:
        market_score = min(1.0, market_score * _NONLINEAR_SCALING_BOOST)

    # labor-separation component
    n_auto = len(finding.autonomous_value_sources)
    n_active = len(finding.active_labor_requirements)
    if n_auto + n_active == 0:
        sep_score = _SEPARATION_NO_EVIDENCE
    else:
        sep_score = n_auto / (n_auto + n_active)
    if not finding.separation_achieved:
        sep_score *= _NO_SEPARATION_FACTOR

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
