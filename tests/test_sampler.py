"""Unit tests for the softmax-weighted sampler."""

from __future__ import annotations

import random

import pytest

from alphamo.sampler import Sampler, _softmax, _weighted_sample_without_replacement
from tests.fixtures.exemplars import ALL_FIXTURES, FOILS


@pytest.fixture()
def populated_db(db, default_run):
    for fixture in ALL_FIXTURES:
        db.insert(fixture.architecture, fixture.scores, run_id=default_run)
    return db


def test_draw_returns_k_seeds(populated_db):
    sampler = Sampler(populated_db, rng=random.Random(0))
    seeds = sampler.draw(island_id=0, k=2)
    assert len(seeds) == 2


def test_draw_handles_pool_smaller_than_k(db, default_run):
    from tests.fixtures.exemplars import SATOSHI_FIXTURE

    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=default_run)
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
        seen.update(s.architecture.name for s in seeds)
    assert seen.isdisjoint(foil_names), f"foils appeared in seeds: {seen & foil_names}"


def test_draw_returns_seed_records(populated_db):
    """Phase 2: draw returns Seed (architecture + scores + fitness) per AlphaEvolve."""
    from alphamo.sampler import Seed
    from alphamo.schemas import Architecture, Scores

    seeds = Sampler(populated_db, rng=random.Random(0)).draw(island_id=0, k=1)
    assert len(seeds) == 1
    seed = seeds[0]
    assert isinstance(seed, Seed)
    assert isinstance(seed.architecture, Architecture)
    assert isinstance(seed.scores, Scores)
    assert seed.fitness > 0.0


def test_draw_respects_run_id_filter(db, default_run):
    """Sampler bound to a run_id must not see another run's candidates."""
    from tests.fixtures.exemplars import SATOSHI_FIXTURE

    other_run = db.create_run(
        hyperparameters={}, parent_goal_version="test", verifier_version="test"
    )
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=other_run)

    sampler = Sampler(db, run_id=default_run)
    assert sampler.draw(island_id=0, k=2) == []

    sampler_other = Sampler(db, run_id=other_run)
    assert len(sampler_other.draw(island_id=0, k=1)) == 1


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


# ----------------------------------------------------- Phase 2 Change 2:
# within-island signature clustering (FunSearch §A.1)


def test_cluster_signature_is_deterministic_given_scores():
    """Same Scores → same signature, regardless of unrelated fields."""
    from alphamo.sampler import cluster_signature
    from alphamo.schemas import Scores

    s_a = Scores(feasibility=0.78, structural=0.85, exemplar_similarity=0.71, middle_class_accessible=True)
    s_b = Scores(feasibility=0.78, structural=0.85, exemplar_similarity=0.71, middle_class_accessible=True)
    assert cluster_signature(s_a) == cluster_signature(s_b)


def test_sampler_signature_is_three_dimensional():
    """Sprint 2: cluster_signature drops exemplar_similarity from its inputs
    and uses 3 numeric dims (feasibility, structural, robustness) plus the
    middle_class_accessible boolean. Resolution=2 was empirically rejected
    (produces 100% singletons at every realistic run scale); the default
    stays at resolution=1."""
    from alphamo.sampler import cluster_signature
    from alphamo.schemas import Scores

    s = Scores(
        feasibility=0.78,
        structural=0.85,
        exemplar_similarity=0.71,  # should NOT influence the signature
        robustness=0.60,
        middle_class_accessible=True,
    )
    sig = cluster_signature(s, resolution=1)
    # 4-tuple: (feasibility, structural, robustness, middle_class).
    # 0.85 rounds to 0.8 at resolution=1 (Python's banker's rounding).
    assert len(sig) == 4
    assert sig == (0.8, 0.8, 0.6, True)

    # Changing exemplar_similarity must not change the signature.
    s_other = s.model_copy(update={"exemplar_similarity": 0.05})
    assert cluster_signature(s_other, resolution=1) == sig

    # Two candidates differing only in robustness produce different signatures
    # at resolution=1 (gap > 0.1 between them).
    s_other_robust = s.model_copy(update={"robustness": 0.20})
    assert cluster_signature(s_other_robust, resolution=1) != sig


def test_cluster_signature_handles_robustness_none():
    """Early-exit candidates have robustness=None; they cluster together."""
    from alphamo.sampler import cluster_signature
    from alphamo.schemas import Scores

    s_early_1 = Scores(
        feasibility=0.40, structural=0.0, robustness=None, middle_class_accessible=True,
    )
    s_early_2 = Scores(
        feasibility=0.40, structural=0.0, robustness=None, middle_class_accessible=True,
    )
    assert cluster_signature(s_early_1) == cluster_signature(s_early_2)
    # Robustness slot is None when robustness is None.
    sig = cluster_signature(s_early_1)
    assert sig[2] is None


