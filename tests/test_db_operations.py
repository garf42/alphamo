"""Tests for Phase 04 ProgramsDB operations: reset, history, diversity, top-N."""

from __future__ import annotations

from alphamo.schemas import Architecture, Scores
from tests.fixtures.exemplars import LEVELS_FIXTURE, ROWLING_FIXTURE, SATOSHI_FIXTURE


def _high_scores() -> Scores:
    return Scores(
        feasibility=0.9, structural=0.9, exemplar_similarity=0.9,
        middle_class_accessible=True,
    )


def test_top_k_in_island_filters_reset_status(db, default_run):
    alive_id = db.insert(
        SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=default_run
    )
    db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        run_id=default_run,
        status="reset",
    )

    rows = db.top_k_in_island(island_id=0, k=10)
    assert [r.id for r in rows] == [alive_id]


def test_reset_island_marks_existing_alive_as_reset(db, default_run):
    alive_id = db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        island_id=1,
    )
    seed_id = db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        run_id=default_run,
        island_id=0,
    )

    db.reset_island(island_id=1, seed_programs=[seed_id], run_id=default_run)

    assert db.get(alive_id).status == "reset"


def test_reset_island_inserts_copies_with_parent_lineage(db, default_run):
    seed_id = db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        island_id=0,
    )
    db.insert(
        LEVELS_FIXTURE.architecture,
        LEVELS_FIXTURE.scores,
        run_id=default_run,
        island_id=1,
    )

    db.reset_island(island_id=1, seed_programs=[seed_id], run_id=default_run)

    alive_in_1 = db.top_k_in_island(island_id=1, k=10)
    assert len(alive_in_1) == 1
    copy = alive_in_1[0]
    assert copy.id != seed_id
    assert copy.architecture_spec["name"] == "Satoshi"
    assert copy.parent_ids == [seed_id]
    assert copy.island_id == 1
    assert copy.run_id == default_run
    assert copy.fitness == db.get(seed_id).fitness


def test_top_programs_from_islands_orders_by_fitness(db, default_run):
    a_id = db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        island_id=0,
    )
    b_id = db.insert(
        LEVELS_FIXTURE.architecture,
        LEVELS_FIXTURE.scores,
        run_id=default_run,
        island_id=1,
    )
    db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        run_id=default_run,
        island_id=2,
    )

    top = db.top_programs_from_islands(island_ids=[0, 1], n=2)
    assert {r.id for r in top} == {a_id, b_id}
    assert top[0].fitness >= top[1].fitness


def test_top_programs_from_islands_skips_reset_rows(db, default_run):
    seed_id = db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        island_id=0,
    )
    db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        run_id=default_run,
        island_id=0,
        status="reset",
    )
    top = db.top_programs_from_islands(island_ids=[0], n=5)
    assert [r.id for r in top] == [seed_id]


def test_top_programs_from_islands_empty_input(db):
    assert db.top_programs_from_islands(island_ids=[], n=5) == []


def test_mean_fitness_per_island_defaults_missing_islands_to_zero(db, default_run):
    db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        island_id=1,
    )
    means = db.mean_fitness_per_island(num_islands=4)
    assert set(means) == {0, 1, 2, 3}
    assert means[0] == 0.0
    assert means[1] > 0.0
    assert means[2] == 0.0


def test_fitness_history_returns_max_per_generation(db, default_run):
    db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=default_run,
        generation=0,
    )
    db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        run_id=default_run,
        generation=0,
    )
    db.insert(
        LEVELS_FIXTURE.architecture,
        LEVELS_FIXTURE.scores,
        run_id=default_run,
        generation=1,
    )

    history = db.fitness_history(generations=2)
    assert len(history) == 2
    # generation 0 contains both Satoshi (highest) and Rowling
    assert history[0] == db.get(1).fitness
    # generation 1 contains only Levels
    assert history[1] == db.get(3).fitness


def test_fitness_history_empty_db(db):
    assert db.fitness_history(generations=5) == []


