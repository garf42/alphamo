"""Stage 1 evidence-shape fixtures for cascade tests.

Sprint Stage 1 PAJAMA renamed Stage 1's output from "model emits a
feasibility float" to "model emits categorical / boolean / list
evidence". Tests that stub `stage1_feasibility` (or construct a
`Stage1Finding` directly to validate cascade flow) need fixtures
that produce known feasibility scores when fed through
`compute_feasibility` AND known soft-zone outcomes when run through
`apply_stage1_soft_zone`.

Three helpers cover the three cascade outcomes:

  - `passing_stage1_finding()`  — evidence → feasibility ≈ 0.83
                                  (well above STAGE1_SOFT_CEILING=0.45;
                                  clean pass with no penalty)
  - `penalty_zone_stage1_finding()` — evidence → feasibility ≈ 0.29
                                  (in [0.15, 0.45]; penalty applied,
                                  candidate continues to Stage 2 with
                                  adjusted feasibility ≈ 0.187)
  - `failing_stage1_finding()`  — evidence → feasibility = 0.0
                                  (below STAGE1_HARD_FLOOR=0.15;
                                  cascade exits with structural=0.0)

The `middle_class_accessible` flag defaults to True on all three (the
False case is an INDEPENDENT structural gate handled at the cascade
level — fixtures that need to exercise that gate construct the
finding directly with `middle_class_accessible=False`).
"""

from __future__ import annotations

from alphamo.schemas.findings import (
    BuyerAccessibility,
    CapitalRequired,
    RegulatorySeverity,
    RevenueType,
    Stage1Finding,
)


def passing_stage1_finding(reasoning: str = "test stub: passing") -> Stage1Finding:
    """Evidence shape that scores comfortably above STAGE1_SOFT_CEILING=0.45.

    compute_feasibility output: 0.83.

    Per-component breakdown:
      revenue           = RECURRING (0.30)
      buyer             = DIRECT_TO_BUSINESS (0.25)
      capital           = 10k_to_100k (0.09)
      regulatory        = MANAGEABLE (-0.03) + 1 blocker (-0.01) = -0.04
      risks             = 1 risk × -0.02 = -0.02
      market_validation = True (+0.10)
      middle_class      = True (+0.15)
      sum               = 0.30 + 0.25 + 0.09 - 0.04 - 0.02 + 0.10 + 0.15 = 0.83

    Soft-zone outcome: clean_pass (0.83 ≥ 0.45). No penalty applied.

    Shaped after a realistic B2B SaaS architecture: clear recurring
    revenue, identified buyer cohort, modest pre-revenue capital,
    workable regulatory burden, validated market.
    """
    return Stage1Finding(
        revenue_mechanism_identified=True,
        revenue_mechanism_description="annual subscription with usage-tier overage billing",
        revenue_type=RevenueType.RECURRING,
        buyer_identified=True,
        buyer_description="mid-market e-commerce operators (50-500 employees)",
        buyer_accessibility=BuyerAccessibility.DIRECT_TO_BUSINESS,
        capital_required=CapitalRequired.BETWEEN_10K_AND_100K,
        capital_justification="cloud infrastructure, initial engineering, basic legal setup",
        regulatory_blockers=["GDPR / data-residency compliance for EU customers"],
        regulatory_severity=RegulatorySeverity.MANAGEABLE,
        feasibility_risks=["depends on continued access to public e-commerce platform APIs"],
        existing_market_validation=True,
        middle_class_accessible=True,
        reasoning=reasoning,
    )


