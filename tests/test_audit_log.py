"""Tests for the append-only meta-layer audit log."""

from __future__ import annotations

from alphamo.meta.audit_log import AuditEvent, AuditLog


def _event(rationale: str = "test", action: str = "continue") -> AuditEvent:
    return AuditEvent(
        timestamp=AuditLog.now(),
        trigger="test",
        classification="no_action",
        action=action,
        rationale=rationale,
        payload={"k": "v"},
    )


def test_append_and_read_roundtrip(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append(_event("first"))
    log.append(_event("second"))
    events = log.read_all()
    assert [e.rationale for e in events] == ["first", "second"]


def test_read_all_empty_when_file_missing(tmp_path):
    log = AuditLog(tmp_path / "missing.jsonl")
    assert log.read_all() == []


def test_append_creates_parent_directory(tmp_path):
    log = AuditLog(tmp_path / "nested" / "deeper" / "audit.jsonl")
    log.append(_event("nested"))
    assert (tmp_path / "nested" / "deeper" / "audit.jsonl").exists()


def test_append_is_append_only(tmp_path):
    path = tmp_path / "audit.jsonl"
    log1 = AuditLog(path)
    log1.append(_event("first"))
    log2 = AuditLog(path)
    log2.append(_event("second"))
    assert [e.rationale for e in log2.read_all()] == ["first", "second"]


def test_payload_roundtrips(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale="r",
            payload={"findings": [{"claim": "x", "severity": "high"}]},
        )
    )
    [event] = log.read_all()
    assert event.payload["findings"][0]["claim"] == "x"
