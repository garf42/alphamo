"""Tests for the harvest-time handoff builder.

The handoff structure honestly separates seeds from generated discoveries:
seed_baselines is informational, top_generated_discoveries is the research
output, no_breakthrough_this_run flags whether the search exceeded its
starting baseline, and winning_architecture is null whenever it didn't.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.context.verifier import VERIFIER_ANCHOR
from alphamo.evaluator import EvaluatorCascade, cascade as cascade_mod
from alphamo.evaluator.exemplar_library import STARTERS
from alphamo.handoff import build_handoff
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage3Finding,
    Stage4Finding,
    StructuralConcern,
)
from tests.fixtures.exemplars import (
    LEVELS_FIXTURE,
    ROWLING_FIXTURE,
    SATOSHI_FIXTURE,
)


@pytest.fixture()
def cascade(monkeypatch) -> EvaluatorCascade:
    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=0.95, middle_class_accessible=True, reasoning="s1 ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=0.9,
            billion_dollar_potential=0.9,
            labor_separation=0.9,
            structural=0.9,
            reasoning="s2 ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage3_exemplars",
        lambda a, c: Stage3Finding(
            closest_exemplar="Satoshi",
            similarity=0.95,
            reasoning="s3 ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85,
            concerns=[
                StructuralConcern(
                    framing="legal_exposure",
                    claim="harvest-time stub concern",
                    evidence="stub",
                    falsification_condition="if x",
                    severity=Severity.LOW,
                )
            ],
            reasoning="s4 ok",
        ),
    )
    return EvaluatorCascade(client=MagicMock())


# ----------------------------------------------------------------- helpers


def _seed_all_islands(db, run_id: str, num_islands: int = 4) -> None:
    """Mirror Orchestrator.seed_if_empty(): every island gets every STARTER."""
    for island_id in range(num_islands):
        for arch, scores in STARTERS:
            db.insert(arch, scores, run_id=run_id, island_id=island_id, generation=0)


def _gen_arch(name: str, entry_resources: str = "laptop, modest savings") -> Architecture:
    return Architecture(
        name=name,
        summary=f"{name} summary",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources=entry_resources,
    )


def _gen_scores(target_fitness: float) -> Scores:
    """Construct a Scores whose 4-way aggregate equals `target_fitness`."""
    return Scores(
        feasibility=target_fitness,
        structural=target_fitness,
        exemplar_similarity=target_fitness,
        robustness=target_fitness,
        middle_class_accessible=True,
    )


def _populate_legacy_three(db, run_id: str) -> tuple[int, int, int]:
    """Insert SATOSHI/ROWLING/LEVELS as gen-0 seed-named candidates."""
    sat = db.insert(
        SATOSHI_FIXTURE.architecture,
        SATOSHI_FIXTURE.scores,
        run_id=run_id,
        island_id=0,
        generation=0,
    )
    rowl = db.insert(
        ROWLING_FIXTURE.architecture,
        ROWLING_FIXTURE.scores,
        run_id=run_id,
        island_id=1,
        generation=0,
    )
    lev = db.insert(
        LEVELS_FIXTURE.architecture,
        LEVELS_FIXTURE.scores,
        run_id=run_id,
        island_id=2,
        generation=0,
    )
    return sat, rowl, lev


# ----------------------------------------------------------------- four edge cases


def test_handoff_seeds_only_no_generated(db, cascade, default_run, tmp_path):
    """Generation 0 only: only STARTERS in DB, no generated candidates.

    Expected: seed_baselines populated, top_generated_discoveries empty,
    no_breakthrough True, winning_architecture None, parent_goal_alignment
    explicitly notes "no generated candidates".
    """
    _seed_all_islands(db, default_run)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)

    assert {b.name for b in handoff.seed_baselines} == {
        "Satoshi", "Rowling", "Levels", "Medvi"
    }
    assert handoff.top_generated_discoveries == []
    assert handoff.no_breakthrough_this_run is True
    assert handoff.winning_architecture is None
    assert "no generated candidates" in handoff.parent_goal_alignment.lower()


def test_handoff_all_generated_below_lowest_seed(db, cascade, default_run, tmp_path):
    """Generated candidates exist but all fall below min(seed_baselines.fitness).

    Lowest seed is Medvi (~0.572). Inserting generated below that should
    leave no_breakthrough=True and winning=None, but top_generated_discoveries
    must still surface them as the best the search produced.
    """
    _seed_all_islands(db, default_run)
    db.insert(_gen_arch("low-1"), _gen_scores(0.40),
              run_id=default_run, island_id=0, generation=5)
    db.insert(_gen_arch("low-2"), _gen_scores(0.30),
              run_id=default_run, island_id=1, generation=6)

    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)

    assert handoff.no_breakthrough_this_run is True
    assert handoff.winning_architecture is None
    assert len(handoff.top_generated_discoveries) == 2
    # Sorted by fitness desc.
    assert handoff.top_generated_discoveries[0].spec.name == "low-1"
    assert handoff.top_generated_discoveries[1].spec.name == "low-2"
    # Alignment text opens with the explicit no-breakthrough acknowledgement.
    assert handoff.parent_goal_alignment.startswith(
        "No generated candidate matched or exceeded seed baselines"
    )
    # Top discoveries described in alignment text.
    assert "low-1" in handoff.parent_goal_alignment


def test_handoff_some_generated_exceed_lowest_seed(db, cascade, default_run, tmp_path):
    """Generated above min seed but below max: counts as breakthrough.

    Medvi (~0.572) is the floor; any generated above 0.572 unlocks
    `winning_architecture`, even if Satoshi (~0.888) is still highest in
    aggregate. The "winner" is the top generated, not a seed.
    """
    _seed_all_islands(db, default_run)
    db.insert(_gen_arch("breakthrough-mid"), _gen_scores(0.65),
              run_id=default_run, island_id=0, generation=10)
    db.insert(_gen_arch("low"), _gen_scores(0.40),
              run_id=default_run, island_id=1, generation=8)

    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)

    assert handoff.no_breakthrough_this_run is False
    assert handoff.winning_architecture is not None
    assert handoff.winning_architecture.spec.name == "breakthrough-mid"
    assert handoff.top_generated_discoveries[0].spec.name == "breakthrough-mid"
    assert "breakthrough-mid" in handoff.parent_goal_alignment


def test_handoff_generated_exceeds_all_seeds(db, cascade, default_run, tmp_path):
    """A real top-of-search discovery: generated exceeds Satoshi (~0.888)."""
    _seed_all_islands(db, default_run)
    db.insert(_gen_arch("super-discovery"), _gen_scores(0.95),
              run_id=default_run, island_id=2, generation=20,
              parent_ids=[1, 2])

    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)

    assert handoff.no_breakthrough_this_run is False
    assert handoff.winning_architecture is not None
    assert handoff.winning_architecture.spec.name == "super-discovery"
    assert handoff.winning_architecture.lineage == [1, 2]
    assert handoff.winning_architecture.generation == 20
    assert handoff.winning_architecture.island_of_origin == 2
    # Alignment text describes the winning generated candidate.
    assert handoff.parent_goal_alignment.startswith(
        "Winning generated candidate 'super-discovery'"
    )


# ----------------------------------------------------------------- structure invariants


def test_seed_baselines_always_four_entries(db, cascade, default_run, tmp_path):
    """Even with no DB rows for a seed, the baseline list is sourced from STARTERS."""
    # Insert only one seed copy and a generated.
    db.insert(SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores,
              run_id=default_run, island_id=0, generation=0)
    db.insert(_gen_arch("g"), _gen_scores(0.5),
              run_id=default_run, island_id=1, generation=2)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert len(handoff.seed_baselines) == 4


def test_top_generated_discoveries_capped_at_default_seven(db, cascade, default_run, tmp_path):
    """Default top-N is 7; extras must be dropped from the discovery list."""
    _seed_all_islands(db, default_run)
    for i in range(10):
        db.insert(
            _gen_arch(f"gen-{i:02d}"),
            _gen_scores(0.6 - i * 0.01),  # 0.60, 0.59, ..., 0.51
            run_id=default_run, island_id=i % 4, generation=5 + i,
        )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert len(handoff.top_generated_discoveries) == 7
    # Highest first.
    assert handoff.top_generated_discoveries[0].spec.name == "gen-00"


# ----------------------------------------------------------------- migrated meta tests


def test_build_handoff_records_eval_count(db, cascade, default_run, tmp_path):
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert handoff.verification_trail.eval_count == 4


def test_build_handoff_uses_verifier_anchor(db, cascade, default_run, tmp_path):
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert handoff.verification_trail.anchor_used == VERIFIER_ANCHOR


def test_build_handoff_carries_run_provenance(db, cascade, default_run, tmp_path):
    """run_id, hyperparameters, parent_goal_version, verifier_version are in the trail."""
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    trail = handoff.verification_trail
    assert trail.run_id == default_run
    assert trail.parent_goal_version == "test"
    assert trail.verifier_version == "test"
    assert isinstance(trail.hyperparameters, dict)


def test_build_handoff_includes_exemplar_comparison_when_cascade_runs(
    db, cascade, default_run, tmp_path
):
    """Re-cascade fires on the top generated candidate, populating exemplar_comparisons."""
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    [comparison] = handoff.verification_trail.exemplar_comparisons
    assert comparison.closest_exemplar == "Satoshi"
    assert comparison.similarity == 0.95


def test_build_handoff_skips_cascade_when_only_seeds(db, cascade, default_run, tmp_path):
    """No generated candidates ⇒ no cascade subject ⇒ empty verification trail data."""
    _seed_all_islands(db, default_run)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert handoff.verification_trail.exemplar_comparisons == []
    assert handoff.verification_trail.adversarial_concerns == []
    assert handoff.verification_trail.final_scores is None


def test_build_handoff_drift_log_projects_audit_events(db, cascade, default_run, tmp_path):
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=default_run,
            trigger="milestone_candidate",
            classification="cosmetic",
            action="continue",
            rationale="not blocking",
            payload={"findings": [{"finding": {"source": "redteam"}}]},
        )
    )
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=default_run,
            trigger="scheduled_interval",
            classification="structural",
            action="pause_for_human",
            rationale="blocks goal",
            payload={"findings": [{"finding": {"source": "research"}}]},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert [e.type for e in handoff.drift_log] == ["cosmetic", "structural"]
    assert [e.source for e in handoff.drift_log] == ["redteam", "research"]
    assert handoff.drift_log[1].action == "pause_for_human"


def test_build_handoff_drift_log_filters_other_runs(db, cascade, default_run, tmp_path):
    """Audit events for OTHER runs must not appear in this handoff's drift log."""
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    other_run_id = db.create_run(
        hyperparameters={}, parent_goal_version="test", verifier_version="test"
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=other_run_id,
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale="from other run",
            payload={},
        )
    )
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=default_run,
            trigger="t",
            classification="cosmetic",
            action="continue",
            rationale="from this run",
            payload={},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert len(handoff.drift_log) == 1
    assert handoff.drift_log[0].rationale == "from this run"


