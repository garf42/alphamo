"""Unit tests for the research agent."""

from __future__ import annotations

from unittest.mock import MagicMock

from alphamo.meta.research import WEB_SEARCH_TOOL, Trigger, run_research
from alphamo.schemas.findings import RawFinding, RawFindingsBatch, Severity


def _mock_client(batch: RawFindingsBatch) -> MagicMock:
    client = MagicMock()
    client.messages.parse.return_value.parsed = batch
    return client


def test_run_research_tags_findings_as_research_source():
    raw = RawFinding(
        claim="x",
        evidence="https://example.com",
        falsification_condition="if y",
        severity=Severity.HIGH,
    )
    client = _mock_client(RawFindingsBatch(findings=[raw]))
    findings = run_research(Trigger.PROGRESS_STALL, client)
    assert len(findings) == 1
    assert findings[0].source == "research"
    assert findings[0].framing is None
    assert findings[0].claim == "x"


def test_run_research_passes_web_search_tool():
    client = _mock_client(RawFindingsBatch(findings=[]))
    run_research(Trigger.MILESTONE_CANDIDATE, client)
    kwargs = client.messages.parse.call_args[1]
    assert WEB_SEARCH_TOOL in kwargs["tools"]


def test_run_research_includes_trigger_in_user_message():
    client = _mock_client(RawFindingsBatch(findings=[]))
    run_research(Trigger.SCHEDULED_INTERVAL, client)
    kwargs = client.messages.parse.call_args[1]
    user_content = kwargs["messages"][0]["content"]
    assert Trigger.SCHEDULED_INTERVAL in user_content


def test_run_research_empty_batch_returns_empty_list():
    client = _mock_client(RawFindingsBatch(findings=[]))
    assert run_research(Trigger.PROGRESS_STALL, client) == []
