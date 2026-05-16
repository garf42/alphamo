"""Unit tests for the IslandsManager.

Sprint 2 redesign: `seed_all_islands` was removed. Islands start empty;
the proposer bootstraps each island from the reference exemplar set. The
periodic-reset machinery still applies, but reseeding now copies from
the alive generated candidates in strong islands rather than from
STARTERS.
"""

from __future__ import annotations

import random

import pytest

from alphamo.islands import IslandsManager
from alphamo.schemas import Architecture, Scores
from tests.fixtures.exemplars import SATOSHI_FIXTURE


def _gen_arch(name: str) -> Architecture:
    return Architecture(
        name=name,
        summary="generated candidate",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources="laptop, modest savings",
    )


def _low_scores() -> Scores:
    return Scores(
        feasibility=0.1, structural=0.1,
        middle_class_accessible=True,
    )


def _high_scores() -> Scores:
    return Scores(
        feasibility=0.9, structural=0.9, robustness=0.9,
        middle_class_accessible=True,
    )


def test_pick_island_returns_valid_id(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=8, rng=random.Random(0))
    for _ in range(50):
        assert 0 <= mgr.pick_island() < 8


def test_rank_by_mean_fitness_orders_strong_islands_first(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=4)
    db.insert(
        SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores,
        run_id=default_run, island_id=2,
    )
    db.insert(_gen_arch("weak"), _low_scores(), run_id=default_run, island_id=0)
    ranked = mgr.rank_by_mean_fitness()
    assert ranked[0] == 2
    assert ranked.index(0) > ranked.index(2)


def test_maybe_reset_returns_none_outside_cadence(db, default_run):
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=4, reset_every_generations=10
    )
    db.insert(_gen_arch("g"), _high_scores(), run_id=default_run, island_id=0)
    assert mgr.maybe_reset(current_generation=5) is None
    assert mgr.maybe_reset(current_generation=0) is None


def test_maybe_reset_wipes_weak_islands_at_cadence(db, default_run):
    """At reset cadence: bottom-half islands get reseeded with copies of the
    top alive candidates from strong islands."""
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=4,
        reset_every_generations=10, top_seed_count=2,
    )
    # Strong islands (0, 1) have high-fitness candidates.
    for island_id in range(2):
        db.insert(
            _gen_arch(f"strong-{island_id}"), _high_scores(),
            run_id=default_run, island_id=island_id,
        )
    # Weak islands (2, 3) have low-fitness candidates.
    for island_id in (2, 3):
        db.insert(
            _gen_arch(f"weak-{island_id}"), _low_scores(),
            run_id=default_run, island_id=island_id,
        )

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None
    assert set(event.strong_islands) == {0, 1}
    assert set(event.weak_islands) == {2, 3}

    # Weak islands now carry copies of the strong-island candidates.
    for weak_island in (2, 3):
        alive = db.top_k_in_island(island_id=weak_island, k=10, run_id=default_run)
        names = {r.architecture_spec["name"] for r in alive}
        assert names.intersection({"strong-0", "strong-1"})


def test_maybe_reset_no_op_when_no_candidates_available(db, default_run):
    """With no alive candidates anywhere, reset can't pick reseed sources → no-op."""
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=4, reset_every_generations=10
    )
    assert mgr.maybe_reset(current_generation=10) is None


def test_diversity_summary_returns_one_entry_per_island(db, default_run):
    mgr = IslandsManager(db, run_id=default_run, num_islands=4)
    for island_id in range(4):
        db.insert(
            _gen_arch(f"g-{island_id}"), _high_scores(),
            run_id=default_run, island_id=island_id,
        )
    summary = mgr.diversity_summary()
    assert set(summary) == {0, 1, 2, 3}
    assert all(0.0 <= v <= 1.0 for v in summary.values())


def test_constructor_rejects_too_few_islands(db, default_run):
    with pytest.raises(ValueError):
        IslandsManager(db, run_id=default_run, num_islands=1)


def test_constructor_rejects_missing_run_id(db):
    with pytest.raises(ValueError):
        IslandsManager(db, run_id="", num_islands=4)
