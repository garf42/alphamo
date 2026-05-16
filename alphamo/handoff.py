"""Construct the final handoff document from a run's DB and audit log.

The handoff is the load-bearing deliverable. Everything before it is plumbing
in service of producing this document.

Sprint 3 redesign: the handoff's `seed_baselines` projection is the
single trivial Solo Service Provider baseline that every island was
initialized with at gen 0. The actual scored fitness of that baseline
(read from any gen-0 trivial-seed candidate in the candidates table)
populates the entry. `top_generated_discoveries` filters out gen-0
trivial-seed copies so the discoveries reflect what the search produced.

Every read here is filtered by `run_id` so that two runs sharing the
same DB produce two separate handoffs. The verification_trail records
the run's hyperparameters and version anchors so the result is
reproducible.
"""

from __future__ import annotations

from typing import Any

from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.verifier import VERIFIER_ANCHOR
from alphamo.database import ProgramsDB
from alphamo.database.schema import Candidate
from alphamo.evaluator import EvaluatorCascade
from alphamo.evaluator.exemplar_library import TRIVIAL_SEED
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import StructuralConcern
from alphamo.schemas.handoff import (
    BaselineSeed,
    DriftLogEntry,
    GeneratedDiscovery,
    Handoff,
    MiddleClassEntryCheck,
    VerificationTrail,
)

TOP_GENERATED_LIMIT = 7


def _audit_event_source(event: AuditEvent) -> str:
    """Recover the meta source ('research' / 'redteam' / '') from the event payload."""
    findings = event.payload.get("findings", [])
    if not findings:
        return ""
    first = findings[0].get("finding", {})
    return first.get("source", "")


def _drift_log_from_audit(
    audit_log: AuditLog, run_id: str
) -> list[DriftLogEntry]:
    entries: list[DriftLogEntry] = []
    matched = [e for e in audit_log.read_all() if e.run_id == run_id]
    for i, event in enumerate(matched):
        entries.append(
            DriftLogEntry(
                iter=i,
                type=event.classification,
                source=_audit_event_source(event),
                action=event.action,
                rationale=event.rationale,
            )
        )
    return entries


def _is_trivial_seed_row(row: Candidate) -> bool:
    """True iff this row is a copy of the gen-0 trivial baseline seed.

    Matched by name + generation. The orchestrator only ever inserts
    TRIVIAL_SEED at generation=0; any later candidate that happens to
    carry the same name (vanishingly unlikely) would not be at gen 0
    and would not be filtered.
    """
    return (
        row.generation == 0
        and row.architecture_spec.get("name") == TRIVIAL_SEED.name
    )


def _baseline_seeds(db: ProgramsDB, run_id: str) -> list[BaselineSeed]:
    """Project the trivial baseline into a single-entry list.

    Reads the actual scored fitness from a gen-0 trivial-seed row in
    this run's candidates table. Falls back to `baseline_fitness=None`
    when no such row exists (e.g. legacy DB that pre-dates the Sprint
    3 bootstrap mechanism).
    """
    notes = getattr(TRIVIAL_SEED, "notes", None) or {}
    baseline_fitness: float | None = None
    for row in db.alive_in_run(run_id):
        if _is_trivial_seed_row(row):
            baseline_fitness = row.fitness
            break
    return [
        BaselineSeed(
            name=TRIVIAL_SEED.name,
            summary=TRIVIAL_SEED.summary,
            capture_mechanism=TRIVIAL_SEED.capture_mechanism,
            baseline_fitness=baseline_fitness,
            design_intent=notes.get("design_intent"),
        )
    ]


def _generated_discovery_from_row(row: Candidate) -> GeneratedDiscovery:
    raw_findings = row.stage4_findings
    findings: list[StructuralConcern] | None
    if raw_findings is None:
        findings = None
    else:
        findings = [StructuralConcern(**f) for f in raw_findings]
    return GeneratedDiscovery(
        spec=Architecture(**row.architecture_spec),
        scores=Scores(**row.scores),
        fitness=row.fitness,
        island_of_origin=row.island_id,
        generation=row.generation,
        lineage=list(row.parent_ids or []),
        stage4_findings=findings,
    )


