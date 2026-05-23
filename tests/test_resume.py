"""Sprint 4 Fix 3: DB-derived resume semantics.

Tests cover:
  - Resume picks up at the correct generation (regression for the
    pre-Sprint-4 bug where resumed runs restarted the loop from gen 1
    and double-counted generations from the perspective of reset cadence
    and milestone gates).
  - Bootstrap is no-op when candidates exist for the run.
  - check_resume_compatibility() returns the right blocking / warning
    splits for various drift scenarios.
  - resume_run() raises ResumeIncompatibleError on parent_goal_version
    mismatch.
  - resume_run() surfaces soft warnings via the on_warning callback.
  - DB helpers (`latest_generation_in_run`, `incomplete_runs`) work
    against representative DB states.
  - The CLI's incomplete-run detection prompt path (mocked via Click's
    CliRunner).

No live LLM calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.parent_goal import PARENT_GOAL_VERSION
from alphamo.context.verifier import VERIFIER_VERSION
from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.exemplar_library import TRIVIAL_SEED
from alphamo.meta.audit_log import AuditLog
from alphamo.orchestrator import (
    Orchestrator,
    ResumeIncompatibleError,
    check_resume_compatibility,
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


def _stub_client() -> MagicMock:
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


def _bridge_provider_factory_to_anthropic_stub(monkeypatch):
    """Sprint 14 bridge: after `monkeypatch.setattr('anthropic.Anthropic', _StubClient)`,
    also rebind the orchestrator's `build_provider` so the new
    factory-driven CLI path lands on the same stub.

    The CLI was changed in Sprint 14 to pass `client=None` to the
    orchestrator, which then calls `build_provider(hp.provider_*)` per
    component. Without this bridge, the factory tries to read
    FIREWORKS_API_KEY and bails before any stubbed call lands.
    """
    from alphamo import orchestrator as _orch_mod
    from alphamo.providers import AnthropicProvider
    import anthropic as _anthropic

    monkeypatch.setattr(
        _orch_mod,
        "build_provider",
        lambda name, **kw: AnthropicProvider(_anthropic.Anthropic()),
    )


def _hp(**kwargs) -> Hyperparameters:
    defaults = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
        candidates_per_generation=1,
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


def _make_orchestrator(db, monkeypatch, tmp_path, hp=None):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    return Orchestrator.for_new_run(db, _stub_client(), audit, hp=hp or _hp())


# ---------------------------------------------------------------- DB helpers


def test_latest_generation_in_run_returns_minus_one_for_empty_run(db, default_run):
    assert db.latest_generation_in_run(default_run) == -1


def test_latest_generation_in_run_returns_max_alive_generation(db, default_run):
    """Max(generation) across alive rows. Reset-status rows excluded."""
    arch = Architecture(
        name="g", summary="s", value_chain="v", capture_mechanism="c",
        entry_resources="r",
    )
    scores = Scores(
        feasibility=0.5, structural=0.5, middle_class_accessible=True,
    )
    db.insert(arch, scores, run_id=default_run, island_id=0, generation=0)
    db.insert(arch, scores, run_id=default_run, island_id=0, generation=5)
    db.insert(arch, scores, run_id=default_run, island_id=1, generation=12)
    assert db.latest_generation_in_run(default_run) == 12


def test_incomplete_runs_returns_runs_with_no_completed_at(db):
    """incomplete_runs lists runs where completed_at IS NULL — the
    candidates for resume detection."""
    rid_complete = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    rid_in_progress = db.create_run(
        hyperparameters={}, parent_goal_version="t", verifier_version="t"
    )
    db.complete_run(rid_complete, "max_generations")

    incomplete = db.incomplete_runs()
    incomplete_ids = {r.run_id for r in incomplete}
    assert rid_in_progress in incomplete_ids
    assert rid_complete not in incomplete_ids


# ---------------------------------------------------------------- check_resume_compatibility


def _fake_run(parent_goal_version="v2", verifier_version="v1", hp=None):
    """Build a Run-shaped object the compatibility check can read.

    We use a plain object (not the SQLAlchemy Run) because the check
    only reads attributes — no DB session required."""
    run = MagicMock()
    run.parent_goal_version = parent_goal_version
    run.verifier_version = verifier_version
    run.hyperparameters = hp if hp is not None else {}
    return run


def test_compat_check_clean_when_versions_match():
    run = _fake_run(
        parent_goal_version="v2",
        verifier_version=VERIFIER_VERSION,
        hp=Hyperparameters().model_dump(),
    )
    blocking, warnings = check_resume_compatibility(
        run,
        current_parent_goal_version="v2",
        current_verifier_version=VERIFIER_VERSION,
        current_default_hp=Hyperparameters(),
    )
    assert blocking == []
    assert warnings == []


def test_compat_check_hard_blocks_on_parent_goal_version_mismatch():
    run = _fake_run(parent_goal_version="v1")
    blocking, _ = check_resume_compatibility(
        run,
        current_parent_goal_version="v2",
        current_verifier_version=VERIFIER_VERSION,
        current_default_hp=Hyperparameters(),
    )
    assert len(blocking) == 1
    assert "PARENT_GOAL_VERSION mismatch" in blocking[0]


def test_compat_check_hard_blocks_on_num_islands_when_override_disagrees():
    """Structural HP block fires only when an override_hp is supplied
    that disagrees with persisted. Without override_hp, the persisted
    value is what gets used; structural block is a no-op."""
    run = _fake_run(hp={"num_islands": 8})
    override = Hyperparameters(num_islands=4)
    blocking, _ = check_resume_compatibility(
        run,
        current_parent_goal_version="v2",
        current_verifier_version=VERIFIER_VERSION,
        current_default_hp=Hyperparameters(),
        override_hp=override,
    )
    assert any("num_islands" in b for b in blocking)


def test_compat_check_hard_blocks_on_cluster_signature_resolution_override():
    """Same structural pattern, different field."""
    run = _fake_run(hp={"cluster_signature_resolution": 1})
    override = Hyperparameters(cluster_signature_resolution=2)
    blocking, _ = check_resume_compatibility(
        run,
        current_parent_goal_version="v2",
        current_verifier_version=VERIFIER_VERSION,
        current_default_hp=Hyperparameters(),
        override_hp=override,
    )
    assert any("cluster_signature_resolution" in b for b in blocking)


def test_compat_check_soft_warns_on_verifier_version_drift():
    run = _fake_run(verifier_version="v0_legacy")
    _, warnings = check_resume_compatibility(
        run,
        current_parent_goal_version="v2",
        current_verifier_version=VERIFIER_VERSION,
        current_default_hp=Hyperparameters(),
    )
    assert any("VERIFIER_VERSION differs" in w for w in warnings)


def test_compat_check_soft_warns_on_non_default_hp_difference():
    """If the persisted run was built with non-default HP, surface that
    fact as a soft warning so the user sees what they're inheriting."""
    run = _fake_run(hp={"milestone_min_generation": 5})
    _, warnings = check_resume_compatibility(
        run,
        current_parent_goal_version="v2",
        current_verifier_version=VERIFIER_VERSION,
        current_default_hp=Hyperparameters(),
    )
    assert any("milestone_min_generation" in w for w in warnings)


