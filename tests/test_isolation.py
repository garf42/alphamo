"""Load-bearing meta-isolation test.

The architecture's core discipline: the proposer's prompt contains the seed
architectures and the parent goal's fitness criteria, but NEVER the
meta-curator's reasoning, NEVER the drift log, NEVER the red-team findings.
This isolation is the structural feature that prevents meta-level drift
from contaminating object-level optimization.

These tests verify that property by injecting distinctive meta-layer state
(audit-log entries, red-team findings, curator decisions) and confirming
that no fragment of it reaches the proposer's call_args.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.meta.curator import Curator
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    CuratorAction,
    MetaFinding,
    Severity,
)
from tests.fixtures.exemplars import SATOSHI_FIXTURE
from tests.fixtures.parsed_message import FakeParsedMessage

DISTINCTIVE_LEAK_MARKER = "LEAK_CANARY_a47b3c"


def _proposer_with_fake_output() -> tuple[Proposer, MagicMock]:
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Architecture(
            name="fake",
            summary="fake",
            value_chain="fake",
            capture_mechanism="fake",
            entry_resources="fake",
        )
    )
    return Proposer(client), client


def _proposer_payload(client: MagicMock) -> str:
    """Concatenate everything the proposer client saw into one string for marker scanning."""
    kwargs = client.messages.parse.call_args[1]
    parts = [kwargs["system"][0]["text"]]
    for msg in kwargs["messages"]:
        content = msg["content"]
        if isinstance(content, str):
            parts.append(content)
        else:
            parts.extend(block.get("text", "") for block in content if isinstance(block, dict))
    return "\n".join(parts)


def test_red_team_findings_do_not_leak_into_proposer(tmp_path):
    """Even if red-team produced findings, the proposer must not see them."""
    leaked_finding = MetaFinding(
        source="redteam",
        framing="regulatory",
        claim=f"{DISTINCTIVE_LEAK_MARKER}: candidate hits regulatory wall",
        evidence="hypothetical",
        falsification_condition="if regulators don't notice",
        severity=Severity.HIGH,
    )
    assert DISTINCTIVE_LEAK_MARKER in leaked_finding.claim

    proposer, client = _proposer_with_fake_output()
    proposer.propose([SATOSHI_FIXTURE.architecture])

    payload = _proposer_payload(client)
    assert DISTINCTIVE_LEAK_MARKER not in payload, (
        "red-team finding text reached the proposer prompt — meta isolation broken"
    )


def test_curator_decision_does_not_leak_into_proposer(tmp_path):
    """Curator rationales must not flow into proposer prompts via any side channel."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    finding = MetaFinding(
        source="redteam",
        framing="regulatory",
        claim="some claim",
        evidence="e",
        falsification_condition="if z",
        severity=Severity.LOW,
    )
    classify_client = MagicMock()
    classify_client.messages.parse.return_value = FakeParsedMessage(
        ClassificationVerdict(
            classification=Classification.STRUCTURAL,
            rationale=f"{DISTINCTIVE_LEAK_MARKER}: must pause",
        )
    )
    decision = Curator(classify_client, audit, run_id="run_test").curate(
        [finding], trigger="t"
    )
    assert decision.action == CuratorAction.PAUSE_FOR_HUMAN

    proposer, prop_client = _proposer_with_fake_output()
    proposer.propose([SATOSHI_FIXTURE.architecture])

    payload = _proposer_payload(prop_client)
    assert DISTINCTIVE_LEAK_MARKER not in payload


def test_audit_log_does_not_leak_into_proposer(tmp_path):
    """Drift-log entries must never reach the proposer, even when sitting on disk."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id="run_test",
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale=f"{DISTINCTIVE_LEAK_MARKER}: parent goal needs reframing",
            payload={"note": DISTINCTIVE_LEAK_MARKER},
        )
    )

    proposer, client = _proposer_with_fake_output()
    proposer.propose([SATOSHI_FIXTURE.architecture])

    payload = _proposer_payload(client)
    assert DISTINCTIVE_LEAK_MARKER not in payload


def test_proposer_module_does_not_import_meta_layer():
    """Structural check: alphamo.proposer must not depend on alphamo.meta.*."""
    import alphamo.proposer as proposer_module

    with open(proposer_module.__file__) as f:
        content = f.read()
    assert "alphamo.meta" not in content
    assert "audit_log" not in content


def test_proposer_prompt_module_does_not_import_meta_layer():
    """Structural check: proposer_prompt must not import the meta layer."""
    import alphamo.prompts.proposer_prompt as pp

    with open(pp.__file__) as f:
        content = f.read()
    assert "alphamo.meta" not in content
    assert "MetaFinding" not in content
