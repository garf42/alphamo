"""Reference exemplars used by the stage-3 comparator.

These are existence proofs for the parent goal: each represents a
configuration where a single individual captured $1B+ in value from a
middle-class-accessible starting position. The stage-3 evaluator scores
candidates by how structurally similar they are to the closest exemplar.
"""

from __future__ import annotations

from alphamo.schemas import Architecture

SATOSHI = Architecture(
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

ROWLING = Architecture(
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

LEVELS = Architecture(
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

EXEMPLARS: list[Architecture] = [SATOSHI, ROWLING, LEVELS]


def format_exemplars_for_prompt() -> str:
    """Render the exemplar library as a stable, cache-friendly prompt section."""
    parts: list[str] = []
    for ex in EXEMPLARS:
        parts.append(
            f"## {ex.name}\n"
            f"Summary: {ex.summary}\n"
            f"Value chain: {ex.value_chain}\n"
            f"Capture mechanism: {ex.capture_mechanism}\n"
            f"Entry resources: {ex.entry_resources}"
        )
    return "\n\n".join(parts)
