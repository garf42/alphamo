"""Sprint 1 tests: Stage 4 persistence + audit-log backfill.

Bug 2 — stage4_findings JSON column added to candidates; orchestrator writes
findings alongside scores. Bug 1 + 2 backfill — recompute robustness and
populate stage4_findings on existing run-006-shape databases from the audit
log without touching the LLM.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.database import ProgramsDB
from alphamo.database.schema import Candidate
from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.exemplar_library import SEED_REFERENCES
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.orchestrator import Orchestrator
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
    StructuralConcern,
)
from tests.fixtures.parsed_message import FakeParsedMessage


# --------------------------------------------------------------------- schema migration


def test_schema_creates_stage4_findings_column_on_fresh_db(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    ProgramsDB(url)
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
    assert "stage4_findings" in cols


def test_migration_adds_stage4_findings_to_pre_sprint1_db(tmp_path):
    """A DB created before Sprint 1 (no stage4_findings column) must auto-migrate."""
    url = f"sqlite:///{tmp_path / 'pre_sprint1.db'}"

    # Build a candidates table WITHOUT stage4_findings.
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE candidates ("
                "id INTEGER PRIMARY KEY,"
                "run_id TEXT,"
                "architecture_spec JSON NOT NULL,"
                "scores JSON NOT NULL,"
                "fitness REAL NOT NULL,"
                "island_id INTEGER,"
                "generation INTEGER,"
                "parent_ids JSON,"
                "status TEXT,"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )

    # Open via ProgramsDB — should migrate.
    ProgramsDB(url)

    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
    assert "stage4_findings" in cols


def test_migration_is_idempotent_across_reopens(tmp_path):
    """Opening the same DB twice does not duplicate-add the column."""
    url = f"sqlite:///{tmp_path / 'idem.db'}"
    ProgramsDB(url)
    ProgramsDB(url)  # should not raise
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        rows = list(conn.execute(text("PRAGMA table_info(candidates)")))
    name_counts: dict[str, int] = {}
    for row in rows:
        name_counts[row[1]] = name_counts.get(row[1], 0) + 1
    assert name_counts["stage4_findings"] == 1


# --------------------------------------------------------------------- orchestrator persistence


def _stub_full_cascade_with_concerns(monkeypatch, stage4_concerns):
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=0.9, middle_class_accessible=True, reasoning="ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=0.9, billion_dollar_potential=0.9,
            labor_separation=0.9, structural=0.9, reasoning="ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.6,
            concerns=stage4_concerns,
            reasoning="stub",
        ),
    )


def _stub_client():
    from alphamo.schemas import Architecture

    client = MagicMock()

    def parse_side_effect(**kwargs):
        if kwargs.get("output_format") is Architecture:
            return FakeParsedMessage(
                Architecture(
                    name="proposed", summary="s", value_chain="vc",
                    capture_mechanism="cm", entry_resources="er",
                )
            )
        if kwargs.get("output_format") is ClassificationVerdict:
            return FakeParsedMessage(
                ClassificationVerdict(
                    classification=Classification.COSMETIC, rationale="stub"
                )
            )
        return FakeParsedMessage(MagicMock())

    client.messages.parse.side_effect = parse_side_effect
    return client


def _disable_milestone_hp() -> Hyperparameters:
    return Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )


def test_orchestrator_persists_stage4_findings_on_stage4_reaching_candidate(
    db, monkeypatch, tmp_path
):
    """Bug 2: Stage 4 concerns must be on the candidate row, not just the audit log."""
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    concerns = [
        StructuralConcern(
            framing="economic", claim="margin compression",
            evidence="competitive markets", falsification_condition="if moat",
            severity=Severity.HIGH,
        ),
        StructuralConcern(
            framing="legal_exposure", claim="UPL exposure",
            evidence="state bar opinions", falsification_condition="if scope narrow",
            severity=Severity.MEDIUM,
        ),
    ]
    _stub_full_cascade_with_concerns(monkeypatch, concerns)

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)

    assert row.stage4_findings is not None
    assert len(row.stage4_findings) == 2
    framings = {c["framing"] for c in row.stage4_findings}
    assert framings == {"economic", "legal_exposure"}


def test_orchestrator_leaves_stage4_findings_null_on_early_exit(
    db, monkeypatch, tmp_path
):
    """Candidates short-circuiting before Stage 4 must have stage4_findings=NULL."""
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    # Stage 1 produces middle_class_accessible=False, triggering middle-class
    # filter exit. Stage 4 never runs.
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=0.9, middle_class_accessible=False, reasoning="failed filter"
        ),
    )
    # Other stages stubbed but should not be called.
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=0.9, billion_dollar_potential=0.9,
            labor_separation=0.9, structural=0.9, reasoning="x",
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(robustness=0.5, concerns=[], reasoning="x"),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)
    assert row.stage4_findings is None


def test_orchestrator_persists_empty_concerns_as_empty_list_not_null(
    db, monkeypatch, tmp_path
):
    """Stage 4 that runs and finds nothing: stage4_findings=[], distinguishable from NULL."""
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    _stub_full_cascade_with_concerns(monkeypatch, stage4_concerns=[])

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)
    assert row.stage4_findings == []


# --------------------------------------------------------------------- backfill


def _fake_stage4_routine_event(
    run_id: str, candidate_id: int, robustness: float, concerns: list[dict]
) -> AuditEvent:
    return AuditEvent(
        timestamp=AuditLog.now(),
        run_id=run_id,
        trigger="stage4_routine",
        classification="routine",
        action="recorded",
        rationale=(
            f"candidate={candidate_id} robustness={robustness:.3f} "
            f"concerns={len(concerns)}"
        ),
        payload={
            "candidate_id": candidate_id,
            "robustness": robustness,
            "concerns": concerns,
            "reasoning": "fake",
        },
    )


def _concern_dict(severity: str, framing: str = "economic") -> dict:
    return {
        "framing": framing,
        "claim": "test claim",
        "evidence": "test evidence",
        "falsification_condition": "if x",
        "severity": severity,
    }


def test_backfill_populates_stage4_findings_and_recomputes_robustness(db, default_run):
    """A pre-Sprint-1-shaped candidate gets stage4_findings populated and
    robustness recomputed via the new formula on backfill."""
    # Insert a candidate WITHOUT stage4_findings, simulating run-006.
    from alphamo.schemas import Scores

    arch_run006 = SEED_REFERENCES[0]
    bad_scores = Scores(
        feasibility=0.85,
        structural=0.85,
        exemplar_similarity=0.85,
        robustness=0.0,  # run-006 bug: clamped to 0
        middle_class_accessible=True,
    )
    cand_id = db.insert(arch_run006, bad_scores, run_id=default_run)

    # Simulate the audit event that would have been logged for this candidate
    # — 15 HIGH + 25 MED, matching run-006 low-end concern counts.
    concerns = (
        [_concern_dict("high")] * 15
        + [_concern_dict("medium")] * 25
    )
    audit_events = [
        _fake_stage4_routine_event(default_run, cand_id, robustness=0.0, concerns=concerns)
    ]

    stats = db.backfill_stage4_from_audit(audit_events, decay_k=0.15)
    assert stats["updated"] == 1
    assert stats["skipped_existing"] == 0

    row = db.get(cand_id)
    assert row.stage4_findings is not None
    assert len(row.stage4_findings) == 40
    # weighted = 15*0.30 + 25*0.10 = 7.0; exp(-1.05) = 0.3499
    new_robustness = row.scores["robustness"]
    assert new_robustness == pytest.approx(0.3499, abs=1e-3)
    # fitness must be re-aggregated too: (0.85 + 0.85 + 0.85 + 0.3499)/4 = 0.7250
    assert row.fitness == pytest.approx(0.7250, abs=1e-3)


def test_backfill_is_idempotent(db, default_run):
    """Re-running backfill on a candidate that already has stage4_findings is a no-op."""
    from alphamo.schemas import Scores

    arch = SEED_REFERENCES[0]
    cand_id = db.insert(
        arch,
        Scores(
            feasibility=0.9, structural=0.9, exemplar_similarity=0.9,
            robustness=0.5, middle_class_accessible=True,
        ),
        run_id=default_run,
        stage4_findings=[_concern_dict("medium")],
    )
    fresh_event = _fake_stage4_routine_event(
        default_run, cand_id, robustness=0.0, concerns=[_concern_dict("high")] * 10
    )
    stats = db.backfill_stage4_from_audit([fresh_event])
    assert stats["updated"] == 0
    assert stats["skipped_existing"] == 1

    row = db.get(cand_id)
    # Unchanged from the original insert.
    assert len(row.stage4_findings) == 1
    assert row.scores["robustness"] == 0.5


def test_backfill_skips_unmatched_candidate_ids(db, default_run):
    """An audit event referencing a candidate id that no longer exists is reported but doesn't error."""
    audit_events = [
        _fake_stage4_routine_event(
            default_run, candidate_id=9999, robustness=0.0,
            concerns=[_concern_dict("high")],
        )
    ]
    stats = db.backfill_stage4_from_audit(audit_events)
    assert stats["updated"] == 0
    assert stats["skipped_missing"] == 1


def test_backfill_ignores_non_stage4_events(db, default_run):
    """Curator-event audit entries do not trigger backfill updates."""
    from alphamo.schemas import Scores

    arch = SEED_REFERENCES[0]
    cand_id = db.insert(
        arch,
        Scores(
            feasibility=0.9, structural=0.9, exemplar_similarity=0.9,
            robustness=0.0, middle_class_accessible=True,
        ),
        run_id=default_run,
    )
    curator_event = AuditEvent(
        timestamp=AuditLog.now(),
        run_id=default_run,
        trigger="milestone_candidate",
        classification="cosmetic",
        action="continue",
        rationale="not relevant",
        payload={"findings": []},
    )
    stats = db.backfill_stage4_from_audit([curator_event])
    assert stats["updated"] == 0
    assert stats["skipped_non_stage4"] == 1
    row = db.get(cand_id)
    assert row.stage4_findings is None  # untouched
