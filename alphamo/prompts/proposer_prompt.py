"""Few-shot prompt template that turns k seeds into a candidate Architecture."""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.schemas import Architecture

PROPOSER_SYSTEM = f"""\
You are the proposer in an evolutionary search over value-capture architectures.

Your task: given seed architectures drawn from the island population, generate \
a NEW architecture that explores a different region of the search space while \
satisfying the parent goal's load-bearing constraints.

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


def render_seeds(seeds: list[Architecture]) -> str:
    """Render seed architectures as the user-turn payload for the proposer."""
    parts = [f"Seed architectures drawn from the island ({len(seeds)} seed(s)):\n"]
    for i, seed in enumerate(seeds, 1):
        parts.append(
            f"--- Seed {i}: {seed.name} ---\n"
            f"Summary: {seed.summary}\n"
            f"Value chain: {seed.value_chain}\n"
            f"Capture mechanism: {seed.capture_mechanism}\n"
            f"Entry resources: {seed.entry_resources}"
        )
    parts.append(
        "Generate a new candidate architecture that is structurally distinct from "
        "the seeds above and satisfies all load-bearing constraints from the parent goal."
    )
    return "\n\n".join(parts)
