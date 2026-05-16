"""Snapshot tests on PARENT_GOAL and on the proposer's system prompt context.

The proposer's system prompt is built from `PROPOSER_SYSTEM`, which
interpolates `PARENT_GOAL` verbatim. Any text that lands in either of
those strings is seen by the LLM on every proposer call. Sprint 3's
intent is that PARENT_GOAL ground the search through structural
constraints, not through named historical patterns — so this test
guards against the four retired pattern names (Satoshi, Rowling,
Levels, Medvi) leaking back into proposer-facing prompt context.

The names are still permitted to appear in:
  - dev-facing Python comments / docstrings (these do not reach the LLM)
  - the research-agent system prompt (a separate prompt path, not the
    proposer's)
  - the adversarial-scrutiny stage's Medvi-class threat-surface
    reference (calibrates the adversarial stage, not the proposer)
  - test fixtures (test-only code, never invoked at production runtime)
"""

from __future__ import annotations

import pytest

from alphamo.context.parent_goal import PARENT_GOAL, PARENT_GOAL_VERSION
from alphamo.prompts.proposer_prompt import PROPOSER_SYSTEM


RETIRED_PATTERN_NAMES = ("Satoshi", "Rowling", "Levels", "Medvi")


@pytest.mark.parametrize("name", RETIRED_PATTERN_NAMES)
def test_parent_goal_does_not_cite_retired_pattern_names(name: str):
    """PARENT_GOAL must not name any of the four retired curated patterns.

    These were removed from `exemplar_library.SEED_REFERENCES` in
    Sprint 3 to eliminate seed-anchoring bias in the proposer's prompt
    context. Citing them in PARENT_GOAL recreates the divergence via
    a back door because PARENT_GOAL is interpolated into every
    evaluator system prompt — including the proposer's.
    """
    assert name not in PARENT_GOAL, (
        f"PARENT_GOAL still cites '{name}' — Sprint 3 follow-up required "
        "the four retired pattern names removed from proposer-facing "
        "prompt context. PARENT_GOAL_VERSION must be bumped if the text "
        "is amended."
    )


@pytest.mark.parametrize("name", RETIRED_PATTERN_NAMES)
def test_proposer_system_prompt_does_not_cite_retired_pattern_names(name: str):
    """The fully-rendered PROPOSER_SYSTEM (which interpolates PARENT_GOAL)
    must not contain any of the four retired pattern names."""
    assert name not in PROPOSER_SYSTEM, (
        f"PROPOSER_SYSTEM still contains '{name}' — proposer-facing "
        "prompt context must not cite the retired curated patterns."
    )


def test_parent_goal_version_reflects_citation_removal():
    """PARENT_GOAL_VERSION must be bumped past 'v1' once the v1 citation
    text was rewritten; otherwise runs persisted under the new framing
    would be indistinguishable from runs that saw the v1 citations."""
    assert PARENT_GOAL_VERSION != "v1", (
        "PARENT_GOAL_VERSION still says 'v1' but the v1 text included the "
        "now-removed Satoshi/Rowling/Levels citation; bump the version so "
        "post-citation-removal runs can be told apart from v1 runs in the DB."
    )


def test_parent_goal_retains_load_bearing_constraints():
    """The three numbered load-bearing constraints must remain in PARENT_GOAL.
    These are the structural grounding that replaces named-pattern citations."""
    for marker in (
        "ONE-PERSON THRESHOLD",
        "BILLION-DOLLAR QUANTUM",
        "MIDDLE-CLASS ACCESSIBLE ENTRY",
    ):
        assert marker in PARENT_GOAL, (
            f"PARENT_GOAL lost the '{marker}' load-bearing constraint — "
            "the structural grounding for the search has been weakened"
        )
