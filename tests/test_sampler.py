"""Unit tests for the softmax-weighted sampler."""

from __future__ import annotations

import random

import pytest

from alphamo.sampler import Sampler, _softmax, _weighted_sample_without_replacement
from tests.fixtures.exemplars import ALL_FIXTURES, FOILS


@pytest.fixture()
def populated_db(db):
    for fixture in ALL_FIXTURES:
        db.insert(fixture.architecture, fixture.scores)
    return db


def test_draw_returns_k_seeds(populated_db):
    sampler = Sampler(populated_db, rng=random.Random(0))
    seeds = sampler.draw(island_id=0, k=2)
    assert len(seeds) == 2


def test_draw_handles_pool_smaller_than_k(db):
    from tests.fixtures.exemplars import SATOSHI_FIXTURE

    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores)
    sampler = Sampler(db)
    seeds = sampler.draw(island_id=0, k=5)
    assert len(seeds) == 1


def test_draw_empty_island_returns_empty(db):
    assert Sampler(db).draw(island_id=0, k=2) == []


def test_draw_excludes_zero_fitness_candidates(populated_db):
    foil_names = {f.architecture.name for f in FOILS}
    sampler = Sampler(populated_db, pool_size=10, rng=random.Random(0))
    seen: set[str] = set()
    for _ in range(30):
        seeds = sampler.draw(island_id=0, k=2)
        seen.update(s.name for s in seeds)
    assert seen.isdisjoint(foil_names), f"foils appeared in seeds: {seen & foil_names}"


def test_draw_returns_architecture_objects(populated_db):
    from alphamo.schemas import Architecture

    seeds = Sampler(populated_db, rng=random.Random(0)).draw(island_id=0, k=1)
    assert len(seeds) == 1
    assert isinstance(seeds[0], Architecture)


def test_softmax_sums_to_one():
    weights = _softmax([0.9, 0.85, 0.8], temperature=1.0)
    assert abs(sum(weights) - 1.0) < 1e-9


def test_softmax_higher_fitness_gets_higher_weight():
    weights = _softmax([0.9, 0.5, 0.1], temperature=1.0)
    assert weights[0] > weights[1] > weights[2]


def test_weighted_sample_without_replacement_no_duplicates():
    rng = random.Random(42)
    indices = _weighted_sample_without_replacement([0.5, 0.3, 0.2], k=2, rng=rng)
    assert len(indices) == 2
    assert len(set(indices)) == 2


def test_weighted_sample_without_replacement_respects_k():
    rng = random.Random(7)
    indices = _weighted_sample_without_replacement([0.4, 0.3, 0.2, 0.1], k=3, rng=rng)
    assert len(indices) == 3
