"""Cascade orchestrator — runs 3 stages with early termination.

The cascade calls progressively more expensive evaluators (Haiku → Sonnet →
Opus adversarial) and stops at the first stage that fails its threshold.
Candidates that fail the middle-class filter exit the cascade with fitness
0 even if they would otherwise score well — this is the "filter, not
penalty" discipline.

Stages:
  - Stage 1 (Haiku) — feasibility + middle-class filter
  - Stage 2 (Sonnet) — structural criteria (one-person threshold, $1B
    potential, labor separation)
  - Stage 3 (Opus, was Stage 4) — adversarial scrutiny under multiple
    framings, producing a robustness score

Stage 3 (adversarial) is NOT a filter — it produces a fitness dimension,
not a pass/fail. It runs after Stage 2 passes.

Renumbering history: The original Stage 3 was an exemplar-similarity
comparison against the four reference seeds. It was retired in the
Sprint 2 redesign (seeds became reference-only; similarity stopped
contributing to fitness because it punished novelty). What was Stage 4
(adversarial scrutiny) is now conceptually Stage 3. Code-level
identifiers `stage4_adversarial` / `stage4_decay_k` are preserved for
persisted-JSON compatibility with older runs and audit logs; only the
CascadeResult field names reflect the new numbering.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from alphamo.evaluator.middle_class_check import passes_middle_class_filter
from alphamo.evaluator.stage1_feasibility import stage1_feasibility
from alphamo.evaluator.stage2_structured import stage2_structured
from alphamo.evaluator.stage4_adversarial import stage4_adversarial
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
)


@dataclass(frozen=True)
class CascadeResult:
    """Cascade output: the final Scores plus per-stage findings.

    `stage3` holds adversarial-scrutiny output (the renamed Stage 4
    finding type — `Stage4Finding` retains its historical class name).
    `stage2` is None on Stage 1 failure / middle-class filter exit.
    `stage3` is None when adversarial scrutiny didn't run (any early exit).
    """

    scores: Scores
    stage1: Stage1Finding
    stage2: Stage2Finding | None
    stage3: Stage4Finding | None
    early_exit: str | None


class EvaluatorCascade:
    """Three-stage scoring pipeline with early termination on weak candidates.

    Stages 1-2 are scoring filters that short-circuit on threshold failure.
    Stage 3 (adversarial) is an additive fitness dimension; it produces a
    robustness score that joins the aggregate but does not gate continuation.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        stage1_threshold: float = 0.4,
        stage2_threshold: float = 0.5,
        stage4_decay_k: float = 0.50,
    ) -> None:
        # max_retries=3 — see Sprint 4 commit. The CLI passes a
        # pre-configured client (also with max_retries=3); the fallback
        # here protects ad-hoc / library callers that didn't supply one.
        self.client = client or anthropic.Anthropic(max_retries=3)
        self.stage1_threshold = stage1_threshold
        self.stage2_threshold = stage2_threshold
        # Field name kept as `stage4_decay_k` for persisted-JSON
        # compatibility; the constant gates the adversarial scrutiny
        # robustness decay regardless of conceptual stage number.
        self.stage4_decay_k = stage4_decay_k

    def evaluate(self, architecture: Architecture) -> CascadeResult:
        s1 = stage1_feasibility(architecture, self.client)

        if not passes_middle_class_filter(s1):
            return CascadeResult(
                scores=Scores(
                    feasibility=s1.feasibility,
                    structural=0.0,
                    exemplar_similarity=None,
                    robustness=None,
                    middle_class_accessible=False,
                ),
                stage1=s1,
                stage2=None,
                stage3=None,
                early_exit="middle_class_filter",
            )

        if s1.feasibility < self.stage1_threshold:
            return CascadeResult(
                scores=Scores(
                    feasibility=s1.feasibility,
                    structural=0.0,
                    exemplar_similarity=None,
                    robustness=None,
                    middle_class_accessible=True,
                ),
                stage1=s1,
                stage2=None,
                stage3=None,
                early_exit="stage1_feasibility",
            )

        s2 = stage2_structured(architecture, self.client)
        if s2.structural < self.stage2_threshold:
            return CascadeResult(
                scores=Scores(
                    feasibility=s1.feasibility,
                    structural=s2.structural,
                    exemplar_similarity=None,
                    robustness=None,
                    middle_class_accessible=True,
                ),
                stage1=s1,
                stage2=s2,
                stage3=None,
                early_exit="stage2_structured",
            )

        # Adversarial scrutiny (was Stage 4) is now the only post-Stage-2
        # work — no parallel exemplar comparison.
        s3 = stage4_adversarial(
            architecture, self.client, decay_k=self.stage4_decay_k
        )

        return CascadeResult(
            scores=Scores(
                feasibility=s1.feasibility,
                structural=s2.structural,
                exemplar_similarity=None,
                robustness=s3.robustness,
                middle_class_accessible=True,
            ),
            stage1=s1,
            stage2=s2,
            stage3=s3,
            early_exit=None,
        )
