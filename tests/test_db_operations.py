"""Tests for Phase 04 ProgramsDB operations: reset, history, diversity, top-N."""

from __future__ import annotations

from alphamo.schemas import Architecture, Scores
from tests.fixtures.exemplars import LEVELS_FIXTURE, ROWLING_FIXTURE, SATOSHI_FIXTURE


def _high_scores() -> Scores:
    return Scores(
        feasibility=0.9, structural=0.9, exemplar_similarity=0.9,
        middle_class_accessible=True,
    )


def test_top_k_in_island_filters_reset_status(db):
    alive_id = db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores)
    db.insert(ROWLING_FIXTURE.architecture, ROWLING_FIXTURE.scores, status="reset")

    rows = db.top_k_in_island(island_id=0, k=10)
    assert [r.id for r in rows] == [alive_id]


def test_reset_island_marks_existing_alive_as_reset(db):
    alive_id = db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, island_id=1)
    seed_id = db.insert(ROWLING_FIXTURE.architecture, ROWLING_FIXTURE.scores, island_id=0)

    db.reset_island(island_id=1, seed_programs=[seed_id])

    assert db.get(alive_id).status == "reset"


def test_reset_island_inserts_copies_with_parent_lineage(db):
    seed_id = db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, island_id=0)
    db.insert(LEVELS_FIXTURE.architecture, LEVELS_FIXTURE.scores, island_id=1)

    db.reset_island(island_id=1, seed_programs=[seed_id])

    alive_in_1 = db.top_k_in_island(island_id=1, k=10)
    assert len(alive_in_1) == 1
    copy = alive_in_1[0]
    assert copy.id != seed_id
    assert copy.architecture_spec["name"] == "Satoshi"
    assert copy.parent_ids == [seed_id]
    assert copy.island_id == 1
    assert copy.fitness == db.get(seed_id).fitness


def test_top_programs_from_islands_orders_by_fitness(db):
    a_id = db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, island_id=0)
    b_id = db.insert(LEVELS_FIXTURE.architecture, LEVELS_FIXTURE.scores, island_id=1)
    db.insert(ROWLING_FIXTURE.architecture, ROWLING_FIXTURE.scores, island_id=2)

    top = db.top_programs_from_islands(island_ids=[0, 1], n=2)
    assert {r.id for r in top} == {a_id, b_id}
    assert top[0].fitness >= top[1].fitness


def test_top_programs_from_islands_skips_reset_rows(db):
    seed_id = db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, island_id=0)
    db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        island_id=0,
        status="reset",
    )
    top = db.top_programs_from_islands(island_ids=[0], n=5)
    assert [r.id for r in top] == [seed_id]


def test_top_programs_from_islands_empty_input(db):
    assert db.top_programs_from_islands(island_ids=[], n=5) == []


def test_mean_fitness_per_island_defaults_missing_islands_to_zero(db):
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, island_id=1)
    means = db.mean_fitness_per_island(num_islands=4)
    assert set(means) == {0, 1, 2, 3}
    assert means[0] == 0.0
    assert means[1] > 0.0
    assert means[2] == 0.0


def test_fitness_history_returns_max_per_generation(db):
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, generation=0)
    db.insert(ROWLING_FIXTURE.architecture, ROWLING_FIXTURE.scores, generation=0)
    db.insert(LEVELS_FIXTURE.architecture, LEVELS_FIXTURE.scores, generation=1)

    history = db.fitness_history(generations=2)
    assert len(history) == 2
    # generation 0 contains both Satoshi (highest) and Rowling
    assert history[0] == db.get(1).fitness
    # generation 1 contains only Levels
    assert history[1] == db.get(3).fitness


def test_fitness_history_empty_db(db):
    assert db.fitness_history(generations=5) == []


def test_diversity_metric_zero_for_identical_candidates(db):
    arch = Architecture(
        name="dup",
        summary="x",
        value_chain="alpha beta gamma",
        capture_mechanism="delta",
        entry_resources="x",
    )
    db.insert(arch, _high_scores())
    db.insert(arch, _high_scores())
    assert db.diversity_metric(island_id=0) == 0.0


def test_diversity_metric_one_for_disjoint_candidates(db):
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
    db.insert(a, _high_scores())
    db.insert(b, _high_scores())
    assert db.diversity_metric(island_id=0) == 1.0


def test_diversity_metric_returns_zero_for_singleton_island(db):
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores)
    assert db.diversity_metric(island_id=0) == 0.0
