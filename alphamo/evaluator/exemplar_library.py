"""Reference exemplars used as proposer-prompt patterns.

Sprint 2 redesign: seeds are now reference-only patterns, not scored
candidates. The four architectures (Satoshi, Rowling, Levels, Medvi)
appear in proposer prompts as structural illustrations of the parent
goal's solution space — what value-capture configurations have actually
hit the $1B target from middle-class starts — but they are NOT inserted
into the candidates table, NOT scored by the cascade, and NOT used as
fitness comparators.

This eliminates several pathologies the prior dual-role design exhibited:

  - Calibration cycles: re-scoring seeds through evolving cascade prompts
    produced numbers that drifted with prompt revisions, not with any
    underlying pattern quality. Without canonical seed scores there is
    nothing to recalibrate.
  - Era-dependent inheritance: when seeds were scored, the cascade pushed
    generated candidates to look more like the seeds — but then punished
    them for inheriting the seeds' era-specific patterns. With seeds as
    reference-only, the cascade evaluates each candidate on its own
    merits against the parent goal directly.
  - Literature-volume bias: heavily-analyzed patterns (Satoshi) scored
    harshly while less-analyzed ones (Rowling) scored generously, with
    no correspondence to actual pattern quality. The asymmetry disappears
    when seeds aren't scored.

Seeds still serve as proposer-prompt patterns via
`format_exemplars_for_prompt()`. The handoff surfaces them as descriptive
reference (mechanism / value chain / capture mechanism / known
fragilities) without fitness numbers.
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

# All seed architectures, ordered for prompt rendering. NOT inserted into
# the candidates table; the proposer reads them as reference patterns.
SEED_REFERENCES: list[Architecture] = [SATOSHI, ROWLING, LEVELS, MEDVI]

# Backward-compatible alias for existing call sites that import EXEMPLARS.
EXEMPLARS: list[Architecture] = SEED_REFERENCES


def format_exemplars_for_prompt() -> str:
    """Render the seed reference set as a stable, cache-friendly prompt section.

    Used by the proposer to expose the four reference patterns at the top
    of every proposal request, so the LLM sees what canonical value-
    capture configurations look like before mutating sampled candidates.
    """
    parts: list[str] = []
    for ex in SEED_REFERENCES:
        section = (
            f"## {ex.name}\n"
            f"Summary: {ex.summary}\n"
            f"Value chain: {ex.value_chain}\n"
            f"Capture mechanism: {ex.capture_mechanism}\n"
            f"Entry resources: {ex.entry_resources}"
        )
        notes = getattr(ex, "notes", None) or {}
        insight = notes.get("structural_insight")
        vulns = notes.get("known_vulnerabilities")
        if insight:
            section += f"\nStructural insight: {insight}"
        if vulns:
            section += f"\nKnown fragilities: {vulns}"
        parts.append(section)
    return "\n\n".join(parts)
