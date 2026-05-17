"""Research agent: external knowledge probe; outputs findings only.

Fires on stalls, milestones, scheduled intervals, or curator request. Uses
the Anthropic web_search server-tool to probe what the model can't already
see. Output goes only to the meta-curator — NEVER to the proposer or
evaluator. This isolation is the structural feature that keeps meta-drift
from contaminating object-level optimization.

Sprint 7 model routing: defaults to SONNET_MODEL (was OPUS_MODEL). The
research task is information-gathering and findings-synthesis around
search results — Sonnet's reasoning is sufficient and the cost savings
accumulate across stall/milestone/scheduled invocations.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import ResearchOutputError, TelemetryContext, parse_or_raise
from alphamo.evaluator._common import MAX_TOKENS_XLONG, SONNET_MODEL, cached_system
from alphamo.prompts.research_prompts import (
    RESEARCH_SYSTEM,
    Trigger,
    render_research_trigger,
)
from alphamo.schemas.findings import MetaFinding, RawFindingsBatch

WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 8,
}


def run_research(
    trigger: str,
    client: Any,
    model: str = SONNET_MODEL,
    telemetry: TelemetryContext | None = None,
) -> list[MetaFinding]:
    """Run one research pass; returns MetaFindings tagged source='research'."""
    batch = parse_or_raise(
        client,
        ResearchOutputError,
        detail=f"trigger={trigger!r}",
        component="research",
        telemetry=telemetry,
        model=model,
        max_tokens=MAX_TOKENS_XLONG,
        thinking={"type": "adaptive"},
        tools=[WEB_SEARCH_TOOL],
        system=cached_system(RESEARCH_SYSTEM),
        messages=[{"role": "user", "content": render_research_trigger(trigger)}],
        output_format=RawFindingsBatch,
    )
    return [
        MetaFinding(source="research", framing=None, **raw.model_dump())
        for raw in batch.findings
    ]


__all__ = ["run_research", "Trigger", "WEB_SEARCH_TOOL"]
