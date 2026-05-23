"""Sprint parallel-candidates: orchestrator step() in batched mode.

Tests for the per-generation parallel pipeline:
  - N candidates produced per step at candidates_per_generation=N
  - Distinct island_ids across the batch (no duplicates)
  - All candidates share the same generation value
  - Backward compat: N=1 produces identical event shape to pre-sprint
  - Partial-success batches do NOT increment consecutive_failures
  - All-fail batches DO increment consecutive_failures
  - Reset cadence fires once per generation, not once per candidate

The orchestrator's cascade and proposer are mocked so these tests run
without any LLM calls. Mocks live at the same monkeypatch points as
the existing test_orchestrator suite.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.errors import Stage1OutputError
from alphamo.evaluator import cascade as cascade_mod
from alphamo.meta.audit_log import AuditLog
from alphamo.orchestrator import Orchestrator
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Stage4Finding


# ----------------------------------------------------------------- helpers


def _stub_cascade_passing(monkeypatch, robustness: float = 0.85) -> None:
    """Stub all 3 cascade stages so every candidate scores cleanly."""
    from tests.fixtures.stage1_evidence import passing_stage1_finding
    from tests.fixtures.stage2_evidence import passing_stage2_finding

    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: passing_stage1_finding(reasoning="stub"),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="stub"),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=robustness, concerns=[], reasoning="stub"
        ),
    )


def _stub_client(architecture_name_prefix: str = "candidate") -> MagicMock:
    """Mock client returning a distinct architecture per call so the
    DB rows don't collapse to a single name."""
    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    counter = {"n": 0}

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            counter["n"] += 1
            return FakeParsedMessage(
                Architecture(
                    name=f"{architecture_name_prefix}-{counter['n']}",
                    summary="s", value_chain="vc",
                    capture_mechanism="cm", entry_resources="er",
                )
            )
        return FakeParsedMessage(MagicMock())

    client.messages.parse.side_effect = parse_side_effect
    return client


def _hp(**kwargs) -> Hyperparameters:
    """Test default HP. Disables curator gate + milestone trigger so
    individual parallel-batch tests can focus on the batch mechanics."""
    defaults = dict(
        num_islands=8,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
        curator_pause_enabled=False,
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


def _make_orchestrator(
    db, monkeypatch, tmp_path, hp=None, client=None
) -> Orchestrator:
    _stub_cascade_passing(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, client or _stub_client(), audit, hp=hp or _hp()
    )
    orch._bootstrap_islands()
    return orch


# ----------------------------------------------------------------- batch shape


def test_step_at_n_equals_num_islands_produces_one_per_island(
    db, monkeypatch, tmp_path
):
    """Production default: candidates_per_generation == num_islands → 8
    candidates per step, one per island."""
    orch = _make_orchestrator(
        db, monkeypatch, tmp_path,
        hp=_hp(num_islands=8, candidates_per_generation=8),
    )
    events = orch.step(generation=1)
    assert len(events) == 8
    # Every island represented exactly once — no duplicates.
    island_ids = [e.island_id for e in events]
    assert sorted(island_ids) == [0, 1, 2, 3, 4, 5, 6, 7]
    # All candidates share the batch generation.
    assert {e.generation for e in events} == {1}
    # Every event carries a successfully-inserted candidate id.
    assert all(e.candidate_id is not None for e in events)
    # Architecture names are all distinct (stub increments per call).
    assert len({e.architecture_name for e in events}) == 8


def test_step_at_n_subset_produces_n_distinct_islands(
    db, monkeypatch, tmp_path
):
    """When candidates_per_generation < num_islands the batch covers a
    subset of islands. No duplicates."""
    orch = _make_orchestrator(
        db, monkeypatch, tmp_path,
        hp=_hp(num_islands=8, candidates_per_generation=3),
    )
    events = orch.step(generation=1)
    assert len(events) == 3
    assert len({e.island_id for e in events}) == 3
    for e in events:
        assert 0 <= e.island_id < 8


def test_step_caps_at_num_islands_when_n_exceeds(db, monkeypatch, tmp_path):
    """candidates_per_generation > num_islands shouldn't double-book any
    island. The orchestrator caps at num_islands."""
    orch = _make_orchestrator(
        db, monkeypatch, tmp_path,
        hp=_hp(num_islands=4, candidates_per_generation=10),
    )
    events = orch.step(generation=1)
    assert len(events) == 4
    assert sorted(e.island_id for e in events) == [0, 1, 2, 3]


# ----------------------------------------------------------------- backward compat (N=1)


def test_step_at_n_equals_1_matches_pre_sprint_event_shape(
    db, monkeypatch, tmp_path
):
    """Backward-compat pin: at candidates_per_generation=1, step() returns
    a single-element list whose IterationEvent matches the pre-sprint
    single-event semantics (one candidate inserted, one island chosen,
    standard fields populated)."""
    orch = _make_orchestrator(
        db, monkeypatch, tmp_path,
        hp=_hp(num_islands=4, candidates_per_generation=1),
    )
    events = orch.step(generation=1)
    assert len(events) == 1
    event = events[0]
    assert event.candidate_id is not None
    assert event.generation == 1
    assert event.failure_reason is None
    assert event.architecture_name is not None
    assert event.fitness is not None
    assert event.fitness > 0.0
    # The candidate row exists and matches the event.
    row = db.get(event.candidate_id)
    assert row.island_id == event.island_id
    assert row.generation == 1


# ----------------------------------------------------------------- failure handling


def test_partial_batch_failure_does_not_increment_consecutive_failures(
    db, monkeypatch, tmp_path
):
    """Sprint parallel-candidates per-generation failure semantics:
    a batch with at least one success resets consecutive_failures.

    Drive the run by mocking Stage 1 to fail every other call. With
    candidates_per_generation=4 the batch has 2 successes + 2 failures
    per generation; the counter must reset to 0 each generation
    rather than incrementing on the failures."""
    from tests.fixtures.stage1_evidence import passing_stage1_finding
    from tests.fixtures.stage2_evidence import passing_stage2_finding

    call_count = {"n": 0}

    def alternating_stage1(arch, c, **kw):
        call_count["n"] += 1
        if call_count["n"] % 2 == 0:
            raise Stage1OutputError(
                stop_reason="parse_error", detail="simulated"
            )
        return passing_stage1_finding(reasoning="stub")

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", alternating_stage1)
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="stub"),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.8, concerns=[], reasoning="stub"
        ),
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            num_islands=4, candidates_per_generation=4,
            max_consecutive_failures=2,
        ),
    )
    # Run 3 generations. Each generation has partial successes, so the
    # counter resets every time; the run must NOT hit the stop condition.
    result = orch.run(max_generations=3)
    assert result.stopped_reason == "max_generations"
    # Verify partial successes happened in the batches.
    n_success = sum(1 for e in result.events if e.candidate_id is not None)
    n_failure = sum(1 for e in result.events if e.failure_reason is not None)
    assert n_success > 0 and n_failure > 0


