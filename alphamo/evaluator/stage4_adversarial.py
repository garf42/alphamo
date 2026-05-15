"""Stage 4 — adversarial robustness scoring.

Replaces the standalone red-team agent. Every candidate that survives
Stage 3 is scrutinised under 8 adversarial framings (regulatory, economic,
operational, scaling, mechanism_robustness, hidden_dependencies,
scaling_cliffs, legal_exposure) running concurrently. Each framing produces
a list of concerns with falsification conditions and severity. The stage
aggregates the concerns and computes a deterministic robustness score
from their severity-weighted count via exponential decay.

Robustness contributes to fitness as a fourth dimension alongside
feasibility / structural / exemplar_similarity. Concerns are persisted on
the candidate (stage4_findings JSON column) and projected into the
handoff trail.
"""

from __future__ import annotations

import math

import anthropic

from alphamo._concurrent import run_parallel
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

# Default decay rate. Bug 1 fix (Sprint 1): the previous linear
# `1.0 - sum(weights)` formula clamped to 0.0 with anything more than ~4
# HIGH concerns. Run-006 observed 39-53 concerns per candidate, which
# routinely produced weighted sums of 7-10, saturating any linear formula.
# Exponential decay produces graded output across the full realistic range.
DEFAULT_DECAY_K = 0.15


def compute_robustness(
    concerns: list[StructuralConcern],
    decay_k: float = DEFAULT_DECAY_K,
) -> float:
    """Robustness = exp(-decay_k * sum(severity_weight(c) for c in concerns)).

    Exponential decay gives graded output across realistic concern counts:
      0 concerns                    → 1.000
      1 HIGH                        → 0.956
      5 HIGH                        → 0.799
      15 HIGH + 25 MED              → 0.350  (run-006 low end)
      25 HIGH + 28 MED + 4 LOW      → 0.210  (run-006 high end)
      ∞                             → 0.0+ (asymptotic, never clamps to 0)

    The return is mathematically in (0, 1]; no clamping required.
    """
    weighted_sum = sum(_SEVERITY_WEIGHT[c.severity] for c in concerns)
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


def stage4_adversarial(
    architecture: Architecture,
    client: anthropic.Anthropic,
    framings: list[str] | None = None,
    model: str = OPUS_MODEL,
    decay_k: float = DEFAULT_DECAY_K,
) -> Stage4Finding:
    """Run all framings (default: 8) concurrently, aggregate, score robustness.

    Falsification-less concerns are dropped before aggregation. The robustness
    score is deterministic from the surviving concerns' severity — the LLM
    judges concerns, the stage judges the candidate.
    """
    framings = framings if framings is not None else DEFAULT_FRAMINGS
    per_framing = run_parallel(
        [
            (lambda f=f: _run_framing(architecture, client, f, model))
            for f in framings
        ]
    )

    all_concerns: list[StructuralConcern] = []
    for concerns in per_framing:
        all_concerns.extend(concerns)
    all_concerns = _enforce_falsification(all_concerns)

    framings_with_concerns = sorted(
        {c.framing for c in all_concerns}
    )
    framings_clean = [f for f in framings if f not in framings_with_concerns]
    if all_concerns:
        reasoning = (
            f"Concerns surfaced under: {', '.join(framings_with_concerns)}. "
            f"Clean under: {', '.join(framings_clean) if framings_clean else '(none)'}."
        )
    else:
        reasoning = (
            f"All {len(framings)} framings returned clean — no structural "
            "concerns surfaced."
        )

    return Stage4Finding(
        robustness=compute_robustness(all_concerns, decay_k=decay_k),
        concerns=all_concerns,
        reasoning=reasoning,
    )
