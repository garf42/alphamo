"""Unit tests for the red-team agent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import RedTeamOutputError
from alphamo.meta.redteam import _enforce_falsification, red_team_candidate
from alphamo.prompts.redteam_prompts import DEFAULT_FRAMINGS, FRAMINGS
from alphamo.schemas.findings import (
    MetaFinding,
    RawFinding,
    RawFindingsBatch,
    Severity,
)
from tests.fixtures.exemplars import SATOSHI_FIXTURE
from tests.fixtures.parsed_message import FakeContentBlock, FakeParsedMessage


def _raw(claim: str, falsifier: str = "if X were true") -> RawFinding:
    return RawFinding(
        claim=claim,
        evidence="some evidence",
        falsification_condition=falsifier,
        severity=Severity.MEDIUM,
    )


def _client_with_batches(per_framing: dict[str, RawFindingsBatch]) -> MagicMock:
    """Mock client that returns the matching batch based on the framing in the system prompt."""
    client = MagicMock()

    def parse_side_effect(**kwargs):
        system_text = kwargs["system"][0]["text"]
        for framing, batch in per_framing.items():
            if FRAMINGS[framing] in system_text:
                return FakeParsedMessage(batch)
        return FakeParsedMessage(RawFindingsBatch(findings=[]))

    client.messages.parse.side_effect = parse_side_effect
    return client


def test_red_team_uses_default_framings():
    client = _client_with_batches({})
    red_team_candidate(SATOSHI_FIXTURE.architecture, client)
    assert client.messages.parse.call_count == len(DEFAULT_FRAMINGS)


def test_red_team_respects_custom_framings():
    client = _client_with_batches({})
    red_team_candidate(
        SATOSHI_FIXTURE.architecture, client, framings=["regulatory"]
    )
    assert client.messages.parse.call_count == 1


def test_red_team_aggregates_findings_across_framings():
    batches = {
        "regulatory": RawFindingsBatch(findings=[_raw("reg flaw")]),
        "economic": RawFindingsBatch(findings=[_raw("econ flaw")]),
        "operational": RawFindingsBatch(findings=[]),
        "scaling": RawFindingsBatch(findings=[_raw("scale flaw")]),
    }
    client = _client_with_batches(batches)
    findings = red_team_candidate(SATOSHI_FIXTURE.architecture, client)
    assert {f.claim for f in findings} == {"reg flaw", "econ flaw", "scale flaw"}


def test_red_team_tags_source_and_framing():
    batches = {"regulatory": RawFindingsBatch(findings=[_raw("a")])}
    client = _client_with_batches(batches)
    findings = red_team_candidate(
        SATOSHI_FIXTURE.architecture, client, framings=["regulatory"]
    )
    assert len(findings) == 1
    assert findings[0].source == "redteam"
    assert findings[0].framing == "regulatory"


def test_red_team_drops_findings_without_falsifier():
    batches = {
        "regulatory": RawFindingsBatch(
            findings=[_raw("good", falsifier="actually falsifiable"), _raw("bad", falsifier="   ")]
        )
    }
    client = _client_with_batches(batches)
    findings = red_team_candidate(
        SATOSHI_FIXTURE.architecture, client, framings=["regulatory"]
    )
    assert [f.claim for f in findings] == ["good"]


def test_enforce_falsification_helper():
    good = MetaFinding(
        source="redteam",
        framing="regulatory",
        claim="x",
        evidence="y",
        falsification_condition="not blank",
        severity=Severity.LOW,
    )
    bad = good.model_copy(update={"falsification_condition": ""})
    assert _enforce_falsification([good, bad]) == [good]


def test_red_team_invalid_framing_raises():
    client = MagicMock()
    with pytest.raises(KeyError):
        red_team_candidate(
            SATOSHI_FIXTURE.architecture, client, framings=["nonexistent"]
        )


def test_red_team_raises_when_parsed_is_none():
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        parsed_output=None,
        stop_reason="end_turn",
        content=[FakeContentBlock("text")],
    )
    with pytest.raises(RedTeamOutputError) as exc_info:
        red_team_candidate(
            SATOSHI_FIXTURE.architecture, client, framings=["regulatory"]
        )
    assert exc_info.value.stop_reason == "end_turn"
    assert "framing='regulatory'" in exc_info.value.detail