# ---------------------------------------------------------------- resume_run wiring


def test_resume_run_raises_resume_incompatible_on_parent_goal_drift(
    db, monkeypatch, tmp_path
):
    """If the persisted run's parent_goal_version disagrees with the
    current code's PARENT_GOAL_VERSION, resume_run refuses."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version="ancient_v0",
        verifier_version="v1",
    )
    with pytest.raises(ResumeIncompatibleError) as exc_info:
        Orchestrator.resume_run(db, _stub_client(), audit, rid)
    assert "PARENT_GOAL_VERSION" in str(exc_info.value)


def test_resume_run_passes_soft_warnings_to_on_warning_callback(
    db, monkeypatch, tmp_path
):
    """Soft warnings flow through the on_warning callable so callers
    (CLI / tests) can route them appropriately."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    rid = db.create_run(
        hyperparameters=_hp(milestone_min_generation=5).model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    captured: list[str] = []
    Orchestrator.resume_run(
        db, _stub_client(), audit, rid, on_warning=captured.append
    )
    assert captured, "expected at least one soft warning routed to callback"
    assert any("milestone_min_generation" in w for w in captured)


# ---------------------------------------------------------------- run() resume semantics


def test_run_picks_up_from_last_completed_generation(
    db, monkeypatch, tmp_path
):
    """Regression for the pre-Sprint-4 bug: a run that completed
    generations 1..N must resume at N+1, not at 1.

    Simulates a partially-complete run by inserting candidates at
    generations 0..5 directly, then calling .run() and verifying the
    for-loop steps from 6 onward."""
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    # Insert gen-0 bootstrap rows.
    for island_id in (0, 1):
        db.insert(
            TRIVIAL_SEED,
            Scores(
                feasibility=0.6, structural=0.2, robustness=0.3,
                middle_class_accessible=True,
            ),
            run_id=orch.run_id, island_id=island_id, generation=0,
        )
    # Insert gen 1..5 evolved candidates.
    for g in range(1, 6):
        db.insert(
            Architecture(
                name=f"existing-gen-{g}", summary="s", value_chain="v",
                capture_mechanism="c", entry_resources="r",
            ),
            Scores(
                feasibility=0.6, structural=0.6, robustness=0.6,
                middle_class_accessible=True,
            ),
            run_id=orch.run_id, island_id=g % 2, generation=g,
        )

    result = orch.run(max_generations=8)

    # Steps run for generations 6, 7, 8 only — three iterations.
    assert len(result.events) == 3
    assert [e.generation for e in result.events] == [6, 7, 8]


