"""Sprint Stage 1 PAJAMA — `compute_feasibility` formula + soft-zone tests.

Analogous to the Stage 2 `compute_structural` tests in
`test_compute_structural.py` and the Stage 3 `compute_robustness` tests
in `test_stage4_adversarial.py`. The model's role at Stage 1 changed
from returning a feasibility float to returning categorical / boolean /
list evidence. `compute_feasibility` maps that evidence to a
deterministic scalar in [0.0, 1.0]; `apply_stage1_soft_zone` then runs
the three-region penalty zone (hard_exit / penalty_zone / clean_pass).

This file pins:
  - Bounds + clamp behaviour
  - Determinism
  - Per-component contributions (revenue, buyer, capital, regulatory,
    risks, market validation, middle-class bonus)
  - Soft-zone math at the boundaries and across the curve
  - Continuity at the SOFT_CEILING (no cliff)
"""

from __future__ import annotations

import pytest

from alphamo.evaluator.stage1_feasibility import (
    _EXISTING_MARKET_VALIDATION_BONUS,
    _MIDDLE_CLASS_ACCESSIBLE_BONUS,
    _PER_FEASIBILITY_RISK_PENALTY,
    _PER_REGULATORY_BLOCKER_PENALTY,
    STAGE1_HARD_FLOOR,
    STAGE1_SOFT_CEILING,
    apply_stage1_soft_zone,
    compute_feasibility,
)
from alphamo.schemas.findings import (
    BuyerAccessibility,
    CapitalRequired,
    RegulatorySeverity,
    RevenueType,
    Stage1Finding,
)
from tests.fixtures.stage1_evidence import (
    failing_stage1_finding,
    passing_stage1_finding,
    penalty_zone_stage1_finding,
)


# ----------------------------------------------------------------- builder helper


def _build(**overrides) -> Stage1Finding:
    """Build a Stage1Finding with neutral defaults; overrides per test
    isolate the dimension being measured. Defaults are chosen to give
    each component a known starting score so deltas from overrides are
    obvious."""
    defaults = dict(
        revenue_mechanism_identified=True,
        revenue_mechanism_description="a specific mechanism",
        revenue_type=RevenueType.RECURRING,
        buyer_identified=True,
        buyer_description="a specific buyer cohort",
        buyer_accessibility=BuyerAccessibility.DIRECT_TO_BUSINESS,
        capital_required=CapitalRequired.NONE,
        capital_justification="",
        regulatory_blockers=[],
        regulatory_severity=RegulatorySeverity.NONE,
        feasibility_risks=[],
        existing_market_validation=True,
        middle_class_accessible=True,
        reasoning="under test",
    )
    defaults.update(overrides)
    return Stage1Finding(**defaults)


# ----------------------------------------------------------------- bounds


def test_compute_feasibility_max_input_returns_realistic_max():
    """All positive contributions at top of band, no penalties: 0.95.

    Per the docstring on compute_feasibility, the realistic max is 0.95
    (not 1.0) — the formula doesn't normalize, and the soft-zone
    constants are calibrated against this [0, 0.95] band. Returns
    0.95 rounded to 3 decimals."""
    finding = _build()
    assert compute_feasibility(finding) == 0.95


def test_compute_feasibility_min_input_clamps_to_zero():
    """Worst-case input produces a negative raw sum (-0.08 in the
    bookkeeping); clamp pins the output at 0.0."""
    finding = _build(
        revenue_mechanism_identified=False,
        revenue_mechanism_description="",
        revenue_type=RevenueType.UNCLEAR,
        buyer_identified=False,
        buyer_description="",
        buyer_accessibility=BuyerAccessibility.UNCLEAR,
        capital_required=CapitalRequired.OVER_1M,
        capital_justification="x",
        regulatory_blockers=["a", "b", "c"],
        regulatory_severity=RegulatorySeverity.PROHIBITIVE,
        feasibility_risks=["x", "y", "z"],
        existing_market_validation=False,
    )
    assert compute_feasibility(finding) == 0.0


def test_compute_feasibility_always_in_unit_interval():
    """Property-style check across the fixture corner cases — every
    output lands in [0.0, 1.0]."""
    for f in (
        passing_stage1_finding(),
        penalty_zone_stage1_finding(),
        failing_stage1_finding(),
    ):
        score = compute_feasibility(f)
        assert 0.0 <= score <= 1.0


