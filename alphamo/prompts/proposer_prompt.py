"""Few-shot prompt template that turns reference exemplars + island seeds
into a candidate Architecture.

Sprint 2 redesign: the prompt now has two sections.

  - REFERENCE EXEMPLARS at the top: the four seed architectures (Satoshi,
    Rowling, Levels, Medvi), shown as structural patterns illustrating
    the parent goal's solution space. Unscored — they are reference, not
    fitness comparators.

  - CANDIDATES TO MUTATE below: zero or more island-drawn candidates
    with per-dimension scores. The proposer is asked to produce a
    structurally distinct architecture inspired by both sections.

When the island is empty (first generation on a fresh island, or just
post-reset), `render_seeds([])` is called and the prompt contains only
the reference exemplars. The proposer then bootstraps the island from
the reference set alone.

The score header no longer mentions exemplar_similarity (retired in
Sprint 2). Robustness shows when present; legacy candidates without
robustness display feasibility/structural only.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.evaluator.exemplar_library import format_exemplars_for_prompt
from alphamo.sampler import Seed
from alphamo.schemas import Architecture

PROPOSER_SYSTEM = f"""\
You are the proposer in an evolutionary search over value-capture architectures.

Your task: given (a) reference exemplars at the top of the user turn — \
structural patterns that have hit the parent goal under prior conditions — \
and (b) candidates to mutate drawn from the island population, generate a \
NEW architecture that explores a different region of the search space while \
satisfying the parent goal's load-bearing constraints.

Reference exemplars are NOT scored, and you should NOT copy them. They \
illustrate what value-capture configurations the parent goal admits. \
Structural novelty relative to both the references and the candidates is \
the goal; surface rebranding is not.

Each candidate to mutate is annotated with its multi-objective scores. Use \
the score patterns to reason about WHICH dimension to push: a candidate \
with high feasibility and low robustness suggests the mechanism is coherent \
but adversarially fragile; a candidate with high structural and low \
feasibility suggests the value-capture story is promising but the entry \
path doesn't yet hang together. Do not optimize for the aggregate fitness \
scalar alone — varying which dimension you push generates more useful \
population diversity than chasing a single number.

Constraints you MUST satisfy in the candidate you generate:
1. Middle-class accessible entry — the starting position requires only modest \
savings ($10-50K range), personal credit, professional skill, and time outside \
a primary job. No family wealth, no institutional backing, no pre-existing \
industry network, no bespoke legal infrastructure at entry.
2. Single individual or single legal entity is the sole value-capture node.
3. Plausible potential to reach $1B+ (revenue, asset holdings, or comparable measure).
4. Operational labor is performed by parties other than the capture node.

The parent goal:

{PARENT_GOAL}\
"""


def _render_score_header(seed: Seed) -> str:
    """One-line header in AlphaEvolve §2.2 style: dimension: value pairs.

    `exemplar_similarity` was retired in Sprint 2 and is omitted. `robustness`
    is shown when present; absent when None (legacy or early-exit candidates).
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


def _reference_section() -> str:
    """Static reference-exemplar block, prepended to every proposer request."""
    return (
        "REFERENCE EXEMPLARS (unscored — structural patterns illustrating "
        "the parent goal's solution space; do not copy):\n\n"
        + format_exemplars_for_prompt()
    )


def render_seeds(seeds: list[Seed]) -> str:
    """Render the proposer user-turn payload: reference exemplars + scored candidates.

    `seeds` may be empty when the island is uninitialized (fresh run, or
    just post-reset). In that case the proposer sees only the reference
    exemplars and bootstraps the island.
    """
    parts = [_reference_section(), ""]
    if seeds:
        parts.append(
            f"CANDIDATES TO MUTATE (drawn from the island, {len(seeds)} candidate(s)):\n"
        )
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
            "Generate a new candidate architecture that is structurally distinct "
            "from the candidates above and from the reference exemplars, while "
            "satisfying all load-bearing constraints from the parent goal."
        )
    else:
        parts.append(
            "CANDIDATES TO MUTATE: (none — the island is empty; bootstrap from "
            "the reference exemplars alone).\n"
        )
        parts.append(
            "Generate a new candidate architecture inspired by the reference "
            "exemplars' structural patterns but instantiating a different "
            "industry, mechanism, or recombination, while satisfying all "
            "load-bearing constraints from the parent goal."
        )
    return "\n\n".join(parts)


def render_seeds_from_architectures(architectures: list[Architecture]) -> str:
    """Back-compat shim for callers that don't have per-dimension scores.

    Used by tests and ad-hoc CLI flows where only Architecture objects are
    available. Produces the prompt with reference exemplars and the given
    architectures as un-scored candidates.
    """
    parts = [_reference_section(), ""]
    if architectures:
        parts.append(
            f"CANDIDATES TO MUTATE (drawn from the island, {len(architectures)} candidate(s)):\n"
        )
        for i, arch in enumerate(architectures, 1):
            parts.append(
                f"--- Candidate {i}: {arch.name} ---\n"
                f"Summary: {arch.summary}\n"
                f"Value chain: {arch.value_chain}\n"
                f"Capture mechanism: {arch.capture_mechanism}\n"
                f"Entry resources: {arch.entry_resources}"
            )
        parts.append(
            "Generate a new candidate architecture that is structurally distinct "
            "from the candidates above and from the reference exemplars, while "
            "satisfying all load-bearing constraints from the parent goal."
        )
    else:
        parts.append(
            "CANDIDATES TO MUTATE: (none — bootstrap from reference exemplars alone).\n"
        )
        parts.append(
            "Generate a new candidate architecture inspired by the reference "
            "exemplars' structural patterns but instantiating a different "
            "industry, mechanism, or recombination, while satisfying all "
            "load-bearing constraints from the parent goal."
        )
    return "\n\n".join(parts)