def test_build_handoff_middle_class_check_reflects_cascade_subject(
    db, cascade, default_run, tmp_path
):
    """The middle_class check reflects the cascade subject (top generated), not a seed."""
    _seed_all_islands(db, default_run)
    db.insert(
        _gen_arch("with-resources", entry_resources="cryptography skill, modest hardware"),
        _gen_scores(0.7),
        run_id=default_run, island_id=0, generation=5,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    check = handoff.middle_class_entry_check
    assert check.passes is True
    assert "cryptography" in check.estimated_starting_resources.lower()
    assert check.stage_sequence == [
        "stage1_feasibility",
        "stage2_structured",
        "stage3_exemplars",
    ]


def test_build_handoff_middle_class_check_placeholder_when_no_generated(
    db, cascade, default_run, tmp_path
):
    """No generated candidate ⇒ placeholder middle_class check (passes=True, empty stages)."""
    _seed_all_islands(db, default_run)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    check = handoff.middle_class_entry_check
    assert check.passes is True
    assert "no generated candidates" in check.estimated_starting_resources.lower()
    assert check.stage_sequence == []


def test_build_handoff_coverage_residual_flags_unresolved_structural(
    db, cascade, default_run, tmp_path
):
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=default_run,
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale="r",
            payload={},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert "1 structural" in handoff.coverage_residual
    assert default_run in handoff.coverage_residual


def test_build_handoff_coverage_residual_clean_when_no_meta(db, cascade, default_run, tmp_path):
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert "no unresolved" in handoff.coverage_residual
    assert "fresh" in handoff.coverage_residual


def test_build_handoff_coverage_residual_marks_resumed_run(db, cascade, default_run, tmp_path):
    _populate_legacy_three(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.6),
              run_id=default_run, island_id=0, generation=3)
    db.mark_run_resumed(default_run)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    assert "resumed" in handoff.coverage_residual


