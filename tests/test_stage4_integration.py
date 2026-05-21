"""Integration tests for adversarial-scrutiny selection-pressure and curator-gate semantics.

Verifies:
  - aggregate_fitness averages over present dimensions; legacy candidates
    (robustness=None, or exemplar_similarity-set legacy data) get a
    smaller-N average; new candidates get a 3-way average over
    feasibility + structural + robustness.
  - cosmetic-only adversarial concerns on a milestone candidate do NOT
    trigger curator pause; structural ones do.
  - Routine adversarial firing writes a record to the audit log (every
    step, not just milestone).

Sprint 2 redesign: the legacy exemplar-similarity stage was retired.
Seeds are no longer scored candidates, so "starter robustness" tests
based on production seed scores are gone.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.database.operations import aggregate_fitness
from alphamo.evaluator import cascade as cascade_mod
from alphamo.meta.audit_log import AuditLog
from alphamo.orchestrator import Orchestrator
from alphamo.schemas import Scores
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
    StructuralConcern,
)
from tests.fixtures.parsed_message import FakeParsedMessage


# --------------------------------------------------------------------- aggregate_fitness


def test_aggregate_fitness_skips_robustness_when_none_legacy_case():
    """A legacy Scores without robustness must average over the two present dims."""
    legacy = Scores(
        feasibility=0.9,
        structural=0.9,
        exemplar_similarity=None,
        robustness=None,
        middle_class_accessible=True,
    )
    # 2-way average preserved.
    assert aggregate_fitness(legacy) == pytest.approx(0.9)


def test_aggregate_fitness_includes_robustness_when_present():
    """New Scores with robustness averages over feasibility + structural + robustness."""
    new = Scores(
        feasibility=0.9,
        structural=0.9,
        robustness=0.6,
        middle_class_accessible=True,
    )
    # (0.9 + 0.9 + 0.6) / 3 = 0.80
    assert aggregate_fitness(new) == pytest.approx(0.80)


def test_aggregate_fitness_legacy_exemplar_similarity_is_included():
    """Old DBs with exemplar_similarity values still contribute that dim to fitness.

    Backward-compat path: a row that was written under the pre-Sprint-2
    schema has `exemplar_similarity: float`. Reading it back today, the
    aggregate must include that dim so its historical fitness is stable.
    """
    legacy = Scores(
        feasibility=0.9,
        structural=0.9,
        exemplar_similarity=0.9,
        robustness=0.6,
        middle_class_accessible=True,
    )
    # (0.9 + 0.9 + 0.9 + 0.6) / 4 = 0.825
    assert aggregate_fitness(legacy) == pytest.approx(0.825)


def test_aggregate_fitness_middle_class_filter_overrides_robustness():
    """If middle_class_accessible=False, fitness is 0 regardless of robustness."""
    failed_filter = Scores(
        feasibility=0.9, structural=0.9,
        robustness=0.99,
        middle_class_accessible=False,
    )
    assert aggregate_fitness(failed_filter) == 0.0


# --------------------------------------------------------------------- milestone + curator


def _stub_full_cascade(monkeypatch, stage4_concerns, stage4_robustness=0.99):
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c, **kw: Stage1Finding(
            feasibility=0.99, middle_class_accessible=True, reasoning="ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c, **kw: Stage2Finding(
            one_person_threshold=0.99, billion_dollar_potential=0.99,
            labor_separation=0.99, structural=0.99, reasoning="ok",
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
    """HP that lets milestone trigger fire easily — low generation gate and
    fitness/robustness floors below the stub values (0.99 fitness, 0.99
    robustness in the stubbed cascade). Sprint 14: explicitly opts in to
    `curator_pause_enabled=True` since the Sprint 14 production default
    is disabled."""
    return Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=1,
        milestone_absolute_fitness_threshold=0.50,
        milestone_absolute_robustness_threshold=0.50,
        curator_pause_enabled=True,
    )


def test_milestone_with_cosmetic_only_concerns_does_not_pause(db, monkeypatch, tmp_path):
    """Cosmetic-only adversarial findings on a milestone do not trigger pause."""
    _stub_full_cascade(
        monkeypatch,
        stage4_concerns=[
            StructuralConcern(
                framing="regulatory", claim="minor wrinkle",
                evidence="e", falsification_condition="if x",
                severity=Severity.LOW,
            )
        ],
        stage4_robustness=0.99,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    # Curator classifies as COSMETIC.
    client = _stub_client(classification=Classification.COSMETIC)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_milestone_hp())

    result = orch.run(max_generations=2)
    assert result.paused is False
    assert result.stopped_reason == "max_generations"


def test_milestone_with_structural_concerns_pauses(db, monkeypatch, tmp_path):
    """At least one structural adversarial finding → curator pauses."""
    _stub_full_cascade(
        monkeypatch,
        stage4_concerns=[
            StructuralConcern(
                framing="legal_exposure", claim="severe risk",
                evidence="e", falsification_condition="if y",
                severity=Severity.HIGH,
            )
        ],
        stage4_robustness=0.99,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _stub_client(classification=Classification.STRUCTURAL)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_milestone_hp())

    result = orch.run(max_generations=10)
    assert result.paused is True
    assert result.stopped_reason == "curator_pause"


def test_routine_adversarial_firing_writes_audit_entry(db, monkeypatch, tmp_path):
    """Every adversarial firing logs a routine audit entry, milestone or not."""
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
    # Disable milestone trigger so this run only produces routine adversarial logs.
    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, client, audit, hp=hp)
    orch.run(max_generations=3)

    events = audit.read_all()
    # Audit trigger string preserved as `stage4_routine` for backward
    # compatibility with pre-Sprint-2 audit logs.
    routine_events = [e for e in events if e.trigger == "stage4_routine"]
    assert len(routine_events) >= 1, (
        "expected at least one routine adversarial-scrutiny audit entry"
    )
    sample = routine_events[0]
    assert sample.classification == "routine"
    assert "robustness" in sample.payload
    assert "concerns" in sample.payload