def _candidate_clears_milestone(
    row: Candidate, hp: Hyperparameters
) -> bool:
    """Match orchestrator._is_milestone semantics on a stored candidate row.

    Fitness must exceed `milestone_absolute_fitness_threshold` AND
    robustness must exceed `milestone_absolute_robustness_threshold`. A
    candidate with None robustness (early-exit, legacy) cannot be a
    breakthrough — adversarial scrutiny never ran on it.

    Note: the orchestrator also gates on `generation >= milestone_min_generation`.
    The handoff intentionally drops that gate — at harvest time the
    question is "did this candidate clear the bar?", not "did it clear
    the bar AND past warmup?". A candidate that hit thresholds early is
    still a breakthrough.
    """
    robustness = row.scores.get("robustness")
    if robustness is None:
        return False
    if row.fitness <= hp.milestone_absolute_fitness_threshold:
        return False
    if robustness <= hp.milestone_absolute_robustness_threshold:
        return False
    return True


def build_handoff(
    db: ProgramsDB,
    audit_log: AuditLog,
    cascade: EvaluatorCascade,
    num_islands: int,
    run_id: str,
    coverage_residual: str = "",
    top_n_generated: int = TOP_GENERATED_LIMIT,
) -> Handoff:
    """Harvest one run into a Handoff. Re-cascades the top candidate
    (if any) to populate the verification trail."""
    if not run_id:
        raise ValueError("run_id is required to build a handoff")
    run = db.get_run(run_id)
    hp = (
        Hyperparameters(**run.hyperparameters)
        if run.hyperparameters
        else Hyperparameters()
    )

    all_alive = db.alive_in_run(run_id)
    if not all_alive:
        raise RuntimeError(
            f"no alive candidates for run {run_id!r} — nothing to harvest"
        )
    # alive_in_run sorts by fitness desc.

    seed_baselines = _baseline_seeds(db, run_id)

    # Sprint 3: gen-0 trivial-seed copies are technically "alive" candidates
    # but they're not search output — filter them out of the discoveries
    # projection so the reader sees what the search produced. They still
    # appear in seed_baselines (with their actual fitness) and in the
    # candidates table; just not double-counted in discoveries.
    discoveries_pool = [c for c in all_alive if not _is_trivial_seed_row(c)]

    top_generated_discoveries = [
        _generated_discovery_from_row(c) for c in discoveries_pool[:top_n_generated]
    ]

    breakthrough_rows = [c for c in discoveries_pool if _candidate_clears_milestone(c, hp)]
    has_breakthrough = bool(breakthrough_rows)
    no_breakthrough = not has_breakthrough
    winning_architecture = (
        _generated_discovery_from_row(breakthrough_rows[0])
        if has_breakthrough
        else None
    )

    # Re-cascade the top discovery for verification trail. Cascade
    # subject is the top by fitness regardless of milestone status — that
    # way the verification trail still contains live cascade output even
    # when no breakthrough occurred. Excludes gen-0 trivial-seed copies
    # (those would always lose to evolved candidates, but we guard
    # explicitly in case a run produced nothing-better-than-baseline).
    cascade_subject_row = (
        discoveries_pool[0] if discoveries_pool else all_alive[0]
    )
    cascade_subject_arch = Architecture(**cascade_subject_row.architecture_spec)
    cascade_result = cascade.evaluate(cascade_subject_arch)

    final_scores = Scores(**cascade_result.scores.model_dump())
    adversarial_concerns: list[StructuralConcern] = (
        list(cascade_result.stage3.concerns)
        if cascade_result.stage3 is not None
        else []
    )

    if winning_architecture is not None:
        parent_goal_alignment = _parent_goal_alignment_winner(
            cascade_result, winning_architecture.spec.name, hp
        )
    else:
        parent_goal_alignment = _parent_goal_alignment_no_breakthrough(
            top_generated_discoveries, cascade_result, hp
        )

    middle_class_check = _middle_class_check(cascade_result, cascade_subject_arch)

    return Handoff(
        seed_baselines=seed_baselines,
        top_generated_discoveries=top_generated_discoveries,
        no_breakthrough_this_run=no_breakthrough,
        winning_architecture=winning_architecture,
        verification_trail=VerificationTrail(
            run_id=run_id,
            hyperparameters=dict(run.hyperparameters),
            parent_goal_version=run.parent_goal_version,
            verifier_version=run.verifier_version,
            final_scores=final_scores,
            anchor_used=VERIFIER_ANCHOR,
            eval_count=db.count_candidates(run_id=run_id),
            exemplar_comparisons=[],
            adversarial_concerns=adversarial_concerns,
        ),
        drift_log=_drift_log_from_audit(audit_log, run_id=run_id),
        parent_goal_alignment=parent_goal_alignment,
        middle_class_entry_check=middle_class_check,
        coverage_residual=coverage_residual
        or _default_coverage_residual(audit_log, run, db),
    )