def test_build_handoff_raises_on_empty_run(db, cascade, default_run, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(RuntimeError, match="nothing to harvest"):
        build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)


def test_build_handoff_raises_on_missing_run(db, cascade, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(KeyError):
        build_handoff(db, audit, cascade, num_islands=4, run_id="run_does_not_exist")


def test_build_handoff_serialisable_to_json(db, cascade, default_run, tmp_path):
    """Full handoff round-trips to JSON (includes new fields and null winner)."""
    _seed_all_islands(db, default_run)
    db.insert(_gen_arch("g"), _gen_scores(0.7),
              run_id=default_run, island_id=0, generation=5)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    payload = handoff.model_dump_json()
    assert "seed_baselines" in payload
    assert "top_generated_discoveries" in payload
    assert "no_breakthrough_this_run" in payload
    assert "Satoshi" in payload  # seed baseline name
    assert default_run in payload


def test_build_handoff_serialisable_when_no_winner(db, cascade, default_run, tmp_path):
    """Null winning_architecture serialises cleanly."""
    _seed_all_islands(db, default_run)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    payload = handoff.model_dump_json()
    # Pydantic emits the optional null explicitly.
    assert '"winning_architecture":null' in payload.replace(" ", "")


def test_generated_discovery_carries_stage4_findings(db, cascade, default_run, tmp_path):
    """If a generated row has stage4_findings persisted, they ride into the handoff."""
    _seed_all_islands(db, default_run)
    findings_payload = [
        {
            "framing": "regulatory",
            "claim": "test claim",
            "evidence": "ev",
            "falsification_condition": "if y",
            "severity": "high",
        }
    ]
    db.insert(
        _gen_arch("with-findings"), _gen_scores(0.7),
        run_id=default_run, island_id=0, generation=5,
        stage4_findings=findings_payload,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    [discovery] = handoff.top_generated_discoveries
    assert discovery.stage4_findings is not None
    assert len(discovery.stage4_findings) == 1
    assert discovery.stage4_findings[0].framing == "regulatory"


def test_generated_discovery_stage4_findings_none_when_legacy(
    db, cascade, default_run, tmp_path
):
    """Pre-Stage-4 candidates (stage4_findings=NULL) preserve the None distinction."""
    _seed_all_islands(db, default_run)
    db.insert(_gen_arch("legacy"), _gen_scores(0.7),
              run_id=default_run, island_id=0, generation=5)  # no stage4_findings
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=default_run)
    [discovery] = handoff.top_generated_discoveries
    assert discovery.stage4_findings is None
