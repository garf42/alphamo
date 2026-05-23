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
from tests.fixtures.stage2_evidence import failing_stage2_finding, passing_stage2_finding
from tests.fixtures.stage1_evidence import failing_stage1_finding, passing_stage1_finding


# --------------------------------------------------------------------- schema migration


def test_schema_creates_stage4_findings_column_on_fresh_db(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    ProgramsDB(url)
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
    assert "stage4_findings" in cols


def test_schema_creates_stage4_assessments_column_on_fresh_db(tmp_path):
    """Sprint 15 (Q2): fresh DB carries the new stage4_assessments column."""
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    ProgramsDB(url)
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
    assert "stage4_assessments" in cols


def test_migration_adds_stage4_assessments_to_pre_sprint15_db(tmp_path):
    """Sprint 15 (Q2): a DB built before Sprint 15 (no stage4_assessments
    column) must auto-migrate when re-opened via ProgramsDB. Existing
    candidate rows are preserved and the new column backfills to NULL."""
    url = f"sqlite:///{tmp_path / 'pre_sprint15.db'}"

    # Build a candidates table WITHOUT stage4_assessments (carrying the
    # Sprint 14 column set — stage4_findings is present, parent_ids is
    # present).
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE candidates ("
                "id INTEGER PRIMARY KEY,"
                "run_id TEXT,"
                "architecture_spec JSON NOT NULL,"
                "scores JSON NOT NULL,"
                "stage4_findings JSON,"
                "fitness REAL NOT NULL,"
                "island_id INTEGER,"
                "generation INTEGER,"
                "parent_ids JSON,"
                "status TEXT,"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        # Seed one legacy row to confirm data preservation.
        conn.execute(
            text(
                "INSERT INTO candidates "
                "(architecture_spec, scores, fitness, status) "
                "VALUES ('{}', '{}', 0.5, 'alive')"
            )
        )

    # Open via ProgramsDB — should add the column without dropping the row.
    ProgramsDB(url)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
        rowcount = conn.execute(text("SELECT COUNT(*) FROM candidates")).scalar()
    assert "stage4_assessments" in cols
    assert rowcount == 1


def test_schema_creates_stage1_evidence_column_on_fresh_db(tmp_path):
    """Sprint Stage 1 PAJAMA: fresh DB carries the new stage1_evidence column."""
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    ProgramsDB(url)
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
    assert "stage1_evidence" in cols


def test_migration_adds_stage1_evidence_to_pre_stage1_pajama_db(tmp_path):
    """Sprint Stage 1 PAJAMA: a DB built before Stage 1 PAJAMA (no
    stage1_evidence column) must auto-migrate when re-opened via
    ProgramsDB. Existing rows are preserved and the new column
    backfills to NULL."""
    url = f"sqlite:///{tmp_path / 'pre_stage1_pajama.db'}"
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        # Post-Stage-2-PAJAMA column set (stage2_evidence present) but
        # no stage1_evidence yet.
        conn.execute(
            text(
                "CREATE TABLE candidates ("
                "id INTEGER PRIMARY KEY,"
                "run_id TEXT,"
                "architecture_spec JSON NOT NULL,"
                "scores JSON NOT NULL,"
                "stage4_findings JSON,"
                "stage4_assessments JSON,"
                "stage2_evidence JSON,"
                "fitness REAL NOT NULL,"
                "island_id INTEGER,"
                "generation INTEGER,"
                "parent_ids JSON,"
                "status TEXT,"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO candidates "
                "(architecture_spec, scores, fitness, status) "
                "VALUES ('{}', '{}', 0.5, 'alive')"
            )
        )
    ProgramsDB(url)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
        rowcount = conn.execute(text("SELECT COUNT(*) FROM candidates")).scalar()
    assert "stage1_evidence" in cols
    assert rowcount == 1


def test_schema_creates_stage2_evidence_column_on_fresh_db(tmp_path):
    """Sprint Stage 2 PAJAMA: fresh DB carries the new stage2_evidence column."""
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    ProgramsDB(url)
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
    assert "stage2_evidence" in cols


def test_migration_adds_stage2_evidence_to_pre_pajama_db(tmp_path):
    """Sprint Stage 2 PAJAMA: a DB built before PAJAMA (no stage2_evidence
    column) must auto-migrate when re-opened via ProgramsDB. Existing
    candidate rows are preserved and the new column backfills to NULL."""
    url = f"sqlite:///{tmp_path / 'pre_pajama.db'}"

    # Build a candidates table at the post-Sprint-15 column set (stage4_
    # findings + stage4_assessments + parent_ids all present) but without
    # the PAJAMA stage2_evidence column.
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE candidates ("
                "id INTEGER PRIMARY KEY,"
                "run_id TEXT,"
                "architecture_spec JSON NOT NULL,"
                "scores JSON NOT NULL,"
                "stage4_findings JSON,"
                "stage4_assessments JSON,"
                "fitness REAL NOT NULL,"
                "island_id INTEGER,"
                "generation INTEGER,"
                "parent_ids JSON,"
                "status TEXT,"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO candidates "
                "(architecture_spec, scores, fitness, status) "
                "VALUES ('{}', '{}', 0.5, 'alive')"
            )
        )

    ProgramsDB(url)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(candidates)"))}
        rowcount = conn.execute(text("SELECT COUNT(*) FROM candidates")).scalar()
    assert "stage2_evidence" in cols
    assert rowcount == 1


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
        lambda a, c, **kw: passing_stage1_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="ok"),
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
        candidates_per_generation=1,
    )


