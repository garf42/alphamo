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
    Stage4Finding,
    StructuralConcern,
)


def _stub_cascade(
    monkeypatch,
    feasibility: float = 0.9,
    structural: float = 0.85,
    similarity: float = 0.9,
    middle_class: bool = True,
    robustness: float = 0.85,
    stage4_concerns: list[StructuralConcern] | None = None,
):
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
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=robustness,
            concerns=stage4_concerns or [],
            reasoning="stub stage4",
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
    # Phase 2: milestone is gated by (a) generation >= milestone_min_generation
    # and (b) fitness > seed_baseline + milestone_fitness_delta. We default the
    # min-generation to 10000 here to disable the trigger for most tests; the
    # milestone-specific tests opt in explicitly.
    defaults = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


def _make_orchestrator(
    db, monkeypatch, tmp_path, client=None, hp=None
) -> Orchestrator:
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = client or _stub_client()
    return Orchestrator.for_new_run(db, client, audit, hp=hp or _hp())


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


def _concern(framing: str = "regulatory", severity: Severity = Severity.MEDIUM) -> StructuralConcern:
    return StructuralConcern(
        framing=framing,
        claim="stub concern",
        evidence="stub evidence",
        falsification_condition="if x were true",
        severity=severity,
    )


def test_step_does_not_invoke_curator_below_baseline_delta(db, monkeypatch, tmp_path):
    """A candidate below baseline+delta must not invoke the curator, even with concerns."""
    # Seed baseline (max of STARTERS) ≈ 0.888 with cascade-produced robustness.
    # Stub fitness ≈ 0.88, below baseline + delta. Stage 4 surfaces concerns,
    # but they should not be routed to the curator because the candidate
    # is not a milestone.
    _stub_cascade(
        monkeypatch,
        feasibility=0.9,
        structural=0.85,
        similarity=0.9,
        stage4_concerns=[_concern(severity=Severity.HIGH)],
    )
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    client = _stub_client()
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, client, audit, hp=_hp(milestone_min_generation=1)
    )
    orch.seed_if_empty()
    event = orch.step(generation=5)
    # No milestone curator firing → no meta_trigger, no curator classify calls.
    assert event.meta_trigger is None
    assert event.meta_decision is None


def test_step_does_not_invoke_curator_before_min_generation(db, monkeypatch, tmp_path):
    """Even a high-fitness candidate must not invoke curator during warmup."""
    _stub_cascade(
        monkeypatch,
        feasibility=0.99,
        structural=0.99,
        similarity=0.99,
        stage4_concerns=[_concern(severity=Severity.HIGH)],
    )
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_hp(milestone_min_generation=25)
    )
    orch.seed_if_empty()
    event = orch.step(generation=5)
    assert event.meta_trigger is None


def test_step_does_not_invoke_curator_when_stage4_clean_on_milestone(
    db, monkeypatch, tmp_path
):
    """A milestone candidate with NO Stage 4 concerns must not invoke the curator.

    Per Decision 3: only structural concerns trigger pause. If Stage 4 is
    clean, there's nothing to classify — the curator shouldn't fire at all.
    """
    _stub_cascade(
        monkeypatch,
        feasibility=0.99,
        structural=0.99,
        similarity=0.99,
        stage4_concerns=[],  # clean
    )
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db,
        _stub_client(),
        audit,
        hp=_hp(milestone_min_generation=1, milestone_fitness_delta=0.01),
    )
    orch.seed_if_empty()
    event = orch.step(generation=30)
    assert event.meta_trigger is None


def test_step_invokes_curator_on_milestone_with_concerns(db, monkeypatch, tmp_path):
    """Past min-generation AND above baseline+delta AND Stage 4 has concerns → curator fires."""
    # 4-way fitness = (0.99 * 4) / 4 = 0.99, comfortably above the
    # cascade-produced Satoshi seed baseline of ~0.888 + delta 0.02 = 0.908.
    _stub_cascade(
        monkeypatch,
        feasibility=0.99,
        structural=0.99,
        similarity=0.99,
        robustness=0.99,
        stage4_concerns=[_concern(framing="legal_exposure", severity=Severity.HIGH)],
    )
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db,
        _stub_client(),
        audit,
        hp=_hp(milestone_min_generation=25, milestone_fitness_delta=0.02),
    )
    orch.seed_if_empty()
    event = orch.step(generation=30)
    assert event.meta_trigger == "milestone_candidate"
    assert event.meta_decision is not None


