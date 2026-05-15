"""Reference exemplars used by the stage-3 comparator.

These are existence proofs for the parent goal: each represents a
configuration where a single individual captured $1B+ in value from a
middle-class-accessible starting position. The stage-3 evaluator scores
candidates by how structurally similar they are to the closest exemplar.

Canonical scores are attached so the islands manager can seed every island
with the same calibrated starting population.
"""

from __future__ import annotations

from alphamo.schemas import Architecture, Scores

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

MEDVI = Architecture(
    name="Medvi",
    summary=(
        "A single operator establishes a last-mile navigation layer between "
        "consumers who cannot navigate a complex regulatory landscape and "
        "licensed infrastructure that already exists to serve them. The "
        "operator captures margin by routing demand through the regulatory "
        "barrier that legitimate providers cannot or will not cross "
        "directly to end users."
    ),
    value_chain=(
        "Licensed providers (medical, legal, financial, or other regulated "
        "infrastructure) perform the actual professional service. End "
        "consumers pay for access and navigation. The single operator "
        "provides the matching, intake, regulatory navigation, and demand "
        "aggregation. AI agents handle intake, compliance routing, and "
        "case management at scale. No employees needed for operations "
        "beyond the single principal."
    ),
    capture_mechanism=(
        "Structural arbitrage between intense demand-side pull (consumers "
        "who need a service they cannot access directly) and licensed-"
        "supply-side capacity (providers who can deliver the service but "
        "cannot or will not reach end users directly due to regulatory "
        "constraints, marketing limits, or specialization). The single "
        "operator sits at the bottleneck and captures margin on every "
        "transaction. Net margins substantially exceed traditional "
        "intermediaries in the same space (16% vs 5% range) because AI "
        "eliminates the labor cost of human navigation staff."
    ),
    entry_resources=(
        "Domain knowledge of one regulated vertical (often acquired "
        "through personal experience or accessible research), $20-50K "
        "for initial regulatory/legal setup and AI infrastructure, time "
        "outside a primary job for initial buildout, standard LLC "
        "formation, off-the-shelf AI provider APIs. No institutional "
        "backing or industry network required at entry — the "
        "architecture itself is the access mechanism."
    ),
    notes={
        "known_vulnerabilities": (
            "Legal exposure: regulatory regimes may challenge the "
            "navigation-layer position as unauthorized practice (UPL "
            "claims), unlicensed activity, or violations of specific "
            "industry regulations. State attorneys general and class-"
            "action lawyers represent live threats. Descendants of this "
            "pattern should explicitly address legal robustness, not "
            "inherit Medvi's specific legal exposure."
        ),
        "structural_insight": (
            "Unlike Satoshi/Rowling which required specific historical "
            "windows, Medvi's pattern is transferable: any vertical with "
            "the (demand-pull + licensed-capacity + regulatory-barrier) "
            "configuration is potentially accessible. The pattern "
            "teaches structural conditions for arbitrage rather than "
            "instance-specific luck."
        ),
    },
)

EXEMPLARS: list[Architecture] = [SATOSHI, ROWLING, LEVELS, MEDVI]

# STARTERS robustness is hand-set to 0.85 (Phase 2). 1.0 would imply pristine,
# but these existence proofs all carry known fragilities — Satoshi depends on
# a 2009 launch window, Rowling on a cultural moment, Levels on platform
# health. 0.85 says "presumed reasonably robust as existence proofs, but with
# known fragilities", giving generated candidates a real baseline to clear
# rather than an impossibly clean seed.
_STARTER_ROBUSTNESS = 0.85

SATOSHI_SCORES = Scores(
    feasibility=0.95,
    structural=0.95,
    exemplar_similarity=1.00,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

ROWLING_SCORES = Scores(
    feasibility=0.85,
    structural=0.90,
    exemplar_similarity=0.95,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

LEVELS_SCORES = Scores(
    feasibility=0.90,
    structural=0.80,
    exemplar_similarity=0.85,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

# Medvi: real $1B+ existence proof. Hand-calibrated scores place it between
# Levels and Rowling on aggregate; same 0.85 robustness as other seeds since
# its known vulnerabilities are flagged in notes.known_vulnerabilities (the
# Stage 4 legal_exposure framing is responsible for selecting away from
# them in descendants — see tests/test_medvi_sanity.py for plumbing proof).
MEDVI_SCORES = Scores(
    feasibility=0.90,
    structural=0.92,
    exemplar_similarity=0.90,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

STARTERS: list[tuple[Architecture, Scores]] = [
    (SATOSHI, SATOSHI_SCORES),
    (ROWLING, ROWLING_SCORES),
    (LEVELS, LEVELS_SCORES),
    (MEDVI, MEDVI_SCORES),
]


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
