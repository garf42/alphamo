"""Run-level hyperparameters: island count, reset cadence, temperatures, thresholds.

Defaults reflect FunSearch / AlphaEvolve calibration:
  - m=8 islands, reset bottom m/2 every ~200 generations
  - softmax sampling temperature ~0.8 (FunSearch uses 1.0; we're slightly
    more exploitative)
  - milestone trigger requires fitness to exceed seed-baseline + delta AND
    generation >= min_generation; the absolute milestone_fitness floor was
    removed in phase 2 because it fires on candidates BELOW the seed
    exemplars
  - cluster temperature follows FunSearch §A.1 (T_0=0.1, N=30000)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Hyperparameters(BaseModel):
    """Tuneable knobs for one production run. Persisted alongside each run."""

    num_islands: int = Field(default=8, ge=2)
    reset_every_generations: int = Field(default=200, ge=1)
    top_seed_count: int = Field(default=5, ge=1)

    pool_size: int = Field(default=8, ge=1)
    k_seeds: int = Field(default=2, ge=1)
    sampling_temperature: float = Field(default=0.8, gt=0.0)

    # FunSearch §A.1 Methods: within-island cluster sampling via Boltzmann
    # selection over cluster aggregate fitness. T_cluster decays as
    #     T_cluster = T_0 * (1 - (n mod N) / N)
    # where n is the current program count in the island. With our generation
    # rate, n stays well below N for any realistic run; the decay is a
    # long-horizon mechanism inherited from FunSearch's defaults.
    cluster_temperature_t0: float = Field(default=0.1, gt=0.0)
    cluster_temperature_period: int = Field(default=30000, ge=1)
    cluster_signature_resolution: int = Field(
        default=1,
        ge=0,
        le=3,
        description=(
            "Decimal places to round each per-dimension score to when forming "
            "the cluster signature. 1 ⇒ {0.0, 0.1, …, 1.0} buckets per axis."
        ),
    )

    stage1_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    stage2_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    stage4_decay_k: float = Field(
        default=0.50,
        gt=0.0,
        description=(
            "Exponential-decay rate for Stage 4's robustness score. "
            "robustness = exp(-stage4_decay_k * weighted_concern_sum). "
            "Calibration history: k=0.15 was tuned for the pre-Sprint-2 "
            "always-find regime (30-50 concerns per candidate). Under the "
            "Sprint 2 reframed prompts (2-10 concerns per candidate), "
            "k=0.50 produces calibrated separation: 0 concerns → 1.00, "
            "2 HIGH → 0.74, 4 HIGH → 0.55, 10 HIGH → 0.22, deep mixed "
            "loads (17+ concerns) → 0.07-0.18. Higher k punishes "
            "concerns more aggressively."
        ),
    )

    milestone_fitness_delta: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Milestone trigger: a candidate's fitness must exceed the run's "
            "seed_baseline_fitness by at least this delta. The seed baseline "
            "is the max aggregate fitness across the gen-0 STARTERS, computed "
            "at run start and persisted into the run's hyperparameters JSON."
        ),
    )
    milestone_min_generation: int = Field(
        default=25,
        ge=0,
        description=(
            "Milestone trigger requires generation >= this. Prevents the "
            "red-team agent from firing during the early-generation warmup "
            "when seed-relative fitness gains are noisy."
        ),
    )

    research_every_generations: int = Field(
        default=50,
        ge=1,
        description="Scheduled research-agent invocation interval.",
    )
    stall_window: int = Field(
        default=15,
        ge=2,
        description="Generation window over which to detect a fitness stall.",
    )
    stall_epsilon: float = Field(
        default=0.01,
        ge=0.0,
        description="Min fitness improvement over the stall window to NOT be stalled.",
    )

    max_consecutive_failures: int = Field(
        default=5,
        ge=1,
        description=(
            "Halt the run after this many consecutive iterations without a "
            "scored candidate (LLM output parsing failures or empty islands). "
            "Guards against burning the API budget on broken outputs."
        ),
    )