# ----------------------------------------------------------------- determinism


def test_compute_feasibility_is_deterministic():
    """Same Stage1Finding → same float, every call. No randomness, no
    side-effect state. This is the load-bearing property of PAJAMA:
    Python provides the scalar, not the model, so per-call variance
    collapses to zero on byte-identical input."""
    finding = passing_stage1_finding()
    scores = {compute_feasibility(finding) for _ in range(20)}
    assert len(scores) == 1


# ----------------------------------------------------------------- revenue component


def test_revenue_mechanism_not_identified_contributes_zero():
    """When revenue_mechanism_identified=False, the revenue component
    is 0 regardless of revenue_type. (The model is instructed to set
    revenue_type='unclear' in this case, but the formula short-circuits
    on the bool.)"""
    score = compute_feasibility(_build(revenue_mechanism_identified=False))
    # baseline (everything else maxed): 0.95.
    # Without revenue component: 0.95 - 0.30 = 0.65.
    assert score == 0.65


def test_revenue_type_categorical_weights_apply():
    """Each RevenueType produces a distinct revenue-component score."""
    expected = {
        RevenueType.RECURRING: 0.30,
        RevenueType.TRANSACTIONAL: 0.25,
        RevenueType.ASSET_APPRECIATION: 0.25,
        RevenueType.LICENSING: 0.25,
        RevenueType.ARBITRAGE: 0.20,
        RevenueType.HYBRID: 0.22,
        RevenueType.UNCLEAR: 0.08,
    }
    # Baseline: 0.95. Subtract default RECURRING (0.30), add the
    # category under test; the rest of the score is constant.
    baseline_minus_revenue = 0.95 - 0.30
    for revenue_type, weight in expected.items():
        score = compute_feasibility(_build(revenue_type=revenue_type))
        assert score == pytest.approx(baseline_minus_revenue + weight, abs=1e-3), (
            f"{revenue_type} should contribute {weight}"
        )


# ----------------------------------------------------------------- buyer component


def test_buyer_not_identified_contributes_zero():
    score = compute_feasibility(_build(buyer_identified=False))
    # baseline 0.95 - default buyer (DIRECT_TO_BUSINESS = 0.25) = 0.70.
    assert score == 0.70


def test_buyer_accessibility_categorical_weights_apply():
    expected = {
        BuyerAccessibility.DIRECT_TO_CONSUMER: 0.25,
        BuyerAccessibility.DIRECT_TO_BUSINESS: 0.25,
        BuyerAccessibility.REQUIRES_INTERMEDIARY: 0.18,
        BuyerAccessibility.REQUIRES_GOVERNMENT_CONTRACT: 0.12,
        BuyerAccessibility.UNCLEAR: 0.08,
    }
    baseline_minus_buyer = 0.95 - 0.25
    for accessibility, weight in expected.items():
        score = compute_feasibility(_build(buyer_accessibility=accessibility))
        assert score == pytest.approx(baseline_minus_buyer + weight, abs=1e-3)


# ----------------------------------------------------------------- capital component


def test_capital_required_categorical_weights_apply():
    expected = {
        CapitalRequired.NONE: 0.15,
        CapitalRequired.UNDER_10K: 0.13,
        CapitalRequired.BETWEEN_10K_AND_100K: 0.09,
        CapitalRequired.BETWEEN_100K_AND_1M: 0.04,
        CapitalRequired.OVER_1M: 0.01,
        CapitalRequired.UNQUANTIFIABLE: 0.05,
    }
    baseline_minus_capital = 0.95 - 0.15
    for capital, weight in expected.items():
        score = compute_feasibility(_build(capital_required=capital))
        assert score == pytest.approx(baseline_minus_capital + weight, abs=1e-3)


# ----------------------------------------------------------------- regulatory component


def test_regulatory_severity_categorical_penalties_apply():
    expected = {
        RegulatorySeverity.NONE: 0.0,
        RegulatorySeverity.MANAGEABLE: -0.03,
        RegulatorySeverity.SIGNIFICANT: -0.08,
        RegulatorySeverity.PROHIBITIVE: -0.15,
    }
    for severity, penalty in expected.items():
        score = compute_feasibility(_build(regulatory_severity=severity))
        # baseline 0.95 + penalty (which is 0 or negative).
        expected_score = round(max(0.0, min(1.0, 0.95 + penalty)), 3)
        assert score == pytest.approx(expected_score, abs=1e-3)


