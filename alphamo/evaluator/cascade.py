"""Cascade orchestrator — runs stages 1-4 with early termination.

The cascade calls progressively more expensive evaluators (Haiku → Sonnet →
Opus exemplar ‖ Opus adversarial) and stops at the first stage that fails
its threshold. Candidates that fail the middle-class filter exit the
cascade with fitness 0 even if they would otherwise score well — this is
the "filter, not penalty" discipline.

Phase 2: Stage 4 (adversarial robustness scrutiny) joins the cascade.
Stage 4 is NOT a filter — it produces a fitness dimension, not a pass/fail.
Stage 3 and Stage 4 run concurrently when Stages 1 and 2 have passed,
since neither needs the other's output as context.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from alphamo._concurrent import run_parallel
from alphamo.evaluator.middle_class_check import passes_middle_class_filter
from alphamo.evaluator.stage1_feasibility import stage1_feasibility
from alphamo.evaluator.stage2_structured import stage2_structured
from alphamo.evaluator.stage3_exemplars import stage3_exemplars
from alphamo.evaluator.stage4_adversarial import stage4_adversarial
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Stage1Finding,
    Stage2Finding,
    Stage3Finding,
    Stage4Finding,
)


@dataclass(frozen=True)
class CascadeResult:
    """Full cascade output: the final Scores plus per-stage findings."""

    scores: Scores
    stage1: Stage1Finding
    stage2: Stage2Finding | None
    stage3: Stage3Finding | None
    stage4: Stage4Finding | None
    early_exit: str | None


class EvaluatorCascade:
    """Four-stage scoring pipeline with early termination on weak candidates.

    Stages 1-3 are scoring filters that short-circuit on threshold failure.
    Stage 4 is an additive fitness dimension; it produces a robustness score
    that joins the aggregate but does not gate continuation.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        stage1_threshold: float = 0.4,
        stage2_threshold: float = 0.5,
    ) -> None:
        self.client = client or anthropic.Anthropic()
        self.stage1_threshold = stage1_threshold
        self.stage2_threshold = stage2_threshold

    def evaluate(self, architecture: Architecture) -> CascadeResult:
        s1 = stage1_feasibility(architecture, self.client)

        if not passes_middle_class_filter(s1):
            return CascadeResult(
                scores=Scores(
                    feasibility=s1.feasibility,
                    structural=0.0,
                    exemplar_similarity=0.0,
                    robustness=None,
                    middle_class_accessible=False,
                ),
                stage1=s1,
                stage2=None,
                stage3=None,
                stage4=None,
                early_exit="middle_class_filter",
            )

        if s1.feasibility < self.stage1_threshold:
            return CascadeResult(
                scores=Scores(
                    feasibility=s1.feasibility,
                    structural=0.0,
                    exemplar_similarity=0.0,
                    robustness=None,
                    middle_class_accessible=True,
                ),
                stage1=s1,
                stage2=None,
                stage3=None,
                stage4=None,
                early_exit="stage1_feasibility",
            )

        s2 = stage2_structured(architecture, self.client)
        if s2.structural < self.stage2_threshold:
            return CascadeResult(
                scores=Scores(
                    feasibility=s1.feasibility,
                    structural=s2.structural,
                    exemplar_similarity=0.0,
                    robustness=None,
                    middle_class_accessible=True,
                ),
                stage1=s1,
                stage2=s2,
                stage3=None,
                stage4=None,
                early_exit="stage2_structured",
            )

        # Stages 3 and 4 are independent — neither needs the other's output.
        # Run them concurrently; wall-clock ≈ max(s3, s4) instead of sum.
        s3, s4 = run_parallel(
            [
                lambda: stage3_exemplars(architecture, self.client),
                lambda: stage4_adversarial(architecture, self.client),
            ],
            max_workers=2,
        )

        return CascadeResult(
            scores=Scores(
                feasibility=s1.feasibility,
                structural=s2.structural,
                exemplar_similarity=s3.similarity,
                robustness=s4.robustness,
                middle_class_accessible=True,
            ),
            stage1=s1,
            stage2=s2,
            stage3=s3,
            stage4=s4,
            early_exit=None,
        )
