"""Tests for run boundaries: creation, isolation, resume, querying, migration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from alphamo.context.hyperparams import Hyperparameters
from alphamo.database import LEGACY_RUN_ID, ProgramsDB
from alphamo.evaluator import cascade as cascade_mod
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.orchestrator import Orchestrator
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
)
from tests.fixtures.exemplars import SATOSHI_FIXTURE
from tests.fixtures.parsed_message import FakeParsedMessage
from tests.fixtures.stage2_evidence import failing_stage2_finding, passing_stage2_finding
from tests.fixtures.stage1_evidence import failing_stage1_finding, passing_stage1_finding


# --------------------------------------------------------------------- helpers


def _stub_cascade(monkeypatch, fit=0.85):
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c, **kw: passing_stage1_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85, concerns=[], reasoning="stub stage4"
        ),
    )


def _stub_client(name: str = "variant") -> MagicMock:
    counter = {"n": 0}
    client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            counter["n"] += 1
            return FakeParsedMessage(
                Architecture(
                    name=f"{name}-{counter['n']}",
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


def _hp(**overrides) -> Hyperparameters:
    base = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,  # disables milestone trigger by default
    )
    base.update(overrides)
    return Hyperparameters(**base)


# --------------------------------------------------------------------- run ids


def test_create_run_returns_unique_ids(db):
    a = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    b = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    assert a != b
    assert a.startswith("run_")
    assert b.startswith("run_")


def test_get_run_returns_persisted_record(db):
    rid = db.create_run(
        hyperparameters={"k_seeds": 3, "sampling_temperature": 0.7},
        parent_goal_version="v1",
        verifier_version="v2",
        notes="hello",
    )
    run = db.get_run(rid)
    assert run.run_id == rid
    assert run.hyperparameters == {"k_seeds": 3, "sampling_temperature": 0.7}
    assert run.parent_goal_version == "v1"
    assert run.verifier_version == "v2"
    assert run.notes == "hello"
    assert run.completed_at is None
    assert run.stopped_reason is None


def test_get_run_missing_raises(db):
    with pytest.raises(KeyError):
        db.get_run("run_does_not_exist")


def test_complete_run_sets_stopped_reason(db):
    rid = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    db.complete_run(rid, "max_generations")
    run = db.get_run(rid)
    assert run.stopped_reason == "max_generations"
    assert run.completed_at is not None


def test_mark_run_resumed_sets_timestamp(db):
    rid = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    assert db.get_run(rid).last_resumed_at is None
    db.mark_run_resumed(rid)
    assert db.get_run(rid).last_resumed_at is not None


def test_list_runs_orders_by_created_at_desc(db):
    a = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    b = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    runs = db.list_runs()
    assert [r.run_id for r in runs[:2]] == [b, a]


def test_latest_run_id_returns_most_recent(db):
    assert db.latest_run_id() is None
    a = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    assert db.latest_run_id() == a
    b = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    assert db.latest_run_id() == b


# --------------------------------------------------------------------- insert / filter


def test_insert_requires_run_id(db):
    with pytest.raises(TypeError):
        db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores)


def test_insert_rejects_empty_run_id(db):
    with pytest.raises(ValueError):
        db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id="")


def test_two_runs_have_non_overlapping_candidate_sets(db):
    r1 = db.create_run(hyperparameters={"a": 1}, parent_goal_version="v1", verifier_version="v1")
    r2 = db.create_run(hyperparameters={"a": 2}, parent_goal_version="v1", verifier_version="v1")
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=r1, island_id=0)
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=r1, island_id=1)
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=r2, island_id=0)

    assert db.count_candidates_in_run(r1) == 2
    assert db.count_candidates_in_run(r2) == 1
    rows_r1 = db.top_k_in_island(island_id=0, k=10, run_id=r1)
    rows_r2 = db.top_k_in_island(island_id=0, k=10, run_id=r2)
    assert {r.id for r in rows_r1}.isdisjoint({r.id for r in rows_r2})


def test_read_paths_filter_by_run_id(db):
    r1 = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    r2 = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=r1, island_id=0, generation=1)
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=r2, island_id=0, generation=1)
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=r2, island_id=0, generation=2)

    assert len(db.top_programs_from_islands([0], n=10, run_id=r1)) == 1
    assert len(db.top_programs_from_islands([0], n=10, run_id=r2)) == 2
    assert db.mean_fitness_per_island(4, run_id=r1)[0] > 0
    assert db.mean_fitness_per_island(4, run_id=r1)[1] == 0
    assert db.fitness_history(5, run_id=r1) != db.fitness_history(5, run_id=r2)


# --------------------------------------------------------------------- orchestrator


def test_orchestrator_for_new_run_creates_run_row(db, tmp_path, monkeypatch):
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    hp = Hyperparameters(num_islands=2, milestone_min_generation=10_000)
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=hp)
    run = db.get_run(orch.run_id)
    assert run.hyperparameters["num_islands"] == 2
    assert run.parent_goal_version  # set from constant
    assert run.verifier_version  # set from constant


def test_two_orchestrator_runs_against_same_db_are_isolated(db, tmp_path, monkeypatch):
    """Run loop A then run loop B against the same DB; they don't share candidates."""
    _stub_cascade(monkeypatch)
    import alphamo.orchestrator as orch_mod
    audit = AuditLog(tmp_path / "audit.jsonl")

    orch_a = Orchestrator.for_new_run(db, _stub_client("a"), audit, hp=_hp())
    result_a = orch_a.run(max_generations=3)

    orch_b = Orchestrator.for_new_run(db, _stub_client("b"), audit, hp=_hp())
    result_b = orch_b.run(max_generations=3)

    assert orch_a.run_id != orch_b.run_id
    assert len(result_a.events) == 3 and len(result_b.events) == 3

    # Each run's generated candidates live under its own run_id; no overlap.
    a_count = db.count_candidates_in_run(orch_a.run_id)
    b_count = db.count_candidates_in_run(orch_b.run_id)
    assert a_count > 0 and b_count > 0
    a_ids = {r.id for r in db.top_programs_from_islands([0, 1], n=100, run_id=orch_a.run_id)}
    b_ids = {r.id for r in db.top_programs_from_islands([0, 1], n=100, run_id=orch_b.run_id)}
    assert a_ids.isdisjoint(b_ids)