def test_aggregate_fitness_ignores_similarity_when_none():
    """A Sprint-2 candidate has exemplar_similarity=None; aggregate_fitness
    must skip the dim and average over the present ones."""
    from alphamo.database.operations import aggregate_fitness
    from alphamo.schemas import Scores

    new = Scores(
        feasibility=0.90,
        structural=0.80,
        exemplar_similarity=None,  # Sprint 2 default
        robustness=0.70,
        middle_class_accessible=True,
    )
    # (0.90 + 0.80 + 0.70) / 3 = 0.80
    assert aggregate_fitness(new) == pytest.approx(0.80)

    # Compare against a legacy row that has a similarity value — that one
    # still aggregates over 4 dims for backward-compat.
    legacy = new.model_copy(update={"exemplar_similarity": 0.60})
    # (0.90 + 0.80 + 0.60 + 0.70) / 4 = 0.75
    assert aggregate_fitness(legacy) == pytest.approx(0.75)


def test_cluster_signature_buckets_nearby_scores_together():
    """At resolution=1, 0.78 and 0.83 round to 0.8 and share a signature axis."""
    from alphamo.sampler import cluster_signature
    from alphamo.schemas import Scores

    s_a = Scores(feasibility=0.78, structural=0.50, exemplar_similarity=0.50, middle_class_accessible=True)
    s_b = Scores(feasibility=0.83, structural=0.50, exemplar_similarity=0.50, middle_class_accessible=True)
    assert cluster_signature(s_a, resolution=1) == cluster_signature(s_b, resolution=1)


def test_cluster_signature_separates_far_scores():
    from alphamo.sampler import cluster_signature
    from alphamo.schemas import Scores

    s_a = Scores(feasibility=0.10, structural=0.50, exemplar_similarity=0.50, middle_class_accessible=True)
    s_b = Scores(feasibility=0.90, structural=0.50, exemplar_similarity=0.50, middle_class_accessible=True)
    assert cluster_signature(s_a) != cluster_signature(s_b)


