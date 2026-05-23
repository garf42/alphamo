"""Sprint 5: pause-and-continue extension to the resume mechanism.

Tests cover:
  - Resume after max_generations stop, run more generations successfully.
  - target_generation must exceed current latest generation
    (CLI errors if not).
  - Reset cadence remains correct across pause boundaries
    (cadence=5, stop at 30, resume to 60 → reset at 30, 35, 40, 45, 50,
    55, 60 — absolute generation numbers, not restart-relative).
  - Multiple pause-resume cycles preserve state (run to 10, resume to
    20, resume to 30).
  - Resume blocks on PARENT_GOAL_VERSION change (Sprint 4 regression
    guard — extension path must not bypass compatibility check).
  - CLI auto-detect shows extend-or-fresh prompt for completed runs.
  - --target-generation requires --resume (no orphan use).
  - --force-resume requires --resume.
  - Resume blocks on consecutive_failures / curator_pause unless
    --force-resume.
  - Resume of crashed run unchanged (Sprint 4 regression).

No live LLM calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.parent_goal import PARENT_GOAL_VERSION
from alphamo.context.verifier import VERIFIER_VERSION
from alphamo.database.operations import ProgramsDB
from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.exemplar_library import TRIVIAL_SEED
from alphamo.meta.audit_log import AuditLog
from alphamo.orchestrator import (
    Orchestrator,
    ResumeIncompatibleError,
)
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
)
from tests.fixtures.parsed_message import FakeParsedMessage
from tests.fixtures.stage2_evidence import failing_stage2_finding, passing_stage2_finding
from tests.fixtures.stage1_evidence import failing_stage1_finding, passing_stage1_finding


# ---------------------------------------------------------------- helpers


def _stub_cascade(monkeypatch):
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: passing_stage1_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85, concerns=[], reasoning="stub",
        ),
    )


def _make_stub_client_factory():
    """Each call to the factory returns a fresh client with an isolated
    architecture counter, so multiple orchestrator runs in one test don't
    interfere."""

    def make() -> MagicMock:
        client = MagicMock()
        counter = {"n": 0}

        def parse_side_effect(**kwargs):
            output_format = kwargs.get("output_format")
            if output_format is Architecture:
                counter["n"] += 1
                return FakeParsedMessage(
                    Architecture(
                        name=f"gen-{counter['n']:03d}",
                        summary="s", value_chain="vc",
                        capture_mechanism="cm", entry_resources="er",
                    )
                )
            if output_format is ClassificationVerdict:
                return FakeParsedMessage(
                    ClassificationVerdict(
                        classification=Classification.COSMETIC, rationale="x"
                    )
                )
            return FakeParsedMessage(MagicMock())

        client.messages.parse.side_effect = parse_side_effect
        return client

    return make


def _hp(**kwargs) -> Hyperparameters:
    defaults = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


# ---------------------------------------------------------------- DB helpers


def test_extendable_runs_lists_only_max_generations_stops(db):
    """extendable_runs returns only runs stopped via max_generations.
    consecutive_failures and curator_pause stops are excluded
    (they need --force-resume; not auto-detected for extension)."""
    rid_max = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    rid_cf = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    rid_cp = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    rid_in_progress = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    db.complete_run(rid_max, "max_generations")
    db.complete_run(rid_cf, "consecutive_failures")
    db.complete_run(rid_cp, "curator_pause")

    extendable_ids = {r.run_id for r in db.extendable_runs()}
    assert rid_max in extendable_ids
    assert rid_cf not in extendable_ids
    assert rid_cp not in extendable_ids
    assert rid_in_progress not in extendable_ids


def test_uncomplete_run_clears_completion_markers(db):
    rid = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    db.complete_run(rid, "max_generations")
    run_before = db.get_run(rid)
    assert run_before.completed_at is not None
    assert run_before.stopped_reason == "max_generations"

    db.uncomplete_run(rid)
    run_after = db.get_run(rid)
    assert run_after.completed_at is None
    assert run_after.stopped_reason is None


def test_uncomplete_run_raises_on_missing_run(db):
    with pytest.raises(KeyError):
        db.uncomplete_run("run_does_not_exist")


# ---------------------------------------------------------------- resume_run extension semantics


def test_resume_run_extends_max_generations_completed_run(
    db, monkeypatch, tmp_path
):
    """A run that stopped via max_generations can be resumed and extended.
    resume_run clears the completion markers so the next run() call can
    re-stamp them on the new termination."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()

    # Phase 1: fresh run to gen 3.
    orch_a = Orchestrator.for_new_run(
        db, make_client(), audit, hp=_hp(num_islands=2)
    )
    result_a = orch_a.run(max_generations=3)
    assert result_a.stopped_reason == "max_generations"
    assert db.get_run(orch_a.run_id).completed_at is not None

    # Phase 2: resume to extend.
    orch_b = Orchestrator.resume_run(db, make_client(), audit, orch_a.run_id)
    # completion markers cleared by resume_run.
    run_mid = db.get_run(orch_a.run_id)
    assert run_mid.completed_at is None
    assert run_mid.stopped_reason is None
    assert run_mid.last_resumed_at is not None

    # Run the extension. With latest_generation_in_run==3 and target==6,
    # the for-loop runs gens 4, 5, 6 — three iterations.
    result_b = orch_b.run(max_generations=6)
    assert len(result_b.events) == 3
    assert [e.generation for e in result_b.events] == [4, 5, 6]
    # Re-stamped after the extension's max_generations stop.
    assert db.get_run(orch_a.run_id).completed_at is not None
    assert db.get_run(orch_a.run_id).stopped_reason == "max_generations"