def test_run_resume_at_max_generations_exits_cleanly(
    db, monkeypatch, tmp_path
):
    """If the persisted run already completed >= max_generations, the
    new run() invocation runs zero steps and marks the run complete."""
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    # Insert a row at gen 25 directly.
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=orch.run_id, island_id=0, generation=25,
    )
    result = orch.run(max_generations=25)
    assert result.events == []
    assert result.stopped_reason == "max_generations"


def test_run_bootstrap_is_noop_when_candidates_exist(db, monkeypatch, tmp_path):
    """Resume path: bootstrap must NOT re-insert trivial-seed rows when
    candidates already exist for the run."""
    orch = _make_orchestrator(db, monkeypatch, tmp_path)
    # Mark the run as already-bootstrapped by inserting a gen-0 row.
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=orch.run_id, island_id=0, generation=0,
    )
    before = db.count_candidates_in_run(orch.run_id)
    inserted = orch._bootstrap_islands()
    assert inserted == 0
    assert db.count_candidates_in_run(orch.run_id) == before


def test_run_reset_cadence_correct_after_resume(db, monkeypatch, tmp_path):
    """The pre-Sprint-4 bug: a resumed run that restarted the loop from
    gen 1 would fire reset cadence at the wrong absolute-generation
    boundaries. Verify that after resume, reset uses the actual
    generation number for cadence calculation."""
    # Cadence 5 so reset would fire at gens 5, 10, 15...
    hp = _hp(num_islands=2, reset_every_generations=5)
    orch = _make_orchestrator(db, monkeypatch, tmp_path, hp=hp)

    # Pre-populate gens 0..3 so the next run starts at gen 4. The first
    # reset should fire at gen 5 (one iteration into the resumed run).
    for island_id in (0, 1):
        for g in (0, 1, 2, 3):
            db.insert(
                Architecture(
                    name=f"existing-{island_id}-{g}", summary="s",
                    value_chain="v", capture_mechanism="c",
                    entry_resources="r",
                ),
                Scores(
                    feasibility=0.6, structural=0.6, robustness=0.6,
                    middle_class_accessible=True,
                ),
                run_id=orch.run_id, island_id=island_id, generation=g,
            )

    result = orch.run(max_generations=6)
    # Reset fires at gen 5 (cadence 5, post-resume start at gen 4).
    reset_events = [e for e in result.events if e.reset_event is not None]
    assert len(reset_events) == 1
    assert reset_events[0].generation == 5


# ---------------------------------------------------------------- CLI


def _runner_invoke(args: list[str], input_text: str | None = None):
    """Invoke the alphamo CLI within an isolated filesystem."""
    from alphamo.main import cli

    runner = CliRunner()
    return runner.invoke(cli, args, input=input_text)


def test_cli_run_rejects_both_resume_and_no_resume(tmp_path):
    result = _runner_invoke(
        [
            "run",
            "--generations", "1",
            "--db", str(tmp_path / "x.db"),
            "--audit", str(tmp_path / "a.jsonl"),
            "--resume", "some_id",
            "--no-resume",
        ]
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_cli_run_detects_in_progress_run_and_prompts(tmp_path, monkeypatch):
    """When neither --resume nor --no-resume is set, an in-progress
    run triggers a confirmation prompt; default response is N (fresh)."""
    from alphamo.database.operations import ProgramsDB

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"

    # Seed an in-progress run in the DB.
    db = ProgramsDB(f"sqlite:///{db_path}")
    incomplete_rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=incomplete_rid, island_id=0, generation=0,
    )

    # Mock anthropic client so the CLI doesn't try to actually call the API.
    import alphamo.main as main_module

    captured_run_id: dict[str, str] = {}
    real_for_new_run = orch_mod.Orchestrator.for_new_run
    real_resume_run = orch_mod.Orchestrator.resume_run

    def fake_for_new_run(*a, **kw):
        orch = real_for_new_run(*a, **kw)
        captured_run_id["used"] = orch.run_id
        captured_run_id["mode"] = "fresh"
        return orch

    def fake_resume_run(*a, **kw):
        orch = real_resume_run(*a, **kw)
        captured_run_id["used"] = orch.run_id
        captured_run_id["mode"] = "resume"
        return orch

    monkeypatch.setattr(
        orch_mod.Orchestrator, "for_new_run", classmethod(lambda cls, *a, **kw: fake_for_new_run(*a, **kw))
    )
    monkeypatch.setattr(
        orch_mod.Orchestrator, "resume_run", classmethod(lambda cls, *a, **kw: fake_resume_run(*a, **kw))
    )

    # Also stub the cascade + research so the run loop doesn't make API calls.
    _stub_cascade(monkeypatch)
    # Mock the anthropic client construction to return a stub.
    class _StubClient:
        def __init__(self, *a, **kw):
            self.messages = MagicMock()
            self.messages.parse.side_effect = _stub_client().messages.parse.side_effect

    monkeypatch.setattr("anthropic.Anthropic", _StubClient)
    _bridge_provider_factory_to_anthropic_stub(monkeypatch)

    # Run with no flags; respond 'n' to the prompt → fresh start.
    result = _runner_invoke(
        [
            "run",
            "--generations", "1",
            "--db", str(db_path),
            "--audit", str(audit_path),
        ],
        input_text="n\n",
    )
    assert result.exit_code == 0, result.output
    assert "Incomplete (crashed) run detected" in result.output
    assert captured_run_id.get("mode") == "fresh"
    # Fresh run produced a different run_id from the existing incomplete one.
    assert captured_run_id["used"] != incomplete_rid


