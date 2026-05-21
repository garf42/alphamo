"""Orchestrator wiring tests with mocked LLM-backed components.

The cascade stage functions, red-team agent, and research agent are all
LLM-backed live and covered separately. These tests verify orchestration —
iteration sequencing, milestone red-team triggers, scheduled research,
curator pause — using monkeypatched stubs.

Sprint 2 redesign: islands start empty; the proposer bootstraps each
island from the reference exemplar set. No seed_if_empty mechanism.
Milestone trigger uses absolute fitness + robustness thresholds.
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
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
    StructuralConcern,
)


def _stub_cascade(
    monkeypatch,
    feasibility: float = 0.9,
    structural: float = 0.85,
    middle_class: bool = True,
    robustness: float = 0.85,
    stage4_concerns: list[StructuralConcern] | None = None,
):
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c, **kw: Stage1Finding(
            feasibility=feasibility,
            middle_class_accessible=middle_class,
            reasoning="stub",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c, **kw: Stage2Finding(
            one_person_threshold=structural,
            billion_dollar_potential=structural,
            labor_separation=structural,
            structural=structural,
            reasoning="stub",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=robustness,
            concerns=stage4_concerns or [],
            reasoning="stub adversarial",
        ),
    )


def _stub_client(
    architecture_name: str = "novel candidate",
    classification: Classification = Classification.COSMETIC,
) -> MagicMock:
    """Mock client routing parse() calls to Architecture or ClassificationVerdict."""
    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            return FakeParsedMessage(
                Architecture(
                    name=architecture_name,
                    summary="s",
                    value_chain="vc",
                    capture_mechanism="cm",
                    entry_resources="er",
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


def _hp(**kwargs) -> Hyperparameters:
    """Default test HP. Disables milestone trigger via high min_generation;
    individual milestone tests override."""
    defaults = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


def _make_orchestrator(
    db, monkeypatch, tmp_path, client=None, hp=None, bootstrap: bool = True
) -> Orchestrator:
    """Construct an orchestrator with stubbed cascade and research.

    `bootstrap=True` (the default) runs `_bootstrap_islands()` so the
    sampler has the trivial seed available in every island — this matches
    what `run()` does before its main loop. Pass `bootstrap=False` to
    leave islands empty (useful for tests of the bootstrap mechanism
    itself or of the `run()` lifecycle end-to-end).
    """
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = client or _stub_client()
    orch = Orchestrator.for_new_run(db, client, audit, hp=hp or _hp())
    if bootstrap:
        orch._bootstrap_islands()
    return orch


# ----------------------------------------------------------------- bootstrap


def test_bootstrap_inserts_trivial_seed_into_every_island_at_gen_zero(
    db, monkeypatch, tmp_path
):
    """Sprint 3 invariant: `_bootstrap_islands()` inserts a copy of
    TRIVIAL_SEED into each of N islands as a gen-0 alive candidate.

    Inverts the Sprint 2 `test_seeds_not_inserted_into_candidates_table`
    invariant — Sprint 3 brings back per-island gen-0 seeding, but with
    a single trivial baseline rather than four curated existence proofs.
    """
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_hp(num_islands=4)
    )

    inserted = orch._bootstrap_islands()
    assert inserted == 4

    rows = db.alive_in_run(orch.run_id)
    assert len(rows) == 4
    for row in rows:
        assert row.architecture_spec["name"] == TRIVIAL_SEED.name
        assert row.generation == 0
    # One row per island.
    assert {r.island_id for r in rows} == {0, 1, 2, 3}


def test_bootstrap_writes_audit_event(db, monkeypatch, tmp_path):
    """Bootstrap step emits a single audit-log event for traceability."""
    _stub_cascade(monkeypatch)
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(audit_path)
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp(num_islands=4))
    orch._bootstrap_islands()

    events = audit.read_all()
    bootstrap_events = [e for e in events if e.trigger == "bootstrap_islands"]
    assert len(bootstrap_events) == 1
    assert bootstrap_events[0].payload["num_islands"] == 4
    assert len(bootstrap_events[0].payload["candidate_ids"]) == 4


def test_bootstrap_is_idempotent_no_op_on_resume(db, monkeypatch, tmp_path):
    """Calling `_bootstrap_islands()` twice (e.g., resume of an already-bootstrapped
    run) is a no-op on the second call."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp(num_islands=2))

    assert orch._bootstrap_islands() == 2
    assert orch._bootstrap_islands() == 0
    rows = db.alive_in_run(orch.run_id)
    assert len(rows) == 2  # not 4


