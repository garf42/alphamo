"""Main loop coordinator: wires sampler + proposer + cascade + islands + meta.

One Orchestrator drives a run. Lifecycle:

  Bootstrap (once per fresh run, in `run()` before the main loop):
    - Score the trivial seed once via the cascade.
    - Insert a copy of the trivial seed into every island as a gen-0
      alive candidate. (Sprint 3, FunSearch alignment: every island
      starts with the same baseline; from gen 1 onward, evolution
      diverges per-island.)

  Inner loop (each iteration):
    1. Pick an island (uniform).
    2. Draw k candidates from the island via softmax-weighted sampling.
    3. Propose a new architecture via Opus — the proposer sees ONLY
       those k island-drawn candidates (no global reference library).
    4. Score it through the cascade.
    5. Insert into the DB.
    6. If the new fitness clears the absolute milestone thresholds,
       fire the red-team curator gate.
    7. Apply the islands manager's reset cadence — when fired, the
       FunSearch per-weak-island independent draw reseeds the bottom-
       half islands.
    8. On scheduled intervals (or stall detection), fire the research
       agent and pass findings to the curator.

Termination: max_generations reached, OR curator returns PAUSE_FOR_HUMAN
on a structural finding, OR `max_consecutive_failures` LLM output failures.

Sprint 3 redesign: bootstrap is back — the trivial Solo Service Provider
seed (`exemplar_library.TRIVIAL_SEED`) is inserted into every island at
gen 0 so the within-island sampler always has at least one row to
return. The proposer never sees a global reference library; everything
it sees comes from the current island.

Every Orchestrator owns exactly one `run_id`. Every insert / read /
audit event is scoped to that run.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.parent_goal import PARENT_GOAL_VERSION
from alphamo.context.verifier import VERIFIER_VERSION
from alphamo.database import ProgramsDB
from alphamo.errors import LLMOutputError
from alphamo.errors import Stage4OutputError
from alphamo.evaluator import EvaluatorCascade
from alphamo.evaluator.exemplar_library import TRIVIAL_SEED
from alphamo.evaluator.stage4_adversarial import FAILED_FRAMINGS_SENTINEL
from alphamo.islands import IslandsManager, ResetEvent
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.meta.curator import Curator
from alphamo.meta.research import run_research
from alphamo.prompts.research_prompts import Trigger
from alphamo.proposer import Proposer
from alphamo.sampler import Sampler
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    CuratorAction,
    CuratorDecision,
    MetaFinding,
    Stage4Finding,
    StructuralConcern,
)

# Audit-log trigger string preserved from pre-Sprint-2 for backward
# compatibility with old audit.jsonl files (run-006, run-007). The
# conceptual stage is now Stage 3, but persisted strings stay.
STAGE4_AUDIT_TRIGGER = "stage4_routine"
ISLAND_RESET_AUDIT_TRIGGER = "island_reset"
BOOTSTRAP_AUDIT_TRIGGER = "bootstrap_islands"
# Sprint 4: emitted when Stage 3 ran with partial framing coverage
# (some framings failed after SDK-level retries exhausted) but enough
# succeeded that the candidate was still scored. Catastrophic-failure
# cases (< STAGE3_MIN_SUCCESSFUL_FRAMINGS succeeded) raise instead
# and flow through the existing iteration-failure path.
STAGE3_PARTIAL_FAILURE_TRIGGER = "stage3_partial_framing_failure"
STAGE3_CATASTROPHIC_FAILURE_TRIGGER = "stage3_catastrophic_framing_failure"


def _stage4_concerns_as_meta_findings(
    concerns: list[StructuralConcern],
) -> list[MetaFinding]:
    """Adapt Stage 4 concerns to the curator's MetaFinding interface."""
    return [
        MetaFinding(
            source="stage4_adversarial",
            framing=c.framing,
            claim=c.claim,
            evidence=c.evidence,
            falsification_condition=c.falsification_condition,
            severity=c.severity,
        )
        for c in concerns
    ]