def test_diversity_metric_zero_for_identical_candidates(db, default_run):
    arch = Architecture(
        name="dup",
        summary="x",
        value_chain="alpha beta gamma",
        capture_mechanism="delta",
        entry_resources="x",
    )
    db.insert(arch, _high_scores(), run_id=default_run)
    db.insert(arch, _high_scores(), run_id=default_run)
    assert db.diversity_metric(island_id=0) == 0.0


def test_diversity_metric_one_for_disjoint_candidates(db, default_run):
    a = Architecture(
        name="a",
        summary="x",
        value_chain="alpha",
        capture_mechanism="beta",
        entry_resources="x",
    )
    b = Architecture(
        name="b",
        summary="x",
        value_chain="gamma",
        capture_mechanism="delta",
        entry_resources="x",
    )
    db.insert(a, _high_scores(), run_id=default_run)
    db.insert(b, _high_scores(), run_id=default_run)
    assert db.diversity_metric(island_id=0) == 1.0


def test_diversity_metric_returns_zero_for_singleton_island(db, default_run):
    db.insert(
        SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=default_run
    )
    assert db.diversity_metric(island_id=0) == 0.0


# ----------------------------------------------------------------- Sprint 17: scored-only reset metric


def _scored_arch(name: str) -> Architecture:
    """Distinct Architecture per name so the four corner-case tests
    below can insert multiple rows on the same island without violating
    any uniqueness expectation."""
    return Architecture(
        name=name, summary="s", value_chain="vc",
        capture_mechanism="cm", entry_resources="er",
    )


def _scored(feasibility: float, structural: float, robustness: float) -> Scores:
    """Full-cascade Scores with all three numeric dims set."""
    return Scores(
        feasibility=feasibility,
        structural=structural,
        robustness=robustness,
        middle_class_accessible=True,
    )


def _stage1_exit_scores(feasibility: float = 0.25) -> Scores:
    """Stage 1 exit: cascade.py:148-159 returns Scores with structural
    hard-coded to 0.0 and robustness=None. `aggregate_fitness` averages
    over feasibility+structural → fitness ≈ feasibility/2."""
    return Scores(
        feasibility=feasibility,
        structural=0.0,
        robustness=None,
        middle_class_accessible=True,
    )


def _middle_class_exit_scores() -> Scores:
    """Middle-class filter exit: cascade.py:132-144 sets middle_class_
    accessible=False. `aggregate_fitness` short-circuits to 0.0
    regardless of the other dims."""
    return Scores(
        feasibility=0.85,
        structural=0.0,
        robustness=None,
        middle_class_accessible=False,
    )


def _bootstrap_seed_scores() -> Scores:
    """Trivial bootstrap seed shape: orchestrator.py:528-535 hard-codes
    feasibility=0.5, structural=0.5, robustness=None, middle_class_
    accessible=True. `aggregate_fitness` → 0.50."""
    return Scores(
        feasibility=0.50,
        structural=0.50,
        robustness=None,
        middle_class_accessible=True,
    )


def test_mean_fitness_per_island_excludes_exit_rows_from_mean(db, default_run):
    """Sprint 17 (Q1): an island with N scored candidates plus M exits
    must rank by the mean over the N scored candidates only, not (N+M).

    Setup: island 0 has two scored candidates at fitness 0.80 + 0.60
    (mean over scored: 0.70) plus three Stage-1 exits at fitness ≈ 0.13
    (would drag the all-alive mean down to ≈ 0.34). Under the Sprint-17
    metric the reported value must be the scored-only mean.
    """
    db.insert(
        _scored_arch("scored_high"), _scored(0.8, 0.8, 0.8),
        run_id=default_run, island_id=0,
    )
    db.insert(
        _scored_arch("scored_low"), _scored(0.6, 0.6, 0.6),
        run_id=default_run, island_id=0,
    )
    for i in range(3):
        db.insert(
            _scored_arch(f"stage1_exit_{i}"), _stage1_exit_scores(),
            run_id=default_run, island_id=0,
        )
    means = db.mean_fitness_per_island(num_islands=1, run_id=default_run)
    # scored mean = (0.8 + 0.6) / 2 = 0.70
    assert abs(means[0] - 0.70) < 1e-9, (
        f"expected scored-only mean ≈ 0.70; got {means[0]}; "
        "Sprint 17 filter likely not applied"
    )