def test_orchestrator_persists_stage4_assessments_on_clean_framing_candidate(
    db, monkeypatch, tmp_path
):
    """Sprint 15 (Q2): when at least one Stage 3 framing returns clean
    with an assessment, the orchestrator must persist the per-framing
    assessment dict to the new stage4_assessments column. Pre-Sprint-15,
    the dict was collapsed into a clipped substring of the
    Stage4Finding.reasoning text and was lost beyond a forensic
    audit-log substring; the closed-RL-loop signal was destroyed at
    the DB boundary."""
    stub_assessments = {
        "regulatory": "operator-licensed throughout; no regulatory exposure surfaced",
        "operational": "single-person constraint cleanly satisfied",
    }
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c, **kw: passing_stage1_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.95,
            concerns=[],
            reasoning="all 9 framings clean",
            framing_assessments=stub_assessments,
        ),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)

    assert row.stage4_assessments is not None
    assert row.stage4_assessments == stub_assessments


def test_orchestrator_persists_stage1_evidence_on_every_inserted_candidate(
    db, monkeypatch, tmp_path
):
    """Sprint Stage 1 PAJAMA: every candidate that gets inserted has
    non-NULL stage1_evidence. Stage 1 is the entry point of the
    cascade, so any insertion path includes a Stage 1 evaluation."""
    from tests.fixtures.stage1_evidence import passing_stage1_finding

    stub_finding = passing_stage1_finding(reasoning="pajama-stage1 persistence test")
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility", lambda a, c, **kw: stub_finding
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85, concerns=[], reasoning="stub",
        ),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)

    assert row.stage1_evidence is not None
    # Categorical fields round-trip as their string values.
    assert row.stage1_evidence["revenue_type"] == "recurring"
    assert row.stage1_evidence["buyer_accessibility"] == "direct_to_business"
    assert row.stage1_evidence["capital_required"] == "10k_to_100k"
    assert row.stage1_evidence["regulatory_severity"] == "manageable"
    # Bottom-line booleans preserved.
    assert row.stage1_evidence["revenue_mechanism_identified"] is True
    assert row.stage1_evidence["middle_class_accessible"] is True
    # List fields preserved.
    assert isinstance(row.stage1_evidence["regulatory_blockers"], list)
    assert len(row.stage1_evidence["regulatory_blockers"]) == 1
    # Reasoning preserved.
    assert row.stage1_evidence["reasoning"] == "pajama-stage1 persistence test"


def test_orchestrator_persists_stage1_evidence_even_on_hard_exit(
    db, monkeypatch, tmp_path
):
    """Sprint Stage 1 PAJAMA: even when the cascade exits via Stage 1
    hard_exit (compute_feasibility < HARD_FLOOR), the candidate row
    still has its Stage 1 evidence persisted — the evidence is the
    audit trail explaining WHY the cascade rejected the candidate."""
    from tests.fixtures.stage1_evidence import failing_stage1_finding, passing_stage1_finding
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    def branched_stage1(arch, c, **kw):
        if arch.name == TRIVIAL_SEED.name:
            return passing_stage1_finding(reasoning="bootstrap ok")
        return failing_stage1_finding(reasoning="why this rejected")

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", branched_stage1)
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: (_ for _ in ()).throw(
            AssertionError("Stage 2 should not run on hard_exit")
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: (_ for _ in ()).throw(
            AssertionError("Stage 3 should not run on hard_exit")
        ),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)

    # Generated candidate (not the bootstrap seed) — hard-exit branch.
    assert row.architecture_spec["name"] != TRIVIAL_SEED.name
    assert row.stage1_evidence is not None
    # The failing fixture's distinctive reasoning string survives.
    assert row.stage1_evidence["reasoning"] == "why this rejected"
    # The cascade did exit hard — Stage 2 evidence column is NULL.
    assert row.stage2_evidence is None