def test_cli_run_explicit_no_resume_flag_skips_prompt(tmp_path, monkeypatch):
    """--no-resume forces fresh, no prompt even with an in-progress run."""
    from alphamo.database.operations import ProgramsDB

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"

    db = ProgramsDB(f"sqlite:///{db_path}")
    incomplete_rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )

    _stub_cascade(monkeypatch)
    class _StubClient:
        def __init__(self, *a, **kw):
            self.messages = MagicMock()
            self.messages.parse.side_effect = _stub_client().messages.parse.side_effect

    monkeypatch.setattr("anthropic.Anthropic", _StubClient)
    _bridge_provider_factory_to_anthropic_stub(monkeypatch)

    result = _runner_invoke(
        [
            "run",
            "--generations", "1",
            "--db", str(db_path),
            "--audit", str(audit_path),
            "--no-resume",
        ]
    )
    assert result.exit_code == 0, result.output
    # No prompt at all — the "Resume?" text never appears.
    assert "Resume?" not in result.output


def test_cli_run_resume_flag_skips_prompt_when_compatible(tmp_path, monkeypatch):
    """Explicit --resume <id> skips the prompt and resumes the named run."""
    from alphamo.database.operations import ProgramsDB

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"

    db = ProgramsDB(f"sqlite:///{db_path}")
    rid = db.create_run(
        hyperparameters=_hp().model_dump(),  # num_islands=2
        parent_goal_version=PARENT_GOAL_VERSION,
        verifier_version=VERIFIER_VERSION,
    )
    # Seed both islands so the sampler always finds a candidate to draw,
    # regardless of which island the rng picks for the resumed iteration.
    for island_id in (0, 1):
        db.insert(
            TRIVIAL_SEED,
            Scores(
                feasibility=0.6, structural=0.2, robustness=0.3,
                middle_class_accessible=True,
            ),
            run_id=rid, island_id=island_id, generation=0,
        )

    _stub_cascade(monkeypatch)
    class _StubClient:
        def __init__(self, *a, **kw):
            self.messages = MagicMock()
            self.messages.parse.side_effect = _stub_client().messages.parse.side_effect

    monkeypatch.setattr("anthropic.Anthropic", _StubClient)
    _bridge_provider_factory_to_anthropic_stub(monkeypatch)

    result = _runner_invoke(
        [
            "run",
            "--generations", "1",
            "--db", str(db_path),
            "--audit", str(audit_path),
            "--resume", rid,
        ]
    )
    assert result.exit_code == 0, result.output
    assert "Resume?" not in result.output
    assert f"resuming run {rid}" in result.output


def test_cli_run_resume_surfaces_incompatibility_error_clearly(tmp_path, monkeypatch):
    """An incompatible explicit --resume surfaces a ClickException with
    a clear "start fresh with --no-resume" hint."""
    from alphamo.database.operations import ProgramsDB

    db_path = tmp_path / "x.db"
    audit_path = tmp_path / "a.jsonl"

    db = ProgramsDB(f"sqlite:///{db_path}")
    rid = db.create_run(
        hyperparameters=_hp().model_dump(),
        parent_goal_version="ancient_v0",
        verifier_version="v1",
    )

    _stub_cascade(monkeypatch)
    class _StubClient:
        def __init__(self, *a, **kw):
            self.messages = MagicMock()

    monkeypatch.setattr("anthropic.Anthropic", _StubClient)
    _bridge_provider_factory_to_anthropic_stub(monkeypatch)

    result = _runner_invoke(
        [
            "run",
            "--generations", "1",
            "--db", str(db_path),
            "--audit", str(audit_path),
            "--resume", rid,
        ]
    )
    assert result.exit_code != 0
    assert "PARENT_GOAL_VERSION" in result.output
    assert "--no-resume" in result.output