def test_mean_fitness_per_island_zero_when_only_exits_present(db, default_run):
    """Sprint 17 (Q2): an island with zero scored candidates — only
    exits / only the bootstrap seed — must rank as 0.0 (lowest). The
    pre-initialised dict at operations.py:546 provides this default;
    the SQL GROUP BY simply omits the island from the result rows.

    Confirms dead islands stay eligible for reset."""
    db.insert(
        _scored_arch("seed_island_2"), _bootstrap_seed_scores(),
        run_id=default_run, island_id=2,
    )
    db.insert(
        _scored_arch("exit_island_2"), _stage1_exit_scores(),
        run_id=default_run, island_id=2,
    )
    # Island 5 has only a middle-class exit (fitness=0.0).
    db.insert(
        _scored_arch("mc_exit_island_5"), _middle_class_exit_scores(),
        run_id=default_run, island_id=5,
    )
    means = db.mean_fitness_per_island(num_islands=8, run_id=default_run)
    assert means[2] == 0.0
    assert means[5] == 0.0
    # Sanity: every island has a key (empty-island default behaviour).
    assert set(means.keys()) == set(range(8))


def test_bootstrap_seed_does_not_count_toward_ranking(db, default_run):
    """Sprint 17 (Q3): the gen-0 trivial seed (fitness 0.50, robustness
    None) must NOT contribute to the reset ranking. The seed has its
    own purpose (guaranteed alive row so the sampler returns something
    on gen 1) but it carries no Stage-3 signal — including it in the
    metric would mask the actual lineage quality on islands that have
    only the seed plus nothing else."""
    # Island 0: just the bootstrap seed.
    db.insert(
        _scored_arch("seed_only"), _bootstrap_seed_scores(),
        run_id=default_run, island_id=0,
    )
    # Island 1: bootstrap seed plus one scored candidate at 0.6.
    db.insert(
        _scored_arch("seed_1_a"), _bootstrap_seed_scores(),
        run_id=default_run, island_id=1,
    )
    db.insert(
        _scored_arch("scored_1_b"), _scored(0.6, 0.6, 0.6),
        run_id=default_run, island_id=1,
    )
    means = db.mean_fitness_per_island(num_islands=2, run_id=default_run)
    # Island 0: no scored rows → 0.0.
    assert means[0] == 0.0
    # Island 1: scored mean = 0.6 (seed excluded).
    assert abs(means[1] - 0.6) < 1e-9


def test_middle_class_exit_does_not_count_toward_ranking(db, default_run):
    """Sprint 17 (Q4): a middle-class-filter exit (fitness=0.0,
    robustness=None) must NOT count toward the ranking on any island.
    Pre-Sprint-17 these rows pulled island means hard toward 0.0; the
    new metric simply ignores them."""
    # Island 0: one scored at 0.75 + two middle-class exits at 0.0.
    db.insert(
        _scored_arch("scored_a"), _scored(0.75, 0.75, 0.75),
        run_id=default_run, island_id=0,
    )
    db.insert(
        _scored_arch("mc_exit_a"), _middle_class_exit_scores(),
        run_id=default_run, island_id=0,
    )
    db.insert(
        _scored_arch("mc_exit_b"), _middle_class_exit_scores(),
        run_id=default_run, island_id=0,
    )
    means = db.mean_fitness_per_island(num_islands=1, run_id=default_run)
    # Pre-Sprint-17 this would be (0.75 + 0.0 + 0.0)/3 = 0.25;
    # Sprint 17 reads it as 0.75 (scored-only).
    assert abs(means[0] - 0.75) < 1e-9


