"""Stage 1 — evidence extraction + deterministic feasibility score.

Sprint 14: routed through `BaseProvider.parse(...)`. Production
default is Fireworks/DeepSeek V4 Flash. No reasoning config — Stage 1
is cheap-tier structured classification.

Sprint Stage 1 PAJAMA: the LLM call returns evidence (categoricals +
booleans + lists), not a feasibility-score float. `compute_feasibility`
maps the evidence to a deterministic scalar — mirroring Stage 2 PAJAMA
and Stage 3's long-standing pattern. Pre-PAJAMA the model produced a
single `feasibility` float and the cascade trusted it directly; the
variance test (commit bcdb86c, 3 candidates × 5 trials) showed
stdev 0.239-0.278 on that float, and the hard threshold at 0.4 turned
the noise into bimodal early-exit outcomes (a candidate near the
threshold randomly got included or excluded based on extraction
noise).

Two design decisions distinguish Stage 1 PAJAMA from Stage 2 PAJAMA:

  1. ADDITIVE FORMULA. compute_feasibility sums bounded per-component
     contributions rather than multiplying. A single boolean flip
     shifts the output by at most ~0.15 rather than the 70% swing a
     0.3x multiplicative penalty would produce. This makes the score
     more robust to per-call evidence-extraction variance.

  2. SOFT PENALTY ZONE replaces the hard threshold. Pre-PAJAMA the
     cascade exited at `s1.feasibility < stage1_threshold (0.4)` —
     a cliff that amplified noise into binary outcomes. Post-PAJAMA
     the cascade has THREE feasibility regions:
       - feasibility < STAGE1_HARD_FLOOR (0.15): hard exit, no
         downstream stages
       - STAGE1_HARD_FLOOR <= feasibility < STAGE1_SOFT_CEILING (0.45):
         penalty zone, candidate continues to Stage 2 but with the
         feasibility scaled down by (raw / ceiling) so the curve is
         continuous at the ceiling
       - feasibility >= STAGE1_SOFT_CEILING: clean pass, no penalty
     See `cascade.py` for the gate logic; the constants below are the
     authoritative source.

`middle_class_accessible=False` continues to trigger an INDEPENDENT
hard fitness-to-zero gate at the cascade level (the PARENT_GOAL's
third constraint is a structural filter, not a soft preference). The
soft-zone logic above only governs the FEASIBILITY axis; the MC axis
remains binary.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import Stage1OutputError, TelemetryContext
from alphamo.evaluator._common import HAIKU_MODEL, MAX_TOKENS_MEDIUM, cached_system
from alphamo.prompts.evaluator_prompts import STAGE1_SYSTEM, render_candidate
from alphamo.providers.base import ensure_provider
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    BuyerAccessibility,
    CapitalRequired,
    RegulatorySeverity,
    RevenueType,
    Stage1Finding,
)


# --------------------------------------------------------------------- compute_feasibility

# Per-RevenueType contribution to compute_feasibility's revenue
# component. Range [0, 0.30]. Recurring/transactional/licensing-style
# mechanisms score top of band; "unclear" is a near-zero output that
# nonetheless preserves SOME signal when the model couldn't classify.
_REVENUE_TYPE_SCORES: dict[RevenueType, float] = {
    RevenueType.RECURRING: 0.30,
    RevenueType.TRANSACTIONAL: 0.25,
    RevenueType.ASSET_APPRECIATION: 0.25,
    RevenueType.LICENSING: 0.25,
    RevenueType.ARBITRAGE: 0.20,
    RevenueType.HYBRID: 0.22,
    RevenueType.UNCLEAR: 0.08,
}

# Per-BuyerAccessibility contribution. Range [0, 0.25]. Direct B2C / B2B
# paths score highest; intermediary / government-contract paths score
# lower because they introduce a dependency the operator doesn't
# control.
_BUYER_ACCESSIBILITY_SCORES: dict[BuyerAccessibility, float] = {
    BuyerAccessibility.DIRECT_TO_CONSUMER: 0.25,
    BuyerAccessibility.DIRECT_TO_BUSINESS: 0.25,
    BuyerAccessibility.REQUIRES_INTERMEDIARY: 0.18,
    BuyerAccessibility.REQUIRES_GOVERNMENT_CONTRACT: 0.12,
    BuyerAccessibility.UNCLEAR: 0.08,
}

# Per-CapitalRequired contribution. Range [0, 0.15]. Calibrated against
# the PARENT_GOAL middle-class-entry constraint ($10K-$50K savings):
# "none" and "under_10k" are clearly accessible (top of band);
# "over_1m" is effectively a hard "no" on the capital axis (bottom).
_CAPITAL_SCORES: dict[CapitalRequired, float] = {
    CapitalRequired.NONE: 0.15,
    CapitalRequired.UNDER_10K: 0.13,
    CapitalRequired.BETWEEN_10K_AND_100K: 0.09,
    CapitalRequired.BETWEEN_100K_AND_1M: 0.04,
    CapitalRequired.OVER_1M: 0.01,
    CapitalRequired.UNQUANTIFIABLE: 0.05,
}

# Per-RegulatorySeverity penalty. Range [-0.15, 0]. Severity is the
# bottom-line aggregate read; the per-blocker penalty below adds an
# incremental cost per specific named blocker so two-axis evidence
# (severity AND blocker count) both shape the output.
_REGULATORY_PENALTIES: dict[RegulatorySeverity, float] = {
    RegulatorySeverity.NONE: 0.0,
    RegulatorySeverity.MANAGEABLE: -0.03,
    RegulatorySeverity.SIGNIFICANT: -0.08,
    RegulatorySeverity.PROHIBITIVE: -0.15,
}

# Per-named-blocker incremental penalty. Gentle (0.01 per entry) so
# many specific blockers add up to a meaningful penalty but no single
# entry dominates. Stacks additively on top of the base severity
# penalty above.
_PER_REGULATORY_BLOCKER_PENALTY = 0.01

# Per-feasibility-risk penalty. Slightly larger than the regulatory-
# blocker penalty (0.02) because execution risks tend to be more
# binary in outcome (API gets revoked = full break) than regulatory
# friction (manageable to fight per-jurisdiction).
_PER_FEASIBILITY_RISK_PENALTY = 0.02

# Bonus for existing-market-validation evidence. Range [0, 0.10].
# Reflects "someone is already paying for something similar" — proof
# of buyer willingness-to-pay regardless of competitive intensity.
_EXISTING_MARKET_VALIDATION_BONUS = 0.10

# Bonus for middle-class-accessible=True. Range [0, 0.15]. Note: the
# False case is handled by the INDEPENDENT hard fitness-to-zero gate
# at `cascade.py` (the PARENT_GOAL filter). This bonus rewards
# candidates that are actively accessible, not just "not excluded".
_MIDDLE_CLASS_ACCESSIBLE_BONUS = 0.15

# --- soft penalty zone constants (consumed by cascade.py) ---

# Below this feasibility score, the cascade exits early with
# structural=0.0 and no Stage-2/Stage-3 invocation. Calibrated to
# catch architectures with no revenue mechanism, no buyer, AND
# significant regulatory burden — a configuration that has no
# plausible $1B+ path even with downstream Stage-2-onward work.
STAGE1_HARD_FLOOR = 0.15

# At and above this feasibility score, the cascade applies no
# penalty — the candidate proceeds with the raw compute_feasibility
# output as its Scores.feasibility. Between HARD_FLOOR and
# SOFT_CEILING the candidate proceeds but with feasibility scaled
# down by (raw / SOFT_CEILING). Calibrated so a candidate that
# clearly identifies a revenue mechanism + buyer (per the bucket
# scores above) lands above ceiling.
STAGE1_SOFT_CEILING = 0.45


def compute_feasibility(finding: Stage1Finding) -> float:
    """Deterministic feasibility score from Stage 1 evidence fields.

    Range: [0.0, 1.0]. Analogous to `compute_robustness` (Stage 3) and
    `compute_structural` (Stage 2) — the LLM provides evidence, this
    function maps it to a scalar via fixed constants. No randomness,
    no LLM calls, no state-dependent inputs.

    Formula: additive (NOT multiplicative — see module docstring for
    why). Sum of per-component contributions, clamped to [0, 1] and
    rounded to 3 decimal places.

      revenue           = REVENUE_TYPE_SCORES[revenue_type]
                          if revenue_mechanism_identified else 0.0
                          # range [0, 0.30]
      buyer             = BUYER_ACCESSIBILITY_SCORES[buyer_accessibility]
                          if buyer_identified else 0.0
                          # range [0, 0.25]
      capital           = CAPITAL_SCORES[capital_required]
                          # range [0, 0.15]
      regulatory        = REGULATORY_PENALTIES[regulatory_severity]
                          - 0.01 * len(regulatory_blockers)
                          # range [-0.15-, 0]
      risks             = -0.02 * len(feasibility_risks)
                          # range [-inf, 0] (clamp handles)
      market_validation = 0.10 if existing_market_validation else 0.0
      middle_class      = 0.15 if middle_class_accessible else 0.0

      feasibility = max(0, min(1, sum)) rounded to 3 decimals

    Max realistic output (all positive contributions at top of band,
    no penalties): 0.30 + 0.25 + 0.15 + 0.10 + 0.15 = 0.95. The
    formula doesn't normalize to 1.0 — the soft penalty zone
    (HARD_FLOOR=0.15, SOFT_CEILING=0.45) is calibrated against this
    realistic max, so the [0, 0.95] range is intentional.
    """
    score = 0.0

    if finding.revenue_mechanism_identified:
        score += _REVENUE_TYPE_SCORES[finding.revenue_type]

    if finding.buyer_identified:
        score += _BUYER_ACCESSIBILITY_SCORES[finding.buyer_accessibility]

    score += _CAPITAL_SCORES[finding.capital_required]

    score += _REGULATORY_PENALTIES[finding.regulatory_severity]
    score -= _PER_REGULATORY_BLOCKER_PENALTY * len(finding.regulatory_blockers)

    score -= _PER_FEASIBILITY_RISK_PENALTY * len(finding.feasibility_risks)

    if finding.existing_market_validation:
        score += _EXISTING_MARKET_VALIDATION_BONUS

    if finding.middle_class_accessible:
        score += _MIDDLE_CLASS_ACCESSIBLE_BONUS

    return round(max(0.0, min(1.0, score)), 3)


def apply_stage1_soft_zone(raw_feasibility: float) -> tuple[float, str]:
    """Apply the Sprint Stage 1 PAJAMA soft penalty zone.

    Returns `(adjusted_feasibility, zone_label)`:

      - raw < STAGE1_HARD_FLOOR
            (adjusted = raw, "hard_exit")
            Cascade caller exits with this feasibility on Scores
            and structural=0.0.

      - STAGE1_HARD_FLOOR <= raw < STAGE1_SOFT_CEILING
            (adjusted = raw² / SOFT_CEILING, "penalty_zone")
            Candidate proceeds to Stage 2. The penalty factor
            (raw / ceiling) decays from ~0.33 at the floor to 1.0 at
            the ceiling, so adjusted = raw × penalty = raw²/ceiling
            is a smooth quadratic curve that meets the clean-pass line
            exactly at the ceiling.

      - raw >= STAGE1_SOFT_CEILING
            (adjusted = raw, "clean_pass")
            No penalty applied. Candidate proceeds with raw feasibility.

    The cascade calls this function once per Stage-1-evaluated
    candidate and uses the returned zone label as the early-exit
    string (when "hard_exit"). The adjusted value is what flows into
    Scores.feasibility downstream.
    """
    if raw_feasibility < STAGE1_HARD_FLOOR:
        return raw_feasibility, "hard_exit"
    if raw_feasibility < STAGE1_SOFT_CEILING:
        adjusted = (raw_feasibility * raw_feasibility) / STAGE1_SOFT_CEILING
        return round(adjusted, 3), "penalty_zone"
    return raw_feasibility, "clean_pass"


# --------------------------------------------------------------------- LLM call


def stage1_feasibility(
    architecture: Architecture,
    client: Any,
    telemetry: TelemetryContext | None = None,
    model: str = HAIKU_MODEL,
) -> Stage1Finding:
    """Score the candidate's feasibility and middle-class accessibility.

    `client` accepts a BaseProvider directly (production path) or an
    Anthropic-shaped SDK client / MagicMock (auto-wrapped). The
    auto-wrap path is what keeps the Sprint 8 MagicMock test pattern
    working unchanged after Sprint 14's migration.
    """
    provider = ensure_provider(client)
    return provider.parse(
        error_cls=Stage1OutputError,
        component="stage1",
        telemetry=telemetry,
        model=model,
        # Sprint PAJAMA-stabilization: bumped MAX_TOKENS_SHORT (2048) →
        # MAX_TOKENS_MEDIUM (4096) to match Stage 2's similarly-sized
        # evidence schema. The new Stage 1 schema has 13 required fields
        # including 3 list-of-string fields (labor_dependency_points
        # equivalents) plus a reasoning string. Worst-case output is
        # ~2000 tokens — right at the 2048 cap, causing truncation under
        # heavy regulatory_blockers / feasibility_risks lists. The
        # CarbonSentry (id=144) variance test saw 2 of 5 trials hit
        # Stage1OutputError; truncation was the most likely cause.
        max_tokens=MAX_TOKENS_MEDIUM,
        system=cached_system(STAGE1_SYSTEM),
        messages=[{"role": "user", "content": render_candidate(architecture)}],
        output_format=Stage1Finding,
    )
