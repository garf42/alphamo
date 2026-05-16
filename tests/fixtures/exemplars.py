"""Test fixtures: hand-shaped exemplar + foil candidates with hand-picked scores.

Sprint 3 redesign: production seeds are gone (replaced by a single
trivial Solo Service Provider baseline in `exemplar_library.py`). These
TEST fixtures keep Architecture instances inline so DB-level / ordering /
fitness-aggregation tests can insert known-fitness rows without spinning
up a live cascade. The fixtures' architectures are TEST-ONLY data; they
do NOT appear in `exemplar_library.SEED_REFERENCES`.

Calibration: SATOSHI_FIXTURE > ROWLING_FIXTURE > LEVELS_FIXTURE under
3-dim aggregation (feasibility + structural + robustness), giving a
deterministic ordering for tests that don't want to depend on cascade
output.

The foils (PE rollup, trust-fund SaaS) verify the middle-class filter
rejects wealth-required configurations.
"""

from __future__ import annotations

from dataclasses import dataclass

from alphamo.schemas import Architecture, Scores


@dataclass(frozen=True)
class Exemplar:
    architecture: Architecture
    scores: Scores


_SATOSHI_ARCH = Architecture(
    name="Satoshi",
    summary="Pseudonymous launch of a permissionless monetary protocol.",
    value_chain="Miners and node operators secure and propagate the chain.",
    capture_mechanism=(
        "Pre-mined / early-mined coin allocation under a fixed-supply protocol "
        "whose value accrues to early holders as the network grows."
    ),
    entry_resources=(
        "Cryptography and distributed-systems skill; time outside a primary job; "
        "commodity hardware; no institutional backing."
    ),
)

_ROWLING_ARCH = Architecture(
    name="Rowling",
    summary="Author retains downstream IP rights across a transmedia franchise.",
    value_chain=(
        "Publishers, film studios, merchandising licensees, and theme parks "
        "perform the operational labor of distribution and production."
    ),
    capture_mechanism=(
        "Copyright ownership over a singular creative IP, licensed across media "
        "with royalty structures that scale with franchise revenue."
    ),
    entry_resources=(
        "Writing skill and time; modest savings; no industry network at start "
        "(per the famous slush-pile origin)."
    ),
)

_LEVELS_ARCH = Architecture(
    name="Levels",
    summary="Solo-operator portfolio of bootstrapped SaaS and media products.",
    value_chain=(
        "Hosted infrastructure providers, payment processors, and the user "
        "community supply operational scale; the operator writes the code."
    ),
    capture_mechanism=(
        "Direct subscription revenue + audience-driven distribution; no "
        "investors, no equity dilution, public build-in-public flywheel."
    ),
    entry_resources=(
        "Programming skill; laptop; modest runway; personal credit; no "
        "institutional backing."
    ),
)

SATOSHI_FIXTURE = Exemplar(
    architecture=_SATOSHI_ARCH,
    scores=Scores(
        feasibility=0.95,
        structural=0.95,
        robustness=0.95,
        middle_class_accessible=True,
    ),
)
ROWLING_FIXTURE = Exemplar(
    architecture=_ROWLING_ARCH,
    scores=Scores(
        feasibility=0.90,
        structural=0.90,
        robustness=0.85,
        middle_class_accessible=True,
    ),
)
LEVELS_FIXTURE = Exemplar(
    architecture=_LEVELS_ARCH,
    scores=Scores(
        feasibility=0.85,
        structural=0.80,
        robustness=0.80,
        middle_class_accessible=True,
    ),
)

# Backward-compat alias for tests that import the bare architecture.
SATOSHI = _SATOSHI_ARCH
ROWLING = _ROWLING_ARCH
LEVELS = _LEVELS_ARCH

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