def test_resume_run_marks_resumed_at_without_reseeding(db, tmp_path, monkeypatch):
    """Resume an existing run — alive candidates stay; resumed timestamp is set."""
    _stub_cascade(monkeypatch)
    import alphamo.orchestrator as orch_mod
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch_a = Orchestrator.for_new_run(db, _stub_client("a"), audit, hp=_hp())
    orch_a.run(max_generations=2)
    count_after_fresh = db.count_candidates_in_run(orch_a.run_id)
    assert count_after_fresh > 0

    Orchestrator.resume_run(db, _stub_client("a"), audit, orch_a.run_id)
    assert db.get_run(orch_a.run_id).last_resumed_at is not None
    # No reseeding behavior — count unchanged after the resume call alone.
    assert db.count_candidates_in_run(orch_a.run_id) == count_after_fresh


def test_resume_run_inherits_hyperparameters(db, tmp_path, monkeypatch):
    """HP from the original run must be queryable and used by the resumed orchestrator."""
    _stub_cascade(monkeypatch)
    audit = AuditLog(tmp_path / "audit.jsonl")
    hp = Hyperparameters(num_islands=3, k_seeds=4, sampling_temperature=0.5)
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=hp)
    run = db.get_run(orch.run_id)
    assert run.hyperparameters["k_seeds"] == 4
    assert run.hyperparameters["sampling_temperature"] == 0.5

    resumed = Orchestrator.resume_run(db, _stub_client(), audit, orch.run_id)
    assert resumed.hp.k_seeds == 4
    assert resumed.hp.sampling_temperature == 0.5


def test_resume_missing_run_raises(db, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(KeyError):
        Orchestrator.resume_run(db, MagicMock(), audit, "run_no_such_thing")


def test_orchestrator_completion_stamps_stopped_reason(db, tmp_path, monkeypatch):
    _stub_cascade(monkeypatch)
    import alphamo.orchestrator as orch_mod
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp())
    orch.run(max_generations=2)
    run = db.get_run(orch.run_id)
    assert run.stopped_reason == "max_generations"
    assert run.completed_at is not None