def penalty_zone_stage1_finding(
    reasoning: str = "test stub: penalty zone",
) -> Stage1Finding:
    """Evidence shape that scores in the soft-penalty zone [0.15, 0.45].

    compute_feasibility output: 0.29.

    Per-component breakdown:
      revenue           = HYBRID (0.22)  — identified but mixed
      buyer             = not identified (0.00)
      capital           = 100k_to_1m (0.04)
      regulatory        = SIGNIFICANT (-0.08) + 2 blockers (-0.02) = -0.10
      risks             = 1 risk × -0.02 = -0.02
      market_validation = False (0.00)
      middle_class      = True (+0.15)
      sum               = 0.22 + 0.00 + 0.04 - 0.10 - 0.02 + 0.00 + 0.15 = 0.29

    Soft-zone outcome: penalty_zone (0.15 ≤ 0.29 < 0.45). The cascade
    applies the (raw²/ceiling) penalty, yielding adjusted feasibility
    ≈ 0.187. Candidate proceeds to Stage 2 with the penalized score.

    Shaped after an ambiguous architecture: revenue mechanism exists
    but mixed, no clear buyer cohort, capital requirements push past
    middle-class, significant regulatory work needed.
    """
    return Stage1Finding(
        revenue_mechanism_identified=True,
        revenue_mechanism_description="mix of licensing fees and per-transaction commissions",
        revenue_type=RevenueType.HYBRID,
        buyer_identified=False,
        buyer_description="",
        buyer_accessibility=BuyerAccessibility.UNCLEAR,
        capital_required=CapitalRequired.BETWEEN_100K_AND_1M,
        capital_justification="initial dataset acquisition + early operations team",
        regulatory_blockers=[
            "state-by-state licensing per use jurisdiction",
            "data-broker registration in applicable states",
        ],
        regulatory_severity=RegulatorySeverity.SIGNIFICANT,
        feasibility_risks=["network effects require Day-1 critical mass that isn't guaranteed"],
        existing_market_validation=False,
        middle_class_accessible=True,
        reasoning=reasoning,
    )


def failing_stage1_finding(reasoning: str = "test stub: failing") -> Stage1Finding:
    """Evidence shape that scores BELOW STAGE1_HARD_FLOOR=0.15.

    compute_feasibility output: 0.0 (clamped from raw -0.08).

    Per-component breakdown:
      revenue           = not identified (0.00)
      buyer             = not identified (0.00)
      capital           = over_1m (0.01)
      regulatory        = PROHIBITIVE (-0.15) + 3 blockers (-0.03) = -0.18
      risks             = 3 risks × -0.02 = -0.06
      market_validation = False (0.00)
      middle_class      = True (+0.15)  — bonus contribution; the False
                          case is the independent hard gate at the
                          cascade level
      raw sum           = 0.00 + 0.00 + 0.01 - 0.18 - 0.06 + 0.00 + 0.15 = -0.08
      clamped to [0, 1] = 0.0

    Soft-zone outcome: hard_exit (0.0 < 0.15). The cascade exits with
    structural=0.0; Stage 2 and Stage 3 do not run.

    Shaped after a clearly-non-viable architecture: no revenue
    mechanism, no buyer, prohibitive regulation, large capital
    requirement, multiple execution risks. The MC bonus keeps the
    final clamped value at 0.0 rather than negative (compute_feasibility
    clamps).
    """
    return Stage1Finding(
        revenue_mechanism_identified=False,
        revenue_mechanism_description="",
        revenue_type=RevenueType.UNCLEAR,
        buyer_identified=False,
        buyer_description="",
        buyer_accessibility=BuyerAccessibility.UNCLEAR,
        capital_required=CapitalRequired.OVER_1M,
        capital_justification="large infrastructure footprint plus multi-year operating runway",
        regulatory_blockers=[
            "FDA premarket approval for medical device classification",
            "DEA Schedule II controlled-substance handling",
            "state-by-state pharmacy board licensure",
        ],
        regulatory_severity=RegulatorySeverity.PROHIBITIVE,
        feasibility_risks=[
            "requires a partnership with a major institution that has never granted one",
            "depends on regulatory change that hasn't been proposed",
            "needs proprietary dataset that doesn't exist publicly",
        ],
        existing_market_validation=False,
        middle_class_accessible=True,
        reasoning=reasoning,
    )
