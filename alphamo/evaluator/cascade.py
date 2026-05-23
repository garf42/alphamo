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
from alphamo.evaluator.stage1_feasibility import (
    apply_stage1_soft_zone,
    compute_feasibility,
    stage1_feasibility,
)
from alphamo.evaluator.stage2_structured import compute_structural, stage2_structured
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
        # Sprint Stage 1 PAJAMA: the model no longer returns a feasibility
        # float; the score comes from the deterministic Python function
        # `compute_feasibility` applied to the model's evidence fields.
        # See alphamo/evaluator/stage1_feasibility.py for the formula
        # and weight constants.
        s1_raw_feasibility = compute_feasibility(s1)

        # The middle-class filter is an INDEPENDENT structural gate per
        # PARENT_GOAL — checked before any feasibility-zone logic. False
        # here triggers a hard fitness-to-zero exit regardless of the
        # rest of the evidence.
        if not passes_middle_class_filter(s1):
            return CascadeResult(
                scores=Scores(
                    feasibility=s1_raw_feasibility,
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

        # Sprint Stage 1 PAJAMA: the pre-PAJAMA hard threshold at
        # `stage1_threshold` (default 0.4) created a cliff that
        # amplified per-call evidence-extraction variance into
        # bimodal early-exit outcomes. The new path runs a three-
        # region soft penalty zone via `apply_stage1_soft_zone`:
        #   - raw < STAGE1_HARD_FLOOR  → hard exit
        #   - raw < STAGE1_SOFT_CEILING → penalty zone, continue with
        #     adjusted feasibility = raw² / SOFT_CEILING (continuous
        #     at the ceiling)
        #   - raw >= STAGE1_SOFT_CEILING → clean pass, no penalty
        # `self.stage1_threshold` is preserved on the cascade for
        # back-compat with persisted HP but is no longer consulted by
        # the gate logic.
        s1_adjusted_feasibility, s1_zone = apply_stage1_soft_zone(s1_raw_feasibility)
        if s1_zone == "hard_exit":
            return CascadeResult(
                scores=Scores(
                    feasibility=s1_adjusted_feasibility,
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
        # Sprint Stage 2 PAJAMA: the model no longer returns a structural
        # float; the score comes from the deterministic Python function
        # `compute_structural` applied to the model's evidence fields.
        # See alphamo/evaluator/stage2_structured.py for the formula and
        # weight constants. The threshold gate still compares against
        # `hp.stage2_threshold` (default 0.5); the comparand is now the
        # PAJAMA-computed scalar.
        s2_structural = compute_structural(s2)
        if s2_structural < self.stage2_threshold:
            return CascadeResult(
                scores=Scores(
                    feasibility=s1_adjusted_feasibility,
                    structural=s2_structural,
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
                feasibility=s1_adjusted_feasibility,
                structural=s2_structural,
                exemplar_similarity=None,
                robustness=s3.robustness,
                middle_class_accessible=True,
            ),
            stage1=s1,
            stage2=s2,
            stage3=s3,
            early_exit=None,
        )
