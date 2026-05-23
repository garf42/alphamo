"""Cascade orchestrator unit tests.

The individual stages are LLM-backed and tested live in
`test_evaluator_calibration.py`. These tests verify the orchestration logic
— thresholds, short-circuiting, middle-class filtering — by injecting
fake stage functions via monkeypatch so they run without API calls.

Sprint 2 redesign: the cascade has 3 stages (feasibility, structural,
adversarial). The exemplar-similarity comparison stage was retired.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.cascade import EvaluatorCascade
from alphamo.schemas.findings import (
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
)
from tests.fixtures.exemplars import PE_ROLLUP_FOIL, SATOSHI_FIXTURE
from tests.fixtures.stage2_evidence import (
    failing_stage2_finding,
    passing_stage2_finding,
)


def _make_s1(feasibility: float, middle_class: bool) -> Stage1Finding:
    """Sprint Stage 1 PAJAMA: select a fixture matching the requested
    soft-zone side, then override middle_class_accessible. `feasibility`
    parameter is interpreted as the desired raw compute_feasibility
    output — < 0.15 picks the failing fixture (hard exit), 0.15-0.45
    picks the penalty-zone fixture, ≥ 0.45 picks the passing fixture.
    Tests previously asking for an exact float get the deterministic
    fixture-scored equivalent."""
    from tests.fixtures.stage1_evidence import (
        failing_stage1_finding,
        passing_stage1_finding,
        penalty_zone_stage1_finding,
    )
    if feasibility < 0.15:
        finding = failing_stage1_finding(reasoning="test stub")
    elif feasibility < 0.45:
        finding = penalty_zone_stage1_finding(reasoning="test stub")
    else:
        finding = passing_stage1_finding(reasoning="test stub")
    return finding.model_copy(update={"middle_class_accessible": middle_class})


def _make_s2(passing: bool = True) -> Stage2Finding:
    """Sprint Stage 2 PAJAMA: model no longer returns a structural float —
    structural is derived from evidence via `compute_structural`. Tests
    that previously asked for a specific scalar now request either the
    passing (structural ≈ 0.773) or failing (structural ≈ 0.049)
    evidence shape from `tests/fixtures/stage2_evidence`."""
    return passing_stage2_finding() if passing else failing_stage2_finding()


def _make_adversarial(robustness: float = 0.85) -> Stage4Finding:
    """Adversarial-scrutiny finding. Stage4Finding class name preserved from
    pre-Sprint-2 for compatibility; the conceptual stage is now Stage 3."""
    return Stage4Finding(
        robustness=robustness,
        concerns=[],
        reasoning="test stub",
    )


def _patch_stage4(monkeypatch, robustness: float = 0.85):
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: _make_adversarial(robustness)
    )


@pytest.fixture()
def cascade() -> EvaluatorCascade:
    return EvaluatorCascade(client=MagicMock(), stage1_threshold=0.4, stage2_threshold=0.5)


def test_passing_candidate_runs_all_three_stages(cascade, monkeypatch):
    s1_calls, s2_calls, s3_calls = [], [], []
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c, **kw: s1_calls.append(a) or _make_s1(0.9, True),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c, **kw: s2_calls.append(a) or _make_s2(passing=True),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: s3_calls.append(a) or _make_adversarial(0.80),
    )

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert len(s1_calls) == 1 and len(s2_calls) == 1 and len(s3_calls) == 1
    assert result.early_exit is None
    # Sprint Stage 1 PAJAMA: feasibility is computed deterministically by
    # compute_feasibility from the stub's evidence shape. The passing
    # Stage 1 fixture is pinned to score 0.83; the soft-zone clean-pass
    # path leaves it unchanged.
    assert result.scores.feasibility == 0.83
    # Sprint Stage 2 PAJAMA: structural is now computed deterministically
    # from the stub's evidence shape by `compute_structural`. The
    # passing_stage2_finding fixture is pinned to score 0.773; the
    # cascade flows that value through to result.scores.structural
    # rather than passing through a model-emitted float.
    assert result.scores.structural == 0.773
    # exemplar_similarity is retired — always None on new candidates.
    assert result.scores.exemplar_similarity is None
    assert result.scores.robustness == 0.80
    assert result.scores.middle_class_accessible is True
    assert result.stage3 is not None


def test_middle_class_failure_short_circuits_to_zero_fitness(cascade, monkeypatch):
    s2_calls, s3_calls = [], []
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c, **kw: _make_s1(0.9, False)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: s2_calls.append(1) or _make_s2(passing=True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: s3_calls.append(1) or _make_adversarial()
    )

    result = cascade.evaluate(PE_ROLLUP_FOIL.architecture)

    assert result.early_exit == "middle_class_filter"
    assert s2_calls == [] and s3_calls == []
    assert result.scores.middle_class_accessible is False
    assert result.scores.structural == 0.0
    assert result.scores.exemplar_similarity is None
    assert result.scores.robustness is None


def test_low_stage1_score_skips_downstream_stages(cascade, monkeypatch):
    """Sprint Stage 1 PAJAMA: feasibility BELOW STAGE1_HARD_FLOOR=0.15
    triggers the cascade's hard_exit zone (Stage 2 / Stage 3 do not
    run). Pre-PAJAMA this test used feasibility=0.2 against
    stage1_threshold=0.4 — under PAJAMA, 0.2 lands in the penalty
    zone (0.15 ≤ x < 0.45), the cascade DOES continue, and the test
    name no longer matches. The new test uses feasibility=0.05 →
    failing fixture → compute_feasibility=0.0 → hard_exit zone, which
    is what 'low stage 1 skips downstream' should now mean."""
    s2_calls, s3_calls = [], []
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c, **kw: _make_s1(0.05, True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: s2_calls.append(1) or _make_s2(passing=True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: s3_calls.append(1) or _make_adversarial()
    )

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert result.early_exit == "stage1_feasibility"
    assert s2_calls == [] and s3_calls == []
    # Sprint Stage 1 PAJAMA: the failing fixture's compute_feasibility
    # output is 0.0 (clamped from raw -0.08) — below STAGE1_HARD_FLOOR
    # so the cascade exits via the hard_exit zone with feasibility=0.0.
    assert result.scores.feasibility == 0.0
    assert result.scores.robustness is None


def test_stage1_penalty_zone_continues_with_scaled_feasibility(cascade, monkeypatch):
    """Sprint Stage 1 PAJAMA: a candidate in the soft penalty zone
    (HARD_FLOOR ≤ raw < SOFT_CEILING) continues to Stage 2 and Stage 3
    with adjusted_feasibility = raw² / SOFT_CEILING. The cascade does
    NOT exit early in this zone — this is the load-bearing no-cliff
    property."""
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: _make_s1(0.30, True),  # → penalty_zone fixture (compute=0.29)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: _make_s2(passing=True)
    )
    _patch_stage4(monkeypatch, robustness=0.85)

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert result.early_exit is None  # NO exit — cascade ran all 3 stages
    assert result.stage2 is not None
    assert result.stage3 is not None
    # Adjusted feasibility = compute_feasibility(penalty_zone fixture)² / SOFT_CEILING
    # = 0.29² / 0.45 ≈ 0.187. The pre-PAJAMA hard-threshold gate would
    # have exited this candidate; the new soft zone keeps it alive
    # with a penalized feasibility.
    assert result.scores.feasibility == pytest.approx(0.187, abs=1e-3)
    assert result.scores.middle_class_accessible is True


def test_stage1_clean_pass_zone_unchanged_feasibility(cascade, monkeypatch):
    """Sprint Stage 1 PAJAMA: a candidate above SOFT_CEILING passes
    through unchanged — no penalty applied."""
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: _make_s1(0.85, True),  # → passing fixture (compute=0.83)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: _make_s2(passing=True)
    )
    _patch_stage4(monkeypatch, robustness=0.85)

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert result.early_exit is None
    assert result.scores.feasibility == 0.83  # unchanged from compute_feasibility


def test_low_stage2_score_skips_stage3(cascade, monkeypatch):
    s3_calls = []
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c, **kw: _make_s1(0.9, True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: _make_s2(passing=False)
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: s3_calls.append(1) or _make_adversarial()
    )

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert result.early_exit == "stage2_structured"
    assert s3_calls == []
    # Sprint Stage 2 PAJAMA: structural derived from the failing fixture's
    # evidence shape (compute_structural ≈ 0.049). The gate at 0.5 fires
    # because the computed value is below threshold; the persisted score
    # is the computed value, not a model-emitted scalar.
    assert result.scores.structural == 0.049
    assert result.scores.structural < cascade.stage2_threshold
    assert result.scores.exemplar_similarity is None
    assert result.scores.robustness is None


def test_cascade_aggregates_fitness_via_db(tmp_path, monkeypatch):
    """The Scores the cascade produces must flow cleanly into ProgramsDB.insert."""
    from alphamo.database import ProgramsDB

    db = ProgramsDB(f"sqlite:///{tmp_path / 'a.db'}")
    run_id = db.create_run(
        hyperparameters={},
        parent_goal_version="test",
        verifier_version="test",
    )
    cascade = EvaluatorCascade(client=MagicMock())
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c, **kw: _make_s1(0.9, True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: _make_s2(passing=True)
    )
    _patch_stage4(monkeypatch, robustness=0.80)

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)
    new_id = db.insert(SATOSHI_FIXTURE.architecture, result.scores, run_id=run_id)

    row = db.get(new_id)
    # 3-way average (feasibility + structural + robustness); exemplar_similarity retired.
    # Sprint Stage 1 PAJAMA + Stage 2 PAJAMA: feasibility=0.83 (from
    # `compute_feasibility(passing_stage1_finding())`, clean-pass zone)
    # and structural=0.773 (`compute_structural(passing_stage2_finding())`).
    # The fitness aggregate is the 3-way mean.
    assert row.fitness == pytest.approx((0.83 + 0.773 + 0.80) / 3.0)
