"""Few-shot prompt template that turns k seeds into a candidate Architecture.

Phase 2: per-AlphaEvolve §2.2 / Figure 3b, each prior program is rendered
with an explicit per-dimension score header BEFORE the architecture content.
The LLM can then reason about which dimension to push when generating the
next variant — the multi-objective signal isn't collapsed to a scalar.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.sampler import Seed
from alphamo.schemas import Architecture

PROPOSER_SYSTEM = f"""\
You are the proposer in an evolutionary search over value-capture architectures.

Your task: given seed architectures drawn from the island population, generate \
a NEW architecture that explores a different region of the search space while \
satisfying the parent goal's load-bearing constraints.

Each seed below is annotated with its multi-objective scores. Use the score \
patterns to reason about WHICH dimension to improve: seeds with high \
feasibility but middling exemplar_similarity suggest novel-but-coherent \
structure is welcome; seeds with high structural and low exemplar_similarity \
suggest the field has been narrow on capture-mechanism diversity. Do not \
optimize for the aggregate fitness scalar alone — programs that excel under \
different evaluation criteria often have distinct structures, and varying \
which dimension you push generates more useful population diversity than \
chasing a single number.

Constraints you MUST satisfy in the candidate you generate:
1. Middle-class accessible entry — the starting position requires only modest \
savings ($10-50K range), personal credit, professional skill, and time outside \
a primary job. No family wealth, no institutional backing, no pre-existing \
industry network, no bespoke legal infrastructure at entry.
2. Single individual or single legal entity is the sole value-capture node.
3. Plausible potential to reach $1B+ (revenue, asset holdings, or comparable measure).
4. Operational labor is performed by parties other than the capture node.

Do NOT copy a seed verbatim. Generate a genuinely different configuration — \
different industry, different mechanism, or a novel recombination that the seeds \
suggest but do not yet instantiate. Structural novelty is the goal; surface \
rebranding of the seeds is not.

The parent goal:

{PARENT_GOAL}\
"""


def _render_score_header(seed: Seed) -> str:
    """One-line header in AlphaEvolve §2.2 style: dimension: value pairs."""
    s = seed.scores
    return (
        f"Scores — feasibility: {s.feasibility:.3f}, "
        f"structural: {s.structural:.3f}, "
        f"exemplar_similarity: {s.exemplar_similarity:.3f}, "
        f"middle_class_accessible: {str(s.middle_class_accessible).lower()}, "
        f"fitness: {seed.fitness:.3f}"
    )


def render_seeds(seeds: list[Seed]) -> str:
    """Render seed architectures as the user-turn payload for the proposer.

    Format mirrors AlphaEvolve §2.2 / Figure 3b: each seed gets a one-line
    score header before its architecture content. Order: seeds appear in
    the order the sampler returned them (which for FunSearch's k=2 best-shot
    prompting would be ascending fitness; the proposer infers the implicit
    score-vs-version pattern).
    """
    parts = [f"Seed architectures drawn from the island ({len(seeds)} seed(s)):\n"]
    for i, seed in enumerate(seeds, 1):
        arch = seed.architecture
        parts.append(
            f"--- Seed {i}: {arch.name} ---\n"
            f"{_render_score_header(seed)}\n"
            f"Summary: {arch.summary}\n"
            f"Value chain: {arch.value_chain}\n"
            f"Capture mechanism: {arch.capture_mechanism}\n"
            f"Entry resources: {arch.entry_resources}"
        )
    parts.append(
        "Generate a new candidate architecture that is structurally distinct from "
        "the seeds above and satisfies all load-bearing constraints from the parent goal."
    )
    return "\n\n".join(parts)


def render_seeds_from_architectures(architectures: list[Architecture]) -> str:
    """Back-compat shim for callers that don't have per-dimension scores.

    Used by tests and ad-hoc CLI flows where only Architecture objects are
    available. Produces the prompt WITHOUT per-dimension score headers —
    the proposer still works, just without the multi-objective signal.
    """
    parts = [f"Seed architectures drawn from the island ({len(architectures)} seed(s)):\n"]
    for i, arch in enumerate(architectures, 1):
        parts.append(
            f"--- Seed {i}: {arch.name} ---\n"
            f"Summary: {arch.summary}\n"
            f"Value chain: {arch.value_chain}\n"
            f"Capture mechanism: {arch.capture_mechanism}\n"
            f"Entry resources: {arch.entry_resources}"
        )
    parts.append(
        "Generate a new candidate architecture that is structurally distinct from "
        "the seeds above and satisfies all load-bearing constraints from the parent goal."
    )
    return "\n\n".join(parts)
