"""Orchestrator wiring tests with mocked LLM-backed components.

The cascade stage functions, red-team agent, and research agent are all
LLM-backed live and covered separately. These tests verify orchestration —
seeding, iteration sequencing, milestone red-team triggers, scheduled
research, curator pause — using monkeypatched stubs.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.evaluator import cascade as cascade_mod
from alphamo.meta.audit_log import AuditLog
from alphamo.orchestrator import Orchestrator
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    MetaFinding,
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage3Finding,
)


def _stub_cascade(monkeypatch, feasibility: float = 0.9, structural: float = 0.85, similarity: float = 0.9, middle_class: bool = True):
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=feasibility,
            middle_class_accessible=middle_class,
            reasoning="stub",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=structural,
            billion_dollar_potential=structural,
            labor_separation=structural,
            structural=structural,
            reasoning="stub",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage3_exemplars",
        lambda a, c: Stage3Finding(
            closest_exemplar="Satoshi", similarity=similarity, reasoning="stub"
        ),
    )


def _stub_client(
    architecture_name: str = "novel candidate",
    classification: Classification = Classification.COSMETIC,
) -> MagicMock:
    """Mock client routing parse() calls to Architecture or ClassificationVerdict."""
    client = MagicMock()

    def parse_side_effect(**kwargs):
        response = MagicMock()
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            response.parsed = Architecture(
                name=architecture_name,
                summary="s",
                value_chain="vc",
                capture_mechanism="cm",
                entry_resources="er",
            )
        elif output_format is ClassificationVerdict:
            response.parsed = ClassificationVerdict(
                classification=classification, rationale="stub"
            )
        else:
            response.parsed = MagicMock()
        return response

    client.messages.parse.side_effect = parse_side_effect
    return client


def _hp(**kwargs) -> Hyperparameters:
    defaults = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_fitness=1.0,  # stub fitness is ~0.88, so this disables red-team
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


def _make_orchestrator(
    db, monkeypatch, tmp_path, client=None, hp=None
) -> Orchestrator:
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "red_team_candidate", lambda *a, **k: [])
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = client or _stub_client()
    return Orchestrator(db, client, audit, hp or _hp())


def test_seed_if_empty_seeds_when_db_is_empty(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    assert orch.seed_if_empty() is True
    assert db.count_candidates(status="alive") > 0


def test_seed_if_empty_no_op_when_db_has_alive_candidates(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    orch.seed_if_empty()
    assert orch.seed_if_empty() is False


def test_step_inserts_a_new_candidate(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    orch.seed_if_empty()
    before = db.count_candidates(status="alive")
    event = orch.step(generation=1)
    assert event.candidate_id is not None
    assert event.skipped_reason is None
    assert db.count_candidates(status="alive") == before + 1


def test_step_skips_empty_island(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    # Don't seed — every island is empty.
    event = orch.step(generation=1)
    assert event.skipped_reason == "empty_island"
    assert event.candidate_id is None


def test_step_does_not_invoke_red_team_below_milestone(db, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        orch_mod,
        "red_team_candidate",
        lambda *a, **k: calls.append(1) or [],
    )
    _stub_cascade(monkeypatch, feasibility=0.9, structural=0.85, similarity=0.9)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator(
        db, _stub_client(), audit, _hp(milestone_fitness=0.99)
    )
    orch.seed_if_empty()
    orch.step(generation=1)
    assert calls == []


def test_step_invokes_red_team_at_or_above_milestone(db, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        orch_mod,
        "red_team_candidate",
        lambda *a, **k: calls.append(1) or [],
    )
    _stub_cascade(monkeypatch, feasibility=0.9, structural=0.9, similarity=0.9)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator(
        db, _stub_client(), audit, _hp(milestone_fitness=0.5)
    )
    orch.seed_if_empty()
    event = orch.step(generation=1)
    assert calls == [1]
    assert event.meta_trigger == "milestone_candidate"


def test_step_invokes_research_on_scheduled_interval(db, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(orch_mod, "red_team_candidate", lambda *a, **k: [])
    monkeypatch.setattr(
        orch_mod, "run_research", lambda trigger, *a, **k: calls.append(trigger) or []
    )
    _stub_cascade(monkeypatch, feasibility=0.5, structural=0.6, similarity=0.6)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator(
        db,
        _stub_client(),
        audit,
        _hp(milestone_fitness=1.0, research_every_generations=5),
    )
    orch.seed_if_empty()
    event = orch.step(generation=5)
    assert calls == ["scheduled_interval"]
    assert event.meta_trigger == "scheduled_interval"


def test_run_returns_after_max_generations(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    result = orch.run(max_generations=3)
    assert len(result.events) == 3
    assert result.paused is False
    assert result.stopped_reason == "max_generations"


def test_run_stops_on_structural_curator_decision(db, monkeypatch, tmp_path):
    _stub_cascade(monkeypatch, feasibility=0.9, structural=0.9, similarity=0.9)
    monkeypatch.setattr(
        orch_mod,
        "red_team_candidate",
        lambda *a, **k: [
            MetaFinding(
                source="redteam",
                framing="regulatory",
                claim="blocks",
                evidence="e",
                falsification_condition="if x",
                severity=Severity.HIGH,
            )
        ],
    )
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _stub_client(classification=Classification.STRUCTURAL)
    orch = Orchestrator(db, client, audit, _hp(milestone_fitness=0.5))
    result = orch.run(max_generations=10)
    assert result.paused is True
    assert result.stopped_reason == "curator_pause"
    assert len(result.events) >= 1
    assert len(result.events) < 10


def test_detect_stall_returns_false_with_short_history(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path, hp=_hp(stall_window=10))
    orch.seed_if_empty()
    assert orch.detect_stall() is False


def test_detect_stall_returns_true_when_window_is_flat(db, monkeypatch, tmp_path):
    from alphamo.schemas import Scores

    # Insert flat fitness rows across many generations.
    for g in range(1, 6):
        db.insert(
            Architecture(
                name=f"n{g}",
                summary="s",
                value_chain="vc",
                capture_mechanism="cm",
                entry_resources="er",
            ),
            Scores(
                feasibility=0.5,
                structural=0.5,
                exemplar_similarity=0.5,
                middle_class_accessible=True,
            ),
            generation=g,
        )
    orch = _make_orchestrator(
        db, monkeypatch, tmp_path, hp=_hp(stall_window=5, stall_epsilon=0.001)
    )
    assert orch.detect_stall() is True
