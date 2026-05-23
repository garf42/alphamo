"""Unit tests for the IslandsManager.

Sprint 3 redesign: `maybe_reset()` now matches FunSearch (Nature 2023,
§A.1 Methods) — per-weak-island independent uniform draw from the
surviving half, single program copied from the chosen surviving island.
Pre-Sprint-3 code shared a top-k across all surviving islands for every
weak island, propagating the surviving population's centroid rather
than allowing genuinely independent reseed paths.

Bootstrap (orchestrator-side) inserts the trivial seed into every island
at gen 0, so the periodic reset has alive candidates to work with from
the very first reset-cadence boundary.
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


def test_reset_at_default_cadence_10_fires_on_gen_10_20_30(db, default_run):
    """Verify the new Hyperparameters default of reset_every_generations=10
    fires reset at gen 10, 20, 30 and not at other generations."""
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=2, reset_every_generations=10
    )
    # Populate both islands so reset has data to work with.
    for island_id in (0, 1):
        db.insert(
            _gen_arch(f"g-{island_id}"), _high_scores(),
            run_id=default_run, island_id=island_id,
        )

    # Fires at multiples of 10.
    assert mgr.maybe_reset(current_generation=10) is not None
    assert mgr.maybe_reset(current_generation=20) is not None
    assert mgr.maybe_reset(current_generation=30) is not None
    # Does not fire at intermediate generations.
    for gen in (1, 9, 11, 15, 19, 21, 29, 31):
        assert mgr.maybe_reset(current_generation=gen) is None


def test_maybe_reset_copies_single_program_not_top_k(db, default_run):
    """Regression for pre-Sprint-3 bug: reset must copy ONE program per weak
    island, not a top-k slice shared across all weak islands.

    Each strong island gets two candidates of different fitness. Reset
    fires; the weak island ends up with one (alive) reset-copy, not k of
    them. (The original alive candidate in the weak island is marked
    'reset' status by db.reset_island.)
    """
    mgr = IslandsManager(
        db,
        run_id=default_run,
        num_islands=4,
        reset_every_generations=10,
        rng=random.Random(0),
    )
    # Strong islands (0, 1): two candidates each, distinct fitness.
    for island_id in (0, 1):
        db.insert(
            _gen_arch(f"strong-{island_id}-high"), _high_scores(),
            run_id=default_run, island_id=island_id,
        )
        db.insert(
            _gen_arch(f"strong-{island_id}-mid"),
            Scores(feasibility=0.6, structural=0.6, robustness=0.6,
                   middle_class_accessible=True),
            run_id=default_run, island_id=island_id,
        )
    # Weak islands (2, 3): one low-fitness candidate each.
    for island_id in (2, 3):
        db.insert(
            _gen_arch(f"weak-{island_id}"), _low_scores(),
            run_id=default_run, island_id=island_id,
        )

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None

    # Exactly ONE reset-copy alive in each weak island.
    for weak_island in (2, 3):
        alive = db.top_k_in_island(island_id=weak_island, k=10, run_id=default_run)
        assert len(alive) == 1, (
            f"weak island {weak_island} has {len(alive)} alive rows post-reset; "
            "FunSearch spec is one program copied per weak island"
        )
        # And it's the BEST of some surviving island (the *-high row),
        # not the *-mid row.
        assert "high" in alive[0].architecture_spec["name"]


def test_maybe_reset_uses_per_weak_island_random_draw(db, default_run):
    """FunSearch spec: each weak island independently samples a surviving
    island uniformly. With strong islands {0, 1} and a seeded RNG, both
    weak islands should NOT necessarily reseed from the same source.
    """
    # rng seed chosen empirically to produce distinct source islands
    # under random.choice([0, 1]) called twice. Most seeds will produce
    # one (0,1) or (1,0) pair within the first few attempts; we use seed=2
    # which yields (1, 0) — independent draws producing different sources.
    mgr = IslandsManager(
        db,
        run_id=default_run,
        num_islands=4,
        reset_every_generations=10,
        rng=random.Random(2),
    )
    # Distinguishable candidates per strong island.
    db.insert(_gen_arch("from-island-0"), _high_scores(),
              run_id=default_run, island_id=0)
    db.insert(_gen_arch("from-island-1"), _high_scores(),
              run_id=default_run, island_id=1)
    # Weak islands.
    for island_id in (2, 3):
        db.insert(_gen_arch(f"weak-{island_id}"), _low_scores(),
                  run_id=default_run, island_id=island_id)

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None
    # Both source_islands entries must be present and within the strong set.
    assert len(event.source_islands) == 2
    for src in event.source_islands:
        assert src in {0, 1}


def test_maybe_reset_chooses_uniformly_from_surviving_islands(db, default_run):
    """Statistical check: across many reset cycles, the choice over
    surviving islands is uniform. We don't have many cycles in one run
    (we'd need many reset cadences), so instead verify the mechanism
    by calling reset many times with re-populated state and aggregating.
    """
    # Set up: 4 islands, strong = {0, 1}, weak = {2, 3}.
    # Repeatedly: insert candidates, fire reset, count which strong
    # island sourced each weak island's reseed, reset state.
    counts = {0: 0, 1: 0}
    mgr_rng = random.Random(42)
    total_draws = 0
    for trial in range(200):
        # Each trial uses an isolated run_id so candidates don't bleed
        # across trials.
        trial_run = db.create_run(
            hyperparameters={}, parent_goal_version="t", verifier_version="t"
        )
        mgr = IslandsManager(
            db, run_id=trial_run, num_islands=4,
            reset_every_generations=10, rng=mgr_rng,
        )
        db.insert(_gen_arch("s0"), _high_scores(), run_id=trial_run, island_id=0)
        db.insert(_gen_arch("s1"), _high_scores(), run_id=trial_run, island_id=1)
        db.insert(_gen_arch("w2"), _low_scores(), run_id=trial_run, island_id=2)
        db.insert(_gen_arch("w3"), _low_scores(), run_id=trial_run, island_id=3)
        event = mgr.maybe_reset(current_generation=10)
        for src in event.source_islands:
            counts[src] += 1
            total_draws += 1

    # 200 trials × 2 weak islands = 400 draws over {0, 1}. Uniform
    # expectation: 200 each. Allow ±30 (well outside expected variance,
    # safely within the binomial 99% range for n=400, p=0.5).
    expected = total_draws / 2
    assert abs(counts[0] - expected) < 30, (
        f"non-uniform draw: counts={counts} expected~{expected}"
    )


def test_reset_event_records_parallel_weak_source_seed_triples(db, default_run):
    """ResetEvent's weak_islands / source_islands / seed_program_ids must
    be parallel lists describing the per-weak-island reseed actions."""
    mgr = IslandsManager(
        db, run_id=default_run, num_islands=4,
        reset_every_generations=10, rng=random.Random(0),
    )
    for island_id in (0, 1):
        db.insert(_gen_arch(f"s-{island_id}"), _high_scores(),
                  run_id=default_run, island_id=island_id)
    for island_id in (2, 3):
        db.insert(_gen_arch(f"w-{island_id}"), _low_scores(),
                  run_id=default_run, island_id=island_id)

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None
    n = len(event.weak_islands)
    assert n == len(event.source_islands) == len(event.seed_program_ids)
    # Each source is in the strong set, each weak is in the weak set.
    for src in event.source_islands:
        assert src in event.strong_islands
    for weak in event.weak_islands:
        assert weak not in event.strong_islands


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


# ----------------------------------------------------------------- Sprint reset-diversity


def test_maybe_reset_source_islands_no_duplicates_when_weak_equals_strong(
    db, default_run
):
    """Sprint reset-diversity: with 4 strong and 4 weak (the default
    8-island shape), every source island must appear AT MOST ONCE
    across all four weak-island seed assignments. Pre-sprint the
    `rng.choice(strong)` draws were independent uniform with
    replacement; run_9f8bba65's gen-120 reset assigned island 0 to all
    four weak islands, seeding id=77 four times. Without-replacement
    sampling makes that impossible at this shape.
    """
    mgr = IslandsManager(
        db,
        run_id=default_run,
        num_islands=8,
        reset_every_generations=10,
        rng=random.Random(0),
    )
    # 4 strong islands (0..3): each with a high-fitness candidate.
    for island_id in range(4):
        db.insert(
            _gen_arch(f"strong-{island_id}"), _high_scores(),
            run_id=default_run, island_id=island_id,
        )
    # 4 weak islands (4..7): one low-fitness candidate each.
    for island_id in range(4, 8):
        db.insert(
            _gen_arch(f"weak-{island_id}"), _low_scores(),
            run_id=default_run, island_id=island_id,
        )

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None
    assert len(event.source_islands) == 4
    # Every source distinct.
    assert len(set(event.source_islands)) == 4, (
        f"source_islands {event.source_islands} contains duplicates; "
        "the without-replacement constraint must guarantee distinct "
        "sources when n_weak ≤ n_strong"
    )
    # And every source is in the strong set.
    assert set(event.source_islands).issubset(set(event.strong_islands))


def test_maybe_reset_source_islands_round_robin_when_weak_exceeds_strong(
    db, default_run
):
    """Sprint reset-diversity: with odd `num_islands` the split is
    uneven (e.g. num_islands=5 → strong=ranked[:2], weak=ranked[2:]
    giving 3 weak vs 2 strong). When weak > strong, sampling without
    replacement runs out of strong islands; the implementation falls
    back to round-robin walking shuffled_strong, so no single source
    island is assigned more than ceil(n_weak / n_strong) times.
    """
    mgr = IslandsManager(
        db,
        run_id=default_run,
        num_islands=5,
        reset_every_generations=10,
        rng=random.Random(0),
    )
    # 2 strong islands.
    for island_id in range(2):
        db.insert(
            _gen_arch(f"strong-{island_id}"), _high_scores(),
            run_id=default_run, island_id=island_id,
        )
    # 3 weak islands.
    for island_id in range(2, 5):
        db.insert(
            _gen_arch(f"weak-{island_id}"), _low_scores(),
            run_id=default_run, island_id=island_id,
        )

    event = mgr.maybe_reset(current_generation=10)
    assert event is not None
    assert len(event.source_islands) == 3
    # No source used more than ceil(3 / 2) = 2 times.
    from collections import Counter
    counts = Counter(event.source_islands)
    max_uses = max(counts.values())
    expected_ceiling = (3 + 2 - 1) // 2  # ceil(3 / 2)
    assert max_uses <= expected_ceiling, (
        f"source_islands counts={dict(counts)} — max use {max_uses} "
        f"exceeds round-robin ceiling {expected_ceiling}"
    )
    # And every source is in the strong set.
    assert set(event.source_islands).issubset(set(event.strong_islands))


def test_maybe_reset_source_diversity_across_many_cycles(db, default_run):
    """Sprint reset-diversity statistical check: across 200 reset cycles
    with 4 strong + 4 weak, EVERY cycle's source_islands must be a
    permutation of the strong set. The without-replacement constraint
    is a per-cycle structural property, not a long-run frequency
    property — pre-sprint the statistical test
    `test_maybe_reset_chooses_uniformly_from_surviving_islands`
    couldn't distinguish duplicate-source cycles from clean ones
    because it aggregated across cycles."""
    mgr_rng = random.Random(7)
    for trial in range(200):
        trial_run = db.create_run(
            hyperparameters={}, parent_goal_version="t", verifier_version="t"
        )
        mgr = IslandsManager(
            db, run_id=trial_run, num_islands=8,
            reset_every_generations=10, rng=mgr_rng,
        )
        for island_id in range(4):
            db.insert(_gen_arch(f"s{island_id}"), _high_scores(),
                      run_id=trial_run, island_id=island_id)
        for island_id in range(4, 8):
            db.insert(_gen_arch(f"w{island_id}"), _low_scores(),
                      run_id=trial_run, island_id=island_id)
        event = mgr.maybe_reset(current_generation=10)
        assert event is not None
        assert len(set(event.source_islands)) == 4, (
            f"trial {trial}: source_islands {event.source_islands} "
            "contains duplicates"
        )
