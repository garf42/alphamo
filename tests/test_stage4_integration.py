"""Integration tests for Stage 4's selection-pressure and curator-gate semantics.

Verifies:
  - Decision 1: STARTERS carry robustness=0.85.
  - Decision 2: aggregate_fitness averages over present dimensions; legacy
    candidates (robustness=None) get 3-way average; new candidates get 4-way.
  - Decision 3: cosmetic-only Stage 4 concerns on a milestone candidate
    do NOT trigger curator pause; structural ones do.
  - Routine Stage 4 firing writes a record to the audit log (every step,
    not just milestone).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.database.operations import aggregate_fitness
from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.exemplar_library import (
    LEVELS_SCORES,
    ROWLING_SCORES,
    SATOSHI_SCORES,
    STARTERS,
)
from alphamo.meta.audit_log import AuditLog
from alphamo.orchestrator import Orchestrator
from alphamo.schemas import Scores
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage3Finding,
    Stage4Finding,
    StructuralConcern,
)
from tests.fixtures.parsed_message import FakeParsedMessage


# --------------------------------------------------------------------- Decision 1


def test_all_starters_carry_robustness_0_85():
    for arch, scores in STARTERS:
        assert scores.robustness == 0.85, (
            f"{arch.name} STARTER missing robustness=0.85 backfill"
        )


def test_satoshi_aggregate_fitness_is_four_way_with_robustness():
    # (0.95 + 0.95 + 1.00 + 0.85) / 4 = 0.9375
    assert aggregate_fitness(SATOSHI_SCORES) == pytest.approx(0.9375)


def test_rowling_levels_aggregates_with_robustness():
    # Rowling: (0.85 + 0.90 + 0.95 + 0.85) / 4 = 0.8875
    assert aggregate_fitness(ROWLING_SCORES) == pytest.approx(0.8875)
    # Levels: (0.90 + 0.80 + 0.85 + 0.85) / 4 = 0.85
    assert aggregate_fitness(LEVELS_SCORES) == pytest.approx(0.85)


# --------------------------------------------------------------------- Decision 2


def test_aggregate_fitness_skips_robustness_when_none_legacy_case():
    """A legacy Scores without robustness must average over the three present dims."""
    legacy = Scores(
        feasibility=0.9,
        structural=0.9,
        exemplar_similarity=0.9,
        robustness=None,  # explicit; same as omitting
        middle_class_accessible=True,
    )
    # 3-way average preserved.
    assert aggregate_fitness(legacy) == pytest.approx(0.9)


def test_aggregate_fitness_includes_robustness_when_present():
    """New Scores with robustness averages over four dims."""
    new = Scores(
        feasibility=0.9,
        structural=0.9,
        exemplar_similarity=0.9,
        robustness=0.6,
        middle_class_accessible=True,
    )
    # (0.9 + 0.9 + 0.9 + 0.6) / 4 = 0.825
    assert aggregate_fitness(new) == pytest.approx(0.825)


def test_aggregate_fitness_middle_class_filter_overrides_robustness():
    """If middle_class_accessible=False, fitness is 0 regardless of robustness."""
    failed_filter = Scores(
        feasibility=0.9, structural=0.9, exemplar_similarity=0.9,
        robustness=0.99,
        middle_class_accessible=False,
    )
    assert aggregate_fitness(failed_filter) == 0.0


# --------------------------------------------------------------------- Decision 3 + audit


def _stub_full_cascade(monkeypatch, stage4_concerns, stage4_robustness=0.99):
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=0.99, middle_class_accessible=True, reasoning="ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=0.99, billion_dollar_potential=0.99,
            labor_separation=0.99, structural=0.99, reasoning="ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage3_exemplars",
        lambda a, c: Stage3Finding(
            closest_exemplar="Satoshi", similarity=0.99, reasoning="ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=stage4_robustness,
            concerns=stage4_concerns,
            reasoning="stub",
        ),
    )


def _stub_client(classification: Classification) -> MagicMock:
    """Curator classifies every finding with the given verdict."""
    from alphamo.schemas import Architecture

    client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            return FakeParsedMessage(
                Architecture(
                    name="proposed", summary="s", value_chain="vc",
                    capture_mechanism="cm", entry_resources="er",
                )
            )
        if output_format is ClassificationVerdict:
            return FakeParsedMessage(
                ClassificationVerdict(
                    classification=classification, rationale="stub"
                )
            )
        return FakeParsedMessage(MagicMock())

    client.messages.parse.side_effect = parse_side_effect
    return client


def _milestone_hp() -> Hyperparameters:
    return Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=1,
        milestone_fitness_delta=0.02,
    )


def test_milestone_with_cosmetic_only_concerns_does_not_pause(db, monkeypatch, tmp_path):
    """Decision 3: cosmetic-only Stage 4 findings on a milestone do not trigger pause."""
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    _stub_full_cascade(
        monkeypatch,
        stage4_concerns=[
            StructuralConcern(
                framing="regulatory", claim="minor wrinkle",
                evidence="e", falsification_condition="if x",
                severity=Severity.LOW,
            )
        ],
        stage4_robustness=0.99,  # high enough to qualify as a milestone
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    # Curator classifies as COSMETIC.
    client = _stub_client(classification=Classification.COSMETIC)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_milestone_hp())

    result = orch.run(max_generations=2)
    assert result.paused is False
    assert result.stopped_reason == "max_generations"


def test_milestone_with_structural_concerns_pauses(db, monkeypatch, tmp_path):
    """Decision 3 inverse: at least one structural Stage 4 finding → curator pauses.

    Robustness is decoupled from concern count in the stub so we can hold
    fitness above the milestone threshold while still presenting a concern
    for the curator to classify.
    """
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    _stub_full_cascade(
        monkeypatch,
        stage4_concerns=[
            StructuralConcern(
                framing="legal_exposure", claim="severe risk",
                evidence="e", falsification_condition="if y",
                severity=Severity.HIGH,
            )
        ],
        stage4_robustness=0.99,  # high robustness in stub so candidate clears milestone
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _stub_client(classification=Classification.STRUCTURAL)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_milestone_hp())

    result = orch.run(max_generations=10)
    assert result.paused is True
    assert result.stopped_reason == "curator_pause"


def test_routine_stage4_firing_writes_audit_entry(db, monkeypatch, tmp_path):
    """Every Stage 4 firing logs a routine audit entry, even without milestone."""
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    _stub_full_cascade(
        monkeypatch,
        stage4_concerns=[
            StructuralConcern(
                framing="economic", claim="margin compression",
                evidence="e", falsification_condition="if z",
                severity=Severity.MEDIUM,
            )
        ],
        stage4_robustness=0.90,
    )
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(audit_path)
    client = _stub_client(classification=Classification.COSMETIC)
    # Disable milestone trigger so this run only produces routine Stage 4 logs.
    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, client, audit, hp=hp)
    orch.run(max_generations=3)

    events = audit.read_all()
    stage4_events = [e for e in events if e.trigger == "stage4_routine"]
    assert len(stage4_events) >= 1, (
        "expected at least one routine Stage 4 audit entry"
    )
    sample = stage4_events[0]
    assert sample.classification == "routine"
    assert "robustness" in sample.payload
    assert "concerns" in sample.payload