# --------------------------------------------------------------------- audit log


def test_audit_events_are_filterable_by_run_id(db, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    r1 = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    r2 = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    for rid in (r1, r1, r2):
        audit.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=rid,
                trigger="t",
                classification="cosmetic",
                action="continue",
                rationale=f"event for {rid}",
            )
        )
    all_events = audit.read_all()
    r1_events = [e for e in all_events if e.run_id == r1]
    r2_events = [e for e in all_events if e.run_id == r2]
    assert len(r1_events) == 2
    assert len(r2_events) == 1


def test_new_run_only_inspects_its_own_candidates(db, tmp_path, monkeypatch):
    """A new run created against a non-empty DB doesn't see other runs' candidates."""
    _stub_cascade(monkeypatch)
    import alphamo.orchestrator as orch_mod
    audit = AuditLog(tmp_path / "audit.jsonl")

    other = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    for island in range(4):
        db.insert(
            SATOSHI_FIXTURE.architecture,
            SATOSHI_FIXTURE.scores,
            run_id=other,
            island_id=island,
        )
    assert db.count_candidates(status="alive") == 4

    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp(num_islands=2))
    orch.run(max_generations=2)
    # New run produced its own candidates.
    assert db.count_candidates_in_run(orch.run_id) > 0
    # Other run untouched.
    assert db.count_candidates_in_run(other) == 4


# --------------------------------------------------------------------- migration


def test_legacy_candidates_get_backfilled(tmp_path):
    """A DB created before runs existed must auto-migrate on next ProgramsDB init."""
    url = f"sqlite:///{tmp_path / 'legacy.db'}"

    # Build a candidates table WITHOUT run_id, the way pre-phase code did.
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE candidates ("
                "id INTEGER PRIMARY KEY,"
                "architecture_spec JSON NOT NULL,"
                "scores JSON NOT NULL,"
                "fitness REAL NOT NULL,"
                "island_id INTEGER,"
                "generation INTEGER,"
                "parent_ids JSON,"
                "status TEXT,"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO candidates (architecture_spec, scores, fitness, island_id, status) "
                "VALUES ('{}', '{}', 0.5, 0, 'alive')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO candidates (architecture_spec, scores, fitness, island_id, status) "
                "VALUES ('{}', '{}', 0.3, 1, 'alive')"
            )
        )

    # Now open via ProgramsDB — should migrate.
    db = ProgramsDB(url)

    legacy = db.get_run(LEGACY_RUN_ID)
    assert legacy.parent_goal_version == "unknown"
    assert legacy.verifier_version == "unknown"
    assert legacy.stopped_reason == "migrated"
    assert "auto-migrated" in (legacy.notes or "")

    assert db.count_candidates_in_run(LEGACY_RUN_ID) == 2


def test_migration_is_idempotent(tmp_path):
    url = f"sqlite:///{tmp_path / 'idempotent.db'}"
    db1 = ProgramsDB(url)
    rid = db1.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    db1.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=rid)

    # Re-open the same DB; migration should not create a legacy run.
    db2 = ProgramsDB(url)
    with pytest.raises(KeyError):
        db2.get_run(LEGACY_RUN_ID)
    assert db2.count_candidates_in_run(rid) == 1


# ----------------------------------------------------------- seeding is internal