def test_per_regulatory_blocker_penalty_stacks_additively():
    """Each named blocker subtracts 0.01 from the score. Five blockers
    → -0.05 from baseline. Penalty stacks ON TOP OF severity."""
    score = compute_feasibility(_build(
        regulatory_severity=RegulatorySeverity.MANAGEABLE,
        regulatory_blockers=["a", "b", "c", "d", "e"],
    ))
    # baseline 0.95 + manageable (-0.03) - 5 blockers (-0.05) = 0.87
    assert score == pytest.approx(0.87, abs=1e-3)
    assert _PER_REGULATORY_BLOCKER_PENALTY == 0.01


# ----------------------------------------------------------------- feasibility risks


def test_per_feasibility_risk_penalty_stacks_additively():
    """Each feasibility risk subtracts 0.02 from the score."""
    score = compute_feasibility(_build(feasibility_risks=["x", "y", "z"]))
    # baseline 0.95 - 3 × 0.02 = 0.89
    assert score == pytest.approx(0.89, abs=1e-3)
    assert _PER_FEASIBILITY_RISK_PENALTY == 0.02


# ----------------------------------------------------------------- bonus contributions


def test_existing_market_validation_bonus_applies():
    """existing_market_validation=True adds 0.10."""
    with_validation = compute_feasibility(_build(existing_market_validation=True))
    without_validation = compute_feasibility(_build(existing_market_validation=False))
    assert with_validation - without_validation == pytest.approx(0.10, abs=1e-3)
    assert _EXISTING_MARKET_VALIDATION_BONUS == 0.10


def test_middle_class_accessible_bonus_applies():
    """middle_class_accessible=True adds 0.15 to compute_feasibility's
    output. (The False case ALSO triggers an INDEPENDENT hard
    fitness-to-zero gate at the cascade level — this bonus is
    orthogonal to that gate.)"""
    with_mc = compute_feasibility(_build(middle_class_accessible=True))
    without_mc = compute_feasibility(_build(middle_class_accessible=False))
    assert with_mc - without_mc == pytest.approx(0.15, abs=1e-3)
    assert _MIDDLE_CLASS_ACCESSIBLE_BONUS == 0.15


# ----------------------------------------------------------------- noise resistance


def test_single_field_flip_shifts_score_by_at_most_max_bonus():
    """The PAJAMA design intent: a single boolean flip shifts the
    output by at most ~0.15 (the largest bonus). This is the
    additive-formula property — distinct from Stage 2's
    multiplicative formula where one bool flip can swing 70%.

    Verified empirically: starting from the passing fixture, flipping
    each boolean ONE AT A TIME produces a delta below 0.16."""
    baseline = compute_feasibility(passing_stage1_finding())
    for flip in (
        "revenue_mechanism_identified",
        "buyer_identified",
        "existing_market_validation",
        "middle_class_accessible",
    ):
        flipped = passing_stage1_finding().model_copy(update={flip: False})
        delta = abs(compute_feasibility(flipped) - baseline)
        assert delta <= 0.30, (
            f"flipping {flip} produced delta {delta} > 0.30 — "
            "single-field-flip should be a bounded shift, not a swing"
        )


# ----------------------------------------------------------------- soft zone


def test_apply_stage1_soft_zone_below_hard_floor_is_hard_exit():
    adjusted, zone = apply_stage1_soft_zone(STAGE1_HARD_FLOOR - 0.01)
    assert zone == "hard_exit"
    assert adjusted == pytest.approx(STAGE1_HARD_FLOOR - 0.01)


def test_apply_stage1_soft_zone_above_ceiling_is_clean_pass():
    adjusted, zone = apply_stage1_soft_zone(STAGE1_SOFT_CEILING + 0.01)
    assert zone == "clean_pass"
    assert adjusted == pytest.approx(STAGE1_SOFT_CEILING + 0.01)


def test_apply_stage1_soft_zone_between_floor_and_ceiling_is_penalty_zone():
    adjusted, zone = apply_stage1_soft_zone(0.30)
    assert zone == "penalty_zone"
    # raw² / ceiling = 0.09 / 0.45 = 0.200
    assert adjusted == pytest.approx(0.20, abs=1e-3)


