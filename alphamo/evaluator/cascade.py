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
from typing import Any

from alphamo.errors import TelemetryContext
from alphamo.evaluator.middle_class_check import passes_middle_class_filter
from alphamo.evaluator.stage1_feasibility import stage1_feasibility
from alphamo.evaluator.stage2_structured import stage2_structured
from alphamo.evaluator.stage4_adversarial import stage4_adversarial
from alphamo.providers.base import BaseProvider, ensure_provider
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
        client: Any = None,
        stage1_threshold: float = 0.4,
        stage2_threshold: float = 0.5,
        stage4_decay_k: float = 0.50,
        stage1_provider: BaseProvider | None = None,
        stage2_provider: BaseProvider | None = None,
        stage3_provider: BaseProvider | None = None,
        stage1_model: str | None = None,
        stage2_model: str | None = None,
        stage3_model: str | None = None,
        stage3_reasoning_effort: str | None = "high",
    ) -> None:
        # Sprint 14: per-stage provider routing. Backward-compat path
        # (a single `client`) still works — auto-wrapped to a single
        # provider used for all three stages. The orchestrator passes
        # per-stage providers/models from Hyperparameters for the
        # production multi-provider path.
        if client is None and stage1_provider is None:
            from alphamo.providers.factory import build_provider

            shared = build_provider("anthropic")
            self.stage1_provider = stage1_provider or shared
            self.stage2_provider = stage2_provider or shared
            self.stage3_provider = stage3_provider or shared
        elif client is not None:
            shared = ensure_provider(client)
            self.stage1_provider = stage1_provider or shared
            self.stage2_provider = stage2_provider or shared
            self.stage3_provider = stage3_provider or shared
        else:
            # explicit per-stage providers supplied
            assert stage1_provider is not None
            self.stage1_provider = stage1_provider
            self.stage2_provider = stage2_provider or stage1_provider
            self.stage3_provider = stage3_provider or stage1_provider

        self.stage1_model = stage1_model
        self.stage2_model = stage2_model
        self.stage3_model = stage3_model
        self.stage3_reasoning_effort = stage3_reasoning_effort
        self.stage1_threshold = stage1_threshold
        self.stage2_threshold = stage2_threshold
        # Field name kept as `stage4_decay_k` for persisted-JSON
        # compatibility; the constant gates the adversarial scrutiny
        # robustness decay regardless of conceptual stage number.
        self.stage4_decay_k = stage4_decay_k

    def evaluate(
        self,
        architecture: Architecture,
        telemetry: TelemetryContext | None = None,
    ) -> CascadeResult:
        s1_kwargs: dict[str, Any] = {"telemetry": telemetry}
        if self.stage1_model is not None:
            s1_kwargs["model"] = self.stage1_model
        s1 = stage1_feasibility(architecture, self.stage1_provider, **s1_kwargs)

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

        s2_kwargs: dict[str, Any] = {"telemetry": telemetry}
        if self.stage2_model is not None:
            s2_kwargs["model"] = self.stage2_model
        s2 = stage2_structured(architecture, self.stage2_provider, **s2_kwargs)
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
        s3_kwargs: dict[str, Any] = {
            "decay_k": self.stage4_decay_k,
            "telemetry": telemetry,
            "reasoning_effort": self.stage3_reasoning_effort,
        }
        if self.stage3_model is not None:
            s3_kwargs["model"] = self.stage3_model
        s3 = stage4_adversarial(architecture, self.stage3_provider, **s3_kwargs)

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
