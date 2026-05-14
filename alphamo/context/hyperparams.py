"""Run-level hyperparameters: island count, reset cadence, temperatures, thresholds.

Defaults follow the architecture doc:
  - m=8 islands, reset bottom m/2 every ~200 generations
  - softmax sampling temperature ~0.8
  - milestone fitness 0.7 triggers red-team
  - research fires on stall and on scheduled interval
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

    stage1_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    stage2_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    milestone_fitness: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Fitness at or above this triggers the red-team agent.",
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
