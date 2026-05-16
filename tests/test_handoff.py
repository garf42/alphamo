"""Tests for the harvest-time handoff builder (Sprint 2 redesign).

The handoff structure:
  - `seed_baselines`: descriptive reference (no fitness), sourced from
    SEED_REFERENCES.
  - `top_generated_discoveries`: alive candidates, sorted by fitness desc.
  - `no_breakthrough_this_run`: True when no candidate cleared the
    absolute milestone thresholds (fitness AND robustness floors).
  - `winning_architecture`: highest-fitness candidate when a breakthrough
    occurred, else null.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.verifier import VERIFIER_ANCHOR
from alphamo.evaluator import EvaluatorCascade, cascade as cascade_mod
from alphamo.handoff import build_handoff
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
    StructuralConcern,
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
            reasoning="s3 ok",
        ),
    )
    return EvaluatorCascade(client=MagicMock())


# ----------------------------------------------------------------- helpers


def _gen_arch(name: str, entry_resources: str = "laptop, modest savings") -> Architecture:
    return Architecture(
        name=name,
        summary=f"{name} summary",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources=entry_resources,
    )


def _scores(target_fitness: float, robustness: float | None = None) -> Scores:
    """Construct Scores whose 3-way aggregate equals `target_fitness`.

    If `robustness` is set explicitly, the aggregate uses (feasibility +
    structural + robustness) / 3 with feasibility = structural = robustness =
    target_fitness. To decouple them, pass robustness explicitly.
    """
    if robustness is None:
        robustness = target_fitness
    # Solve: (f + s + r) / 3 = target_fitness → f + s = 3*target - r.
    fs = 3 * target_fitness - robustness
    half = fs / 2
    return Scores(
        feasibility=max(0.0, min(1.0, half)),
        structural=max(0.0, min(1.0, half)),
        robustness=robustness,
        middle_class_accessible=True,
    )


def _hp_low_milestone() -> Hyperparameters:
    """HP with low absolute thresholds so test candidates can clear them."""
    return Hyperparameters(
        milestone_absolute_fitness_threshold=0.50,
        milestone_absolute_robustness_threshold=0.50,
    )


def _hp_high_milestone() -> Hyperparameters:
    """HP with high thresholds so test candidates cannot clear them."""
    return Hyperparameters(
        milestone_absolute_fitness_threshold=0.99,
        milestone_absolute_robustness_threshold=0.99,
    )


def _make_run(db, hp: Hyperparameters | None = None) -> str:
    """Create a run with explicit hyperparameters so milestone gating is controllable."""
    hp = hp or Hyperparameters()
    return db.create_run(
        hyperparameters=hp.model_dump(),
        parent_goal_version="test",
        verifier_version="test",
    )


# ----------------------------------------------------------------- shape


def test_handoff_seed_baselines_is_single_trivial_entry(db, cascade, tmp_path):
    """Sprint 3: seed_baselines is a single-entry list — the trivial baseline.

    Inverts the Sprint 2 invariant ("descriptive references, multiple
    entries, no fitness"). Sprint 3 carries one entry — the gen-0
    trivial Solo Service Provider — with its actual scored fitness from
    the candidates table.
    """
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=1)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    assert len(handoff.seed_baselines) == 1
    [baseline] = handoff.seed_baselines
    assert baseline.name == TRIVIAL_SEED.name
    assert baseline.summary
    assert baseline.capture_mechanism
    # design_intent comes from the TRIVIAL_SEED's notes field.
    assert baseline.design_intent is not None
    assert "exceeded by evolution" in baseline.design_intent.lower()


def test_handoff_baseline_carries_actual_scored_fitness(db, cascade, tmp_path):
    """When a gen-0 trivial-seed row exists in this run, baseline_fitness
    reflects its actual scored fitness from the candidates table."""
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    run_id = _make_run(db)
    # Insert a gen-0 trivial-seed copy with a known fitness.
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=run_id, island_id=0, generation=0,
    )
    # Plus a generated discovery so the handoff has something to harvest.
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=1, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    [baseline] = handoff.seed_baselines
    # Aggregate = (0.6 + 0.2 + 0.3) / 3 = 0.3667
    assert baseline.baseline_fitness == pytest.approx(0.3667, abs=1e-3)


def test_handoff_baseline_fitness_is_none_when_no_gen0_seed_row(
    db, cascade, tmp_path
):
    """Legacy DB without a gen-0 trivial-seed row: baseline_fitness is None."""
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=1)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    [baseline] = handoff.seed_baselines
    assert baseline.baseline_fitness is None


def test_handoff_top_discoveries_excludes_gen0_trivial_seed_copies(
    db, cascade, tmp_path
):
    """Gen-0 trivial-seed copies must NOT appear in top_generated_discoveries —
    they belong in seed_baselines, not in the search-output projection."""
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    run_id = _make_run(db)
    db.insert(
        TRIVIAL_SEED,
        Scores(
            feasibility=0.6, structural=0.2, robustness=0.3,
            middle_class_accessible=True,
        ),
        run_id=run_id, island_id=0, generation=0,
    )
    db.insert(_gen_arch("real-discovery"), _scores(0.6),
              run_id=run_id, island_id=1, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    discovery_names = {d.spec.name for d in handoff.top_generated_discoveries}
    assert TRIVIAL_SEED.name not in discovery_names
    assert "real-discovery" in discovery_names


# ----------------------------------------------------------------- breakthrough semantics


def test_handoff_no_breakthrough_when_no_candidate_clears_thresholds(
    db, cascade, tmp_path
):
    """Candidates exist but none clears absolute milestone thresholds."""
    run_id = _make_run(db, hp=_hp_high_milestone())
    db.insert(_gen_arch("low-1"), _scores(0.50), run_id=run_id, island_id=0, generation=5)
    db.insert(_gen_arch("low-2"), _scores(0.40), run_id=run_id, island_id=1, generation=6)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    assert handoff.no_breakthrough_this_run is True
    assert handoff.winning_architecture is None
    assert len(handoff.top_generated_discoveries) == 2
    assert handoff.top_generated_discoveries[0].spec.name == "low-1"  # highest fitness
    assert handoff.parent_goal_alignment.startswith(
        "No candidate cleared the absolute milestone thresholds"
    )


def test_handoff_breakthrough_when_candidate_clears_both_thresholds(
    db, cascade, tmp_path
):
    """A candidate clearing fitness AND robustness floors is the winner."""
    run_id = _make_run(db, hp=_hp_low_milestone())  # 0.50 / 0.50 floors
    db.insert(
        _gen_arch("winner"),
        _scores(0.80, robustness=0.80),
        run_id=run_id, island_id=2, generation=10, parent_ids=[1, 2],
    )
    db.insert(
        _gen_arch("also-clears"),
        _scores(0.70, robustness=0.70),
        run_id=run_id, island_id=1, generation=11,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    assert handoff.no_breakthrough_this_run is False
    assert handoff.winning_architecture is not None
    assert handoff.winning_architecture.spec.name == "winner"
    assert handoff.winning_architecture.lineage == [1, 2]
    assert handoff.winning_architecture.generation == 10
    assert handoff.winning_architecture.island_of_origin == 2
    assert handoff.parent_goal_alignment.startswith(
        "Winning candidate 'winner' cleared absolute milestone thresholds"
    )


def test_handoff_no_breakthrough_when_fitness_clears_but_robustness_doesnt(
    db, cascade, tmp_path
):
    """Fitness alone isn't enough — robustness must also clear the floor."""
    # HP: fitness floor 0.50, robustness floor 0.80.
    hp = Hyperparameters(
        milestone_absolute_fitness_threshold=0.50,
        milestone_absolute_robustness_threshold=0.80,
    )
    run_id = _make_run(db, hp=hp)
    # Candidate has fitness 0.70 (clears 0.50) but robustness 0.60 (below 0.80).
    db.insert(
        _gen_arch("fragile-but-high-fitness"),
        _scores(0.70, robustness=0.60),
        run_id=run_id, island_id=0, generation=10,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    assert handoff.no_breakthrough_this_run is True
    assert handoff.winning_architecture is None


def test_handoff_no_breakthrough_when_robustness_is_none(db, cascade, tmp_path):
    """A candidate whose adversarial scrutiny didn't run (robustness=None)
    cannot be a breakthrough, regardless of fitness."""
    run_id = _make_run(db, hp=_hp_low_milestone())
    early_exit_scores = Scores(
        feasibility=0.95,
        structural=0.95,
        robustness=None,
        middle_class_accessible=True,
    )
    db.insert(
        _gen_arch("early-exit-but-high"),
        early_exit_scores,
        run_id=run_id, island_id=0, generation=10,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)

    assert handoff.no_breakthrough_this_run is True
    assert handoff.winning_architecture is None


# ----------------------------------------------------------------- structure invariants


def test_top_generated_discoveries_capped_at_default_seven(db, cascade, tmp_path):
    """Default top-N is 7; extras must be dropped from the discovery list."""
    run_id = _make_run(db, hp=_hp_high_milestone())
    for i in range(10):
        db.insert(
            _gen_arch(f"gen-{i:02d}"),
            _scores(0.6 - i * 0.01),
            run_id=run_id, island_id=i % 4, generation=5 + i,
        )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert len(handoff.top_generated_discoveries) == 7
    assert handoff.top_generated_discoveries[0].spec.name == "gen-00"


def test_build_handoff_records_eval_count(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert handoff.verification_trail.eval_count == 1


def test_build_handoff_uses_verifier_anchor(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert handoff.verification_trail.anchor_used == VERIFIER_ANCHOR


def test_build_handoff_carries_run_provenance(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    trail = handoff.verification_trail
    assert trail.run_id == run_id
    assert trail.parent_goal_version == "test"
    assert trail.verifier_version == "test"
    assert isinstance(trail.hyperparameters, dict)


def test_build_handoff_exemplar_comparisons_always_empty(db, cascade, tmp_path):
    """Sprint 2: exemplar_comparisons field exists for JSON-shape stability
    but is never populated — Stage 3 (exemplar similarity) was retired."""
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert handoff.verification_trail.exemplar_comparisons == []


def test_build_handoff_drift_log_projects_audit_events(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=run_id,
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
            run_id=run_id,
            trigger="scheduled_interval",
            classification="structural",
            action="pause_for_human",
            rationale="blocks goal",
            payload={"findings": [{"finding": {"source": "research"}}]},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert [e.type for e in handoff.drift_log] == ["cosmetic", "structural"]
    assert [e.source for e in handoff.drift_log] == ["redteam", "research"]
    assert handoff.drift_log[1].action == "pause_for_human"


def test_build_handoff_drift_log_filters_other_runs(db, cascade, tmp_path):
    """Audit events for OTHER runs must not appear in this handoff's drift log."""
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
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
            run_id=run_id,
            trigger="t",
            classification="cosmetic",
            action="continue",
            rationale="from this run",
            payload={},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert len(handoff.drift_log) == 1
    assert handoff.drift_log[0].rationale == "from this run"


def test_build_handoff_middle_class_check_reflects_cascade_subject(db, cascade, tmp_path):
    """The middle_class check reflects the cascade subject (top candidate)."""
    run_id = _make_run(db)
    db.insert(
        _gen_arch("with-resources", entry_resources="cryptography skill, modest hardware"),
        _scores(0.7),
        run_id=run_id, island_id=0, generation=5,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    check = handoff.middle_class_entry_check
    assert check.passes is True
    assert "cryptography" in check.estimated_starting_resources.lower()


def test_build_handoff_coverage_residual_flags_unresolved_structural(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append(
        AuditEvent(
            timestamp=AuditLog.now(),
            run_id=run_id,
            trigger="t",
            classification="structural",
            action="pause_for_human",
            rationale="r",
            payload={},
        )
    )
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert "1 structural" in handoff.coverage_residual
    assert run_id in handoff.coverage_residual


def test_build_handoff_coverage_residual_clean_when_no_meta(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert "no unresolved" in handoff.coverage_residual
    assert "fresh" in handoff.coverage_residual


def test_build_handoff_coverage_residual_marks_resumed_run(db, cascade, tmp_path):
    run_id = _make_run(db)
    db.insert(_gen_arch("g"), _scores(0.6), run_id=run_id, island_id=0, generation=3)
    db.mark_run_resumed(run_id)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    assert "resumed" in handoff.coverage_residual


def test_build_handoff_raises_on_empty_run(db, cascade, tmp_path):
    run_id = _make_run(db)
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(RuntimeError, match="nothing to harvest"):
        build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)


def test_build_handoff_raises_on_missing_run(db, cascade, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(KeyError):
        build_handoff(db, audit, cascade, num_islands=4, run_id="run_does_not_exist")


def test_build_handoff_serialisable_to_json(db, cascade, tmp_path):
    """Full handoff round-trips to JSON."""
    from alphamo.evaluator.exemplar_library import TRIVIAL_SEED

    run_id = _make_run(db, hp=_hp_low_milestone())
    db.insert(_gen_arch("g"), _scores(0.7), run_id=run_id, island_id=0, generation=5)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    payload = handoff.model_dump_json()
    assert "seed_baselines" in payload
    assert "top_generated_discoveries" in payload
    assert "no_breakthrough_this_run" in payload
    # Sprint 3: trivial baseline replaces the 4 curated seeds in JSON output.
    assert TRIVIAL_SEED.name in payload
    assert run_id in payload


def test_build_handoff_serialisable_when_no_winner(db, cascade, tmp_path):
    """Null winning_architecture serialises cleanly."""
    run_id = _make_run(db, hp=_hp_high_milestone())
    db.insert(_gen_arch("low"), _scores(0.3), run_id=run_id, island_id=0, generation=5)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    payload = handoff.model_dump_json()
    assert '"winning_architecture":null' in payload.replace(" ", "")


def test_generated_discovery_carries_stage4_findings(db, cascade, tmp_path):
    """If a candidate row has stage4_findings persisted, they ride into the handoff."""
    run_id = _make_run(db)
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
        _gen_arch("with-findings"), _scores(0.7),
        run_id=run_id, island_id=0, generation=5,
        stage4_findings=findings_payload,
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    [discovery] = handoff.top_generated_discoveries
    assert discovery.stage4_findings is not None
    assert len(discovery.stage4_findings) == 1
    assert discovery.stage4_findings[0].framing == "regulatory"


def test_generated_discovery_stage4_findings_none_when_legacy(db, cascade, tmp_path):
    """Legacy candidates (stage4_findings=NULL) preserve the None distinction."""
    run_id = _make_run(db)
    db.insert(_gen_arch("legacy"), _scores(0.7),
              run_id=run_id, island_id=0, generation=5)
    audit = AuditLog(tmp_path / "audit.jsonl")
    handoff = build_handoff(db, audit, cascade, num_islands=4, run_id=run_id)
    [discovery] = handoff.top_generated_discoveries
    assert discovery.stage4_findings is None