@dataclass
class IterationEvent:
    """One iteration's audit record. The orchestrator emits these."""

    generation: int
    island_id: int
    candidate_id: int | None = None
    fitness: float | None = None
    architecture_name: str | None = None
    early_exit: str | None = None
    skipped_reason: str | None = None
    reset_event: ResetEvent | None = None
    meta_trigger: str | None = None
    meta_decision: CuratorDecision | None = None
    failure_reason: str | None = None
    """Set when an LLM-side parse failure prevented the candidate from being
    scored or when a non-blocking meta call failed. Together with
    `candidate_id`: candidate_id is None → eval-side failure (counts toward
    consecutive_failures); candidate_id set → meta-side failure (the
    candidate is in the DB and forward progress was made)."""


@dataclass
class RunResult:
    """What the orchestrator returns after a run."""

    events: list[IterationEvent] = field(default_factory=list)
    paused: bool = False
    stopped_reason: str = "max_generations"
    consecutive_failures_at_stop: int = 0


class ResumeIncompatibleError(Exception):
    """Raised by `Orchestrator.resume_run` when the persisted run cannot
    be safely resumed under the current code.

    Carries the run_id and the list of blocking reasons so the CLI can
    surface a clear "stored=X, current=Y, fix=Z" message to the user.
    """

    def __init__(self, run_id: str, blocking_reasons: list[str]) -> None:
        self.run_id = run_id
        self.blocking_reasons = list(blocking_reasons)
        msg = (
            f"cannot resume run {run_id!r} — "
            + "; ".join(blocking_reasons)
        )
        super().__init__(msg)


def check_resume_compatibility(
    run: Any,
    *,
    current_parent_goal_version: str,
    current_verifier_version: str,
    current_default_hp: Any,
    override_hp: Any | None = None,
) -> tuple[list[str], list[str]]:
    """Compare a persisted run against current code; return (blocking, warnings).

    HARD BLOCK (returned in the first list — caller must refuse resume):
      - parent_goal_version mismatch (search criterion changed; old
        candidates were evaluated under different prompts).
      - num_islands or cluster_signature_resolution mismatch BETWEEN
        PERSISTED HP AND `override_hp` (when override_hp is supplied).
        Today's `resume_run` doesn't support HP override, so these
        structural blocks are vacuous in normal flow — but the check
        is wired in case a future feature adds an override path.

    SOFT WARN (returned in the second list — caller surfaces to user
    but resume proceeds):
      - verifier_version mismatch (cascade behavior may have changed
        between original run and now).
      - Any persisted Hyperparameter that differs from the current
        code's default. Informational only — surfaces that the
        original run was configured with non-default HP, which a
        future replay would need to reproduce explicitly.

    Why parent_goal_version is blocked but other code-default changes
    aren't: PARENT_GOAL_VERSION is the search-criterion identity; old
    candidates were evaluated under different criteria, so their
    fitness ordering is meaningless under the new criterion. HP
    defaults are tuning knobs — the persisted run will keep using its
    persisted values regardless of what the current default happens
    to be, so a default change is informational, not blocking.
    """
    blocking: list[str] = []
    warnings: list[str] = []

    if run.parent_goal_version != current_parent_goal_version:
        blocking.append(
            f"PARENT_GOAL_VERSION mismatch (stored {run.parent_goal_version!r}, "
            f"current {current_parent_goal_version!r})"
        )

    persisted_hp = dict(run.hyperparameters or {})

    structural_hp = ("num_islands", "cluster_signature_resolution")
    if override_hp is not None:
        override_dict = override_hp.model_dump()
        for key in structural_hp:
            if key not in persisted_hp:
                continue
            if persisted_hp[key] != override_dict.get(key):
                blocking.append(
                    f"{key} mismatch — override_hp requests "
                    f"{override_dict.get(key)!r} but the persisted run was "
                    f"built with {persisted_hp[key]!r}; structural HP cannot "
                    "change across resume"
                )

    if run.verifier_version != current_verifier_version:
        warnings.append(
            f"VERIFIER_VERSION differs (stored {run.verifier_version!r}, "
            f"current {current_verifier_version!r}); cascade behavior may "
            "have changed since the original run"
        )

    default_hp_dict = current_default_hp.model_dump()
    for key, persisted_value in persisted_hp.items():
        default_value = default_hp_dict.get(key)
        if default_value is not None and persisted_value != default_value:
            warnings.append(
                f"hyperparameter '{key}' differs from current default "
                f"(stored {persisted_value!r}, current default {default_value!r})"
            )

    return blocking, warnings


