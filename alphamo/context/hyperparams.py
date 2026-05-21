"""Run-level hyperparameters: island count, reset cadence, temperatures, thresholds.

Defaults reflect FunSearch / AlphaEvolve calibration:
  - m=8 islands, reset bottom m/2 every ~200 generations
  - softmax sampling temperature ~0.8 (FunSearch uses 1.0; we're slightly
    more exploitative)
  - milestone trigger uses absolute fitness + robustness thresholds, not
    seed-relative; the seed-baseline mechanism was removed when seeds
    stopped being scored candidates (see exemplar_library.py)
  - cluster temperature follows FunSearch §A.1 (T_0=0.1, N=30000)

`extra="ignore"` is set so that runs created under older schemas (with
keys like `seed_baseline_fitness` or `milestone_fitness_delta` in the
persisted JSON) still load. Those keys are silently dropped on read.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Hyperparameters(BaseModel):
    """Tuneable knobs for one production run. Persisted alongside each run."""

    model_config = ConfigDict(extra="ignore")

    num_islands: int = Field(default=8, ge=2)
    reset_every_generations: int = Field(
        default=40,
        ge=1,
        description=(
            "Cadence of FunSearch-style island reset. Sprint 11 raised the "
            "default 10 → 40 for the 200-generation target run length. At "
            "cadence 10 over 200 gens, 20 reset events fire with only ~10 "
            "generations between resets — not enough for within-island "
            "evolution to produce diversity worth propagating. At cadence "
            "40, 5 reset events fire with ~40 generations between, "
            "matching FunSearch's 'occasional' character at our scale. "
            "The Sprint 3 default of 10 was calibrated for 15-100 gen "
            "runs; the pre-Sprint-3 default of 200 effectively disabled "
            "reset for any realistic run."
        ),
    )
    top_seed_count: int = Field(
        default=1,
        ge=1,
        description=(
            "Number of top programs to copy when reseeding a weak island "
            "post-reset. FunSearch (Nature 2023): a single program from a "
            "uniformly-randomly-chosen surviving island. We keep this "
            "field for backward compatibility with persisted-JSON HP, but "
            "the FunSearch-correct reset path in IslandsManager always "
            "copies one program per weak-island independently."
        ),
    )

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
            "the cluster signature. 1 ⇒ {0.0, 0.1, …, 1.0} buckets per axis. "
            "With 3 score dimensions, resolution=1 yields ~125 effective "
            "buckets given realistic [0.2, 0.95] cascade output, which "
            "preserves multi-candidate clusters at typical island scale "
            "(25-400 candidates). Resolution=2 was tested and degenerates "
            "to 100% singletons at every realistic scale — do not bump."
        ),
    )

    stage1_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    stage2_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    stage4_decay_k: float = Field(
        default=0.50,
        gt=0.0,
        description=(
            "Exponential-decay rate for the adversarial robustness score. "
            "robustness = exp(-stage4_decay_k * weighted_concern_sum). "
            "Calibration history: k=0.15 was tuned for the pre-Sprint-2 "
            "always-find regime (30-50 concerns per candidate). Under the "
            "Sprint 2 reframed prompts (2-10 concerns per candidate), "
            "k=0.50 produces calibrated separation: 0 concerns → 1.00, "
            "2 HIGH → 0.74, 4 HIGH → 0.55, 10 HIGH → 0.22, deep mixed "
            "loads (17+ concerns) → 0.07-0.18. Higher k punishes "
            "concerns more aggressively. Field kept as `stage4_decay_k` "
            "for persisted-JSON compatibility with older runs even though "
            "adversarial scrutiny is now conceptually Stage 3."
        ),
    )

    milestone_absolute_fitness_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description=(
            "Milestone trigger: candidate aggregate fitness must exceed this "
            "absolute floor to qualify. With 3-dim aggregation (feasibility "
            "+ structural + robustness, similarity dropped), 0.80 requires "
            "average ≥ 0.80 across the three dimensions. Replaces the prior "
            "seed-relative `seed_baseline_fitness + milestone_fitness_delta` "
            "comparison, which was abandoned when seeds stopped being "
            "scored candidates."
        ),
    )
    milestone_absolute_robustness_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description=(
            "Milestone trigger: candidate robustness must exceed this "
            "absolute floor to qualify. Under stage4_decay_k=0.50, "
            "robustness ≥ 0.70 caps weighted concern sum at ≤ 0.71 — "
            "roughly ≤ 2 HIGH or ≤ 7 MEDIUM concerns (or any equivalent "
            "mix). Plausible bar for 'this candidate withstood adversarial "
            "scrutiny'."
        ),
    )
    milestone_min_generation: int = Field(
        default=25,
        ge=0,
        description=(
            "Milestone trigger requires generation >= this. Prevents the "
            "red-team agent from firing during the early-generation warmup "
            "when fitness signal is noisy."
        ),
    )

    # Sprint 12: `research_every_generations` removed alongside the
    # research module. Layer B's per-run-start refresh provides
    # current-developments grounding so the scheduled-research
    # invocation isn't needed.
    #
    # `stall_window` and `stall_epsilon` are RETAINED as orphan
    # configuration. detect_stall() previously fired only via the
    # removed `_maybe_research` path; the method body still exists
    # in case future work wants stall-only audit logging without
    # triggering research. Flagged in Sprint 12 commit message;
    # decision to drop or repurpose deferred.
    stall_window: int = Field(
        default=15,
        ge=2,
        description=(
            "Generation window over which to detect a fitness stall. "
            "Sprint 12: orphan config — was consumed only by the "
            "removed research-trigger path. Retained pending decision "
            "on stall-only audit logging."
        ),
    )
    stall_epsilon: float = Field(
        default=0.01,
        ge=0.0,
        description=(
            "Min fitness improvement over the stall window to NOT be "
            "stalled. Sprint 12: orphan (see stall_window note)."
        ),
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