def test_seed_baseline_is_persisted_in_run_hyperparameters(db, monkeypatch, tmp_path):
    """The computed seed_baseline_fitness must survive into the run row's HP JSON."""
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp())
    orch.seed_if_empty()
    run = db.get_run(orch.run_id)
    assert "seed_baseline_fitness" in run.hyperparameters
    # Cascade-produced canonical scores: Satoshi remains the highest aggregate.
    # (0.9500 + 0.9700 + 1.0000 + 0.6319) / 4.0 = 0.887975
    assert run.hyperparameters["seed_baseline_fitness"] == pytest.approx(0.887975, abs=0.005)


def test_resumed_run_inherits_seed_baseline(db, monkeypatch, tmp_path):
    """Resume of a previously-seeded run must read the baseline from HP JSON, not recompute."""
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch_a = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp())
    orch_a.seed_if_empty()
    baseline = orch_a.seed_baseline_fitness
    assert baseline is not None

    orch_resumed = Orchestrator.resume_run(db, _stub_client(), audit, orch_a.run_id)
    assert orch_resumed.seed_baseline_fitness == baseline
    # seed_if_empty must NOT re-seed and must NOT recompute.
    assert orch_resumed.seed_if_empty() is False
    assert orch_resumed.seed_baseline_fitness == baseline


def test_step_invokes_research_on_scheduled_interval(db, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        orch_mod, "run_research", lambda trigger, *a, **k: calls.append(trigger) or []
    )
    _stub_cascade(monkeypatch, feasibility=0.5, structural=0.6, similarity=0.6)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db,
        _stub_client(),
        audit,
        hp=_hp(research_every_generations=5),
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
    # Make the proposer's output score above the seed baseline so the
    # milestone gate fires past gen 1, and stub Stage 4 to surface a
    # high-severity concern that the (structural-classifying) curator
    # will escalate to PAUSE_FOR_HUMAN.
    _stub_cascade(
        monkeypatch,
        feasibility=0.99,
        structural=0.99,
        similarity=0.99,
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
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _stub_client(classification=Classification.STRUCTURAL)
    orch = Orchestrator.for_new_run(
        db,
        client,
        audit,
        hp=_hp(milestone_min_generation=1, milestone_fitness_delta=0.01),
    )
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

    orch = _make_orchestrator(
        db, monkeypatch, tmp_path, hp=_hp(stall_window=5, stall_epsilon=0.001)
    )
    # Insert flat fitness rows across many generations into THIS orchestrator's run.
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
            run_id=orch.run_id,
            generation=g,
        )
    assert orch.detect_stall() is True


def _client_that_raises_proposer_error_then_succeeds(failures: int) -> MagicMock:
    """Mock client where the first `failures` proposer calls return None and the rest succeed."""
    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    call_state = {"proposer_calls": 0}

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            call_state["proposer_calls"] += 1
            if call_state["proposer_calls"] <= failures:
                return FakeParsedMessage(
                    parsed_output=None,
                    stop_reason="refusal",
                )
            return FakeParsedMessage(
                Architecture(
                    name=f"variant-{call_state['proposer_calls']}",
                    summary="s",
                    value_chain="vc",
                    capture_mechanism="cm",
                    entry_resources="er",
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
    """One failed eval → loop continues; next iteration scores a candidate."""
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_that_raises_proposer_error_then_succeeds(failures=1)
    orch = Orchestrator.for_new_run(db, client, audit, hp=_hp(max_consecutive_failures=5))

    result = orch.run(max_generations=5)

    assert result.stopped_reason == "max_generations"
    assert result.consecutive_failures_at_stop == 0  # last 4 succeeded
    failures = [e for e in result.events if e.failure_reason is not None and e.candidate_id is None]
    inserts = [e for e in result.events if e.candidate_id is not None]
    assert len(failures) == 1
    assert len(inserts) == 4
    assert "proposer" in failures[0].failure_reason


def test_consecutive_proposer_failures_halt_run(db, monkeypatch, tmp_path):
    """N consecutive eval-side failures (no successful insert between them) halt the run."""
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
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
    """A success between failures should reset the counter so the run doesn't halt."""
    _stub_cascade(monkeypatch)
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    audit = AuditLog(tmp_path / "audit.jsonl")

    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    pattern = iter([
        False, False,  # 2 failures
        True,          # success → reset counter
        False, False,  # 2 more failures (counter at 2, below threshold of 3)
        True, True, True,  # more successes
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
