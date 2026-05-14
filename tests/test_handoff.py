"""Tests for the harvest-time handoff builder."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.context.verifier import VERIFIER_ANCHOR
from alphamo.evaluator import EvaluatorCascade, cascade as cascade_mod
from alphamo.handoff import build_handoff
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import Stage1Finding, Stage2Finding, Stage3Finding
from tests.fixtures.exemplars import (
    LEVELS_FIXTURE,
    ROWLING_FIXTURE,
    SATOSHI_FIXTURE,
)


@pytest.fixture()
def cascade(monkeypatch) -> EvaluatorCascade:
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=0.95, middle_class_accessible=True, reasoning="s1 ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=0.9,
            billion_dollar_potential=0.9,
            labor_separation=0.9,
            structural=0.9,
            reasoning="s2 ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage3_exemplars",
        lambda a, c: Stage3Finding(
            closest_exemplar="Satoshi",
            similarity=0.95,
            reasoning="s3 ok",
        ),
    )
    return EvaluatorCascade(client=MagicMock())


def _populate(db) -> tuple[int, int, int]:
    sat = db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, island_id=0)
    rowl = db.insert(ROWLING_FIXTURE.architecture, ROWLING_FIXTURE.scores, island_id=1)
    lev = db.insert(LEVELS_FIXTURE.architecture, LEVELS_FIXTURE.scores, island_id=2)
    return sat, rowl, lev


def test_build_handoff_picks_highest_fitness_winner(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    assert handoff.winning_architecture.spec.name == "Satoshi"


def test_build_handoff_includes_alternates_from_other_islands(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    alternate_names = {a.spec.name for a in handoff.alternates}
    assert alternate_names == {"Rowling", "Levels"}


def test_build_handoff_records_eval_count(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    assert handoff.verification_trail.eval_count == 3


def test_build_handoff_uses_verifier_anchor(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    assert handoff.verification_trail.anchor_used == VERIFIER_ANCHOR


def test_build_handoff_includes_exemplar_comparison(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    [comparison] = handoff.verification_trail.exemplar_comparisons
    assert comparison.closest_exemplar == "Satoshi"
    assert comparison.similarity == 0.95


def test_build_handoff_drift_log_projects_audit_events(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            trigger="milestone_candidate",
            classification="cosmetic",
            action="continue",
            rationale="not blocking",
            payload={"findings": [{"finding": {"source": "redteam"}}]},
        )
    )
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            trigger="scheduled_interval",
            classification="structural",
            action="pause_for_human",
            rationale="blocks goal",
            payload={"findings": [{"finding": {"source": "research"}}]},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    assert [e.type for e in handoff.drift_log] == ["cosmetic", "structural"]
    assert [e.source for e in handoff.drift_log] == ["redteam", "research"]
    assert handoff.drift_log[1].action == "pause_for_human"


def test_build_handoff_middle_class_check_reflects_winner(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    check = handoff.middle_class_entry_check
    assert check.passes is True
    assert "cryptography" in check.estimated_starting_resources.lower()
    assert check.stage_sequence == [
        "stage1_feasibility",
        "stage2_structured",
        "stage3_exemplars",
    ]


def test_build_handoff_coverage_residual_flags_unresolved_structural(
    db, cascade, tmp_path
):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale="r",
            payload={},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    assert "1 structural" in handoff.coverage_residual


def test_build_handoff_coverage_residual_clean_when_no_meta(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    assert "no unresolved" in handoff.coverage_residual


def test_build_handoff_raises_on_empty_db(db, cascade, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(RuntimeError, match="nothing to harvest"):
        build_handoff(db, audit, cascade, num_islands=4)


def test_build_handoff_serialisable_to_json(db, cascade, tmp_path):
    _populate(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4)
    payload = handoff.model_dump_json()
    assert "Satoshi" in payload
    assert "verification_trail" in payload
