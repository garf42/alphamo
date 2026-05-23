"""Sprint Stage 2 PAJAMA — `compute_structural` formula tests.

Analogous to the Stage 3 `compute_robustness` tests in
`test_stage4_adversarial.py`. The model's role at Stage 2 changed from
returning a structural float to returning categorical / boolean / list
evidence. `compute_structural` maps that evidence to a deterministic
scalar in [0.0, 1.0]; this file pins:

  - Bounds: max-evidence shape → 1.0; min-evidence shape → 0.0.
  - Determinism: repeated calls on the same input return the same float.
  - Sub-component independence: each criterion contributes independently
    (no cross-criterion interaction in v1).
  - The penalty / boost / floor constants behave per the docstring's
    breakdown.

`compute_structural` has no LLM calls, no DB access, no random state —
it's a pure function of the Stage2Finding. None of these tests touch
the cascade or any provider.
"""

from __future__ import annotations

import pytest

from alphamo.evaluator.stage2_structured import (
    _NONLINEAR_SCALING_BONUS,
    _NO_CAPTURE_MECHANISM_PENALTY,
    _NO_MARKET_NAMED_PENALTY,
    _NO_SEPARATION_PENALTY,
    _ONE_PERSON_FAIL_PENALTY,
    _PER_LABOR_POINT_PENALTY,
    _SEPARATION_NO_EVIDENCE,
    compute_structural,
)
from alphamo.schemas.findings import (
    AutomationPlausibility,
    Stage2Finding,
    TAMEstimate,
)
from tests.fixtures.stage2_evidence import (
    failing_stage2_finding,
    passing_stage2_finding,
)


# ----------------------------------------------------------------- builder helper


def _build(**overrides) -> Stage2Finding:
    """Build a Stage2Finding with neutral defaults; overrides per test
    isolate the dimension being measured. Defaults are chosen to give
    each sub-component a known starting score so deltas from overrides
    are obvious."""
    defaults = dict(
        # ops defaults: 1.0 score (ALREADY_AUTOMATED, no labor, operable)
        labor_dependency_points=[],
        automation_plausibility=AutomationPlausibility.ALREADY_AUTOMATED,
        one_person_operable=True,
        # market defaults: 1.0 score (>$100B, named, identified, nonlinear)
        target_market_named=True,
        target_market_description="a specific market",
        tam_estimate=TAMEstimate.OVER_100B,
        capture_mechanism_identified=True,
        capture_mechanism_description="a specific mechanism",
        nonlinear_scaling_path=False,  # leave the boost off in baseline
        # separation defaults: 1.0 score (2 autonomous, 0 active, achieved)
        autonomous_value_sources=["alpha", "beta"],
        active_labor_requirements=[],
        separation_achieved=True,
        reasoning="under test",
    )
    defaults.update(overrides)
    return Stage2Finding(**defaults)


# ----------------------------------------------------------------- bounds


def test_compute_structural_max_input_returns_one():
    """Every input maxed: structural = 1.0."""
    finding = _build(nonlinear_scaling_path=True)  # boost capped at 1.0
    assert compute_structural(finding) == 1.0


def test_compute_structural_min_input_returns_zero():
    """Every input pessimised: structural floors at 0.0."""
    finding = _build(
        labor_dependency_points=["a"] * 20,  # auto - 0.08*20 floors at 0
        automation_plausibility=AutomationPlausibility.REQUIRES_HUMAN_JUDGMENT,
        one_person_operable=False,
        target_market_named=False,
        target_market_description="",
        tam_estimate=TAMEstimate.SUB_1B,  # 0.0 base
        capture_mechanism_identified=False,
        capture_mechanism_description="",
        nonlinear_scaling_path=False,
        autonomous_value_sources=[],
        active_labor_requirements=["a", "b", "c"],
        separation_achieved=False,
    )
    assert compute_structural(finding) == 0.0


def test_compute_structural_always_in_unit_interval():
    """Property-style check across the fixture corner cases — every
    output is in [0.0, 1.0]."""
    for f in (passing_stage2_finding(), failing_stage2_finding()):
        score = compute_structural(f)
        assert 0.0 <= score <= 1.0


# ----------------------------------------------------------------- determinism