def test_step_inserts_a_new_candidate(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    before = db.count_candidates(status="alive")
    event = orch.step(generation=1)
    assert event.candidate_id is not None
    assert event.skipped_reason is None
    assert db.count_candidates(status="alive") == before + 1


# ----------------------------------------------------------------- milestone trigger


def _concern(framing: str = "regulatory", severity: Severity = Severity.MEDIUM) -> StructuralConcern:
    return StructuralConcern(
        framing=framing,
        claim="stub concern",
        evidence="stub evidence",
        falsification_condition="if x were true",
        severity=severity,
    )


def test_milestone_does_not_fire_below_absolute_fitness_threshold(db, monkeypatch, tmp_path):
    """Fitness below the absolute floor → no milestone, no curator firing."""
    _stub_cascade(
        monkeypatch,
        feasibility=0.6, structural=0.6,
        robustness=0.95,  # high robustness, but low fitness
        stage4_concerns=[_concern(severity=Severity.HIGH)],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.80,
            milestone_absolute_robustness_threshold=0.50,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger is None
    assert event.meta_decision is None


def test_milestone_does_not_fire_below_absolute_robustness_threshold(db, monkeypatch, tmp_path):
    """Robustness below the absolute floor → no milestone, even with high fitness."""
    _stub_cascade(
        monkeypatch,
        feasibility=0.95, structural=0.95,
        robustness=0.40,  # below floor
        stage4_concerns=[_concern(severity=Severity.HIGH)],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.50,
            milestone_absolute_robustness_threshold=0.70,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger is None


def test_milestone_does_not_fire_before_min_generation(db, monkeypatch, tmp_path):
    """Even a high-fitness candidate must not invoke curator during warmup."""
    _stub_cascade(
        monkeypatch,
        feasibility=0.99, structural=0.99,
        robustness=0.99,
        stage4_concerns=[_concern(severity=Severity.HIGH)],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=25,
            milestone_absolute_fitness_threshold=0.50,
            milestone_absolute_robustness_threshold=0.50,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger is None


def test_milestone_does_not_fire_when_adversarial_clean(db, monkeypatch, tmp_path):
    """A milestone candidate with NO concerns must not invoke the curator —
    there's nothing structural to classify, and routine classification doesn't
    qualify as a curator pause."""
    _stub_cascade(
        monkeypatch,
        feasibility=0.99, structural=0.99,
        robustness=0.99,
        stage4_concerns=[],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.50,
            milestone_absolute_robustness_threshold=0.50,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=30)
    assert event.meta_trigger is None


def test_milestone_fires_at_absolute_threshold_boundary_for_fitness(db, monkeypatch, tmp_path):
    """Fitness just above threshold + robustness clear → milestone fires."""
    # 3-dim aggregate of (0.85, 0.85, 0.85) = 0.85; threshold 0.80 → clears.
    _stub_cascade(
        monkeypatch,
        feasibility=0.85, structural=0.85,
        robustness=0.85,
        stage4_concerns=[_concern(framing="legal_exposure", severity=Severity.HIGH)],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.80,
            milestone_absolute_robustness_threshold=0.70,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger == "milestone_candidate"
    assert event.meta_decision is not None


def test_milestone_fires_at_absolute_threshold_boundary_for_robustness(db, monkeypatch, tmp_path):
    """Robustness just above threshold + fitness clear → milestone fires."""
    _stub_cascade(
        monkeypatch,
        feasibility=0.95, structural=0.95,
        robustness=0.75,  # just above floor of 0.70
        stage4_concerns=[_concern(severity=Severity.HIGH)],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.80,
            milestone_absolute_robustness_threshold=0.70,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger == "milestone_candidate"


def test_milestone_does_not_fire_when_robustness_is_none(db, monkeypatch, tmp_path):
    """An early-exit candidate (robustness=None) can never be a milestone."""
    # Force early exit at stage 1.
    _stub_cascade(monkeypatch, feasibility=0.2, structural=0.9, robustness=0.95)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.10,  # low floor
            milestone_absolute_robustness_threshold=0.10,
        ),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger is None


# ----------------------------------------------------------------- research + stall


def test_step_does_not_fire_research_meta_path_under_sprint12(
    db, monkeypatch, tmp_path
):
    """Sprint 12 removed the scheduled-research / stall-triggered
    research meta-path. Only the milestone-curate meta path remains.
    A step that previously would have triggered scheduled research
    now produces an event with meta_trigger=None."""
    _stub_cascade(monkeypatch, feasibility=0.5, structural=0.6)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        # Even at the old research-trigger boundary (gen 5, divisible by
        # legacy research_every_generations=5), no meta path fires.
        hp=_hp(),
    )
    orch._bootstrap_islands()
    event = orch.step(generation=5)
    assert event.meta_trigger is None


def test_run_returns_after_max_generations(db, monkeypatch, tmp_path):
    # bootstrap=False here because run() does its own bootstrap; calling
    # both would double-bootstrap. Bootstrap is idempotent (no-op on
    # second call) so either order is safe, but skipping the helper
    # bootstrap keeps the test's intent clear.
    orch = _make_orchestrator(db, monkeypatch, tmp_path, bootstrap=False)
    result = orch.run(max_generations=3)
    assert len(result.events) == 3
    assert result.paused is False
    assert result.stopped_reason == "max_generations"


def test_run_emits_island_reset_audit_event_at_cadence(db, monkeypatch, tmp_path):
    """When run() crosses a reset cadence boundary, an island_reset audit
    event must be emitted with weak/source/seed-program payload."""
    _stub_cascade(monkeypatch)
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(audit_path)
    # Cadence 2 so reset fires within a short test run; 4 islands so we
    # have a meaningful weak/strong split.
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            num_islands=4,
            reset_every_generations=2,
            research_every_generations=1000,
        ),
    )
    orch.run(max_generations=4)

    events = audit.read_all()
    reset_events = [e for e in events if e.trigger == "island_reset"]
    # Reset fires at gen 2 and gen 4 (cadence 2, max_generations 4).
    assert len(reset_events) >= 1, "expected at least one island_reset audit event"
    sample = reset_events[0]
    assert sample.classification == "routine"
    payload = sample.payload
    assert "weak_islands" in payload
    assert "source_islands" in payload
    assert "seed_program_ids" in payload
    assert len(payload["weak_islands"]) == len(payload["source_islands"])
    assert len(payload["weak_islands"]) == len(payload["seed_program_ids"])


def test_run_stops_on_structural_curator_decision(db, monkeypatch, tmp_path):
    _stub_cascade(
        monkeypatch,
        feasibility=0.99, structural=0.99,
        robustness=0.99,
        stage4_concerns=[
            StructuralConcern(
                framing="regulatory",
                claim="blocks",
                evidence="e",
                falsification_condition="if x",
                severity=Severity.HIGH,
            )
        ],
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _stub_client(classification=Classification.STRUCTURAL)
    orch = Orchestrator.for_new_run(
        db, client, audit,
        hp=_hp(
            milestone_min_generation=1,
            milestone_absolute_fitness_threshold=0.50,
            milestone_absolute_robustness_threshold=0.50,
        ),
    )
    result = orch.run(max_generations=10)
    assert result.paused is True
    assert result.stopped_reason == "curator_pause"
    assert 1 <= len(result.events) < 10


def test_detect_stall_returns_false_with_short_history(db, monkeypatch, tmp_path):
    orch = _make_orchestrator(db, monkeypatch, tmp_path, hp=_hp(stall_window=10))
    assert orch.detect_stall() is False


def test_detect_stall_returns_true_when_window_is_flat(db, monkeypatch, tmp_path):
    from alphamo.schemas import Scores

    orch = _make_orchestrator(
        db, monkeypatch, tmp_path, hp=_hp(stall_window=5, stall_epsilon=0.001)
    )
    # Flat fitness across many generations.
    for g in range(1, 6):
        db.insert(
            Architecture(
                name=f"n{g}", summary="s", value_chain="vc",
                capture_mechanism="cm", entry_resources="er",
            ),
            Scores(
                feasibility=0.5, structural=0.5,
                middle_class_accessible=True,
            ),
            run_id=orch.run_id,
            generation=g,
        )
    assert orch.detect_stall() is True


# ----------------------------------------------------------------- failure handling


def _client_that_raises_proposer_error_then_succeeds(failures: int) -> MagicMock:
    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    call_state = {"proposer_calls": 0}

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            call_state["proposer_calls"] += 1
            if call_state["proposer_calls"] <= failures:
                return FakeParsedMessage(parsed_output=None, stop_reason="refusal")
            return FakeParsedMessage(
                Architecture(
                    name=f"variant-{call_state['proposer_calls']}",
                    summary="s", value_chain="vc",
                    capture_mechanism="cm", entry_resources="er",
                )
            )
        if output_format is ClassificationVerdict:
            return FakeParsedMessage(
                ClassificationVerdict(
                    classification=Classification.COSMETIC, rationale="stub"
                )
            )
        return FakeParsedMessage(MagicMock())

    client.messages.parse.side_effect = parse_side_effect
    return client


def test_single_proposer_failure_does_not_halt_run(db, monkeypatch, tmp_path):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_that_raises_proposer_error_then_succeeds(failures=1)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_hp(max_consecutive_failures=5))

    result = orch.run(max_generations=5)

    assert result.stopped_reason == "max_generations"
    assert result.consecutive_failures_at_stop == 0
    failures = [e for e in result.events if e.failure_reason is not None and e.candidate_id is None]
    inserts = [e for e in result.events if e.candidate_id is not None]
    assert len(failures) == 1
    assert len(inserts) == 4
    assert "proposer" in failures[0].failure_reason


def test_consecutive_proposer_failures_halt_run(db, monkeypatch, tmp_path):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_that_raises_proposer_error_then_succeeds(failures=100)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_hp(max_consecutive_failures=3))

    result = orch.run(max_generations=20)

    assert result.stopped_reason == "consecutive_failures"
    assert result.consecutive_failures_at_stop == 3
    assert len(result.events) == 3
    assert all(e.candidate_id is None for e in result.events)
    assert all(e.failure_reason is not None for e in result.events)


def test_consecutive_counter_resets_on_successful_insert(db, monkeypatch, tmp_path):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")

    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    pattern = iter([
        False, False,
        True,
        False, False,
        True, True, True,
    ])

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            ok = next(pattern, True)
            if not ok:
                return FakeParsedMessage(parsed_output=None, stop_reason="refusal")
            return FakeParsedMessage(
                Architecture(name="ok", summary="s", value_chain="vc",
                             capture_mechanism="cm", entry_resources="er")
            )
        return FakeParsedMessage(
            ClassificationVerdict(classification=Classification.COSMETIC, rationale="x")
        )

    client.messages.parse.side_effect = parse_side_effect
    orch = Orchestrator.for_new_run(db, client, audit, hp=_hp(max_consecutive_failures=3))

    result = orch.run(max_generations=8)

    assert result.stopped_reason == "max_generations"
    inserts = [e for e in result.events if e.candidate_id is not None]
    failures = [e for e in result.events if e.failure_reason is not None and e.candidate_id is None]
    assert len(failures) == 4
    assert len(inserts) >= 1
