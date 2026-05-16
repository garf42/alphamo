"""Stage 3 — adversarial robustness scoring (renamed from Stage 4 in Sprint 2).

Every candidate that survives Stage 2 is scrutinised under N adversarial
framings running concurrently (currently 9; see
alphamo.prompts.stage4_prompts.DEFAULT_FRAMINGS for the canonical list).
Each framing produces a list of concerns with falsification conditions
and severity. The stage aggregates the concerns and computes a
deterministic robustness score from their severity-weighted count via
exponential decay.

File / symbol names retain the `stage4` historical prefix
(`stage4_adversarial`, `Stage4OutputError`, `STAGE4_AUDIT_TRIGGER`) for
persisted-JSON and audit-log compatibility with pre-Sprint-2 runs. The
conceptual stage is now Stage 3 of three.

Cost: each framing is one independent Opus call running in parallel, so
the stage's per-candidate cost scales linearly with framing count.

SPRINT 4 — TIERED PARTIAL-FAILURE HANDLING:

A single framing's API failure no longer aborts the whole candidate
evaluation. The new flow:

  - All 9 framings run concurrently via `run_parallel_collect_results`.
    Exceptions are caught and returned in place of results.
  - If ≥ STAGE3_MIN_SUCCESSFUL_FRAMINGS succeeded: compute robustness
    from the successful framings' concerns, append a `_meta` sentinel
    concern recording the failed framings (so the partial-coverage
    fact is persisted on the candidate row), and continue normally.
  - If < STAGE3_MIN_SUCCESSFUL_FRAMINGS succeeded: raise
    Stage4OutputError so the orchestrator treats this candidate as
    a cascade-level failure (not inserted as alive, counts toward
    `consecutive_failures`).

The 5-of-9 threshold is a constant (not a Hyperparameter); promote to
HP if we need to tune. The Anthropic SDK's `max_retries=3` (configured
at client construction) absorbs transient 408/409/429/500+/connection
errors before a failure reaches us, so a "failed framing" by the time
it gets here is a genuinely persistent failure — not a transient blip.
"""

from __future__ import annotations

import math

import anthropic

from alphamo._concurrent import run_parallel_collect_results
from alphamo.errors import Stage4OutputError, parse_or_raise
from alphamo.evaluator._common import MAX_TOKENS_LONG, OPUS_MODEL, cached_system
from alphamo.prompts.stage4_prompts import (
    DEFAULT_FRAMINGS,
    render_candidate,
    stage4_system,
)
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    RawFindingsBatch,
    Severity,
    Stage4Finding,
    StructuralConcern,
)

# Per-concern severity weights — sum these across all concerns to get the
# weighted concern total, then feed into the exponential decay below.
# Preserved from the Phase 2 calibration: HIGH=0.30, MEDIUM=0.10, LOW=0.03.
_SEVERITY_WEIGHT: dict[Severity, float] = {
    Severity.HIGH: 0.30,
    Severity.MEDIUM: 0.10,
    Severity.LOW: 0.03,
}

# Default decay rate. Calibration history:
#   - Bug 1 fix (Sprint 1): the prior linear `1.0 - sum(weights)` formula
#     clamped to 0.0 with anything more than ~4 HIGH concerns. Switched
#     to exponential decay with k=0.15, tuned for the pre-Sprint-2
#     always-find regime (run-006 observed 39-53 concerns per candidate).
#   - Sprint 2 recalibration: the reframed prompts produce 2-10 concerns
#     per candidate. k=0.15 in that regime leaves robustness inflated
#     (Satoshi 0.835, Rowling 0.914 — implausible for 1990s-era patterns).
#     Bumped to k=0.50, which produces calibrated separation:
#       0 concerns         → 1.00
#       2 HIGH (Rowling)   → 0.74
#       4 HIGH (Satoshi)   → 0.55
#       10 HIGH            → 0.22
#       17 mixed (Levels)  → 0.18
#       27 mixed (Medvi)   → 0.07
DEFAULT_DECAY_K = 0.50

# Sprint 4: tiered partial-failure threshold. With 9 framings, ≥5 must
# succeed for the candidate to be scored at all. Below threshold the
# signal is too degraded to trust — the candidate is treated as a
# cascade-level failure.
STAGE3_MIN_SUCCESSFUL_FRAMINGS = 5

# Sentinel framing name used to record which framings failed in the
# persisted stage4_findings JSON. The compute_robustness function and
# all downstream consumers (handoff, audit) filter this out so it never
# contributes to the robustness score, but it remains queryable for
# forensics.
FAILED_FRAMINGS_SENTINEL = "_meta"


def compute_robustness(
    concerns: list[StructuralConcern],
    decay_k: float = DEFAULT_DECAY_K,
) -> float:
    """Robustness = exp(-decay_k * sum(severity_weight(c) for c in concerns)).

    Sprint 4: `_meta` sentinel concerns (used to record failed framings)
    are filtered out before weighting — they're forensic metadata, not
    real findings against the candidate.

    Exponential decay gives graded output across realistic concern counts:
      0 concerns                    → 1.000
      1 HIGH                        → 0.956
      5 HIGH                        → 0.799
      15 HIGH + 25 MED              → 0.350  (run-006 low end)
      25 HIGH + 28 MED + 4 LOW      → 0.210  (run-006 high end)
      ∞                             → 0.0+ (asymptotic, never clamps to 0)

    The return is mathematically in (0, 1]; no clamping required.
    """
    real_concerns = [c for c in concerns if c.framing != FAILED_FRAMINGS_SENTINEL]
    weighted_sum = sum(_SEVERITY_WEIGHT[c.severity] for c in real_concerns)
    return math.exp(-decay_k * weighted_sum)