def test_compute_structural_is_deterministic():
    """Same Stage2Finding → same float, every call. No randomness, no
    side-effect state in the function or its constants."""
    finding = passing_stage2_finding()
    scores = {compute_structural(finding) for _ in range(20)}
    assert len(scores) == 1


# ----------------------------------------------------------------- ops sub-component


def test_per_labor_point_penalty_lowers_ops_score():
    """Adding labor_dependency_points reduces ops_score by 0.08 each."""
    baseline = compute_structural(_build())  # ops = 1.0
    with_one = compute_structural(_build(labor_dependency_points=["a"]))
    # ops_score drops from 1.0 → 0.92; the other two stay at 1.0;
    # new structural = (0.92 + 1.0 + 1.0) / 3 = 0.973
    assert baseline > with_one
    assert with_one == pytest.approx((0.92 + 1.0 + 1.0) / 3.0, abs=1e-3)


def test_one_person_operable_false_applies_additive_penalty():
    """Sprint PAJAMA-stabilization: one_person_operable=False subtracts
    _ONE_PERSON_FAIL_PENALTY (0.20) from ops_score (additive, not
    multiplicative). Pre-stabilization this was `× 0.3` which produced
    a 70% swing on ops; the additive form caps the swing at 0.20.
    """
    score = compute_structural(_build(one_person_operable=False))
    # ops: max(0, 1.0 - 0.20) = 0.80; market = 1.0; sep = 1.0
    # structural = (0.80 + 1.0 + 1.0) / 3 = 0.933
    assert score == pytest.approx((0.80 + 1.0 + 1.0) / 3.0, abs=1e-3)
    assert _ONE_PERSON_FAIL_PENALTY == 0.20


def test_automation_plausibility_categorical_weights_apply():
    """Each AutomationPlausibility category produces a distinct ops base score."""
    expected = {
        AutomationPlausibility.ALREADY_AUTOMATED: 1.0,
        AutomationPlausibility.AUTOMATABLE_WITH_EXISTING_TOOLS: 0.75,
        AutomationPlausibility.REQUIRES_CUSTOM_ENGINEERING: 0.4,
        AutomationPlausibility.REQUIRES_HUMAN_JUDGMENT: 0.1,
    }
    for plausibility, base in expected.items():
        score = compute_structural(_build(automation_plausibility=plausibility))
        # ops = base * 1.0 (operable); market = 1.0; sep = 1.0
        assert score == pytest.approx((base + 1.0 + 1.0) / 3.0, abs=1e-3), (
            f"{plausibility} should produce ops base score {base}"
        )


# ----------------------------------------------------------------- market sub-component


def test_tam_estimate_categorical_weights_apply():
    """Each TAMEstimate bucket produces a distinct market base score."""
    expected = {
        TAMEstimate.SUB_1B: 0.0,
        TAMEstimate.ONE_TO_10B: 0.4,
        TAMEstimate.TEN_TO_100B: 0.7,
        TAMEstimate.OVER_100B: 1.0,
        TAMEstimate.UNQUANTIFIABLE: 0.2,
    }
    for bucket, base in expected.items():
        score = compute_structural(_build(tam_estimate=bucket))
        # ops = 1.0; market = base * 1.0 * 1.0 (named, identified, no boost);
        # sep = 1.0
        assert score == pytest.approx((1.0 + base + 1.0) / 3.0, abs=1e-3), (
            f"{bucket} should produce market base score {base}"
        )


def test_target_market_not_named_applies_additive_penalty():
    """Sprint PAJAMA-stabilization: target_market_named=False subtracts
    _NO_MARKET_NAMED_PENALTY (0.15) from market_score."""
    score = compute_structural(_build(target_market_named=False))
    # market: max(0, 1.0 - 0.15) = 0.85
    assert score == pytest.approx((1.0 + 0.85 + 1.0) / 3.0, abs=1e-3)
    assert _NO_MARKET_NAMED_PENALTY == 0.15


def test_capture_mechanism_unidentified_applies_additive_penalty():
    """Sprint PAJAMA-stabilization: capture_mechanism_identified=False
    subtracts _NO_CAPTURE_MECHANISM_PENALTY (0.15) from market_score."""
    score = compute_structural(_build(capture_mechanism_identified=False))
    assert score == pytest.approx((1.0 + 0.85 + 1.0) / 3.0, abs=1e-3)
    assert _NO_CAPTURE_MECHANISM_PENALTY == 0.15