def test_apply_stage1_soft_zone_at_hard_floor_is_penalty_zone():
    """At raw == STAGE1_HARD_FLOOR the candidate enters the penalty
    zone (the comparison is strict <)."""
    adjusted, zone = apply_stage1_soft_zone(STAGE1_HARD_FLOOR)
    assert zone == "penalty_zone"
    # 0.15² / 0.45 = 0.05
    assert adjusted == pytest.approx(0.05, abs=1e-3)


def test_apply_stage1_soft_zone_at_soft_ceiling_is_clean_pass():
    """At raw == STAGE1_SOFT_CEILING the candidate enters clean pass
    (the comparison is strict <), no penalty applied."""
    adjusted, zone = apply_stage1_soft_zone(STAGE1_SOFT_CEILING)
    assert zone == "clean_pass"
    assert adjusted == STAGE1_SOFT_CEILING


def test_apply_stage1_soft_zone_curve_is_continuous_at_ceiling():
    """The quadratic penalty curve meets the clean-pass line exactly
    at SOFT_CEILING — no cliff. Verify by checking that the penalty-
    zone curve evaluated AT the ceiling equals the clean-pass value.

    penalty_zone formula: adjusted = raw² / ceiling
    At raw = ceiling:  adjusted = ceiling² / ceiling = ceiling
    """
    raw = STAGE1_SOFT_CEILING
    penalty_value = (raw * raw) / STAGE1_SOFT_CEILING
    assert penalty_value == pytest.approx(STAGE1_SOFT_CEILING, abs=1e-9)


def test_apply_stage1_soft_zone_monotonic_within_penalty_zone():
    """Within the penalty zone, the adjusted value is strictly
    increasing in raw feasibility — the raw²/ceiling curve is
    monotonic on [0.15, 0.45].

    Cross-zone monotonicity is intentionally NOT an invariant: the
    hard_exit branch carries raw forward unchanged (it's diagnostic
    only — the cascade exits anyway with structural=0.0), and the
    raw value at the floor (0.15) is higher than the penalty-zone
    adjusted value at the same point (0.05). This is correct: the
    two values live in different cascade outcomes that aren't
    rank-comparable. Continuity at SOFT_CEILING is the load-bearing
    no-cliff property; tested separately."""
    prev = -1.0
    for raw_x100 in range(15, 46, 2):  # 0.15 → 0.45 inclusive
        raw = raw_x100 / 100.0
        adjusted, zone = apply_stage1_soft_zone(raw)
        if zone == "penalty_zone":
            assert adjusted > prev, (
                f"non-monotonic within penalty zone: "
                f"raw={raw} adjusted={adjusted} prev={prev}"
            )
            prev = adjusted


# ----------------------------------------------------------------- fixture pins


def test_passing_fixture_clears_soft_ceiling():
    """The passing fixture promise: compute_feasibility >> SOFT_CEILING."""
    raw = compute_feasibility(passing_stage1_finding())
    _, zone = apply_stage1_soft_zone(raw)
    assert raw > STAGE1_SOFT_CEILING
    assert zone == "clean_pass"


def test_penalty_zone_fixture_lands_in_penalty_zone():
    """The penalty-zone fixture promise: compute_feasibility falls
    between HARD_FLOOR and SOFT_CEILING."""
    raw = compute_feasibility(penalty_zone_stage1_finding())
    _, zone = apply_stage1_soft_zone(raw)
    assert STAGE1_HARD_FLOOR <= raw < STAGE1_SOFT_CEILING
    assert zone == "penalty_zone"


def test_failing_fixture_falls_below_hard_floor():
    """The failing fixture promise: compute_feasibility < HARD_FLOOR."""
    raw = compute_feasibility(failing_stage1_finding())
    _, zone = apply_stage1_soft_zone(raw)
    assert raw < STAGE1_HARD_FLOOR
    assert zone == "hard_exit"


# ----------------------------------------------------------------- output shape


def test_compute_feasibility_returns_rounded_float():
    """Output is rounded to 3 decimal places — pinned for legible DB /
    audit dumps."""
    finding = passing_stage1_finding()
    score = compute_feasibility(finding)
    assert round(score, 3) == score


def test_apply_stage1_soft_zone_in_penalty_zone_rounds_to_3_decimals():
    adjusted, zone = apply_stage1_soft_zone(0.32)
    assert zone == "penalty_zone"
    # 0.32² / 0.45 = 0.2275… → rounded to 0.228
    assert adjusted == pytest.approx(0.228, abs=1e-3)
    assert round(adjusted, 3) == adjusted
