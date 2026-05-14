"""Query templates for the research agent's web-search invocations.

The research agent's job is to surface external knowledge the inner loop
cannot see: competitor activity, regulatory shifts, novel structural patterns,
exemplar validation. It outputs findings only — never proposes new
architectures. The curator decides what (if anything) to do with them.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL


class Trigger:
    """Stable trigger labels — used both for prompt rendering and audit logs."""

    PROGRESS_STALL = "progress_stall"
    MILESTONE_CANDIDATE = "milestone_candidate"
    SCHEDULED_INTERVAL = "scheduled_interval"
    CURATOR_REQUEST = "curator_request"


RESEARCH_SYSTEM = f"""\
You are the research agent for an evolutionary search over value-capture \
architectures. Your job is to surface external knowledge the inner loop is \
unaware of: competitor activity, regulatory shifts, novel structural patterns, \
exemplar validation.

Discipline:
1. Every finding MUST include claim, evidence (URL or direct citation), a \
falsification_condition (a concrete fact that would make the finding NOT a \
problem if true), and severity.
2. Empty findings are first-class outputs. If your searches turn up nothing \
material, emit an empty list.
3. You do NOT propose new architectures. Your output goes to the meta-curator \
only — never to the proposer or evaluator.
4. Limit yourself to roughly 5-8 web searches per invocation.

The parent goal you are guarding:

{PARENT_GOAL}\
"""


QUERY_TEMPLATES: dict[str, str] = {
    "competitor_scan": (
        "Recently-launched single-operator businesses (last 12 months) "
        "capturing $100M+ from middle-class-accessible starting positions. "
        "Are any structurally similar to known exemplars? Are any novel?"
    ),
    "regulatory_update": (
        "Regulatory shifts (last 12 months) affecting value-capture "
        "architectures: solo-operator businesses, crypto protocols, IP rights, "
        "tax-residency arbitrage. Anything that invalidates prior assumptions?"
    ),
    "exemplar_validation": (
        "Recent re-evaluations of Satoshi-era protocol economics, "
        "Rowling-style IP ownership, or Levels-style indie-hacker economics. "
        "Anything suggesting the structural claims behind these exemplars "
        "have shifted?"
    ),
    "novel_patterns": (
        "Emerging structural patterns where a single individual captures "
        "unusually high value from middle-class entry resources. Anything "
        "that looks like a new exemplar class?"
    ),
}


def render_research_trigger(trigger: str) -> str:
    """Render the user-turn payload for a research pass."""
    lines = [f"Research pass triggered by: {trigger}.", ""]
    lines.append("Investigate the following queries via web search:")
    for name, q in QUERY_TEMPLATES.items():
        lines.append(f"- {name}: {q}")
    lines.append("")
    lines.append(
        "Return a RawFindingsBatch. Empty list is fine if nothing material surfaced."
    )
    return "\n".join(lines)