def test_nonlinear_scaling_bonus_additive_capped_at_one():
    """Sprint PAJAMA-stabilization: nonlinear_scaling_path=True adds
    _NONLINEAR_SCALING_BONUS (0.10) to market_score, capped at 1.0
    (the dimension ceiling). Pre-stabilization this was `× 1.3` —
    the multiplicative form produced larger swings on mid-range
    market scores."""
    # OVER_100B (base 1.0) + 0.10 → capped at 1.0.
    score = compute_structural(_build(nonlinear_scaling_path=True))
    assert score == 1.0
    # TEN_TO_100B (base 0.7) + 0.10 = 0.80; NOT capped.
    score = compute_structural(_build(
        tam_estimate=TAMEstimate.TEN_TO_100B,
        nonlinear_scaling_path=True,
    ))
    expected_market = min(1.0, 0.7 + _NONLINEAR_SCALING_BONUS)
    assert expected_market == pytest.approx(0.80, abs=1e-9)
    assert score == pytest.approx((1.0 + expected_market + 1.0) / 3.0, abs=1e-3)
    assert _NONLINEAR_SCALING_BONUS == 0.10


# ----------------------------------------------------------------- separation sub-component


def test_separation_no_evidence_baseline():
    """Both lists empty → sep_score = 0.25 (the _SEPARATION_NO_EVIDENCE
    constant). Centered low so absence-of-evidence isn't a free pass."""
    score = compute_structural(_build(
        autonomous_value_sources=[],
        active_labor_requirements=[],
        # separation_achieved still True; the no-evidence baseline applies
        # regardless because the ratio is undefined.
    ))
    assert score == pytest.approx(
        (1.0 + 1.0 + _SEPARATION_NO_EVIDENCE) / 3.0, abs=1e-3
    )


def test_separation_ratio_over_list_lengths():
    """sep_score = n_autonomous / (n_autonomous + n_active) when at least
    one entry exists in either list."""
    # 3 autonomous, 1 active → ratio 0.75
    score = compute_structural(_build(
        autonomous_value_sources=["a", "b", "c"],
        active_labor_requirements=["x"],
    ))
    assert score == pytest.approx((1.0 + 1.0 + 0.75) / 3.0, abs=1e-3)


def test_separation_not_achieved_applies_additive_penalty():
    """Sprint PAJAMA-stabilization: separation_achieved=False subtracts
    _NO_SEPARATION_PENALTY (0.20) from sep_score. Pre-stabilization
    this was `× 0.5`, a 50% swing on the sep component."""
    score = compute_structural(_build(separation_achieved=False))
    # sep: max(0, 1.0 - 0.20) = 0.80
    assert score == pytest.approx((1.0 + 1.0 + 0.80) / 3.0, abs=1e-3)
    assert _NO_SEPARATION_PENALTY == 0.20


# ----------------------------------------------------------------- cross-criterion independence


def test_sub_components_combine_via_arithmetic_mean():
    """Equal-weight mean of the three sub-component scores — verify
    against a hand-computed configuration where each sub-component lands
    at a distinct value."""
    # ops: AUTOMATABLE_WITH_EXISTING_TOOLS (0.75), no labor, operable → 0.75
    # market: $10B-$100B (0.7) named, identified, no boost → 0.7
    # sep: 1 auto / 1 active = 0.5, separation_achieved=True → 0.5
    finding = _build(
        automation_plausibility=AutomationPlausibility.AUTOMATABLE_WITH_EXISTING_TOOLS,
        tam_estimate=TAMEstimate.TEN_TO_100B,
        autonomous_value_sources=["x"],
        active_labor_requirements=["y"],
    )
    # structural = (0.75 + 0.70 + 0.50) / 3 = 0.65
    assert compute_structural(finding) == pytest.approx(0.65, abs=1e-3)


