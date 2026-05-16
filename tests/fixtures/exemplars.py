"""Test fixtures: positive exemplars + foils with hand-picked scores.

Sprint 2 redesign: production seeds are no longer scored. These TEST
fixtures keep hand-picked Scores attached so DB-level / ordering /
fitness-aggregation tests can insert known-fitness rows without spinning
up a live cascade. The fixtures' scores are test-only — they do NOT
appear in `exemplar_library.py`'s production seed references.

The Architecture instances themselves are imported from
`alphamo.evaluator.exemplar_library` so test architecture data and the
runtime reference set can't drift apart.

The foils (PE rollup, trust-fund SaaS) verify the middle-class filter
rejects wealth-required configurations.
"""

from __future__ import annotations

from dataclasses import dataclass

from alphamo.evaluator.exemplar_library import LEVELS, ROWLING, SATOSHI
from alphamo.schemas import Architecture, Scores


@dataclass(frozen=True)
class Exemplar:
    architecture: Architecture
    scores: Scores


# Hand-picked test scores. Calibrated so Satoshi > Rowling > Levels under
# 3-dim aggregation (feasibility + structural + robustness), giving a
# deterministic ordering for tests that don't want to depend on
# cascade output.
SATOSHI_FIXTURE = Exemplar(
    architecture=SATOSHI,
    scores=Scores(
        feasibility=0.95,
        structural=0.95,
        robustness=0.95,
        middle_class_accessible=True,
    ),
)
ROWLING_FIXTURE = Exemplar(
    architecture=ROWLING,
    scores=Scores(
        feasibility=0.90,
        structural=0.90,
        robustness=0.85,
        middle_class_accessible=True,
    ),
)
LEVELS_FIXTURE = Exemplar(
    architecture=LEVELS,
    scores=Scores(
        feasibility=0.85,
        structural=0.80,
        robustness=0.80,
        middle_class_accessible=True,
    ),
)

PE_ROLLUP_FOIL = Exemplar(
    architecture=Architecture(
        name="PE rollup",
        summary="Private-equity consolidation of fragmented services market.",
        value_chain="Acquired operating companies; their staff perform the work.",
        capture_mechanism=(
            "Leveraged acquisitions, multiple arbitrage on exit, GP carry."
        ),
        entry_resources=(
            "$100M+ committed fund, deal-team headcount, LP relationships."
        ),
    ),
    scores=Scores(
        feasibility=0.80,
        structural=0.70,
        middle_class_accessible=False,
    ),
)

TRUST_FUND_SAAS_FOIL = Exemplar(
    architecture=Architecture(
        name="Trust-fund SaaS",
        summary="SaaS launched off family-office seed capital and warm intros.",
        value_chain="Hired engineering team; founder steers.",
        capture_mechanism=(
            "Equity in venture-scale company seeded by family wealth and "
            "pre-existing industry network."
        ),
        entry_resources="$1M+ family seed, bespoke counsel, warm investor intros.",
    ),
    scores=Scores(
        feasibility=0.70,
        structural=0.75,
        middle_class_accessible=False,
    ),
)

EXEMPLARS: list[Exemplar] = [SATOSHI_FIXTURE, ROWLING_FIXTURE, LEVELS_FIXTURE]
FOILS: list[Exemplar] = [PE_ROLLUP_FOIL, TRUST_FUND_SAAS_FOIL]
ALL_FIXTURES: list[Exemplar] = EXEMPLARS + FOILS
