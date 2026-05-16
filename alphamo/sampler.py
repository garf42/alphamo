"""Inner-loop sampler: draws k seed candidates from an island.

Phase 2:
  - Sampler.draw() returns Seed records (architecture + per-dimension scores
    + fitness) so the proposer can render scores into the prompt per
    AlphaEvolve §2.2.
  - Within-island sampling follows FunSearch §A.1: programs are clustered by
    their per-dimension score signature; one cluster is selected via
    Boltzmann selection over cluster aggregate fitness with a decaying
    temperature; k candidates are drawn from the chosen cluster (with
    fallback to neighbouring clusters if the chosen one has fewer than k).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphamo.database import ProgramsDB

from alphamo.schemas import Architecture, Scores

ClusterSignature = tuple[float, float, float | None, bool]


@dataclass(frozen=True)
class Seed:
    """One candidate drawn from the population, with its scoring metadata."""

    architecture: Architecture
    scores: Scores
    fitness: float


def _softmax(values: list[float], temperature: float) -> list[float]:
    scaled = [v / temperature for v in values]
    max_v = max(scaled)
    exps = [math.exp(v - max_v) for v in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def _weighted_sample_without_replacement(
    weights: list[float],
    k: int,
    rng: random.Random | None = None,
) -> list[int]:
    if rng is None:
        rng = random.Random()
    remaining = list(enumerate(weights))
    result: list[int] = []
    for _ in range(min(k, len(remaining))):
        total = sum(w for _, w in remaining)
        threshold = rng.random() * total
        cumulative = 0.0
        for pos, (idx, w) in enumerate(remaining):
            cumulative += w
            if cumulative >= threshold:
                result.append(idx)
                remaining.pop(pos)
                break
    return result


def cluster_signature(scores: Scores, resolution: int = 1) -> ClusterSignature:
    """FunSearch signature: per-dimension scores rounded to `resolution` decimals.

    Programs with the same signature land in the same cluster. The boolean
    `middle_class_accessible` is part of the signature so accessible and
    inaccessible candidates can't share a cluster (in practice inaccessible
    rows get filtered before clustering, but the discipline keeps the
    invariant explicit).

    Sprint 2 redesign: signature dropped from 4 numeric dims to 3 when
    exemplar_similarity was retired as a fitness dimension. Resolution=2
    was tested as a compensating granularity bump and produced 100%
    singleton clusters at every realistic island scale (25-400
    candidates), destroying FunSearch's diversity-preservation property.
    Resolution=1 with 3 dims preserves healthy multi-candidate clusters
    (~125 effective buckets given realistic [0.2, 0.95] cascade output;
    top clusters of 4-7 candidates at 200-400 island scale).

    `robustness` slot rounds None to itself, so candidates that exited
    early (robustness=None) cluster together by-construction — the
    desired behavior since they all failed the same stage.
    """
    robustness = scores.robustness
    rounded_robustness = (
        None if robustness is None else round(robustness, resolution)
    )
    return (
        round(scores.feasibility, resolution),
        round(scores.structural, resolution),
        rounded_robustness,
        bool(scores.middle_class_accessible),
    )


def _cluster_temperature(t0: float, n: int, period: int) -> float:
    """FunSearch §A.1 Eq. 1: T_cluster = T_0 · (1 - (n mod N) / N).

    `n` is the current program count in the island. The temperature decays
    linearly within a period of length `period`, then resets — a long-horizon
    exploration→exploitation schedule. For runs much shorter than `period`,
    T_cluster stays close to T_0.
    """
    return t0 * (1.0 - (n % period) / period)


def _row_to_seed(row) -> Seed:
    return Seed(
        architecture=Architecture(**row.architecture_spec),
        scores=Scores(**row.scores),
        fitness=row.fitness,
    )


class Sampler:
    """Two-stage within-island sampler: cluster, then candidate.

    Algorithm (FunSearch §A.1):
      1. Fetch all alive candidates in the island for this run.
      2. Drop zero-fitness rows (failed the middle-class filter).
      3. Group by cluster_signature (rounded per-dimension scores).
      4. Compute each cluster's aggregate score (max fitness in cluster).
      5. Compute T_cluster from current island population size.
      6. Boltzmann-sample one cluster.
      7. Draw k candidates uniformly without replacement from that cluster.
         If the chosen cluster has fewer than k, fill the remainder by
         drawing from other clusters in fitness order.

    When `run_id` is set, sampling is restricted to that run's candidates.
    """

    def __init__(
        self,
        db: "ProgramsDB",
        temperature: float = 1.0,
        pool_size: int = 1000,
        rng: random.Random | None = None,
        run_id: str | None = None,
        cluster_temperature_t0: float = 0.1,
        cluster_temperature_period: int = 30000,
        cluster_signature_resolution: int = 1,
    ) -> None:
        self.db = db
        self.temperature = temperature
        self.pool_size = pool_size
        self.rng = rng or random.Random()
        self.run_id = run_id
        self.cluster_temperature_t0 = cluster_temperature_t0
        self.cluster_temperature_period = cluster_temperature_period
        self.cluster_signature_resolution = cluster_signature_resolution

    # ------------------------------------------------------------------ public

    def draw(self, island_id: int, k: int = 2) -> list[Seed]:
        """Two-stage clustering draw. Returns up to k Seed records."""
        rows = self.db.top_k_in_island(
            island_id=island_id, k=self.pool_size, run_id=self.run_id
        )
        alive = [r for r in rows if r.fitness > 0.0]
        if not alive:
            return []
        if len(alive) <= k:
            return [_row_to_seed(r) for r in alive]

        # 1. Group by signature.
        clusters: dict[ClusterSignature, list] = {}
        for row in alive:
            sig = cluster_signature(
                Scores(**row.scores), self.cluster_signature_resolution
            )
            clusters.setdefault(sig, []).append(row)

        # 2. Cluster aggregate scores = max fitness in each cluster.
        sig_keys = list(clusters.keys())
        cluster_aggregates = [max(r.fitness for r in clusters[s]) for s in sig_keys]

        # 3. Decaying cluster temperature.
        n = len(alive)
        t_cluster = _cluster_temperature(
            self.cluster_temperature_t0, n, self.cluster_temperature_period
        )
        # Clamp to a minimum to avoid division-by-zero in the Boltzmann
        # exponent when n approaches a period boundary.
        t_cluster = max(t_cluster, 1e-6)

        # 4. Boltzmann-sample one cluster.
        weights = _softmax(cluster_aggregates, t_cluster)
        chosen_idx = _weighted_sample_without_replacement(weights, 1, rng=self.rng)[0]
        chosen_sig = sig_keys[chosen_idx]
        chosen_cluster = clusters[chosen_sig]

        # 5. Draw k uniformly from the chosen cluster.
        chosen_rows = self._draw_from_cluster(chosen_cluster, k)

        # 6. Fallback if the chosen cluster has fewer than k: fill remainder
        # from other clusters by fitness, deterministically.
        if len(chosen_rows) < k:
            already = {r.id for r in chosen_rows}
            others = [r for r in alive if r.id not in already]
            others.sort(key=lambda r: r.fitness, reverse=True)
            need = k - len(chosen_rows)
            chosen_rows.extend(others[:need])

        return [_row_to_seed(r) for r in chosen_rows]

    # ------------------------------------------------------------------ helpers

    def _draw_from_cluster(self, cluster_rows: list, k: int) -> list:
        """Uniform sample without replacement from a cluster."""
        if len(cluster_rows) <= k:
            return list(cluster_rows)
        return self.rng.sample(cluster_rows, k)