def test_all_fail_batch_increments_consecutive_failures(
    db, monkeypatch, tmp_path
):
    """A batch in which every candidate fails counts as one consecutive-
    failure generation. After max_consecutive_failures such batches in
    a row, the run halts with stopped_reason='consecutive_failures'."""
    def always_fail_stage1(arch, c, **kw):
        raise Stage1OutputError(
            stop_reason="parse_error", detail="simulated catastrophic"
        )

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", always_fail_stage1)
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: None
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.8, concerns=[], reasoning="stub"
        ),
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            num_islands=4, candidates_per_generation=4,
            max_consecutive_failures=2,
        ),
    )
    result = orch.run(max_generations=10)
    assert result.stopped_reason == "consecutive_failures"
    assert result.consecutive_failures_at_stop == 2


# ----------------------------------------------------------------- reset cadence


def test_reset_fires_once_per_generation_not_per_candidate(
    db, monkeypatch, tmp_path
):
    """The maybe_reset call lives outside the per-candidate fan-out so
    it should fire exactly once per generation, not N times. With 8
    candidates per generation and reset_every_generations=1, exactly
    one reset audit event per generation should be emitted."""
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(audit_path)
    _stub_cascade_passing(monkeypatch)
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            num_islands=4, candidates_per_generation=4,
            reset_every_generations=1, milestone_min_generation=10_000,
        ),
    )
    orch._bootstrap_islands()
    orch.step(generation=1)
    orch.step(generation=2)
    reset_events = [
        e for e in audit.read_all() if e.trigger == "island_reset"
    ]
    # Exactly 2 reset events: one for gen 1, one for gen 2.
    assert len(reset_events) == 2
    assert {e.payload["generation"] for e in reset_events} == {1, 2}


# ----------------------------------------------------------------- audit attribution


def test_telemetry_attributes_each_candidate_to_its_island(
    db, monkeypatch, tmp_path
):
    """Each parallel pipeline gets its own TelemetryContext so llm_usage
    events attribute back to the right (gen, island) pair. Verified
    indirectly via the per-candidate stage4_routine audit events, which
    carry the candidate_id assigned by the per-pipeline insert."""
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(audit_path)
    _stub_cascade_passing(monkeypatch)
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit,
        hp=_hp(
            num_islands=4, candidates_per_generation=4,
            milestone_min_generation=10_000,
        ),
    )
    orch._bootstrap_islands()
    events = orch.step(generation=1)
    candidate_ids = {e.candidate_id for e in events}
    stage4_events = [
        e for e in audit.read_all() if e.trigger == "stage4_routine"
    ]
    # One stage4_routine event per candidate in the batch.
    assert len(stage4_events) == 4
    audit_candidate_ids = {e.payload["candidate_id"] for e in stage4_events}
    assert audit_candidate_ids == candidate_ids
