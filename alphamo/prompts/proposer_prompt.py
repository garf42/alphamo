"""Few-shot prompt template that turns k island-drawn candidates into a
new candidate Architecture.

Sprint 3 redesign (FunSearch/AlphaEvolve alignment): the proposer sees
ONLY candidates drawn from the current island. No global reference
library, no per-generation exemplar anchoring. The within-island k=2
best-shot sampling pattern (FunSearch §A.1 Methods) is the sole context
the proposer gets for mutation.

The prompt is pure k-shot: the user turn lists the k candidates with
per-dimension score headers and asks for a structurally distinct
variant. Reference exemplars (the 4 curated seeds Sprint 2 left as a
prompt section) are gone — they were producing cross-island convergence
even after Sprint 2 removed them from the fitness signal.

Bootstrap: each island starts with a copy of the trivial seed at
generation 0 (`orchestrator._bootstrap_islands()`), so the sampler
always has at least one candidate to return. `render_seeds([])` raises
— empty seed lists are an invariant violation, not a valid input.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.sampler import Seed
from alphamo.schemas import Architecture

PROPOSER_SYSTEM = f"""\
You are the proposer in an evolutionary search over value-capture architectures.

Below in the user turn are k candidates drawn from the same island in \
the population. Generate a new architecture that is structurally \
distinct from those candidates AND addresses the parent goal's \
constraints more completely than what you see.

Each candidate is annotated with its multi-objective scores. Use the \
score pattern to reason about WHICH dimension to push: a candidate with \
high feasibility and low robustness is coherent but adversarially \
fragile; high structural and low feasibility is a promising mechanism \
that doesn't yet hang together; high feasibility but failing \
labor_separation is a single-person bottleneck that needs a labor- \
externalisation mechanism. Do not optimize for the aggregate scalar \
alone — varying which dimension you push generates more useful \
diversity than chasing one number.

Constraints you MUST satisfy in the candidate you generate:
1. Middle-class accessible entry — the starting position requires only modest \
savings ($10-50K range), personal credit, professional skill, and time outside \
a primary job. No family wealth, no institutional backing, no pre-existing \
industry network, no bespoke legal infrastructure at entry.
2. Single individual or single legal entity is the sole value-capture node.
3. Plausible potential to reach $1B+ (revenue, asset holdings, or comparable measure).
4. Operational labor is performed by parties other than the capture node.

Generate a structurally distinct architecture — not a surface rewording of \
the candidates shown. Different industry, different mechanism, or a novel \
recombination that the candidates suggest but do not yet instantiate.

The parent goal:

{PARENT_GOAL}\
"""


def _render_score_header(seed: Seed) -> str:
    """One-line AlphaEvolve §2.2 style score header — dimension: value.

    `exemplar_similarity` was retired in Sprint 2 and is omitted.
    `robustness` is shown when present; absent when None (legacy or
    early-exit candidates).
    """
    s = seed.scores
    parts = [
        f"feasibility: {s.feasibility:.3f}",
        f"structural: {s.structural:.3f}",
    ]
    if s.robustness is not None:
        parts.append(f"robustness: {s.robustness:.3f}")
    parts.append(f"middle_class_accessible: {str(s.middle_class_accessible).lower()}")
    parts.append(f"fitness: {seed.fitness:.3f}")
    return "Scores — " + ", ".join(parts)


def render_seeds(seeds: list[Seed]) -> str:
    """Render island-drawn candidates as the proposer's user-turn payload.

    Empty `seeds` is an invariant violation: bootstrap inserts the trivial
    seed into every island at gen 0 and reset reseeds wiped islands with
    a copy of a surviving island's best, so the sampler should always
    have at least one alive row to return.
    """
    if not seeds:
        raise ValueError(
            "render_seeds requires at least one Seed — empty islands are an "
            "invariant violation post-bootstrap"
        )
    parts = [
        f"CANDIDATES FROM THE CURRENT ISLAND ({len(seeds)} candidate(s)):\n"
    ]
    for i, seed in enumerate(seeds, 1):
        arch = seed.architecture
        parts.append(
            f"--- Candidate {i}: {arch.name} ---\n"
            f"{_render_score_header(seed)}\n"
            f"Summary: {arch.summary}\n"
            f"Value chain: {arch.value_chain}\n"
            f"Capture mechanism: {arch.capture_mechanism}\n"
            f"Entry resources: {arch.entry_resources}"
        )
    parts.append(
        "Generate a new candidate architecture that is structurally "
        "distinct from the candidates above and addresses the parent "
        "goal's constraints more completely. Push whichever score "
        "dimension is weakest in the candidates you were shown."
    )
    return "\n\n".join(parts)


def render_seeds_from_architectures(architectures: list[Architecture]) -> str:
    """Back-compat shim for callers that don't have per-dimension scores.

    Used by tests and ad-hoc CLI flows where only Architecture objects
    are available. Same prompt shape as `render_seeds` minus the score
    headers.
    """
    if not architectures:
        raise ValueError(
            "render_seeds_from_architectures requires at least one Architecture"
        )
    parts = [
        f"CANDIDATES FROM THE CURRENT ISLAND ({len(architectures)} candidate(s)):\n"
    ]
    for i, arch in enumerate(architectures, 1):
        parts.append(
            f"--- Candidate {i}: {arch.name} ---\n"
            f"Summary: {arch.summary}\n"
            f"Value chain: {arch.value_chain}\n"
            f"Capture mechanism: {arch.capture_mechanism}\n"
            f"Entry resources: {arch.entry_resources}"
        )
    parts.append(
        "Generate a new candidate architecture that is structurally "
        "distinct from the candidates above and addresses the parent "
        "goal's constraints more completely."
    )
    return "\n\n".join(parts)
