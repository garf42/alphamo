"""Unit tests for the meta-curator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import CuratorOutputError
from alphamo.meta.audit_log import AuditLog
from alphamo.meta.curator import Curator
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    CuratorAction,
    MetaFinding,
    Severity,
)
from tests.fixtures.parsed_message import FakeContentBlock, FakeParsedMessage


def _finding(claim: str = "x") -> MetaFinding:
    return MetaFinding(
        source="redteam",
        framing="regulatory",
        claim=claim,
        evidence="e",
        falsification_condition="if y were true",
        severity=Severity.MEDIUM,
    )


def _client_with_classifications(
    verdicts: list[ClassificationVerdict],
) -> MagicMock:
    """Mock client that returns verdicts in order on successive parse() calls."""
    client = MagicMock()
    client.messages.parse.side_effect = [FakeParsedMessage(v) for v in verdicts]
    return client


def _cosmetic(rationale: str = "not structural") -> ClassificationVerdict:
    return ClassificationVerdict(
        classification=Classification.COSMETIC, rationale=rationale
    )


def _structural(rationale: str = "blocks parent goal") -> ClassificationVerdict:
    return ClassificationVerdict(
        classification=Classification.STRUCTURAL, rationale=rationale
    )


def test_no_findings_returns_continue(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_with_classifications([])
    decision = Curator(client, audit).curate([], trigger="scheduled_interval")
    assert decision.action == CuratorAction.CONTINUE
    assert decision.classified == []


def test_all_cosmetic_returns_continue(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_with_classifications([_cosmetic(), _cosmetic()])
    decision = Curator(client, audit).curate(
        [_finding("a"), _finding("b")], trigger="scheduled_interval"
    )
    assert decision.action == CuratorAction.CONTINUE
    assert len(decision.classified) == 2
    assert all(c.classification == Classification.COSMETIC for c in decision.classified)


def test_any_structural_pauses_for_human(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_with_classifications([_cosmetic(), _structural()])
    decision = Curator(client, audit).curate(
        [_finding("a"), _finding("b")], trigger="milestone_candidate"
    )
    assert decision.action == CuratorAction.PAUSE_FOR_HUMAN


def test_curate_writes_audit_event(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_with_classifications([_cosmetic()])
    Curator(client, audit).curate(
        [_finding("a")], trigger="progress_stall"
    )
    events = audit.read_all()
    assert len(events) == 1
    assert events[0].trigger == "progress_stall"
    assert events[0].classification == "no_action"
    assert events[0].action == "continue"


def test_audit_event_records_structural_classification(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_with_classifications([_structural()])
    Curator(client, audit).curate(
        [_finding("a")], trigger="milestone_candidate"
    )
    [event] = audit.read_all()
    assert event.classification == "structural"
    assert event.action == "pause_for_human"


def test_classify_passes_finding_text_to_llm(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_with_classifications([_cosmetic()])
    Curator(client, audit).curate(
        [_finding("distinctive_claim_string")], trigger="t"
    )
    kwargs = client.messages.parse.call_args[1]
    assert "distinctive_claim_string" in kwargs["messages"][0]["content"]


def test_classify_raises_curator_output_error_when_parsed_is_none(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        parsed_output=None,
        stop_reason="max_tokens",
        content=[FakeContentBlock("text")],
    )
    with pytest.raises(CuratorOutputError) as exc_info:
        Curator(client, audit).curate([_finding("x")], trigger="milestone_candidate")
    assert exc_info.value.stop_reason == "max_tokens"
    assert exc_info.value.content_block_types == ["text"]
    assert audit.read_all() == []  # no audit event when classify fails
