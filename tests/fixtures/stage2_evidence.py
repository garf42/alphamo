"""Stage 2 evidence-shape fixtures for cascade tests.

Sprint Stage 2 PAJAMA renamed Stage 2's output from
"model emits four floats" to "model emits categorical / boolean / list
evidence". Tests that stub `stage2_structured` (or construct a
`Stage2Finding` directly to validate cascade flow) need a way to
build evidence-shaped fixtures that produce known structural scores
when fed through `compute_structural`.

Two helpers cover the common cases:

  - `passing_stage2_finding()`  — evidence shaped to score ≈ 0.773 via
                                  `compute_structural`. Comfortably above
                                  the default `stage2_threshold=0.5`.
  - `failing_stage2_finding()`  — evidence shaped to score ≈ 0.040.
                                  Comfortably below the gate.

Each helper accepts a `reasoning=` kwarg for tests that distinguish
between fixture instances. They take no other arguments — the evidence
shape is fixed so the resulting structural score is reproducible across
tests.
"""

from __future__ import annotations

from alphamo.schemas.findings import (
    AutomationPlausibility,
    Stage2Finding,
    TAMEstimate,
)


def passing_stage2_finding(reasoning: str = "test stub: passing") -> Stage2Finding:
    """Evidence shape that scores comfortably above stage2_threshold=0.5.

    compute_structural output: 0.773 (rounded).

    Sub-component breakdown:
      ops_score    = max(0, 0.40 - 0.08·1) × 1.0 = 0.32
                     (REQUIRES_CUSTOM_ENGINEERING with 1 labor point,
                      one_person_operable=True)
      market_score = min(1.0, 1.00 × 1.0 × 1.0 × 1.3) = 1.0
                     (>$100B TAM, target market named, capture mechanism
                      identified, nonlinear scaling path → boost capped)
      sep_score    = 2 / (2 + 0) × 1.0 = 1.0
                     (2 autonomous sources, 0 active requirements,
                      separation_achieved=True)
      structural   = (0.32 + 1.0 + 1.0) / 3 = 0.773

    Shaped after a Satoshi-ish architecture: protocol-IP capture,
    minimal-labor mechanism, decoupled value generation.
    """
    return Stage2Finding(
        labor_dependency_points=["protocol maintenance"],
        automation_plausibility=AutomationPlausibility.REQUIRES_CUSTOM_ENGINEERING,
        one_person_operable=True,
        target_market_named=True,
        target_market_description="global digital-asset holders",
        tam_estimate=TAMEstimate.OVER_100B,
        capture_mechanism_identified=True,
        capture_mechanism_description="genesis-block allocation under protocol IP",
        nonlinear_scaling_path=True,
        autonomous_value_sources=[
            "protocol runs 24/7 without operator involvement",
            "asset appreciation compounds independent of labor",
        ],
        active_labor_requirements=[],
        separation_achieved=True,
        reasoning=reasoning,
    )


def failing_stage2_finding(reasoning: str = "test stub: failing") -> Stage2Finding:
    """Evidence shape that scores BELOW stage2_threshold=0.5.

    compute_structural output: 0.040.

    Sub-component breakdown:
      ops_score    = max(0, 0.10 - 0.08·6) × 0.3 = 0.0
                     (REQUIRES_HUMAN_JUDGMENT with 6 labor points,
                      one_person_operable=False; the auto score is
                      already negative pre-clamp, so ops floors to 0)
      market_score = 0.40 × 0.3 × 0.4 × 1.0 = 0.048
                     ($1B-$10B TAM, market not named, mechanism not
                      identified, no nonlinear path)
      sep_score    = 1 / (1 + 4) × 0.5 = 0.10
                     (1 autonomous, 4 active, separation_achieved=False)
      structural   = (0.00 + 0.048 + 0.10) / 3 = 0.0493… → round(3) = 0.049

    Shaped after a vague consultancy: labor-intensive ops, no clear
    moat, value tied to operator time.
    """
    return Stage2Finding(
        labor_dependency_points=[
            "client intake interviews",
            "custom proposal drafting",
            "regulatory filing per engagement",
            "onsite delivery and supervision",
            "post-engagement compliance",
            "annual partner audit responses",
        ],
        automation_plausibility=AutomationPlausibility.REQUIRES_HUMAN_JUDGMENT,
        one_person_operable=False,
        target_market_named=False,
        target_market_description="",
        tam_estimate=TAMEstimate.ONE_TO_10B,
        capture_mechanism_identified=False,
        capture_mechanism_description="",
        nonlinear_scaling_path=False,
        autonomous_value_sources=["template document archive"],
        active_labor_requirements=[
            "client meetings",
            "engagement delivery",
            "review cycles",
            "billing administration",
        ],
        separation_achieved=False,
        reasoning=reasoning,
    )