def _parent_goal_alignment_winner(
    cascade_result: Any, winner_name: str, hp: Hyperparameters
) -> str:
    """Compose alignment text describing the winning candidate."""
    parts: list[str] = [
        f"Winning candidate '{winner_name}' cleared absolute milestone "
        f"thresholds (fitness > {hp.milestone_absolute_fitness_threshold}, "
        f"robustness > {hp.milestone_absolute_robustness_threshold})."
    ]
    if cascade_result.stage2 is not None:
        parts.append(f"Structural fit: {cascade_result.stage2.reasoning}")
    if cascade_result.stage3 is not None:
        parts.append(f"Adversarial scrutiny: {cascade_result.stage3.reasoning}")
    if cascade_result.stage1 is not None and len(parts) == 1:
        parts.append(f"Feasibility: {cascade_result.stage1.reasoning}")
    return " // ".join(parts)


def _parent_goal_alignment_no_breakthrough(
    top_generated: list[GeneratedDiscovery],
    cascade_result: Any,
    hp: Hyperparameters,
) -> str:
    """Compose alignment text when no candidate cleared the milestone thresholds."""
    if not top_generated:
        return "this run produced no candidates."
    opener = (
        f"No candidate cleared the absolute milestone thresholds this run "
        f"(fitness > {hp.milestone_absolute_fitness_threshold} AND "
        f"robustness > {hp.milestone_absolute_robustness_threshold}). "
        "The search produced the following candidates worth examination: "
    )
    descriptions = ", ".join(
        f"{g.spec.name} (fitness {g.fitness:.4f}"
        + (
            f", robustness {g.scores.robustness:.4f}"
            if g.scores.robustness is not None
            else ""
        )
        + ")"
        for g in top_generated[:3]
    )
    body = descriptions
    if cascade_result is not None:
        cascade_parts: list[str] = []
        if cascade_result.stage2 is not None:
            cascade_parts.append(
                f"top candidate structural fit: {cascade_result.stage2.reasoning}"
            )
        if cascade_result.stage3 is not None:
            cascade_parts.append(
                f"adversarial scrutiny: {cascade_result.stage3.reasoning}"
            )
        if cascade_parts:
            body += " // " + " // ".join(cascade_parts)
    return opener + body


def _middle_class_check(
    cascade_result: Any | None, subject: Architecture | None
) -> MiddleClassEntryCheck:
    if cascade_result is None or subject is None:
        return MiddleClassEntryCheck(
            passes=True,
            estimated_starting_resources="(no candidates this run)",
            stage_sequence=[],
        )
    return MiddleClassEntryCheck(
        passes=cascade_result.scores.middle_class_accessible,
        estimated_starting_resources=subject.entry_resources,
        stage_sequence=[
            stage
            for stage, present in [
                ("stage1_feasibility", cascade_result.stage1 is not None),
                ("stage2_structured", cascade_result.stage2 is not None),
                ("stage3_adversarial", cascade_result.stage3 is not None),
            ]
            if present
        ],
    )


def _default_coverage_residual(
    audit_log: AuditLog, run: Any, db: ProgramsDB
) -> str:
    events = [e for e in audit_log.read_all() if e.run_id == run.run_id]
    structural = sum(1 for e in events if e.classification == "structural")

    if run.last_resumed_at is not None:
        prefix = f"Run {run.run_id} (resumed from prior session; last resumed at {run.last_resumed_at.isoformat()})."
    else:
        prefix = f"Run {run.run_id} (fresh; created {run.created_at.isoformat()})."

    if structural:
        residual = (
            f"{structural} structural meta-finding(s) still unresolved at harvest; "
            "review the drift log before downstream implementation."
        )
    else:
        residual = "no unresolved meta-findings at harvest"
    return f"{prefix} {residual}"