def test_multiple_pause_resume_cycles_preserve_state(db, monkeypatch, tmp_path):
    """Three cycles: run to 3, extend to 6, extend to 9. Each cycle
    picks up at last_completed+1 and stops cleanly at its target."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()

    orch_a = Orchestrator.for_new_run(
        db, make_client(), audit, hp=_hp(num_islands=2)
    )
    orch_a.run(max_generations=3)
    run_id = orch_a.run_id

    orch_b = Orchestrator.resume_run(db, make_client(), audit, run_id)
    result_b = orch_b.run(max_generations=6)
    assert [e.generation for e in result_b.events] == [4, 5, 6]

    orch_c = Orchestrator.resume_run(db, make_client(), audit, run_id)
    result_c = orch_c.run(max_generations=9)
    assert [e.generation for e in result_c.events] == [7, 8, 9]

    # All candidates from all three cycles are in the DB for the one run_id.
    final_max = db.latest_generation_in_run(run_id)
    assert final_max == 9


def test_reset_cadence_correct_across_pause_boundaries(db, monkeypatch, tmp_path):
    """Reset cadence uses absolute generation numbers, not restart-relative.

    Cadence=5: resets should fire at gen 5, 10, 15... regardless of where
    in the sequence the run was paused. This test runs to gen 7 (one reset
    at gen 5), then resumes to gen 12 (one more reset at gen 10).
    """
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()
    hp = _hp(num_islands=2, reset_every_generations=5)

    orch_a = Orchestrator.for_new_run(db, make_client(), audit, hp=hp)
    result_a = orch_a.run(max_generations=7)
    reset_gens_a = [e.generation for e in result_a.events if e.reset_event is not None]
    assert reset_gens_a == [5], (
        f"first phase: expected reset at gen 5, got {reset_gens_a}"
    )

    orch_b = Orchestrator.resume_run(db, make_client(), audit, orch_a.run_id)
    result_b = orch_b.run(max_generations=12)
    reset_gens_b = [e.generation for e in result_b.events if e.reset_event is not None]
    # First reset post-resume should fire at gen 10 — absolute generation,
    # not "gen 8 + 5" = 13 (which would be the bug if cadence reset on
    # resume boundary).
    assert reset_gens_b == [10], (
        f"resume phase: expected reset at gen 10, got {reset_gens_b}"
    )


def test_resume_blocks_on_parent_goal_version_change_for_extension(
    db, monkeypatch, tmp_path
):
    """Regression of Sprint 4 behavior — the extension path must not
    bypass the compatibility check."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()

    rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version="ancient_v0",
        verifier_version="v1",
    )
    db.complete_run(rid, "max_generations")
    # Seed a candidate so the run is non-empty (latest_generation_in_run > -1).
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=rid, island_id=0, generation=3,
    )

    with pytest.raises(ResumeIncompatibleError) as exc_info:
        Orchestrator.resume_run(db, make_client(), audit, rid)
    assert "PARENT_GOAL_VERSION" in str(exc_info.value)
    # Run row's completion markers must NOT have been cleared on failure
    # — the failure happens before uncomplete_run runs.
    assert db.get_run(rid).completed_at is not None


# ---------------------------------------------------------------- stopped_reason gating


def test_resume_blocks_on_consecutive_failures_without_force(
    db, monkeypatch, tmp_path
):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()

    rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    db.complete_run(rid, "consecutive_failures")

    with pytest.raises(ResumeIncompatibleError) as exc_info:
        Orchestrator.resume_run(db, make_client(), audit, rid)
    assert "consecutive_failures" in str(exc_info.value)
    assert "force-resume" in str(exc_info.value)


def test_resume_blocks_on_curator_pause_without_force(db, monkeypatch, tmp_path):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()

    rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    db.complete_run(rid, "curator_pause")

    with pytest.raises(ResumeIncompatibleError) as exc_info:
        Orchestrator.resume_run(db, make_client(), audit, rid)
    assert "curator_pause" in str(exc_info.value)


