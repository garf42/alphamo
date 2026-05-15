"""Regression test for reset-reseed isolation from meta-layer state.

The reset reseed (alphamo/database/operations.py::reset_island) must copy
ONLY: architecture_spec, scores, fitness, generation, parent_ids/lineage.
It must NOT carry any audit-log entries, curator notes, or red-team
findings, even when the source candidate triggered meta-layer activity.

The structural guarantee is that the Candidate schema has no column for
meta-layer state — these tests assert that property end-to-end and lock
it in against future schema changes.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from alphamo.database import ProgramsDB
from alphamo.database.operations import ProgramsDB as _ProgramsDB
from alphamo.database.schema import Candidate
from alphamo.meta.audit_log import AuditLog
from alphamo.meta.curator import Curator
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    MetaFinding,
    Severity,
)

LEAK_MARKER = "RESEED_LEAK_CANARY_8z2q"


def _candidate_with_marker_in_notes(name: str = "src") -> tuple[Architecture, Scores]:
    arch = Architecture(
        name=name,
        summary="s",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources="er",
        notes={"clean": "no meta state in here"},
    )
    scores = Scores(
        feasibility=0.9,
        structural=0.9,
        exemplar_similarity=0.9,
        middle_class_accessible=True,
    )
    return arch, scores


def test_candidate_schema_has_no_meta_layer_columns():
    """Structural guarantee: there is no slot on Candidate where meta-layer
    (curator / audit / drift-log) state could live.

    `stage4_findings` is explicitly NOT meta-layer state — it's evaluator
    output (adversarial concerns from Stage 4 of the cascade), persisted on
    the candidate row alongside `scores`. Per the Sprint-1 design,
    stage4_findings DOES travel with reseed because evaluator output
    belongs to the architecture, the same way scores do. We exclude it
    from the meta-layer scan below.
    """
    META_TOKENS = ("audit", "curator", "redteam", "red_team", "drift")
    EVAL_OUTPUT_COLUMNS = {"stage4_findings"}

    suspected = {
        c.name
        for c in Candidate.__table__.columns
        if any(tok in c.name.lower() for tok in META_TOKENS)
    }
    suspected -= EVAL_OUTPUT_COLUMNS
    assert suspected == set(), (
        f"Candidate gained meta-layer columns: {suspected} — "
        "reset_island must be reviewed for what it copies"
    )


def test_reset_island_only_copies_whitelisted_fields():
    """Lock in the field list that reset_island reads off the source row."""
    src = inspect.getsource(_ProgramsDB.reset_island)
    allowed_source_fields = {
        "source.architecture_spec",
        "source.scores",
        "source.stage4_findings",
        "source.fitness",
        "source.generation",
        "source.id",
    }
    forbidden_source_fields = [
        "source.notes",
        "source.audit",
        "source.findings",
        "source.curator",
        "source.payload",
    ]
    for needle in allowed_source_fields:
        assert needle in src, f"reset_island stopped reading {needle}"
    for needle in forbidden_source_fields:
        assert needle not in src, f"reset_island now reads {needle} — review for leakage"


def test_audit_event_has_no_candidate_foreign_key():
    """AuditEvent must not reference a *candidate* row by id.

    `run_id` is allowed and required — it points at runs.run_id, never at a
    candidate. The reseed-isolation guarantee is that meta state has no path
    back to a specific candidate, not that audit events can't carry any id.
    """
    from alphamo.meta.audit_log import AuditEvent

    fields = set(AuditEvent.model_fields)
    suspect = {f for f in fields if "candidate" in f.lower()}
    assert suspect == set(), (
        f"AuditEvent gained candidate-referencing fields: {suspect}"
    )
    # run_id is the only id-shaped field that should exist.
    id_fields = {f for f in fields if "_id" in f.lower()}
    assert id_fields == {"run_id"}, (
        f"AuditEvent gained unexpected id-shaped fields beyond run_id: "
        f"{id_fields - {'run_id'}}"
    )


def test_meta_finding_has_no_candidate_reference():
    """MetaFinding must not carry a candidate id."""
    fields = set(MetaFinding.model_fields)
    suspect = {f for f in fields if "candidate" in f.lower() or f == "id"}
    assert suspect == set(), (
        f"MetaFinding gained candidate-referencing fields: {suspect}"
    )


def test_reseed_after_curator_writes_audit_log(db, default_run, tmp_path):
    """Full path: candidate triggers curator → audit written → island reset → reseed.

    The reseed must inherit architecture/scores/lineage and nothing else; the
    audit log must remain on disk unaltered; the reseed row must have no
    pointer (direct or indirect) into the audit entries.
    """
    src_arch, src_scores = _candidate_with_marker_in_notes("source-candidate")
    src_id = db.insert(src_arch, src_scores, run_id=default_run, island_id=0)
    db.insert(
        Architecture(
            name="weak",
            summary="s",
            value_chain="vc",
            capture_mechanism="cm",
            entry_resources="er",
        ),
        Scores(
            feasibility=0.1,
            structural=0.1,
            exemplar_similarity=0.1,
            middle_class_accessible=True,
        ),
        run_id=default_run,
        island_id=1,
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    finding = MetaFinding(
        source="redteam",
        framing="regulatory",
        claim=f"{LEAK_MARKER}: the source candidate has a regulatory wrinkle",
        evidence="hypothetical",
        falsification_condition="if regulators sign off",
        severity=Severity.MEDIUM,
    )
    from tests.fixtures.parsed_message import FakeParsedMessage

    classify_client = MagicMock()
    classify_client.messages.parse.return_value = FakeParsedMessage(
        ClassificationVerdict(
            classification=Classification.COSMETIC,
            rationale=f"{LEAK_MARKER}: not blocking",
        )
    )
    Curator(classify_client, audit, run_id=default_run).curate(
        [finding], trigger="milestone_candidate"
    )

    audit_before = audit.read_all()
    assert len(audit_before) == 1
    assert LEAK_MARKER in audit_before[0].payload["findings"][0]["finding"]["claim"]

    db.reset_island(island_id=1, seed_programs=[src_id], run_id=default_run)

    [reseed] = db.top_k_in_island(island_id=1, k=10)
    assert reseed.id != src_id
    assert reseed.architecture_spec == db.get(src_id).architecture_spec
    assert reseed.scores == db.get(src_id).scores
    assert reseed.parent_ids == [src_id]
    assert reseed.status == "alive"
    assert reseed.island_id == 1

    serialised = repr(reseed) + " " + repr(reseed.architecture_spec) + " " + repr(reseed.scores) + " " + repr(reseed.parent_ids)
    assert LEAK_MARKER not in serialised, (
        "reseed somehow contains meta-layer canary string"
    )

    forbidden_attrs = ("audit", "findings", "curator_notes", "drift_log")
    for attr in forbidden_attrs:
        assert not hasattr(reseed, attr), (
            f"reseed gained attribute {attr!r} — meta state may be leaking"
        )

    audit_after = audit.read_all()
    assert audit_after == audit_before, "reset_island must not touch the audit log"


def test_reseed_preserves_clean_notes_but_does_not_invent_them(db, default_run, tmp_path):
    """architecture_spec.notes round-trips byte-for-byte across a reseed."""
    src_arch = Architecture(
        name="notes-source",
        summary="s",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources="er",
        notes={"foo": "bar", "baz": "qux"},
    )
    src_scores = Scores(
        feasibility=0.9, structural=0.9, exemplar_similarity=0.9,
        middle_class_accessible=True,
    )
    src_id = db.insert(src_arch, src_scores, run_id=default_run, island_id=0)
    db.insert(
        Architecture(name="w", summary="s", value_chain="vc", capture_mechanism="cm", entry_resources="er"),
        Scores(feasibility=0.1, structural=0.1, exemplar_similarity=0.1, middle_class_accessible=True),
        run_id=default_run,
        island_id=1,
    )

    db.reset_island(island_id=1, seed_programs=[src_id], run_id=default_run)
    [reseed] = db.top_k_in_island(island_id=1, k=10)

    assert reseed.architecture_spec["notes"] == {"foo": "bar", "baz": "qux"}
