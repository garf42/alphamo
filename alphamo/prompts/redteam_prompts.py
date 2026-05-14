"""Adversarial prompt templates for the red-team agent.

Each framing is a separate adversarial lens — different adversaries find
different failure modes. The system prompt enforces the falsification
discipline: every finding must include a concrete fact that, if true, would
make the finding NOT a problem. Without it, the finding is dropped at
validation time.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.schemas import Architecture

FRAMINGS: dict[str, str] = {
    "regulatory": (
        "Examine the candidate for regulatory and legal failure modes the "
        "evaluator might have missed. Could a regulator shut it down? Are "
        "there licensing requirements that block middle-class entry? Could the "
        "structure fail compliance review in a major jurisdiction?"
    ),
    "economic": (
        "Examine the candidate for economic and unit-economics failure modes. "
        "Are assumed margins realistic at scale? Is there a commoditization "
        "trap? Does competition erode the capture mechanism before it reaches "
        "$1B?"
    ),
    "operational": (
        "Examine the candidate for operational failure modes. Single points of "
        "failure, fragile dependencies, hidden labor requirements that would "
        "violate the labor-separation constraint, organizational complexity "
        "that breaks the one-person threshold."
    ),
    "scaling": (
        "Examine the candidate for scaling failure modes. Does the capture "
        "mechanism degrade at scale? Are there hidden costs that grow "
        "superlinearly? Does the architecture force the single individual to "
        "do more work as it scales (violating labor separation)?"
    ),
}

DEFAULT_FRAMINGS: list[str] = list(FRAMINGS.keys())


def redteam_system(framing: str) -> str:
    """System prompt for a single red-team framing pass."""
    if framing not in FRAMINGS:
        raise KeyError(f"unknown framing: {framing!r}")
    return f"""\
You are the red-team adversary for an evolutionary search over value-capture \
architectures. Your job is to find STRUCTURAL flaws the evaluator missed.

Framing for this pass: {FRAMINGS[framing]}

Discipline:
1. Every finding MUST include a falsification_condition — a concrete fact \
that, if true, would make the finding NOT a problem. Findings without a \
falsifier are filtered out at validation time.
2. Empty findings are first-class outputs. "No significant structural flaws \
under this framing" is the correct answer when you find none; do NOT \
manufacture concerns.
3. Surface failure modes are not findings — only structural ones. A typo is \
not a finding; a missing capture mechanism IS a finding.

The parent goal you are red-teaming against:

{PARENT_GOAL}\
"""


def render_candidate(architecture: Architecture) -> str:
    """Render the candidate as the user-turn payload."""
    return (
        f"Candidate to red-team:\n\n"
        f"Name: {architecture.name}\n"
        f"Summary: {architecture.summary}\n"
        f"Value chain: {architecture.value_chain}\n"
        f"Capture mechanism: {architecture.capture_mechanism}\n"
        f"Entry resources: {architecture.entry_resources}"
    )
