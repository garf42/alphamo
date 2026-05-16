"""Construct the final handoff document from a run's DB and audit log.

The handoff is the load-bearing deliverable. Everything before it is plumbing
in service of producing this document.

The builder honestly separates seeds (what the run started with) from
generated discoveries (what the search produced). A seed never wins:
`winning_architecture` is null whenever no generated candidate exceeded a
seed baseline, and `no_breakthrough_this_run` flags that case explicitly.

Every read here is filtered by `run_id` so that two runs sharing the same DB
produce two separate handoffs. The verification_trail records the run's
hyperparameters and version anchors so the result is reproducible.
"""

from __future__ import annotations

from typing import Any

from alphamo.context.verifier import VERIFIER_ANCHOR
from alphamo.database import ProgramsDB
from alphamo.database.operations import aggregate_fitness
from alphamo.database.schema import Candidate
from alphamo.evaluator import EvaluatorCascade
from alphamo.evaluator.exemplar_library import STARTERS
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import StructuralConcern
from alphamo.schemas.handoff import (
    DriftLogEntry,
    ExemplarComparison,
    GeneratedDiscovery,
    Handoff,
    MiddleClassEntryCheck,
    SeedBaseline,
    VerificationTrail,
)

TOP_GENERATED_LIMIT = 7

_STARTER_NAMES: frozenset[str] = frozenset(arch.name for arch, _ in STARTERS)


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


def _seed_baselines(seed_rows: list[Candidate]) -> list[SeedBaseline]:
    """Build the seed_baselines list from the canonical STARTERS constant.

    `island_of_origin` is the lowest island_id where this seed-named
    candidate is currently alive in the run. Defaults to 0 if no copy is
    alive (which would be unusual — every island gets every starter at
    seed_if_empty time).
    """
    out: list[SeedBaseline] = []
    for arch, scores in STARTERS:
        copies = [r for r in seed_rows if r.architecture_spec.get("name") == arch.name]
        island_of_origin = min((r.island_id for r in copies), default=0)
        out.append(
            SeedBaseline(
                name=arch.name,
                scores=scores,
                fitness=aggregate_fitness(scores),
                island_of_origin=island_of_origin,
            )
        )
    return out


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


def build_handoff(
    db: ProgramsDB,
    audit_log: AuditLog,
    cascade: EvaluatorCascade,
    num_islands: int,
    run_id: str,
    coverage_residual: str = "",
    top_n_generated: int = TOP_GENERATED_LIMIT,
) -> Handoff:
    """Harvest one run into a Handoff. Re-cascades the top generated candidate
    (if any) to populate the verification trail."""
    if not run_id:
        raise ValueError("run_id is required to build a handoff")
    run = db.get_run(run_id)

    all_alive = db.alive_in_run(run_id)
    if not all_alive:
        raise RuntimeError(
            f"no alive candidates for run {run_id!r} — nothing to harvest"
        )

    seed_rows: list[Candidate] = []
    generated_rows: list[Candidate] = []
    for c in all_alive:
        if c.architecture_spec.get("name") in _STARTER_NAMES:
            seed_rows.append(c)
        else:
            generated_rows.append(c)
    # alive_in_run sorts by fitness desc; the partition preserves that order.

    seed_baselines = _seed_baselines(seed_rows)
    min_seed_fitness = min(b.fitness for b in seed_baselines)

    top_generated_discoveries = [
        _generated_discovery_from_row(c) for c in generated_rows[:top_n_generated]
    ]

    has_breakthrough = (
        bool(generated_rows) and generated_rows[0].fitness > min_seed_fitness
    )
    no_breakthrough = not has_breakthrough
    winning_architecture = top_generated_discoveries[0] if has_breakthrough else None

    # Re-cascade the top generated candidate (if any) for the verification
    # trail. Skip if the run produced only seeds — those were already
    # cascade-scored at `score-seeds` time and don't need re-verification.
    cascade_subject_arch: Architecture | None = None
    cascade_result: Any | None = None
    if generated_rows:
        cascade_subject_arch = Architecture(**generated_rows[0].architecture_spec)
        cascade_result = cascade.evaluate(cascade_subject_arch)

    final_scores: Scores | None = None
    exemplar_comparisons: list[ExemplarComparison] = []
    adversarial_concerns: list[StructuralConcern] = []
    if cascade_result is not None:
        final_scores = Scores(**cascade_result.scores.model_dump())
        if cascade_result.stage3 is not None:
            s3 = cascade_result.stage3
            exemplar_comparisons.append(
                ExemplarComparison(
                    closest_exemplar=s3.closest_exemplar,
                    similarity=s3.similarity,
                    reasoning=s3.reasoning,
                )
            )
        if cascade_result.stage4 is not None:
            adversarial_concerns = list(cascade_result.stage4.concerns)

    if winning_architecture is not None:
        parent_goal_alignment = _parent_goal_alignment_winner(
            cascade_result, winning_architecture.spec.name
        )
    else:
        parent_goal_alignment = _parent_goal_alignment_no_breakthrough(
            top_generated_discoveries, cascade_result
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
            exemplar_comparisons=exemplar_comparisons,
            adversarial_concerns=adversarial_concerns,
        ),
        drift_log=_drift_log_from_audit(audit_log, run_id=run_id),
        parent_goal_alignment=parent_goal_alignment,
        middle_class_entry_check=middle_class_check,
        coverage_residual=coverage_residual
        or _default_coverage_residual(audit_log, run, db),
    )


def _parent_goal_alignment_winner(
    cascade_result: Any, winner_name: str
) -> str:
    """Compose alignment text describing the winning generated candidate."""
    parts: list[str] = [f"Winning generated candidate '{winner_name}':"]
    if cascade_result is not None:
        if cascade_result.stage3 is not None:
            parts.append(f"Exemplar fit: {cascade_result.stage3.reasoning}")
        if cascade_result.stage2 is not None:
            parts.append(f"Structural fit: {cascade_result.stage2.reasoning}")
        if cascade_result.stage1 is not None and len(parts) == 1:
            parts.append(f"Feasibility: {cascade_result.stage1.reasoning}")
    return " // ".join(parts)


def _parent_goal_alignment_no_breakthrough(
    top_generated: list[GeneratedDiscovery], cascade_result: Any
) -> str:
    """Compose alignment text when no generated candidate beat any seed.

    Opens with explicit acknowledgement, then describes the top 1-3 generated
    discoveries (if any) as the best the search produced, plus per-stage
    cascade reasoning on the top one.
    """
    if not top_generated:
        return "this run produced no generated candidates."
    opener = (
        "No generated candidate matched or exceeded seed baselines this run. "
        "The seed exemplars remain the highest-scoring architectures, but the "
        "search produced the following candidates worth examination: "
    )
    descriptions = ", ".join(
        f"{g.spec.name} (fitness {g.fitness:.4f})" for g in top_generated[:3]
    )
    body = descriptions
    if cascade_result is not None:
        cascade_parts: list[str] = []
        if cascade_result.stage3 is not None:
            cascade_parts.append(
                f"top candidate exemplar fit: {cascade_result.stage3.reasoning}"
            )
        if cascade_result.stage2 is not None:
            cascade_parts.append(
                f"structural fit: {cascade_result.stage2.reasoning}"
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
            estimated_starting_resources="(no generated candidates this run)",
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
                ("stage3_exemplars", cascade_result.stage3 is not None),
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
