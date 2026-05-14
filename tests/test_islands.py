"""Unit tests for the IslandsManager."""

from __future__ import annotations

import random

import pytest

from alphamo.evaluator.exemplar_library import STARTERS
from alphamo.islands import IslandsManager
from alphamo.schemas import Architecture, Scores
from tests.fixtures.exemplars import SATOSHI_FIXTURE


def _low_arch(name: str) -> tuple[Architecture, Scores]:
    return (
        Architecture(
            name=name,
            summary="low-fitness placeholder",
            value_chain="generic",
            capture_mechanism="generic",
            entry_resources="generic",
        ),
        Scores(
            feasibility=0.1,
            structural=0.1,
            exemplar_similarity=0.1,
            middle_class_accessible=True,
        ),
    )


def test_seed_all_islands_inserts_starters_into_every_island(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=4)
    mgr.seed_all_islands(STARTERS)
    for island_id in range(4):
        rows = db.top_k_in_island(island_id=island_id, k=10, run_id=default_run)
        assert {r.architecture_spec["name"] for r in rows} == {
            arch.name for arch, _ in STARTERS
        }
        assert all(r.run_id == default_run for r in rows)


def test_pick_island_returns_valid_id(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=8, rng=random.Random(0))
    for _ in range(50):
        assert 0 <= mgr.pick_island() < 8


def test_rank_by_mean_fitness_orders_strong_islands_first(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=4)
    db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        island_id=2,
    )
    low_arch, low_scores = _low_arch("weak")
    db.insert(low_arch, low_scores, run_id=default_run, island_id=0)
    ranked = mgr.rank_by_mean_fitness()
    assert ranked[0] == 2
    assert ranked.index(0) > ranked.index(2)


def test_maybe_reset_returns_none_outside_cadence(db, default_run):
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=4, reset_every_generations=10
    )
    mgr.seed_all_islands(STARTERS)
    assert mgr.maybe_reset(current_generation=5) is None
    assert mgr.maybe_reset(current_generation=0) is None


def test_maybe_reset_wipes_weak_islands_at_cadence(db, default_run):
    mgr = IslandsManager(
        db,
        run_id=default_run,
        num_islands=4,
        reset_every_generations=10,
        top_seed_count=2,
    )
    for island_id in range(2):
        db.insert(
            SATOSHI_FIXTURE.architecture,
            SATOSHI_FIXTURE.scores,
            run_id=default_run,
            island_id=island_id,
        )
    low_arch, low_scores = _low_arch("weak")
    for island_id in (2, 3):
        db.insert(low_arch, low_scores, run_id=default_run, island_id=island_id)

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None
    assert set(event.strong_islands) == {0, 1}
    assert set(event.weak_islands) == {2, 3}

    for weak_island in (2, 3):
        alive = db.top_k_in_island(
            island_id=weak_island, k=10, run_id=default_run
        )
        assert {r.architecture_spec["name"] for r in alive} == {"Satoshi"}


def test_maybe_reset_no_op_when_no_seeds_available(db, default_run):
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=4, reset_every_generations=10
    )
    assert mgr.maybe_reset(current_generation=10) is None


def test_diversity_summary_returns_one_entry_per_island(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=4)
    mgr.seed_all_islands(STARTERS)
    summary = mgr.diversity_summary()
    assert set(summary) == {0, 1, 2, 3}
    assert all(0.0 <= v <= 1.0 for v in summary.values())


def test_constructor_rejects_too_few_islands(db, default_run):
    with pytest.raises(ValueError):
        IslandsManager(db, run_id=default_run, num_islands=1)


def test_constructor_rejects_missing_run_id(db):
    with pytest.raises(ValueError):
        IslandsManager(db, run_id="", num_islands=4)