def test_mean_fitness_per_island_matches_pre_sprint17_when_all_rows_scored(
    db, default_run
):
    """Sprint 17 (Q5) — backward-compat invariant: a run where every
    candidate has a non-null robustness produces ranking values
    identical to the pre-Sprint-17 implementation. The change is a
    pure filter; the math over the surviving rows is unchanged.

    Three islands, mix of scored fitnesses. Old implementation's mean
    = new implementation's mean down to floating-point equality, since
    the WHERE-clause filter removes no rows in this case.
    """
    # Island 0: 0.7 + 0.5 → mean 0.6
    db.insert(_scored_arch("a"), _scored(0.7, 0.7, 0.7), run_id=default_run, island_id=0)
    db.insert(_scored_arch("b"), _scored(0.5, 0.5, 0.5), run_id=default_run, island_id=0)
    # Island 1: 0.9 alone → mean 0.9
    db.insert(_scored_arch("c"), _scored(0.9, 0.9, 0.9), run_id=default_run, island_id=1)
    # Island 2: 0.4 + 0.6 + 0.8 → mean 0.6
    db.insert(_scored_arch("d"), _scored(0.4, 0.4, 0.4), run_id=default_run, island_id=2)
    db.insert(_scored_arch("e"), _scored(0.6, 0.6, 0.6), run_id=default_run, island_id=2)
    db.insert(_scored_arch("f"), _scored(0.8, 0.8, 0.8), run_id=default_run, island_id=2)
    means = db.mean_fitness_per_island(num_islands=3, run_id=default_run)
    assert abs(means[0] - 0.6) < 1e-9
    assert abs(means[1] - 0.9) < 1e-9
    assert abs(means[2] - 0.6) < 1e-9


def test_rank_by_mean_fitness_orders_by_sprint17_metric(db, default_run):
    """End-to-end: `IslandsManager.rank_by_mean_fitness` (islands.py:91-94)
    must produce a ranking driven by the scored-only metric, mirroring
    the run_9f8bba65 motivating case where Island 1 (avg_scored 0.689 +
    3 exits) ranked BELOW Island 6 (avg_scored 0.664, 0 exits) under
    the old metric but should rank ABOVE under Sprint 17.

    Concretely: this test builds two islands with the same shape
    as the report — Island 1 = strong scored + several exits, Island
    6 = slightly weaker scored + no exits. Sprint 17 must rank
    Island 1 above Island 6."""
    from alphamo.islands import IslandsManager

    # Island 1: scored mean 0.689 (two scored candidates) + 3 Stage-1
    # exits at fitness ≈ 0.13 (these would drag the pre-Sprint-17 mean
    # well below Island 6).
    db.insert(
        _scored_arch("i1_scored_a"), _scored(0.7, 0.7, 0.7),
        run_id=default_run, island_id=1,
    )
    db.insert(
        _scored_arch("i1_scored_b"), _scored(0.65, 0.65, 0.7),
        run_id=default_run, island_id=1,
    )
    for k in range(3):
        db.insert(
            _scored_arch(f"i1_exit_{k}"), _stage1_exit_scores(),
            run_id=default_run, island_id=1,
        )
    # Island 6: scored mean 0.664 (two scored candidates), zero exits.
    db.insert(
        _scored_arch("i6_scored_a"), _scored(0.66, 0.66, 0.66),
        run_id=default_run, island_id=6,
    )
    db.insert(
        _scored_arch("i6_scored_b"), _scored(0.668, 0.66, 0.668),
        run_id=default_run, island_id=6,
    )

    mgr = IslandsManager(db, run_id=default_run, num_islands=8)
    ranked = mgr.rank_by_mean_fitness()
    # Strongest first. Under Sprint 17, Island 1's scored mean
    # (≈ 0.687) edges Island 6's (≈ 0.664). The other 6 islands have
    # zero scored rows → 0.0 → ranked at the bottom (any tie-break
    # ordering among them is fine, only the Island-1-vs-Island-6
    # relative position matters here).
    pos_1 = ranked.index(1)
    pos_6 = ranked.index(6)
    assert pos_1 < pos_6, (
        f"under Sprint 17 the scored-only metric should rank Island 1 "
        f"(scored mean ~0.687) above Island 6 (scored mean ~0.664). "
        f"Got ranked={ranked}, Island 1 at position {pos_1}, "
        f"Island 6 at position {pos_6}."
    )