def _enforce_falsification(
    concerns: list[StructuralConcern],
) -> list[StructuralConcern]:
    """Drop concerns whose falsification_condition is blank — the discipline
    that lets the curator distinguish structural from cosmetic.
    """
    return [c for c in concerns if c.falsification_condition.strip()]


def _run_framing(
    architecture: Architecture,
    client: anthropic.Anthropic,
    framing: str,
    model: str,
) -> list[StructuralConcern]:
    """Single Opus call for one framing; tag returned concerns with the framing."""
    batch: RawFindingsBatch = parse_or_raise(
        client,
        Stage4OutputError,
        detail=f"framing={framing!r}",
        model=model,
        max_tokens=MAX_TOKENS_LONG,
        thinking={"type": "adaptive"},
        system=cached_system(stage4_system(framing)),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=RawFindingsBatch,
    )
    return [
        StructuralConcern(
            framing=framing,
            claim=raw.claim,
            evidence=raw.evidence,
            falsification_condition=raw.falsification_condition,
            severity=raw.severity,
        )
        for raw in batch.findings
    ]


def _failed_framings_sentinel(failed_framings: list[str]) -> StructuralConcern:
    """Build the `_meta` sentinel concern that records the failed framings.

    Persisted as part of the candidate's stage4_findings JSON so the
    partial-coverage fact survives any audit-log loss. compute_robustness
    and downstream consumers filter on `framing == FAILED_FRAMINGS_SENTINEL`.
    """
    return StructuralConcern(
        framing=FAILED_FRAMINGS_SENTINEL,
        claim="framings_failed",
        evidence=", ".join(failed_framings),
        falsification_condition="all framings complete successfully",
        severity=Severity.LOW,
    )


def stage4_adversarial(
    architecture: Architecture,
    client: anthropic.Anthropic,
    framings: list[str] | None = None,
    model: str = OPUS_MODEL,
    decay_k: float = DEFAULT_DECAY_K,
) -> Stage4Finding:
    """Run all framings concurrently with tiered partial-failure handling.

    Sprint 4 behavior:
      - All framings run in parallel via `run_parallel_collect_results`.
      - If ≥ STAGE3_MIN_SUCCESSFUL_FRAMINGS succeed: build Stage4Finding
        from survivors; append `_meta` sentinel concern recording the
        failed framings; reasoning field notes partial coverage.
      - If < STAGE3_MIN_SUCCESSFUL_FRAMINGS succeed: raise
        Stage4OutputError. The orchestrator's cascade-failure path
        catches this and treats the candidate as not-inserted.

    Falsification-less concerns are dropped before aggregation. The
    robustness score is deterministic from the surviving concerns'
    severity — the LLM judges concerns, the stage judges the candidate.
    """
    framings = framings if framings is not None else DEFAULT_FRAMINGS

    raw_results = run_parallel_collect_results(
        [
            (lambda f=f: _run_framing(architecture, client, f, model))
            for f in framings
        ]
    )

    succeeded_framings: list[str] = []
    failed_framings: list[str] = []
    all_concerns: list[StructuralConcern] = []
    for framing, result in zip(framings, raw_results):
        if isinstance(result, Exception):
            failed_framings.append(framing)
        else:
            succeeded_framings.append(framing)
            all_concerns.extend(result)

    if len(succeeded_framings) < STAGE3_MIN_SUCCESSFUL_FRAMINGS:
        # Catastrophic Stage 3 failure: signal is too degraded to score
        # the candidate. Raise so the orchestrator's existing
        # `except LLMOutputError` path counts this as an iteration
        # failure and skips insertion.
        raise Stage4OutputError(
            stop_reason="stage3_catastrophic_framing_failure",
            content_block_types=[],
            detail=(
                f"only {len(succeeded_framings)} of {len(framings)} framings "
                f"succeeded (min required: {STAGE3_MIN_SUCCESSFUL_FRAMINGS}); "
                f"failed_framings={failed_framings}"
            ),
        )

    all_concerns = _enforce_falsification(all_concerns)

    framings_with_concerns = sorted({c.framing for c in all_concerns})
    framings_clean = [
        f for f in succeeded_framings if f not in framings_with_concerns
    ]
    if all_concerns:
        reasoning = (
            f"Concerns surfaced under: {', '.join(framings_with_concerns)}. "
            f"Clean under: {', '.join(framings_clean) if framings_clean else '(none)'}."
        )
    else:
        reasoning = (
            f"All {len(succeeded_framings)} succeeded framings returned clean "
            "— no structural concerns surfaced."
        )

    if failed_framings:
        reasoning += (
            f" PARTIAL COVERAGE: {len(failed_framings)} of {len(framings)} "
            f"framings failed ({', '.join(failed_framings)}); robustness "
            "computed from the surviving framings only."
        )
        # Persist failed-framing list as a sentinel concern so the
        # partial-coverage fact survives in the candidate's
        # stage4_findings JSON. Filtered out of compute_robustness.
        all_concerns.append(_failed_framings_sentinel(failed_framings))

    return Stage4Finding(
        robustness=compute_robustness(all_concerns, decay_k=decay_k),
        concerns=all_concerns,
        reasoning=reasoning,
    )