def test_orchestrator_persists_stage2_evidence_when_stage2_runs(
    db, monkeypatch, tmp_path
):
    """Sprint Stage 2 PAJAMA: candidates that reached Stage 2 have the
    full evidence dict persisted in stage2_evidence. The structural
    scalar on Scores is the deterministic output of compute_structural;
    the evidence dict is the audit trail behind it."""
    from tests.fixtures.stage2_evidence import passing_stage2_finding

    stub_finding = passing_stage2_finding(reasoning="pajama-persistence test")
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c, **kw: passing_stage1_finding(reasoning="ok"),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured", lambda a, c, **kw: stub_finding
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85, concerns=[], reasoning="stub",
        ),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)

    assert row.stage2_evidence is not None
    # Categorical fields round-trip as their string values.
    assert (
        row.stage2_evidence["automation_plausibility"]
        == "requires_custom_engineering"
    )
    assert row.stage2_evidence["tam_estimate"] == ">$100B"
    # Bottom-line booleans preserved.
    assert row.stage2_evidence["one_person_operable"] is True
    assert row.stage2_evidence["separation_achieved"] is True
    # List fields preserved.
    assert isinstance(row.stage2_evidence["autonomous_value_sources"], list)
    assert len(row.stage2_evidence["autonomous_value_sources"]) == 2
    # Reasoning string preserved.
    assert row.stage2_evidence["reasoning"] == "pajama-persistence test"


def test_orchestrator_leaves_stage2_evidence_null_on_stage1_exit(
    db, monkeypatch, tmp_path
):
    """Sprint Stage 2 PAJAMA: candidates that short-circuited at Stage 1
    (middle-class filter exit OR feasibility threshold exit) MUST have
    stage2_evidence=NULL — Stage 2 didn't run, there's no evidence to
    record."""
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    def branched_stage1(arch, c, **kw):
        # Trivial seed bootstrap path completes; the proposer-generated
        # candidate uses failing_stage1_finding (compute_feasibility=0.0,
        # below STAGE1_HARD_FLOOR=0.15), so the cascade exits in the
        # hard_exit zone before Stage 2 runs.
        if arch.name == TRIVIAL_SEED.name:
            return passing_stage1_finding(reasoning="ok")
        return failing_stage1_finding(reasoning="too low")

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", branched_stage1)
    # Stage 2 / 3 stubs exist but shouldn't fire on the generated
    # candidate — the test ALSO confirms they didn't fire by checking
    # the early_exit column.
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: (_ for _ in ()).throw(
            AssertionError("Stage 2 should not run on Stage 1 exit")
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: (_ for _ in ()).throw(
            AssertionError("Stage 3 should not run on Stage 1 exit")
        ),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(
        db, _stub_client(), audit, hp=_disable_milestone_hp()
    )
    result = orch.run(max_generations=1)
    # The generated candidate is whichever was inserted at gen=1 with
    # name != TRIVIAL_SEED.
    candidate_event = next(e for e in result.events if e.candidate_id is not None)
    row = db.get(candidate_event.candidate_id)
    assert row.architecture_spec["name"] != TRIVIAL_SEED.name
    assert row.stage2_evidence is None


def test_orchestrator_persists_stage4_findings_on_stage4_reaching_candidate(
    db, monkeypatch, tmp_path
):
    """Bug 2: Stage 4 concerns must be on the candidate row, not just the audit log."""
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
    """Candidates short-circuiting before Stage 4 must have stage4_findings=NULL.

    Sprint 3: bootstrap inserts the trivial seed first; this test
    branches the stage1 stub by architecture name so the trivial seed
    bootstraps successfully but the proposer-generated candidate
    fails the middle-class filter — the resulting row is the one
    whose stage4_findings we assert on.
    """
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED
    def stage1_branched(arch, c, **kw):
        if arch.name == TRIVIAL_SEED.name:
            return passing_stage1_finding(reasoning="bootstrap ok")
        # Sprint Stage 1 PAJAMA: middle_class_accessible=False is the
        # MC hard gate. Build a fixture that otherwise scores cleanly
        # but has the MC bool flipped, so the cascade exits via the
        # MC path rather than via a low compute_feasibility score.
        return passing_stage1_finding(reasoning="failed filter").model_copy(
            update={"middle_class_accessible": False}
        )

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", stage1_branched)
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: passing_stage2_finding(reasoning="x"),
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
    assert row.architecture_spec["name"] != TRIVIAL_SEED.name
    assert row.stage4_findings is None


def test_orchestrator_persists_empty_concerns_as_empty_list_not_null(
    db, monkeypatch, tmp_path
):
    """Stage 4 that runs and finds nothing: stage4_findings=[], distinguishable from NULL."""
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