def test_one_labor_point_penalty_constant():
    """Per-labor-point penalty applies linearly until ops_score floors at 0."""
    assert _PER_LABOR_POINT_PENALTY == 0.08
    # 5 labor points under ALREADY_AUTOMATED (1.0): ops = 1.0 - 0.40 = 0.60
    score = compute_structural(_build(labor_dependency_points=["a"] * 5))
    assert score == pytest.approx((0.60 + 1.0 + 1.0) / 3.0, abs=1e-3)
    # 13 labor points under ALREADY_AUTOMATED: 1.0 - 1.04 = -0.04 → clamped to 0
    score = compute_structural(_build(labor_dependency_points=["a"] * 13))
    assert score == pytest.approx((0.0 + 1.0 + 1.0) / 3.0, abs=1e-3)


# ----------------------------------------------------------------- noise resistance


def test_single_field_flip_swings_structural_by_at_most_design_cap():
    """Sprint PAJAMA-stabilization load-bearing invariant: flipping any
    single boolean field on a Stage2Finding shifts the final structural
    score by AT MOST 0.20.

    The constraint is the design cap from the sprint spec; the formula
    is calibrated to land well under it (the largest single-field
    contribution is 0.20 on a sub-component, which the 3-way mean
    divides to 0.067 on the final score). This test guards against a
    future refactor that re-introduces a multiplicative penalty large
    enough to violate the cap.

    Coverage: every bottom-line boolean on Stage2Finding plus a one-
    labor-point increment, exercised from both a maxed-baseline and
    a partially-saturated baseline (to verify caps don't artificially
    hide variance when one sub-component is at the ceiling).
    """
    DESIGN_CAP = 0.20

    boolean_flips = (
        "one_person_operable",
        "target_market_named",
        "capture_mechanism_identified",
        "nonlinear_scaling_path",
        "separation_achieved",
    )

    for baseline_overrides in (
        # Max-baseline: every dimension at its ceiling.
        dict(nonlinear_scaling_path=True),
        # Partial-baseline: TEN_TO_100B market so the nonlinear bonus
        # ISN'T capped at the dimension ceiling, exposing the full
        # additive swing.
        dict(tam_estimate=TAMEstimate.TEN_TO_100B),
        # Mid-baseline: REQUIRES_CUSTOM_ENGINEERING ops + one labor
        # point + mixed separation lists. Realistic for the variance-
        # test candidates (Proptax, TaxVeritas).
        dict(
            automation_plausibility=AutomationPlausibility.REQUIRES_CUSTOM_ENGINEERING,
            labor_dependency_points=["maintenance"],
            tam_estimate=TAMEstimate.TEN_TO_100B,
            autonomous_value_sources=["a", "b"],
            active_labor_requirements=["c"],
        ),
    ):
        baseline = _build(**baseline_overrides)
        baseline_score = compute_structural(baseline)
        for flip in boolean_flips:
            current_value = getattr(baseline, flip)
            flipped = baseline.model_copy(update={flip: not current_value})
            delta = abs(compute_structural(flipped) - baseline_score)
            assert delta <= DESIGN_CAP, (
                f"flipping {flip} on baseline={baseline_overrides} "
                f"produced delta {delta:.4f} > design cap {DESIGN_CAP}"
            )

        # One additional labor point: should be well under the cap too.
        labored = baseline.model_copy(
            update={
                "labor_dependency_points": baseline.labor_dependency_points + ["extra"],
            }
        )
        delta = abs(compute_structural(labored) - baseline_score)
        assert delta <= DESIGN_CAP, (
            f"+1 labor point on baseline={baseline_overrides} "
            f"produced delta {delta:.4f} > design cap {DESIGN_CAP}"
        )


# ----------------------------------------------------------------- output shape


def test_compute_structural_returns_rounded_float():
    """Output is rounded to 3 decimal places — the persisted column
    only needs that many digits and rounding keeps the DB value
    legible in audit dumps."""
    finding = passing_stage2_finding()
    score = compute_structural(finding)
    # Round-trip identity check: round(score, 3) == score.
    assert round(score, 3) == score


def test_passing_fixture_clears_default_threshold():
    """The Sprint Stage 2 PAJAMA fixture promise: passing_stage2_finding's
    output > 0.5 (default stage2_threshold), failing_stage2_finding's
    output < 0.5."""
    from alphamo.context.hyperparams import Hyperparameters
    threshold = Hyperparameters().stage2_threshold
    assert compute_structural(passing_stage2_finding()) > threshold
    assert compute_structural(failing_stage2_finding()) < threshold