def test_cluster_temperature_decays_within_period():
    """T_cluster decreases linearly with n within a single period."""
    from alphamo.sampler import _cluster_temperature

    t0 = 0.1
    period = 100
    # At n=0, T = T_0; at n=period/2, T = T_0/2; at n=period, T = T_0 (reset).
    assert _cluster_temperature(t0, 0, period) == pytest.approx(t0)
    assert _cluster_temperature(t0, period // 2, period) == pytest.approx(t0 / 2)
    # After one full period, (n mod period) wraps back to 0.
    assert _cluster_temperature(t0, period, period) == pytest.approx(t0)


def test_cluster_temperature_uses_configured_params():
    """The Sampler's stored cluster temperature params reach the formula."""
    from alphamo.sampler import Sampler

    sampler = Sampler(
        db=None,  # not touched in this assertion
        cluster_temperature_t0=0.2,
        cluster_temperature_period=50,
    )
    assert sampler.cluster_temperature_t0 == 0.2
    assert sampler.cluster_temperature_period == 50


def test_clustering_differs_from_naive_fitness_sort(db, default_run):
    """A fitness-tie population scattered across clusters draws differently from a fitness-sorted top-k.

    Build a population where the top-2 by fitness sit in the SAME signature
    bucket (so naive top-k always returns both), but several other clusters
    also have viable candidates. Clustered sampling under a moderate
    temperature must occasionally pick from a different cluster, producing
    draws the naive sampler would not.
    """
    from alphamo.sampler import Sampler, cluster_signature
    from alphamo.schemas import Architecture, Scores

    # Two clusters: one at high fitness (cluster A), several at slightly
    # lower fitness (clusters B, C, D). With T_0=0.1 the chosen-cluster
    # weight on A is dominant but not absolute.
    def _arch(name: str) -> Architecture:
        return Architecture(
            name=name, summary="s", value_chain="vc",
            capture_mechanism="cm", entry_resources="er",
        )

    def _scores(f: float, s: float, x: float) -> Scores:
        return Scores(
            feasibility=f, structural=s, exemplar_similarity=x,
            middle_class_accessible=True,
        )

    # Cluster A: 3 candidates at high fitness.
    for i in range(3):
        db.insert(_arch(f"A{i}"), _scores(0.92, 0.92, 0.92), run_id=default_run)
    # Cluster B / C / D: lower-fitness but still alive.
    db.insert(_arch("B"), _scores(0.50, 0.50, 0.50), run_id=default_run)
    db.insert(_arch("C"), _scores(0.30, 0.70, 0.50), run_id=default_run)
    db.insert(_arch("D"), _scores(0.70, 0.30, 0.50), run_id=default_run)

    # Use a temperature high enough that lower-fitness clusters are sampled
    # with non-trivial probability over many draws.
    sampler = Sampler(
        db, run_id=default_run, rng=random.Random(0),
        cluster_temperature_t0=1.0,
    )
    drawn_names: set[str] = set()
    for _ in range(40):
        seeds = sampler.draw(island_id=0, k=2)
        drawn_names.update(s.architecture.name for s in seeds)

    # At T_0=1.0 across 40 draws we expect to see at least one non-A cluster.
    non_a = {n for n in drawn_names if not n.startswith("A")}
    assert non_a, (
        f"clustered sampler never explored non-top cluster across 40 draws; "
        f"drawn names: {drawn_names}"
    )


def test_clustering_at_low_temperature_concentrates_on_best_cluster(db, default_run):
    """T_0 near zero → almost-always pick the top-aggregate cluster."""
    from alphamo.sampler import Sampler
    from alphamo.schemas import Architecture, Scores

    def _arch(name: str) -> Architecture:
        return Architecture(
            name=name, summary="s", value_chain="vc",
            capture_mechanism="cm", entry_resources="er",
        )

    def _scores(f: float) -> Scores:
        return Scores(
            feasibility=f, structural=f, exemplar_similarity=f,
            middle_class_accessible=True,
        )

    # Two distinct clusters at clearly different fitness levels.
    for i in range(3):
        db.insert(_arch(f"HIGH{i}"), _scores(0.92), run_id=default_run)
    for i in range(3):
        db.insert(_arch(f"LOW{i}"), _scores(0.40), run_id=default_run)

    sampler = Sampler(
        db, run_id=default_run, rng=random.Random(0),
        cluster_temperature_t0=1e-4,  # near-zero ⇒ argmax-like behavior
    )
    high_hits = 0
    total = 30
    for _ in range(total):
        seeds = sampler.draw(island_id=0, k=2)
        if all(s.architecture.name.startswith("HIGH") for s in seeds):
            high_hits += 1
    assert high_hits >= total * 0.8, (
        f"low-temperature sampler should concentrate on best cluster; "
        f"only {high_hits}/{total} draws were all-HIGH"
    )


def test_clustering_falls_back_to_other_clusters_when_chosen_too_small(db, default_run):
    """If chosen cluster has < k programs, fill from other clusters."""
    from alphamo.sampler import Sampler
    from alphamo.schemas import Architecture, Scores

    def _arch(name: str) -> Architecture:
        return Architecture(
            name=name, summary="s", value_chain="vc",
            capture_mechanism="cm", entry_resources="er",
        )

    # Cluster A has just 1 candidate; the rest sit in cluster B.
    db.insert(_arch("solo_A"), Scores(feasibility=0.92, structural=0.92, exemplar_similarity=0.92, middle_class_accessible=True), run_id=default_run)
    for i in range(3):
        db.insert(_arch(f"B{i}"), Scores(feasibility=0.50, structural=0.50, exemplar_similarity=0.50, middle_class_accessible=True), run_id=default_run)

    # Force very low temperature so cluster A is almost-always chosen first.
    sampler = Sampler(
        db, run_id=default_run, rng=random.Random(0),
        cluster_temperature_t0=1e-4,
    )
    seeds = sampler.draw(island_id=0, k=3)
    # Even with cluster A chosen, we should get 3 seeds (1 from A, 2 from B).
    assert len(seeds) == 3
    names = {s.architecture.name for s in seeds}
    assert "solo_A" in names  # the chosen cluster's lone candidate
    assert sum(1 for n in names if n.startswith("B")) >= 2  # fallback fills the rest


# ----------------------------------------------------------------- Sprint 15 (Q7) within-cluster Boltzmann


class _FitnessRow:
    """Minimal stand-in for a Candidate row — _draw_from_cluster reads
    only `.id` and `.fitness`."""

    def __init__(self, id_: int, fitness: float) -> None:
        self.id = id_
        self.fitness = fitness


def _bare_sampler(temperature: float, seed: int = 0) -> Sampler:
    """Build a Sampler with a seeded RNG and no DB access — _draw_from_
    cluster doesn't touch self.db, so we can pass None."""
    return Sampler(
        db=None,  # type: ignore[arg-type]
        temperature=temperature,
        rng=random.Random(seed),
    )


def test_within_cluster_boltzmann_prefers_higher_fitness_at_low_temperature():
    """Sprint 15 (Q7): at T=0.1 the within-cluster draw should
    selection-pressure toward higher-fitness rows.

    Over many independent draws of k=1 from a fixed cluster of four
    rows with fitnesses {0.4, 0.5, 0.6, 0.7}, the empirical pick
    frequencies must match the Boltzmann normalization within
    sampling tolerance. With weights w_i = exp(f_i / 0.1), the
    normalized probabilities are:

        0.4 → ~0.0321  (exp(4)  ≈    54.6)
        0.5 → ~0.0871  (exp(5)  ≈   148.4)
        0.6 → ~0.2369  (exp(6)  ≈   403.4)
        0.7 → ~0.6439  (exp(7)  ≈  1096.6)

    Expected counts at N=4000 with binomial stddev ≈ √(N·p·(1-p)):
        0.4: 128 ± 35
        0.5: 348 ± 56
        0.6: 948 ± 85
        0.7: 2576 ± 96
    Tolerance bands at ±3σ.
    """
    rows = [
        _FitnessRow(1, 0.4),
        _FitnessRow(2, 0.5),
        _FitnessRow(3, 0.6),
        _FitnessRow(4, 0.7),
    ]
    sampler = _bare_sampler(temperature=0.1, seed=42)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    N = 4000
    for _ in range(N):
        picked = sampler._draw_from_cluster(rows, k=1)
        counts[picked[0].id] += 1
    # Ordering invariant: higher fitness picked more than lower fitness.
    assert counts[4] > counts[3] > counts[2] > counts[1]
    # Numerical bands matching the Boltzmann normalization at ±3σ.
    assert abs(counts[1] - 128) < 105
    assert abs(counts[2] - 348) < 168
    assert abs(counts[3] - 948) < 255
    assert abs(counts[4] - 2576) < 288


def test_within_cluster_boltzmann_approaches_uniform_at_high_temperature():
    """Backward-compat invariant: at very high T (here T=1000), the
    Boltzmann weights flatten and the within-cluster draw approaches
    uniform. Across N=4000 draws of k=1 from 4 rows, each row should
    land roughly N/4 = 1000 ± sampling noise. With seed-fixed RNG we
    pin tight enough bounds (±150 = ~15% slack) that a regression to
    deterministic argmax would clearly fail this test."""
    rows = [
        _FitnessRow(1, 0.4),
        _FitnessRow(2, 0.5),
        _FitnessRow(3, 0.6),
        _FitnessRow(4, 0.7),
    ]
    sampler = _bare_sampler(temperature=1000.0, seed=42)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    N = 4000
    for _ in range(N):
        picked = sampler._draw_from_cluster(rows, k=1)
        counts[picked[0].id] += 1
    expected = N // 4
    for cid in (1, 2, 3, 4):
        assert abs(counts[cid] - expected) < 150, (
            f"row {cid} picked {counts[cid]} times; expected ~{expected} "
            "under near-uniform high-temperature Boltzmann"
        )


def test_within_cluster_boltzmann_handles_tied_fitness_uniformly():
    """When all rows have equal fitness, the Boltzmann weights are
    all equal (= exp(0) after the max-shift). The draw must reduce
    to uniform without crashing."""
    rows = [_FitnessRow(i, 0.5) for i in range(1, 5)]
    sampler = _bare_sampler(temperature=0.1, seed=7)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    N = 2000
    for _ in range(N):
        picked = sampler._draw_from_cluster(rows, k=1)
        counts[picked[0].id] += 1
    expected = N // 4
    for cid in (1, 2, 3, 4):
        assert abs(counts[cid] - expected) < 120


def test_within_cluster_boltzmann_returns_all_rows_when_cluster_smaller_than_k():
    """If the cluster contains fewer rows than k, return all of them.
    Preserves the upper-level Sampler.draw fallback semantics at
    sampler.py:219-224."""
    rows = [_FitnessRow(1, 0.5), _FitnessRow(2, 0.7)]
    sampler = _bare_sampler(temperature=0.1)
    picked = sampler._draw_from_cluster(rows, k=5)
    assert {r.id for r in picked} == {1, 2}


def test_within_cluster_boltzmann_no_duplicates_without_replacement():
    """k draws from a cluster must return k DISTINCT rows. The sequential
    weighted draw with explicit remove() must not return the same row
    twice."""
    rows = [_FitnessRow(i, 0.1 * i) for i in range(1, 6)]
    sampler = _bare_sampler(temperature=0.05, seed=1)
    picked = sampler._draw_from_cluster(rows, k=3)
    assert len(picked) == 3
    assert len({r.id for r in picked}) == 3
