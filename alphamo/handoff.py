"""Construct the final handoff document from a run's DB and audit log.

The handoff is the load-bearing deliverable. Everything before it is plumbing
in service of producing this document. The builder re-runs the verifier on
the winner so the verification_trail has live stage-3 reasoning (eval_count
is taken from the DB, not double-counted).
"""

from __future__ import annotations

from typing import Any

from alphamo.context.verifier import VERIFIER_ANCHOR
from alphamo.database import ProgramsDB
from alphamo.evaluator import EvaluatorCascade
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.handoff import (
    AlternateCandidate,
    DriftLogEntry,
    ExemplarComparison,
    Handoff,
    MiddleClassEntryCheck,
    VerificationTrail,
    WinningArchitecture,
)


def _audit_event_source(event: AuditEvent) -> str:
    """Recover the meta source ('research' / 'redteam' / '') from the event payload."""
    findings = event.payload.get("findings", [])
    if not findings:
        return ""
    first = findings[0].get("finding", {})
    return first.get("source", "")


def _drift_log_from_audit(audit_log: AuditLog) -> list[DriftLogEntry]:
    entries: list[DriftLogEntry] = []
    for i, event in enumerate(audit_log.read_all()):
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


def _alternates_from_islands(
    db: ProgramsDB, num_islands: int, winner_island_id: int, winner_id: int
) -> list[AlternateCandidate]:
    alternates: list[AlternateCandidate] = []
    for island_id in range(num_islands):
        if island_id == winner_island_id:
            continue
        top = db.top_programs_from_islands([island_id], n=1)
        if not top or top[0].id == winner_id:
            continue
        row = top[0]
        alternates.append(
            AlternateCandidate(
                spec=Architecture(**row.architecture_spec),
                scores=Scores(**row.scores),
                island_of_origin=row.island_id,
                generation=row.generation,
            )
        )
    return alternates


def build_handoff(
    db: ProgramsDB,
    audit_log: AuditLog,
    cascade: EvaluatorCascade,
    num_islands: int,
    coverage_residual: str = "",
) -> Handoff:
    """Harvest the run into a Handoff. Re-runs the cascade on the winner."""
    all_islands = list(range(num_islands))
    top = db.top_programs_from_islands(all_islands, n=1)
    if not top:
        raise RuntimeError("no alive candidates — nothing to harvest")
    winner = top[0]

    winner_arch = Architecture(**winner.architecture_spec)
    winner_scores = Scores(**winner.scores)
    winner_lineage: list[int] = list(winner.parent_ids or [])

    cascade_result = cascade.evaluate(winner_arch)

    exemplar_comparisons: list[ExemplarComparison] = []
    if cascade_result.stage3 is not None:
        s3 = cascade_result.stage3
        exemplar_comparisons.append(
            ExemplarComparison(
                closest_exemplar=s3.closest_exemplar,
                similarity=s3.similarity,
                reasoning=s3.reasoning,
            )
        )

    parent_goal_alignment = _parent_goal_alignment_text(cascade_result)
    middle_class_check = _middle_class_check(cascade_result, winner_arch)

    return Handoff(
        winning_architecture=WinningArchitecture(
            spec=winner_arch,
            scores=winner_scores,
            island_of_origin=winner.island_id,
            generation=winner.generation,
            lineage=winner_lineage,
        ),
        alternates=_alternates_from_islands(
            db, num_islands, winner.island_id, winner.id
        ),
        verification_trail=VerificationTrail(
            final_scores=Scores(**cascade_result.scores.model_dump()),
            anchor_used=VERIFIER_ANCHOR,
            eval_count=db.count_candidates(),
            exemplar_comparisons=exemplar_comparisons,
        ),
        drift_log=_drift_log_from_audit(audit_log),
        parent_goal_alignment=parent_goal_alignment,
        middle_class_entry_check=middle_class_check,
        coverage_residual=coverage_residual or _default_coverage_residual(audit_log),
    )


def _parent_goal_alignment_text(cascade_result: Any) -> str:
    """Compose a parent_goal_alignment string from per-stage reasoning."""
    parts: list[str] = []
    if cascade_result.stage3 is not None:
        parts.append(f"Exemplar fit: {cascade_result.stage3.reasoning}")
    if cascade_result.stage2 is not None:
        parts.append(f"Structural fit: {cascade_result.stage2.reasoning}")
    if cascade_result.stage1 is not None and not parts:
        parts.append(f"Feasibility: {cascade_result.stage1.reasoning}")
    return " // ".join(parts) if parts else "no per-stage reasoning available"


def _middle_class_check(
    cascade_result: Any, winner: Architecture
) -> MiddleClassEntryCheck:
    return MiddleClassEntryCheck(
        passes=cascade_result.scores.middle_class_accessible,
        estimated_starting_resources=winner.entry_resources,
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


def _default_coverage_residual(audit_log: AuditLog) -> str:
    events = audit_log.read_all()
    structural = sum(1 for e in events if e.classification == "structural")
    if structural:
        return (
            f"{structural} structural meta-finding(s) still unresolved at harvest; "
            "review the drift log before downstream implementation."
        )
    return "no unresolved meta-findings at harvest"
