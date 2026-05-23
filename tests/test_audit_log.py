"""Tests for the append-only meta-layer audit log."""

from __future__ import annotations

from alphamo.meta.audit_log import AuditEvent, AuditLog


def _event(rationale: str = "test", action: str = "continue", run_id: str = "run_test") -> AuditEvent:
    return AuditEvent(
        timestamp=AuditLog.now(),
        run_id=run_id,
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
            run_id="run_test",
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale="r",
            payload={"findings": [{"claim": "x", "severity": "high"}]},
        )
    )
    [event] = log.read_all()
    assert event.payload["findings"][0]["claim"] == "x"
    assert event.run_id == "run_test"


# ----------------------------------------------------------------- Sprint parallel-candidates: thread safety


def test_concurrent_appends_do_not_lose_or_corrupt_events(tmp_path):
    """Sprint parallel-candidates: with N parallel candidate pipelines
    in step(), multiple threads call audit_log.append concurrently
    (each provider.parse emits an llm_usage event). Without the lock
    around the file write, two writers' bytes can interleave, producing
    truncated lines or merged JSON.

    Spawn 8 threads × 25 events each (200 total) and verify every
    event roundtrips cleanly via read_all (no lost events, every line
    parses as valid JSON, content preserved)."""
    import threading

    log = AuditLog(tmp_path / "audit.jsonl")
    n_threads = 8
    events_per_thread = 25

    def writer(thread_id: int) -> None:
        for i in range(events_per_thread):
            log.append(_event(rationale=f"t{thread_id}-{i}"))

    threads = [
        threading.Thread(target=writer, args=(t,)) for t in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    events = log.read_all()
    # No event lost.
    assert len(events) == n_threads * events_per_thread, (
        f"expected {n_threads * events_per_thread} events, got {len(events)}; "
        "concurrent appends must not drop any"
    )
    # Every event content preserved (no interleaved bytes destroyed
    # the JSON structure or the rationale field).
    rationales = {e.rationale for e in events}
    expected = {
        f"t{t}-{i}"
        for t in range(n_threads)
        for i in range(events_per_thread)
    }
    assert rationales == expected, (
        f"missing/garbled events: only={rationales - expected}, "
        f"missing={expected - rationales}"
    )
