"""Test fixtures: positive exemplars + foils with hand-picked scores.

The Architecture instances themselves live in
`alphamo.evaluator.exemplar_library` — they're imported from there so the
test calibration data and the runtime exemplar library can't drift apart.

The foils (PE rollup, trust-fund SaaS) are test-only — they exist purely
to verify the middle-class filter rejects wealth-required configurations.

Scores attached to each fixture are hand-picked for the phase-01 DB-level
test where the DB takes scores it's given. Phase-02 cascade tests compute
their own scores via the LLM evaluator and ignore these.
"""

from __future__ import annotations

from dataclasses import dataclass

from alphamo.evaluator.exemplar_library import (
    LEVELS,
    LEVELS_SCORES,
    ROWLING,
    ROWLING_SCORES,
    SATOSHI,
    SATOSHI_SCORES,
)
from alphamo.schemas import Architecture, Scores


@dataclass(frozen=True)
class Exemplar:
    architecture: Architecture
    scores: Scores


SATOSHI_FIXTURE = Exemplar(architecture=SATOSHI, scores=SATOSHI_SCORES)
ROWLING_FIXTURE = Exemplar(architecture=ROWLING, scores=ROWLING_SCORES)
LEVELS_FIXTURE = Exemplar(architecture=LEVELS, scores=LEVELS_SCORES)

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
        exemplar_similarity=0.60,
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
        exemplar_similarity=0.65,
        middle_class_accessible=False,
    ),
)

EXEMPLARS: list[Exemplar] = [SATOSHI_FIXTURE, ROWLING_FIXTURE, LEVELS_FIXTURE]
FOILS: list[Exemplar] = [PE_ROLLUP_FOIL, TRUST_FUND_SAAS_FOIL]
ALL_FIXTURES: list[Exemplar] = EXEMPLARS + FOILS
