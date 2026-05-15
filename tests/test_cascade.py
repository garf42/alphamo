"""Cascade orchestrator unit tests.

The individual stages are LLM-backed and tested live in
`test_evaluator_calibration.py`. These tests verify the orchestration logic
— thresholds, short-circuiting, middle-class filtering — by injecting
fake stage functions via monkeypatch so they run without API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.cascade import EvaluatorCascade
from alphamo.schemas.findings import (
    Stage1Finding,
    Stage2Finding,
    Stage3Finding,
    Stage4Finding,
)
from tests.fixtures.exemplars import PE_ROLLUP_FOIL, SATOSHI_FIXTURE


def _make_s1(feasibility: float, middle_class: bool) -> Stage1Finding:
    return Stage1Finding(
        feasibility=feasibility,
        middle_class_accessible=middle_class,
        reasoning="test stub",
    )


def _make_s2(structural: float) -> Stage2Finding:
    return Stage2Finding(
        one_person_threshold=structural,
        billion_dollar_potential=structural,
        labor_separation=structural,
        structural=structural,
        reasoning="test stub",
    )


def _make_s3(similarity: float) -> Stage3Finding:
    return Stage3Finding(
        closest_exemplar="Satoshi",
        similarity=similarity,
        reasoning="test stub",
    )


def _make_s4(robustness: float = 0.85) -> Stage4Finding:
    return Stage4Finding(
        robustness=robustness,
        concerns=[],
        reasoning="test stub",
    )


def _patch_stage4(monkeypatch, robustness: float = 0.85):
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: _make_s4(robustness)
    )


@pytest.fixture()
def cascade() -> EvaluatorCascade:
    return EvaluatorCascade(client=MagicMock(), stage1_threshold=0.4, stage2_threshold=0.5)


def test_passing_candidate_runs_all_four_stages(cascade, monkeypatch):
    s1_calls, s2_calls, s3_calls, s4_calls = [], [], [], []
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: s1_calls.append(a) or _make_s1(0.9, True),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: s2_calls.append(a) or _make_s2(0.85),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage3_exemplars",
        lambda a, c: s3_calls.append(a) or _make_s3(0.92),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: s4_calls.append(a) or _make_s4(0.80),
    )

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert (
        len(s1_calls) == 1
        and len(s2_calls) == 1
        and len(s3_calls) == 1
        and len(s4_calls) == 1
    )
    assert result.early_exit is None
    assert result.scores.feasibility == 0.9
    assert result.scores.structural == 0.85
    assert result.scores.exemplar_similarity == 0.92
    assert result.scores.robustness == 0.80
    assert result.scores.middle_class_accessible is True
    assert result.stage4 is not None


def test_middle_class_failure_short_circuits_to_zero_fitness(cascade, monkeypatch):
    s2_calls, s3_calls, s4_calls = [], [], []
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c: _make_s1(0.9, False)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c: s2_calls.append(1) or _make_s2(0.9)
    )
    monkeypatch.setattr(
        cascade_mod, "stage3_exemplars", lambda a, c: s3_calls.append(1) or _make_s3(0.9)
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: s4_calls.append(1) or _make_s4()
    )

    result = cascade.evaluate(PE_ROLLUP_FOIL.architecture)

    assert result.early_exit == "middle_class_filter"
    assert s2_calls == [] and s3_calls == [] and s4_calls == []
    assert result.scores.middle_class_accessible is False
    assert result.scores.structural == 0.0
    assert result.scores.exemplar_similarity == 0.0
    assert result.scores.robustness is None


def test_low_stage1_score_skips_stage2_and_stage3_and_stage4(cascade, monkeypatch):
    s2_calls, s3_calls, s4_calls = [], [], []
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c: _make_s1(0.2, True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c: s2_calls.append(1) or _make_s2(0.9)
    )
    monkeypatch.setattr(
        cascade_mod, "stage3_exemplars", lambda a, c: s3_calls.append(1) or _make_s3(0.9)
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: s4_calls.append(1) or _make_s4()
    )

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert result.early_exit == "stage1_feasibility"
    assert s2_calls == [] and s3_calls == [] and s4_calls == []
    assert result.scores.feasibility == 0.2
    assert result.scores.robustness is None


def test_low_stage2_score_skips_stage3_and_stage4(cascade, monkeypatch):
    s3_calls, s4_calls = [], []
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c: _make_s1(0.9, True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c: _make_s2(0.3)
    )
    monkeypatch.setattr(
        cascade_mod, "stage3_exemplars", lambda a, c: s3_calls.append(1) or _make_s3(0.9)
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", lambda a, c, **kw: s4_calls.append(1) or _make_s4()
    )

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)

    assert result.early_exit == "stage2_structured"
    assert s3_calls == [] and s4_calls == []
    assert result.scores.structural == 0.3
    assert result.scores.exemplar_similarity == 0.0
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
        cascade_mod, "stage1_feasibility", lambda a, c: _make_s1(0.9, True)
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c: _make_s2(0.85)
    )
    monkeypatch.setattr(
        cascade_mod, "stage3_exemplars", lambda a, c: _make_s3(0.92)
    )
    _patch_stage4(monkeypatch, robustness=0.80)

    result = cascade.evaluate(SATOSHI_FIXTURE.architecture)
    new_id = db.insert(SATOSHI_FIXTURE.architecture, result.scores, run_id=run_id)

    row = db.get(new_id)
    # 4-way average now that Stage 4 ran.
    assert row.fitness == pytest.approx((0.9 + 0.85 + 0.92 + 0.80) / 4.0)
