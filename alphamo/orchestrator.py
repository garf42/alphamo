"""Main loop coordinator: wires sampler + proposer + cascade + islands + meta.

One Orchestrator drives a run. Each iteration:
  1. Pick an island (uniform).
  2. Draw k candidates from the island via softmax-weighted sampling.
     If the island is empty, draw is empty and the proposer bootstraps
     from the reference exemplars alone (Sprint 2 redesign: seeds are
     no longer inserted into the candidates table).
  3. Propose a new architecture via Opus.
  4. Score it through the cascade.
  5. Insert into the DB.
  6. If the new fitness clears the absolute milestone thresholds, fire
     the red-team agent and pass findings to the curator.
  7. Apply the islands manager's reset cadence.
  8. On scheduled intervals (or stall detection), fire the research agent
     and pass findings to the curator.

Termination: max_generations reached, OR curator returns PAUSE_FOR_HUMAN
on a structural finding, OR `max_consecutive_failures` LLM output failures.

Sprint 2 redesign: the milestone trigger uses absolute fitness +
robustness thresholds, not seed-relative comparison. The
`seed_baseline_fitness` mechanism was removed when seeds stopped being
scored candidates.

Every Orchestrator owns exactly one `run_id`. Every insert / read / audit
event is scoped to that run. Construct via `Orchestrator.for_new_run(...)`
to start a fresh run; via `Orchestrator.resume_run(...)` to attach to an
existing one.

The orchestrator never lets meta-layer state into the proposer's prompt —
that isolation is enforced by the seam between Proposer (which reads only
Architecture seeds) and Curator (which writes only to the audit log).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import anthropic

from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.parent_goal import PARENT_GOAL_VERSION
from alphamo.context.verifier import VERIFIER_VERSION
from alphamo.database import ProgramsDB
from alphamo.errors import LLMOutputError
from alphamo.evaluator import EvaluatorCascade
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
    ) -> "Orchestrator":
        """Attach to an existing Run row. Hyperparameters come from the row.

        Raises KeyError if run_id does not exist. Sets `last_resumed_at` on
        the run so the handoff can report fresh-vs-resumed.
        """
        run = db.get_run(run_id)
        hp = Hyperparameters(**run.hyperparameters) if run.hyperparameters else Hyperparameters()
        db.mark_run_resumed(run_id)
        return cls(db, client, audit_log, run_id=run_id, hp=hp, rng=rng)

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

        Stops early on (a) a structural curator pause or (b) when
        consecutive eval-side failures reach `hp.max_consecutive_failures`.
        Stamps the run's `stopped_reason` and `completed_at` on the Run row
        before returning.

        Sprint 2 redesign: no `seed_if_empty()` step — islands start empty
        and the proposer bootstraps each island from the reference exemplar
        set on its first iteration.
        """
        result = RunResult()
        consecutive_failures = 0
        for generation in range(1, max_generations + 1):
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