def test_resume_with_force_proceeds_on_blocked_stopped_reason(
    db, monkeypatch, tmp_path
):
    """--force-resume overrides the stopped_reason block."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    make_client = _make_stub_client_factory()

    rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    db.complete_run(rid, "curator_pause")
    # Seed a row so latest_generation_in_run > -1.
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=rid, island_id=0, generation=2,
    )

    orch = Orchestrator.resume_run(
        db, make_client(), audit, rid, force=True
    )
    # Run row's completion markers cleared.
    assert db.get_run(rid).completed_at is None
    assert db.get_run(rid).stopped_reason is None
    assert orch.run_id == rid


# ---------------------------------------------------------------- CLI


def _runner_invoke(args: list[str], input_text: str | None = None):
    from alphamo.main import cli

    runner = CliRunner()
    return runner.invoke(cli, args, input=input_text)


def _stub_anthropic(monkeypatch):
    _stub_cascade(monkeypatch)
    class _StubClient:
        def __init__(self, *a, **kw):
            client = MagicMock()
            counter = {"n": 0}

            def parse_side_effect(**kwargs):
                output_format = kwargs.get("output_format")
                if output_format is Architecture:
                    counter["n"] += 1
                    return FakeParsedMessage(
                        Architecture(
                            name=f"gen-{counter['n']:03d}",
                            summary="s", value_chain="vc",
                            capture_mechanism="cm", entry_resources="er",
                        )
                    )
                if output_format is ClassificationVerdict:
                    return FakeParsedMessage(
                        ClassificationVerdict(
                            classification=Classification.COSMETIC, rationale="x"
                        )
                    )
                return FakeParsedMessage(MagicMock())

            client.messages.parse.side_effect = parse_side_effect
            self.messages = client.messages

    monkeypatch.setattr("anthropic.Anthropic", _StubClient)
    # Sprint 14: CLI no longer constructs `anthropic.Anthropic()`
    # directly — `client=None` is passed to the orchestrator, which
    # builds providers via the factory. Bridge the legacy stub: when
    # the orchestrator asks the factory for any provider, return an
    # AnthropicProvider wrapping a fresh `anthropic.Anthropic()` —
    # which the line above just stubbed to `_StubClient`. Net effect:
    # `provider.parse(...)` ends up calling `_StubClient().messages.parse(...)`,
    # exactly as before the migration.
    from alphamo import orchestrator as _orch_mod
    from alphamo.providers import AnthropicProvider
    import anthropic as _anthropic
    monkeypatch.setattr(
        _orch_mod,
        "build_provider",
        lambda name, **kw: AnthropicProvider(_anthropic.Anthropic()),
    )


def test_cli_target_generation_requires_resume(tmp_path):
    result = _runner_invoke(
        [
            "run",
            "--generations", "10",
            "--db", str(tmp_path / "x.db"),
            "--audit", str(tmp_path / "a.jsonl"),
            "--target-generation", "20",
        ]
    )
    assert result.exit_code != 0
    assert "--target-generation requires --resume" in result.output


def test_cli_force_resume_requires_resume(tmp_path):
    result = _runner_invoke(
        [
            "run",
            "--generations", "10",
            "--db", str(tmp_path / "x.db"),
            "--audit", str(tmp_path / "a.jsonl"),
            "--force-resume",
        ]
    )
    assert result.exit_code != 0
    assert "--force-resume requires --resume" in result.output


def test_cli_target_generation_must_exceed_current_max(tmp_path, monkeypatch):
    """--target-generation <= latest_generation_in_run is rejected by the
    CLI with a clear error (rather than silently exiting with zero
    iterations)."""
    _stub_anthropic(monkeypatch)

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"
    db = ProgramsDB(f"sqlite:///{db_path}")
    rid = db.create_run(
        hyperparameters=_hp(num_islands=2).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    for island_id in (0, 1):
        db.insert(
            TRIVIAL_SEED,
            Scores(
                feasibility=0.6, structural=0.2, robustness=0.3,
                middle_class_accessible=True,
            ),
            run_id=rid, island_id=island_id, generation=5,
        )
    db.complete_run(rid, "max_generations")

    # latest_generation_in_run == 5; ask for target=5 (not >) → error.
    result = _runner_invoke(
        [
            "run",
            "--db", str(db_path),
            "--audit", str(audit_path),
            "--resume", rid,
            "--target-generation", "5",
        ]
    )
    assert result.exit_code != 0
    assert "strictly greater" in result.output
    assert "latest=5" in result.output
    assert "requested=5" in result.output


def test_cli_extends_completed_run_via_target_generation(tmp_path, monkeypatch):
    """End-to-end: completed run + --resume + --target-generation N
    continues from latest+1 through N inclusive."""
    _stub_anthropic(monkeypatch)

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"
    db = ProgramsDB(f"sqlite:///{db_path}")
    rid = db.create_run(
        hyperparameters=_hp(num_islands=2).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    for island_id in (0, 1):
        db.insert(
            TRIVIAL_SEED,
            Scores(
                feasibility=0.6, structural=0.2, robustness=0.3,
                middle_class_accessible=True,
            ),
            run_id=rid, island_id=island_id, generation=3,
        )
    db.complete_run(rid, "max_generations")
    starting_count = db.count_candidates_in_run(rid)

    result = _runner_invoke(
        [
            "run",
            "--db", str(db_path),
            "--audit", str(audit_path),
            "--resume", rid,
            "--target-generation", "5",
        ]
    )
    assert result.exit_code == 0, result.output
    # Extension ran gens 4 and 5 — two new candidates added.
    assert db.count_candidates_in_run(rid) == starting_count + 2
    assert db.latest_generation_in_run(rid) == 5
    assert f"resuming run {rid} from generation 4 through 5" in result.output


def test_cli_auto_detect_shows_extend_prompt_for_completed_run(tmp_path, monkeypatch):
    """When a completed run exists and --generations > its current max,
    the CLI prompts the user to extend or start fresh."""
    _stub_anthropic(monkeypatch)

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"
    db = ProgramsDB(f"sqlite:///{db_path}")
    rid = db.create_run(
        hyperparameters=_hp(num_islands=2).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    for island_id in (0, 1):
        db.insert(
            TRIVIAL_SEED,
            Scores(
                feasibility=0.6, structural=0.2, robustness=0.3,
                middle_class_accessible=True,
            ),
            run_id=rid, island_id=island_id, generation=2,
        )
    db.complete_run(rid, "max_generations")

    # --generations 5 > current max (2) so extend prompt fires. User declines.
    result = _runner_invoke(
        [
            "run",
            "--generations", "5",
            "--db", str(db_path),
            "--audit", str(audit_path),
        ],
        input_text="n\n",
    )
    assert result.exit_code == 0, result.output
    assert "Extendable completed run detected" in result.output
    assert "Extend completed run?" in result.output
    # User declined → fresh run started (new run_id appears, original
    # completed run is unchanged).
    assert "started run " in result.output


def test_cli_auto_detect_does_not_offer_extend_when_target_already_reached(
    tmp_path, monkeypatch
):
    """If --generations is <= the completed run's current max, no extend
    prompt fires (the extension wouldn't extend)."""
    _stub_anthropic(monkeypatch)

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"
    db = ProgramsDB(f"sqlite:///{db_path}")
    rid = db.create_run(
        hyperparameters=_hp(num_islands=2).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    for island_id in (0, 1):
        db.insert(
            TRIVIAL_SEED,
            Scores(
                feasibility=0.6, structural=0.2, robustness=0.3,
                middle_class_accessible=True,
            ),
            run_id=rid, island_id=island_id, generation=10,
        )
    db.complete_run(rid, "max_generations")

    # --generations 10 == current max → no extension would occur.
    result = _runner_invoke(
        [
            "run",
            "--generations", "10",
            "--db", str(db_path),
            "--audit", str(audit_path),
        ]
    )
    assert result.exit_code == 0, result.output
    assert "Extendable completed run detected" not in result.output
    assert "Extend completed run?" not in result.output


def test_cli_crashed_run_still_takes_precedence_in_prompt(tmp_path, monkeypatch):
    """When both an incomplete (crashed) and an extendable (completed)
    run exist, the crashed run is offered first."""
    _stub_anthropic(monkeypatch)

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"
    db = ProgramsDB(f"sqlite:///{db_path}")
    # Completed run first (older).
    rid_completed = db.create_run(
        hyperparameters=_hp(num_islands=2).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    db.complete_run(rid_completed, "max_generations")
    # Crashed run second (more recent).
    rid_crashed = db.create_run(
        hyperparameters=_hp(num_islands=2).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=rid_crashed, island_id=0, generation=2,
    )

    # Decline both prompts; verify the crashed one was offered first.
    result = _runner_invoke(
        [
            "run",
            "--generations", "20",
            "--db", str(db_path),
            "--audit", str(audit_path),
        ],
        input_text="n\nn\n",
    )
    assert result.exit_code == 0, result.output
    crashed_idx = result.output.find("Incomplete (crashed) run detected")
    completed_idx = result.output.find("Extendable completed run detected")
    assert crashed_idx != -1
    assert completed_idx != -1
    assert crashed_idx < completed_idx