def test_fresh_run_creates_exactly_one_run_with_bootstrap_and_generated(
    db, tmp_path, monkeypatch
):
    """`alphamo run` on a fresh DB → one Run row + bootstrap trivial-seed
    rows + proposer-generated candidates.

    Sprint 3 redesign: bootstrap inserts the trivial Solo Service
    Provider seed into every island at gen 0; the proposer then evolves
    from there. The pre-Sprint-3 invariant ("no seed candidates in the
    DB") is inverted — seeds ARE in the DB now, just one trivial
    baseline rather than four curated existence proofs.
    """
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    _stub_cascade(monkeypatch)
    import alphamo.orchestrator as orch_mod
    audit = AuditLog(tmp_path / "audit.jsonl")

    hp = _hp(num_islands=4)
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=hp)
    orch.run(max_generations=3)

    runs = db.list_runs()
    assert len(runs) == 1, (
        f"expected exactly one run row; got {[(r.run_id, r.hyperparameters) for r in runs]}"
    )
    only_run = runs[0]
    assert only_run.run_id == orch.run_id
    assert only_run.hyperparameters["num_islands"] == 4
    assert only_run.stopped_reason == "max_generations"

    total_in_run = db.count_candidates_in_run(orch.run_id)
    # 4 bootstrap rows (one per island) + at least one generated candidate.
    assert total_in_run >= 4 + 1
    assert db.count_candidates() == total_in_run

    rows = db.alive_in_run(orch.run_id)
    # Bootstrap rows: TRIVIAL_SEED in each island at gen 0.
    trivial_rows = [
        r for r in rows
        if r.architecture_spec["name"] == TRIVIAL_SEED.name and r.generation == 0
    ]
    assert len(trivial_rows) == 4

    # Sprint 3: the 4 retired curated seed names must NOT appear in the
    # candidates table (they were removed from exemplar_library).
    retired_names = {"Satoshi", "Rowling", "Levels", "Medvi"}
    assert not any(r.architecture_spec["name"] in retired_names for r in rows)


def test_new_run_does_not_see_prior_runs_candidates(db, tmp_path, monkeypatch):
    """Prior runs' candidates are invisible to a new run's sampler.

    Lay down a prior run with a distinctive candidate, then start a fresh run.
    The fresh run's sampler must not be able to draw the prior run's candidate.
    """
    _stub_cascade(monkeypatch)
    import alphamo.orchestrator as orch_mod
    prior_run_id = db.create_run(
        hyperparameters={"legacy": True},
        parent_goal_version="v0",
        verifier_version="v0",
        notes="simulated prior run",
    )
    prior_id = db.insert(
        Architecture(
            name="ZOMBIE_FROM_PRIOR_RUN",
            summary="should never appear in a new run's sampler",
            value_chain="vc",
            capture_mechanism="cm",
            entry_resources="er",
        ),
        Scores(
            feasibility=0.99,
            structural=0.99,
            middle_class_accessible=True,
        ),
        run_id=prior_run_id,
        island_id=0,
    )
    db.complete_run(prior_run_id, "manual_simulation")

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=_hp(num_islands=2))
    orch.run(max_generations=2)

    fresh_count = db.count_candidates_in_run(orch.run_id)
    assert fresh_count > 0

    for island_id in range(orch.hp.num_islands):
        rows = db.top_k_in_island(island_id=island_id, k=100, run_id=orch.run_id)
        names = {r.architecture_spec["name"] for r in rows}
        assert "ZOMBIE_FROM_PRIOR_RUN" not in names

    zombie = db.get(prior_id)
    assert zombie.run_id == prior_run_id
    assert zombie.architecture_spec["name"] == "ZOMBIE_FROM_PRIOR_RUN"

    run_ids = {r.run_id for r in db.list_runs()}
    assert {prior_run_id, orch.run_id}.issubset(run_ids)


# ----------------------------------------------------------- CLI surface


def test_seed_subcommand_no_longer_exists():
    """alphamo seed was removed in Phase 1.1 (seeding is internal to `run`)."""
    from alphamo.main import cli

    assert "seed" not in cli.commands, (
        f"`alphamo seed` should be gone; cli.commands={list(cli.commands)}"
    )


def test_resolve_run_id_errors_when_db_has_no_runs(db):
    """The helper backing every read-only subcommand must not auto-create runs."""
    import click as _click

    from alphamo.main import _resolve_run_id

    with pytest.raises(_click.ClickException, match="no runs in this DB"):
        _resolve_run_id(db, None)


def test_resolve_run_id_returns_latest_when_no_explicit_run(db):
    older = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    newer = db.create_run(hyperparameters={}, parent_goal_version="v1", verifier_version="v1")
    from alphamo.main import _resolve_run_id

    assert _resolve_run_id(db, None) == newer
    assert older != newer