def _default_resume_warning(message: str) -> None:
    """Default soft-warning sink for `resume_run`: print to stderr."""
    print(f"WARNING (resume): {message}", file=sys.stderr)


class Orchestrator:
    """Drives one production run end-to-end, scoped to one `run_id`."""

    def __init__(
        self,
        db: ProgramsDB,
        client: anthropic.Anthropic,
        audit_log: AuditLog,
        run_id: str,
        hp: Hyperparameters | None = None,
        rng: random.Random | None = None,
    ) -> None:
        if not run_id:
            raise ValueError("run_id is required for Orchestrator")
        self.db = db
        self.client = client
        self.audit_log = audit_log
        self.run_id = run_id
        self.hp = hp or Hyperparameters()
        self.rng = rng or random.Random()

        self.islands = IslandsManager(
            db,
            run_id=run_id,
            num_islands=self.hp.num_islands,
            reset_every_generations=self.hp.reset_every_generations,
            top_seed_count=self.hp.top_seed_count,
            rng=self.rng,
        )
        self.sampler = Sampler(
            db,
            temperature=self.hp.sampling_temperature,
            pool_size=self.hp.pool_size,
            rng=self.rng,
            run_id=run_id,
            cluster_temperature_t0=self.hp.cluster_temperature_t0,
            cluster_temperature_period=self.hp.cluster_temperature_period,
            cluster_signature_resolution=self.hp.cluster_signature_resolution,
        )
        self.proposer = Proposer(client)
        self.cascade = EvaluatorCascade(
            client,
            stage1_threshold=self.hp.stage1_threshold,
            stage2_threshold=self.hp.stage2_threshold,
            stage4_decay_k=self.hp.stage4_decay_k,
        )
        self.curator = Curator(client, audit_log, run_id=run_id)

    # ------------------------------------------------------------------ factories

    @classmethod
    def for_new_run(
        cls,
        db: ProgramsDB,
        client: anthropic.Anthropic,
        audit_log: AuditLog,
        hp: Hyperparameters | None = None,
        rng: random.Random | None = None,
        notes: str | None = None,
    ) -> "Orchestrator":
        """Create a fresh Run row and return an Orchestrator bound to it."""
        hp = hp or Hyperparameters()
        run_id = db.create_run(
            hyperparameters=hp.model_dump(),
            parent_goal_version=PARENT_GOAL_VERSION,
            verifier_version=VERIFIER_VERSION,
            notes=notes,
        )
        return cls(db, client, audit_log, run_id=run_id, hp=hp, rng=rng)

    @classmethod
    def resume_run(
        cls,
        db: ProgramsDB,
        client: anthropic.Anthropic,
        audit_log: AuditLog,
        run_id: str,
        rng: random.Random | None = None,
        on_warning: Callable[[str], None] | None = None,
    ) -> "Orchestrator":
        """Attach to an existing Run row. Hyperparameters come from the row.

        Sprint 4: applies a compatibility check between the persisted run
        and the current code's PARENT_GOAL_VERSION + VERIFIER_VERSION +
        structural HP. HARD-BLOCK conditions raise
        `ResumeIncompatibleError`; SOFT-WARN conditions go to `on_warning`
        (defaults to stderr-print) and resume proceeds.

        Raises KeyError if run_id does not exist. Raises
        ResumeIncompatibleError on a structural mismatch. Sets
        `last_resumed_at` on the run so the handoff can report
        fresh-vs-resumed.
        """
        run = db.get_run(run_id)
        hp = Hyperparameters(**run.hyperparameters) if run.hyperparameters else Hyperparameters()

        blocking, warnings = check_resume_compatibility(
            run,
            current_parent_goal_version=PARENT_GOAL_VERSION,
            current_verifier_version=VERIFIER_VERSION,
            current_default_hp=Hyperparameters(),
        )
        if blocking:
            raise ResumeIncompatibleError(run_id, blocking)
        if warnings:
            emit = on_warning if on_warning is not None else _default_resume_warning
            for warning in warnings:
                emit(warning)

        db.mark_run_resumed(run_id)
        return cls(db, client, audit_log, run_id=run_id, hp=hp, rng=rng)

    # ------------------------------------------------------------------ bootstrap

    def _bootstrap_islands(self) -> int:
        """Insert a copy of `TRIVIAL_SEED` into every island as a gen-0
        alive candidate. Returns the number of seed copies inserted.

        No-op when this run already has alive candidates (resumed run, or
        bootstrap already executed in a prior session). On a fresh run,
        scores the trivial seed once through the cascade and copies the
        resulting Scores into each island's gen-0 row.

        FunSearch alignment: "Each island is initialized with a copy of
        the user-provided initial program and is evolved separately."
        Single architecture, copied to all m islands; per-island
        evolution proceeds independently.

        We deliberately score the seed ONCE and copy the scores to all
        islands rather than running the cascade m times on the same
        architecture. The cascade has LLM-side variance; m independent
        evaluations would inject noise into what should be m identical
        starting points. Cost saving (m-1 evaluations) is incidental;
        the calibration argument is the load-bearing reason.
        """
        if self.db.count_candidates_in_run(self.run_id) > 0:
            return 0

        result = self.cascade.evaluate(TRIVIAL_SEED)
        stage4_findings_payload = (
            [c.model_dump(mode="json") for c in result.stage3.concerns]
            if result.stage3 is not None
            else None
        )
        inserted_ids: list[int] = []
        for island_id in range(self.hp.num_islands):
            candidate_id = self.db.insert(
                TRIVIAL_SEED,
                result.scores,
                run_id=self.run_id,
                island_id=island_id,
                generation=0,
                stage4_findings=stage4_findings_payload,
            )
            inserted_ids.append(candidate_id)

        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=BOOTSTRAP_AUDIT_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"trivial_seed='{TRIVIAL_SEED.name}' "
                    f"fitness={inserted_ids and self.db.get(inserted_ids[0]).fitness or 0.0:.4f} "
                    f"inserted_into_islands={list(range(self.hp.num_islands))}"
                ),
                payload={
                    "seed_architecture": TRIVIAL_SEED.model_dump(mode="json"),
                    "seed_scores": result.scores.model_dump(mode="json"),
                    "candidate_ids": inserted_ids,
                    "num_islands": self.hp.num_islands,
                },
            )
        )
        return len(inserted_ids)

    # ------------------------------------------------------------------ loop

    def detect_stall(self) -> bool:
        """True if max fitness has barely moved over the last `stall_window` generations."""
        history = self.db.fitness_history(self.hp.stall_window, run_id=self.run_id)
        if len(history) < self.hp.stall_window:
            return False
        return max(history) - min(history) < self.hp.stall_epsilon

    def _is_milestone(
        self, generation: int, fitness: float, robustness: float | None
    ) -> bool:
        """A candidate is a milestone iff ALL conditions hold:

          (1) past the early-generation warmup (`milestone_min_generation`),
          (2) aggregate fitness exceeds the absolute fitness threshold, and
          (3) robustness exceeds the absolute robustness threshold.

        Sprint 2 redesign: thresholds are absolute, not seed-relative. The
        `seed_baseline_fitness + delta` comparison was retired with the
        seeds-as-candidates mechanism. Robustness is None when adversarial
        scrutiny didn't run (any early exit) — those candidates can't be
        milestones since they haven't been scrutinised.
        """
        if generation < self.hp.milestone_min_generation:
            return False
        if robustness is None:
            return False
        if fitness <= self.hp.milestone_absolute_fitness_threshold:
            return False
        if robustness <= self.hp.milestone_absolute_robustness_threshold:
            return False
        return True

    def _log_stage4_routine(
        self, candidate_id: int, stage4: Stage4Finding
    ) -> None:
        """Record a Stage 4 firing in the audit log, regardless of milestone status.

        Every Stage 4 firing logs its robustness, concern counts, and
        framings that surfaced concerns. Milestone-routed curator events
        are logged separately by the Curator itself.
        """
        framings_with_concerns = sorted({c.framing for c in stage4.concerns})
        n_high = sum(1 for c in stage4.concerns if c.severity.value == "high")
        n_med = sum(1 for c in stage4.concerns if c.severity.value == "medium")
        n_low = sum(1 for c in stage4.concerns if c.severity.value == "low")
        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=STAGE4_AUDIT_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"candidate={candidate_id} robustness={stage4.robustness:.3f} "
                    f"concerns={len(stage4.concerns)} (high={n_high} med={n_med} low={n_low}) "
                    f"framings_with_concerns={framings_with_concerns}"
                ),
                payload={
                    "candidate_id": candidate_id,
                    "robustness": stage4.robustness,
                    "concerns": [c.model_dump(mode="json") for c in stage4.concerns],
                    "reasoning": stage4.reasoning,
                },
            )
        )

    def _log_stage3_partial_failure(
        self, candidate_id: int, sentinel: StructuralConcern
    ) -> None:
        """Sprint 4: record that Stage 3 ran with partial framing coverage.

        Emitted when some framings failed but enough succeeded (≥
        STAGE3_MIN_SUCCESSFUL_FRAMINGS) that the candidate was still
        scored and inserted. The candidate row's stage4_findings JSON
        already carries the `_meta` sentinel concern; this audit event
        surfaces it as a first-class run-time signal for monitoring.
        """
        failed_framings = (
            sentinel.evidence.split(", ") if sentinel.evidence else []
        )
        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=STAGE3_PARTIAL_FAILURE_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"candidate={candidate_id} partial Stage 3 coverage: "
                    f"{len(failed_framings)} framing(s) failed "
                    f"({', '.join(failed_framings)})"
                ),
                payload={
                    "candidate_id": candidate_id,
                    "failed_framings": failed_framings,
                },
            )
        )

    def _log_stage3_catastrophic_failure(
        self,
        generation: int,
        island_id: int,
        architecture: Architecture,
        exc: Stage4OutputError,
    ) -> None:
        """Sprint 4: record a catastrophic Stage 3 failure.

        Emitted when fewer than STAGE3_MIN_SUCCESSFUL_FRAMINGS framings
        succeeded. The candidate is NOT inserted into the DB; the
        iteration counts as a failure for the consecutive_failures gate.
        The architecture spec is captured in the payload so the run can
        be re-analyzed post-hoc to see which candidate triggered the
        failure (it's not in the candidates table).
        """
        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=STAGE3_CATASTROPHIC_FAILURE_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"generation={generation} island={island_id} "
                    f"architecture='{architecture.name}': {exc}"
                ),
                payload={
                    "generation": generation,
                    "island_id": island_id,
                    "architecture": architecture.model_dump(mode="json"),
                    "detail": exc.detail,
                },
            )
        )

    def _log_island_reset(self, generation: int, event: ResetEvent) -> None:
        """Record a FunSearch-style island reset in the audit log.

        Captures the parallel weak/source/seed-program triples so a
        post-run analysis can reconstruct, for each weak island, which
        surviving island supplied its reseed and which program was
        copied. Lineage on the resulting reset-copy rows in the
        candidates table points back to the source program independently.
        """
        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=ISLAND_RESET_AUDIT_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"generation={generation} weak_islands={event.weak_islands} "
                    f"strong_islands={event.strong_islands} "
                    f"source_islands={event.source_islands} "
                    f"seed_program_ids={event.seed_program_ids}"
                ),
                payload={
                    "generation": generation,
                    "weak_islands": list(event.weak_islands),
                    "strong_islands": list(event.strong_islands),
                    "source_islands": list(event.source_islands),
                    "seed_program_ids": list(event.seed_program_ids),
                },
            )
        )

    def _maybe_milestone_curate(
        self,
        generation: int,
        candidate_id: int,
        fitness: float,
        stage4: Stage4Finding,
    ) -> tuple[str, CuratorDecision] | None:
        """If the candidate is a milestone AND adversarial scrutiny surfaced
        concerns, invoke the curator's classify-and-gate path.

        Per Decision 3: only STRUCTURAL concerns trigger pause. The curator's
        existing semantics handle that — it classifies each concern and pauses
        on any STRUCTURAL classification, continues on cosmetic-only.

        A milestone with empty Stage 4 concerns (clean adversarial pass) does
        not invoke the curator — there's nothing to classify.
        """
        if not self._is_milestone(generation, fitness, stage4.robustness):
            return None
        if not stage4.concerns:
            return None
        meta_findings = _stage4_concerns_as_meta_findings(stage4.concerns)
        decision = self.curator.curate(
            meta_findings, trigger=Trigger.MILESTONE_CANDIDATE
        )
        return Trigger.MILESTONE_CANDIDATE, decision

    def _maybe_research(
        self, generation: int
    ) -> tuple[str, CuratorDecision] | None:
        trigger: str | None = None
        if generation % self.hp.research_every_generations == 0:
            trigger = Trigger.SCHEDULED_INTERVAL
        elif self.detect_stall():
            trigger = Trigger.PROGRESS_STALL
        if trigger is None:
            return None
        findings = run_research(trigger, self.client)
        decision = self.curator.curate(findings, trigger=trigger)
        return trigger, decision

    def step(self, generation: int) -> IterationEvent:
        """Run one inner-loop generation. Returns an audit record.

        LLM parse failures on the eval-side path (proposer or cascade) return
        an event with `candidate_id=None` and `failure_reason` set; nothing
        is inserted. Meta-side failures (red-team / research / curator) are
        recorded in `failure_reason` but do not roll back the inserted
        candidate — forward progress was made.
        """
        island_id = self.islands.pick_island()
        seeds = self.sampler.draw(island_id=island_id, k=self.hp.k_seeds)
        # Empty seeds is OK: the proposer bootstraps from the reference
        # exemplars alone. This is the expected path on the first iteration
        # for each island (Sprint 2 redesign: islands start empty).

        try:
            architecture = self.proposer.propose(seeds)
        except LLMOutputError as exc:
            return IterationEvent(
                generation=generation,
                island_id=island_id,
                failure_reason=str(exc),
            )

        try:
            result = self.cascade.evaluate(architecture)
        except LLMOutputError as exc:
            # Sprint 4: distinguish catastrophic Stage 3 failure (most
            # framings failed; signal degraded) from generic LLM-output
            # failures. The former gets its own audit-event trigger so
            # post-run analysis can identify Anthropic-side outages.
            if (
                isinstance(exc, Stage4OutputError)
                and exc.stop_reason == "stage3_catastrophic_framing_failure"
            ):
                self._log_stage3_catastrophic_failure(
                    generation, island_id, architecture, exc
                )
            return IterationEvent(
                generation=generation,
                island_id=island_id,
                architecture_name=architecture.name,
                failure_reason=str(exc),
            )

        # Sprint 1 (Bug 2): Stage 4 concerns persist on the candidate row so
        # they're queryable per candidate via SQL, not just buried in the
        # audit-log JSONL. NULL when the cascade short-circuited before
        # Stage 4 (Stage 1/2/3 exit) or middle-class filter failure.
        stage4_findings_payload = (
            [c.model_dump(mode="json") for c in result.stage3.concerns]
            if result.stage3 is not None
            else None
        )
        candidate_id = self.db.insert(
            architecture,
            result.scores,
            run_id=self.run_id,
            island_id=island_id,
            generation=generation,
            stage4_findings=stage4_findings_payload,
        )
        row = self.db.get(candidate_id)

        # Every Stage 4 firing is recorded in the audit log, milestone or not.
        # This is the routine selection-pressure path: robustness is already
        # in the candidate's scores, but the per-framing diagnostic trail is
        # the only place the concerns themselves get persisted.
        if result.stage3 is not None:
            self._log_stage4_routine(candidate_id, result.stage3)
            # Sprint 4: also emit a dedicated audit event when Stage 3 ran
            # with partial coverage (one or more framings failed after SDK
            # retries exhausted). The sentinel concern in stage3.concerns
            # carries the failed-framings list.
            failed_framings = [
                c for c in result.stage3.concerns
                if c.framing == FAILED_FRAMINGS_SENTINEL
            ]
            if failed_framings:
                self._log_stage3_partial_failure(
                    candidate_id, failed_framings[0]
                )

        meta_trigger: str | None = None
        meta_decision: CuratorDecision | None = None
        meta_failure: str | None = None
        try:
            milestone_outcome = (
                self._maybe_milestone_curate(
                    generation, candidate_id, row.fitness, result.stage3
                )
                if result.stage3 is not None
                else None
            )
            if milestone_outcome is not None:
                meta_trigger, meta_decision = milestone_outcome
            else:
                research_outcome = self._maybe_research(generation)
                if research_outcome is not None:
                    meta_trigger, meta_decision = research_outcome
        except LLMOutputError as exc:
            meta_failure = str(exc)

        reset_event = self.islands.maybe_reset(generation)
        if reset_event is not None:
            self._log_island_reset(generation, reset_event)

        return IterationEvent(
            generation=generation,
            island_id=island_id,
            candidate_id=candidate_id,
            fitness=row.fitness,
            architecture_name=architecture.name,
            early_exit=result.early_exit,
            reset_event=reset_event,
            meta_trigger=meta_trigger,
            meta_decision=meta_decision,
            failure_reason=meta_failure,
        )

    def run(self, max_generations: int) -> RunResult:
        """Drive up to `max_generations` iterations.

        Bootstrap step: before the main loop, every island gets a copy
        of the trivial seed at gen 0 via `_bootstrap_islands()`. No-op
        on resume (existing alive candidates ⇒ skip).

        Sprint 4: the loop's start generation is derived from the DB
        after bootstrap — `db.latest_generation_in_run + 1`. On a fresh
        run this is 1 (bootstrap inserts at gen 0). On a resumed run
        that previously completed N generations, this is N+1 — fixing
        the pre-Sprint-4 bug where resumed runs restarted the loop
        from gen 1 and double-counted generations from the perspective
        of reset cadence and milestone gates.

        Stops early on (a) a structural curator pause or (b) when
        consecutive eval-side failures reach `hp.max_consecutive_failures`.
        If start_generation > max_generations (the run already completed
        more iterations than the user requested), exits cleanly with
        stopped_reason="max_generations" without running any steps.

        Stamps the run's `stopped_reason` and `completed_at` on the Run
        row before returning.
        """
        self._bootstrap_islands()
        start_generation = self.db.latest_generation_in_run(self.run_id) + 1
        # Bootstrap inserts at generation 0, so post-bootstrap fresh runs
        # have start_generation = 1. Defensive max() guards against the
        # case where the run somehow has no candidates at all (would
        # otherwise produce start_generation = 0).
        start_generation = max(1, start_generation)
        result = RunResult()
        consecutive_failures = 0
        for generation in range(start_generation, max_generations + 1):
            event = self.step(generation)
            result.events.append(event)

            if event.candidate_id is not None:
                consecutive_failures = 0
            elif event.failure_reason is not None:
                consecutive_failures += 1
                if consecutive_failures >= self.hp.max_consecutive_failures:
                    result.stopped_reason = "consecutive_failures"
                    result.consecutive_failures_at_stop = consecutive_failures
                    self.db.complete_run(self.run_id, result.stopped_reason)
                    return result

            if (
                event.meta_decision is not None
                and event.meta_decision.action == CuratorAction.PAUSE_FOR_HUMAN
            ):
                result.paused = True
                result.stopped_reason = "curator_pause"
                result.consecutive_failures_at_stop = consecutive_failures
                self.db.complete_run(self.run_id, result.stopped_reason)
                return result
        result.consecutive_failures_at_stop = consecutive_failures
        self.db.complete_run(self.run_id, result.stopped_reason)
        return result


__all__ = ["IterationEvent", "Orchestrator", "RunResult"]
