"""Main loop coordinator: wires sampler + proposer + cascade + islands + meta.

One Orchestrator drives a run. Lifecycle:

  Bootstrap (once per fresh run, in `run()` before the main loop):
    - Score the trivial seed once via the cascade.
    - Insert a copy of the trivial seed into every island as a gen-0
      alive candidate. (Sprint 3, FunSearch alignment: every island
      starts with the same baseline; from gen 1 onward, evolution
      diverges per-island.)

  Inner loop (each generation — Sprint parallel-candidates):
    1. Pick N islands via `islands.pick_islands(candidates_per_generation)`.
       At candidates_per_generation = num_islands the result is a
       shuffled permutation — every island runs once per generation.
    2. Build a per-island snapshot of alive rows ONCE — every parallel
       pipeline reads from this snapshot, not from the live DB. This
       keeps the sampling view consistent across the batch: no candidate
       in the batch can see another candidate from the same batch.
    3. Sample seeds per island from the snapshot (cheap, no LLM).
    4. Fan out N proposer+cascade pipelines via
       `_concurrent.run_parallel_collect_results` capped at
       `max_parallel_candidates` workers. Each pipeline returns either
       a `_PipelineSuccess` (architecture + cascade result) or a
       `_PipelineFailure` carrying the failure stage label and exception.
    5. Sequentially process results: db.insert each success, write the
       Stage 4 routine / partial-failure / cascade-failure /
       proposer-failure audit events, run milestone curate per success.
       Sequential because SQLite serializes writes anyway and the audit
       log writes need stable ordering for diagnostics.
    6. Once per generation (NOT per candidate): apply the islands
       manager's reset cadence. The reset sees the full batch of new
       inserts and chooses sources accordingly. When fired, the
       FunSearch per-weak-island independent draw reseeds the bottom-
       half islands.
    (Sprint 12 removed the scheduled-research / stall-triggered
    research meta-path. Layer B's per-run-start refresh now provides
    current-developments grounding; the curator fires on milestone
    candidates only.)

Termination: max_generations reached, OR curator returns PAUSE_FOR_HUMAN
on a structural finding, OR `max_consecutive_failures` consecutive
all-fail generations. Sprint parallel-candidates redefined the failure
unit from "consecutive iterations" to "consecutive generations in
which no candidate succeeded" — at candidates_per_generation=1 the two
are identical, at N>1 the new shape is more permissive (a batch with
even one success resets the counter).

Sprint 3 redesign: bootstrap is back — the trivial Solo Service Provider
seed (`exemplar_library.TRIVIAL_SEED`) is inserted into every island at
gen 0 so the within-island sampler always has at least one row to
return. The proposer never sees a global reference library; everything
it sees comes from the current island.

Every Orchestrator owns exactly one `run_id`. Every insert / read /
audit event is scoped to that run.
"""

from __future__ import annotations

import functools
import random
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from alphamo._concurrent import run_parallel_collect_results
from alphamo.context.hyperparams import Hyperparameters
from alphamo.context.parent_goal import PARENT_GOAL_VERSION
from alphamo.context.verifier import VERIFIER_VERSION
from alphamo.database import ProgramsDB
from alphamo.errors import LLMOutputError
from alphamo.errors import (
    Stage1OutputError,
    Stage2OutputError,
    Stage4OutputError,
    TelemetryContext,
)
from alphamo.evaluator import EvaluatorCascade
from alphamo.evaluator.exemplar_library import TRIVIAL_SEED
from alphamo.evaluator.stage4_adversarial import FAILED_FRAMINGS_SENTINEL
from alphamo.islands import IslandsManager, ResetEvent
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.meta.curator import Curator
# Sprint 12: research module removed. The MILESTONE_CANDIDATE trigger
# label survived (curator path needs it for milestone-candidate audit
# events); now defined locally rather than imported from the deleted
# research_prompts module.
MILESTONE_CANDIDATE_TRIGGER = "milestone_candidate"
from alphamo.proposer import Proposer
from alphamo.providers.base import BaseProvider, ensure_provider
from alphamo.providers.factory import build_provider
from alphamo.sampler import Sampler, Seed
from alphamo.schemas import Architecture, Scores


def _build_component_providers(
    client: Any,
    hp: Hyperparameters,
) -> tuple[BaseProvider, BaseProvider, BaseProvider, BaseProvider, BaseProvider]:
    """Resolve one provider per LLM-calling component.

    Two paths:
      1. `client` is non-None (legacy / test path) — auto-wrap into an
         AnthropicProvider and share across all five components. The
         per-HP routing fields are bypassed so MagicMock-driven tests
         keep working unchanged.
      2. `client` is None (production CLI path) — build one provider
         per component from `hp.provider_*` via the factory. Identical
         provider names share an underlying SDK client via the
         factory's per-process cache.

    Returns (proposer, stage1, stage2, stage3, curator) in that order.
    """
    if client is not None:
        shared = ensure_provider(client)
        return shared, shared, shared, shared, shared
    return (
        build_provider(hp.provider_proposer),
        build_provider(hp.provider_stage1),
        build_provider(hp.provider_stage2),
        build_provider(hp.provider_stage3),
        build_provider(hp.provider_curator),
    )
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
# Sprint 15 (Q4): one event per FAILED framing call, additive to the
# existing partial / catastrophic triggers (those fire at the gate
# level; this one fires per-framing on the actual failure). Emitted
# from inside stage4_adversarial via the telemetry context; not
# imported back into stage4_adversarial.py to avoid a circular import
# (orchestrator.py already imports FAILED_FRAMINGS_SENTINEL from
# stage4_adversarial.py — keeping that direction unidirectional).
# stage4_adversarial uses the literal string "stage3_framing_call";
# this constant is the canonical reference for tests and consumers.
STAGE3_FRAMING_CALL = "stage3_framing_call"
# Sprint 7: previously-silent failure paths in step() now emit dedicated
# audit events. PROPOSER_FAILURE_TRIGGER fires when proposer.propose()
# raises an LLMOutputError (parse error, refusal, truncation).
# CASCADE_FAILURE_TRIGGER fires when cascade.evaluate() raises any
# LLMOutputError that ISN'T the already-instrumented Stage 3
# catastrophic case — e.g. Stage 1 (Haiku) or Stage 2 (Sonnet)
# parse errors, or generic Stage 4OutputError without the catastrophic
# stop_reason.
PROPOSER_FAILURE_TRIGGER = "proposer_failure"
CASCADE_FAILURE_TRIGGER = "cascade_failure"


# Sprint 7: map exception class → stage label used in cascade_failure
# audit events. Keeps the audit-payload string canonical and queryable.
# Stage4OutputError covers adversarial scrutiny; the catastrophic
# sub-case is filtered out before we get here.
_CASCADE_FAILURE_STAGE_LABEL: dict[type, str] = {
    Stage1OutputError: "feasibility",
    Stage2OutputError: "structural",
    Stage4OutputError: "adversarial",
}


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


@dataclass(frozen=True)
class _PipelineSuccess:
    """Sprint parallel-candidates: result of one successful proposer +
    cascade pass. Carries everything the post-fan-out sequential pass
    needs to perform db.insert + audit logging + milestone curate.
    Thread-immutable (frozen) so it can move across thread boundaries
    without locking."""

    island_id: int
    architecture: Architecture
    cascade_result: Any  # CascadeResult; typed as Any to avoid the import cycle
    parent_ids: list[int] | None


@dataclass(frozen=True)
class _PipelineFailure:
    """Sprint parallel-candidates: result of one failed proposer +
    cascade pass. Carries the failure stage and exception so the
    sequential post-pass writes the correct audit event.

    `stage`:
      - "proposer"               — proposer.propose raised LLMOutputError
      - "stage3_catastrophic"    — Stage 3 framings dropped below the floor
      - "cascade"                — any other cascade-side LLMOutputError
    `architecture` is None for proposer-stage failures (no architecture
    produced); set for cascade-stage failures (the candidate the cascade
    refused to score).
    """

    island_id: int
    architecture: Architecture | None
    stage: str
    exc: LLMOutputError


@dataclass
class RunResult:
    """What the orchestrator returns after a run."""

    events: list[IterationEvent] = field(default_factory=list)
    paused: bool = False
    stopped_reason: str = "max_generations"
    consecutive_failures_at_stop: int = 0


# Sprint 5: stopped_reasons that block resume unless `force=True` is passed.
# `max_generations` is the intentional-stop case and is freely extendable;
# the other two reasons signal that the run hit something worth a human
# review before pressing on.
_FORCE_REQUIRED_STOPPED_REASONS = frozenset(
    {"consecutive_failures", "curator_pause"}
)


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
        client: Any,
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

        # Sprint 14: build one provider per component from Hyperparameters.
        # When `client` is provided directly (legacy path, including tests
        # passing a MagicMock), every component shares the auto-wrapped
        # provider — the per-HP routing fields are bypassed for that path
        # so existing tests stay byte-stable. The production CLI path
        # passes `client=None` and lets each component route from HP.
        proposer_provider, stage1_provider, stage2_provider, \
            stage3_provider, curator_provider = _build_component_providers(
                client, self.hp
            )
        self.proposer = Proposer(
            proposer_provider,
            model=self.hp.model_proposer,
            reasoning_effort=self.hp.reasoning_effort_proposer,
        )
        self.cascade = EvaluatorCascade(
            stage1_provider=stage1_provider,
            stage2_provider=stage2_provider,
            stage3_provider=stage3_provider,
            stage1_model=self.hp.model_stage1,
            stage2_model=self.hp.model_stage2,
            stage3_model=self.hp.model_stage3,
            stage3_reasoning_effort=self.hp.reasoning_effort_stage3,
            stage1_threshold=self.hp.stage1_threshold,
            stage2_threshold=self.hp.stage2_threshold,
            stage4_decay_k=self.hp.stage4_decay_k,
        )
        self.curator = Curator(
            curator_provider,
            audit_log,
            run_id=run_id,
            model=self.hp.model_curator,
            reasoning_effort=self.hp.reasoning_effort_curator,
        )

    # ------------------------------------------------------------------ factories

    @classmethod
    def for_new_run(
        cls,
        db: ProgramsDB,
        client: Any,
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
        client: Any,
        audit_log: AuditLog,
        run_id: str,
        rng: random.Random | None = None,
        on_warning: Callable[[str], None] | None = None,
        force: bool = False,
    ) -> "Orchestrator":
        """Attach to an existing Run row. Hyperparameters come from the row.

        Sprint 4: applies a compatibility check between the persisted run
        and the current code's PARENT_GOAL_VERSION + VERIFIER_VERSION +
        structural HP. HARD-BLOCK conditions raise
        `ResumeIncompatibleError`; SOFT-WARN conditions go to `on_warning`
        (defaults to stderr-print) and resume proceeds.

        Sprint 5: resume supports extending completed runs (those whose
        `stopped_reason="max_generations"`) — the row's `completed_at`
        and `stopped_reason` get cleared so the next `run()` call can
        treat it as in-progress again. Runs stopped via
        `consecutive_failures` or `curator_pause` are BLOCKED unless
        `force=True`: those stop reasons signal something worth a human
        review before pressing on.

        Raises KeyError if run_id does not exist. Raises
        ResumeIncompatibleError on a structural mismatch or on a
        blocked stopped_reason without force. Sets `last_resumed_at`
        on the run so the handoff can report fresh-vs-resumed.
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

        if (
            not force
            and run.stopped_reason in _FORCE_REQUIRED_STOPPED_REASONS
        ):
            raise ResumeIncompatibleError(
                run_id,
                [
                    f"stopped_reason={run.stopped_reason!r} requires "
                    "--force-resume to resume — this stop reason "
                    "signals something worth a human review before "
                    "pressing on"
                ],
            )

        if warnings:
            emit = on_warning if on_warning is not None else _default_resume_warning
            for warning in warnings:
                emit(warning)

        # Sprint 5: previously-completed runs (max_generations stop) need
        # their completion markers cleared so the next run() call can
        # extend them. The orchestrator will re-stamp these on the next
        # termination. Crashed runs (completed_at NULL) skip this
        # branch and proceed straight to mark_run_resumed.
        if run.completed_at is not None or run.stopped_reason is not None:
            db.uncomplete_run(run_id)

        db.mark_run_resumed(run_id)
        return cls(db, client, audit_log, run_id=run_id, hp=hp, rng=rng)

    # ------------------------------------------------------------------ bootstrap

    def _bootstrap_islands(self) -> int:
        """Insert a copy of `TRIVIAL_SEED` into every island as a gen-0
        alive candidate. Returns the number of seed copies inserted.

        No-op when this run already has alive candidates (resumed run, or
        bootstrap already executed in a prior session).

        FunSearch alignment: "Each island is initialized with a copy of
        the user-provided initial program and is evolved separately."
        Single architecture, copied to all m islands; per-island
        evolution proceeds independently.

        Sprint 14 fix: the trivial seed gets a HARD-CODED model-independent
        Scores rather than running through the cascade. The trivial seed
        is a GA initializer, not a candidate being scored for quality —
        it just needs to be alive (`fitness > 0.0`) so the within-island
        sampler returns something on gen 1. The pre-Sprint-14 design
        scored it through Stage 1 + Stage 2 + 9 Stage 3 framings (11 LLM
        calls per run, identical seed every time, model-family-dependent
        output). That assumed the trivial seed would score above 0.0
        across model families; DeepSeek V4 Flash treats "no leverage, no
        scale" as incoherent and returns feasibility=0.0, which fails
        stage1_threshold=0.4, zeroes structural, and (via
        `aggregate_fitness`) produces fitness=0.0 — below the sampler's
        strict `fitness > 0.0` alive filter, dropping the seed and
        crashing the proposer on gen 1 with empty seeds.

        Hard-coded `feasibility=0.50, structural=0.50` gives the seed an
        aggregate fitness of 0.50 — comfortably above the alive
        threshold, low enough that any real generated candidate scoring
        on its merits sorts above it. `robustness=None` and
        `exemplar_similarity=None` follow the Sprint 2/4 conventions
        for fields that weren't computed.

        Side effect of skipping the cascade: bootstrap no longer emits
        any `llm_usage` audit events. The `bootstrap` audit event still
        fires and carries the hard-coded scores.
        """
        if self.db.count_candidates_in_run(self.run_id) > 0:
            return 0

        # Sprint 14: model-independent Scores. See docstring for the
        # full rationale — short version, the trivial seed is a GA
        # initializer, not a candidate being evaluated.
        seed_scores = Scores(
            feasibility=0.50,
            structural=0.50,
            robustness=None,
            exemplar_similarity=None,
            middle_class_accessible=True,
        )
        stage4_findings_payload = None
        inserted_ids: list[int] = []
        for island_id in range(self.hp.num_islands):
            candidate_id = self.db.insert(
                TRIVIAL_SEED,
                seed_scores,
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
                    "seed_scores": seed_scores.model_dump(mode="json"),
                    "candidate_ids": inserted_ids,
                    "num_islands": self.hp.num_islands,
                },
            )
        )
        return len(inserted_ids)

    # ------------------------------------------------------------------ loop

    # Sprint 13: detect_stall() removed. The method had no callers after
    # Sprint 12's research-removal sweep deleted `_maybe_research`. The
    # Sprint 12 commit flagged the orphan status; the decision was to
    # delete cleanly rather than maintain unused code. If stall-triggered
    # intervention is wanted in the future, it gets purpose-built then
    # rather than resurrected from this orphan. `stall_window` and
    # `stall_epsilon` Hyperparameters fields removed alongside.

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

    def _log_proposer_failure(
        self,
        generation: int,
        island_id: int,
        exc: LLMOutputError,
    ) -> None:
        """Sprint 7: record a proposer-side LLMOutputError as a structured
        audit event so the previously-silent failure path is queryable
        post-run from audit.jsonl alone.

        Carries stop_reason + truncated detail so post-run analysis can
        distinguish parse failures (refusal / max_tokens / schema
        mismatch) without needing the raw exception object.
        """
        stop_reason = getattr(exc, "stop_reason", None) or "unknown"
        detail = str(exc)[:300]
        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=PROPOSER_FAILURE_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"generation={generation} island_id={island_id} "
                    f"stop_reason={stop_reason} detail={detail}"
                ),
                payload={
                    "generation": generation,
                    "island_id": island_id,
                    "stop_reason": stop_reason,
                    "detail": detail,
                },
            )
        )

    def _log_cascade_failure(
        self,
        generation: int,
        island_id: int,
        architecture: Architecture,
        exc: LLMOutputError,
    ) -> None:
        """Sprint 7: record a cascade-side LLMOutputError as a structured
        audit event. Covers Stage 1 / Stage 2 / non-catastrophic Stage 3
        (adversarial) cases. The Stage 3 catastrophic sub-case has its
        own dedicated trigger (`stage3_catastrophic_framing_failure`)
        and is routed to `_log_stage3_catastrophic_failure` instead;
        the caller filters that case out before invoking this method.
        """
        stage = _CASCADE_FAILURE_STAGE_LABEL.get(type(exc), "unknown")
        stop_reason = getattr(exc, "stop_reason", None) or "unknown"
        detail = str(exc)[:300]
        arch_name = architecture.name if architecture is not None else "unknown"
        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                run_id=self.run_id,
                trigger=CASCADE_FAILURE_TRIGGER,
                classification="routine",
                action="recorded",
                rationale=(
                    f"generation={generation} island_id={island_id} "
                    f"stage={stage} architecture={arch_name} "
                    f"stop_reason={stop_reason} detail={detail}"
                ),
                payload={
                    "generation": generation,
                    "island_id": island_id,
                    "stage": stage,
                    "architecture_name": arch_name,
                    "stop_reason": stop_reason,
                    "detail": detail,
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
        telemetry: TelemetryContext | None = None,
    ) -> tuple[str, CuratorDecision] | None:
        """If the candidate is a milestone AND adversarial scrutiny surfaced
        concerns, invoke the curator's classify-and-gate path.

        Per Decision 3: only STRUCTURAL concerns trigger pause. The curator's
        existing semantics handle that — it classifies each concern and pauses
        on any STRUCTURAL classification, continues on cosmetic-only.

        A milestone with empty Stage 4 concerns (clean adversarial pass) does
        not invoke the curator — there's nothing to classify.

        Sprint 14 follow-up: gated on `hp.curator_pause_enabled`. Defaults
        to False (disabled) so production unattended runs execute through
        to the defined generation count without human-review stops. Set
        `curator_pause_enabled=True` on the HP to opt in.
        """
        if not self.hp.curator_pause_enabled:
            return None
        if not self._is_milestone(generation, fitness, stage4.robustness):
            return None
        if not stage4.concerns:
            return None
        meta_findings = _stage4_concerns_as_meta_findings(stage4.concerns)
        decision = self.curator.curate(
            meta_findings,
            trigger=MILESTONE_CANDIDATE_TRIGGER,
            telemetry=telemetry,
        )
        return MILESTONE_CANDIDATE_TRIGGER, decision

    def _snapshot_islands(
        self, island_ids: list[int]
    ) -> dict[int, list]:
        """Sprint parallel-candidates: build a per-island view of alive
        rows so all parallel pipelines see a consistent snapshot.

        Reads at most `sampler.pool_size` rows per island (matching
        `sampler.draw()`'s live-query behaviour) so the snapshot path
        and the live-query path see the same candidate pool. Built
        once per generation, before fan-out.
        """
        return {
            iid: self.db.top_k_in_island(
                island_id=iid, k=self.sampler.pool_size, run_id=self.run_id
            )
            for iid in island_ids
        }

    def _run_candidate_pipeline(
        self,
        island_id: int,
        seeds: list[Seed],
        telemetry: TelemetryContext,
    ) -> _PipelineSuccess | _PipelineFailure:
        """Sprint parallel-candidates: thread-safe proposer + cascade pass.

        Runs INSIDE the parallel fan-out. Does NOT touch the database;
        the caller does sequential inserts after the join. Audit-log
        writes are restricted to the deep `llm_usage` events emitted by
        provider.parse — those go through `AuditLog.append` which is
        thread-safe (sprint parallel-candidates added a lock).

        Returns:
          - _PipelineSuccess on a clean run: caller inserts the row and
            writes the stage4_routine / stage3_partial / milestone-
            curator audit events sequentially.
          - _PipelineFailure on proposer / cascade LLMOutputError: caller
            writes the corresponding failure audit event sequentially
            (so the audit log retains stable per-generation ordering).

        The two-bucket return shape lets `step()` partition results
        cleanly without re-raising across thread boundaries — the
        `run_parallel_collect_results` helper's `Exception` channel is
        reserved for genuinely unexpected (non-LLMOutputError) errors,
        which are bubbled up unchanged so the orchestrator can crash
        loudly instead of silently swallowing bugs.
        """
        try:
            architecture = self.proposer.propose(seeds, telemetry=telemetry)
        except LLMOutputError as exc:
            return _PipelineFailure(
                island_id=island_id,
                architecture=None,
                stage="proposer",
                exc=exc,
            )

        try:
            cascade_result = self.cascade.evaluate(
                architecture, telemetry=telemetry
            )
        except LLMOutputError as exc:
            if (
                isinstance(exc, Stage4OutputError)
                and exc.stop_reason == "stage3_catastrophic_framing_failure"
            ):
                stage = "stage3_catastrophic"
            else:
                stage = "cascade"
            return _PipelineFailure(
                island_id=island_id,
                architecture=architecture,
                stage=stage,
                exc=exc,
            )

        parent_ids = [s.id for s in seeds if s.id is not None] or None
        return _PipelineSuccess(
            island_id=island_id,
            architecture=architecture,
            cascade_result=cascade_result,
            parent_ids=parent_ids,
        )

    def _process_pipeline_failure(
        self,
        generation: int,
        failure: _PipelineFailure,
    ) -> IterationEvent:
        """Sequential post-fan-out: write the failure audit event and
        return the IterationEvent shape the caller expects. Mirrors the
        pre-sprint inline failure-handling paths in `step()` so the
        emitted audit triggers stay byte-stable."""
        if failure.stage == "proposer":
            self._log_proposer_failure(generation, failure.island_id, failure.exc)
            return IterationEvent(
                generation=generation,
                island_id=failure.island_id,
                failure_reason=str(failure.exc),
            )
        if failure.stage == "stage3_catastrophic":
            # architecture is non-None here by construction
            self._log_stage3_catastrophic_failure(
                generation, failure.island_id, failure.architecture, failure.exc
            )
        else:  # "cascade"
            self._log_cascade_failure(
                generation, failure.island_id, failure.architecture, failure.exc
            )
        return IterationEvent(
            generation=generation,
            island_id=failure.island_id,
            architecture_name=(
                failure.architecture.name
                if failure.architecture is not None
                else None
            ),
            failure_reason=str(failure.exc),
        )

    def _process_pipeline_success(
        self,
        generation: int,
        success: _PipelineSuccess,
        telemetry: TelemetryContext,
    ) -> IterationEvent:
        """Sequential post-fan-out: insert the candidate, write the
        stage4_routine / stage3_partial / milestone-curator audit
        events, and return the IterationEvent."""
        result = success.cascade_result
        architecture = success.architecture
        island_id = success.island_id

        # Sprint 1 (Bug 2): Stage 4 concerns persist on the candidate row so
        # they're queryable per candidate via SQL, not just buried in the
        # audit-log JSONL. NULL when the cascade short-circuited before
        # Stage 4 (Stage 1/2/3 exit) or middle-class filter failure.
        stage4_findings_payload = (
            [c.model_dump(mode="json") for c in result.stage3.concerns]
            if result.stage3 is not None
            else None
        )
        # Sprint 15 (Q2): per-framing clean-pass assessments persisted
        # to the new stage4_assessments column.
        stage4_assessments_payload = (
            (result.stage3.framing_assessments or None)
            if result.stage3 is not None
            else None
        )
        # Sprint Stage 2 PAJAMA: persist the full Stage 2 evidence dict.
        stage2_evidence_payload = (
            result.stage2.model_dump(mode="json")
            if result.stage2 is not None
            else None
        )
        # Sprint Stage 1 PAJAMA: persist the full Stage 1 evidence dict.
        stage1_evidence_payload = (
            result.stage1.model_dump(mode="json")
            if result.stage1 is not None
            else None
        )
        candidate_id = self.db.insert(
            architecture,
            result.scores,
            run_id=self.run_id,
            island_id=island_id,
            generation=generation,
            parent_ids=success.parent_ids,
            stage4_findings=stage4_findings_payload,
            stage4_assessments=stage4_assessments_payload,
            stage2_evidence=stage2_evidence_payload,
            stage1_evidence=stage1_evidence_payload,
        )
        row = self.db.get(candidate_id)

        if result.stage3 is not None:
            self._log_stage4_routine(candidate_id, result.stage3)
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
                    generation,
                    candidate_id,
                    row.fitness,
                    result.stage3,
                    telemetry=telemetry,
                )
                if result.stage3 is not None
                else None
            )
            if milestone_outcome is not None:
                meta_trigger, meta_decision = milestone_outcome
        except LLMOutputError as exc:
            meta_failure = str(exc)

        return IterationEvent(
            generation=generation,
            island_id=island_id,
            candidate_id=candidate_id,
            fitness=row.fitness,
            architecture_name=architecture.name,
            early_exit=result.early_exit,
            meta_trigger=meta_trigger,
            meta_decision=meta_decision,
            failure_reason=meta_failure,
        )

    def step(self, generation: int) -> list[IterationEvent]:
        """Run one generation. Returns one IterationEvent per candidate
        in the batch (1 to candidates_per_generation events).

        Sprint parallel-candidates: the per-generation pipeline:
          1. `islands.pick_islands(candidates_per_generation)` — N
             distinct island ids.
          2. `_snapshot_islands(island_ids)` — one DB read per island.
             All parallel samplers draw from this snapshot so no
             intra-batch sibling can pollute another's view.
          3. Sample seeds per island sequentially (cheap; no LLM).
          4. Run N proposer+cascade pipelines in parallel via
             `run_parallel_collect_results` capped at
             `max_parallel_candidates` workers.
          5. Sequential post-pass: db.insert for each success, write
             the per-result audit events, run milestone curator gate.
          6. `islands.maybe_reset(generation)` once for the whole batch.

        Backward compat invariant: at `candidates_per_generation=1`
        the returned list has length 1 and the single event matches
        the pre-sprint single-event semantics, including reset_event
        being attached to the sole event.
        """
        n = min(self.hp.candidates_per_generation, self.hp.num_islands)
        island_ids = self.islands.pick_islands(n)

        # Sprint parallel-candidates: snapshot built ONCE before fan-out.
        # Empty per-island lists are fine — proposer.propose tolerates
        # empty seeds (the bootstrap path always has TRIVIAL_SEED so in
        # practice every post-bootstrap island has at least one row).
        snapshot = self._snapshot_islands(island_ids)

        # Per-island telemetry contexts; each pipeline gets its own so
        # the `llm_usage` audit events attribute correctly to (gen,
        # island). TelemetryContext is frozen so it's safe to pass into
        # worker threads.
        telemetry_per_island: dict[int, TelemetryContext] = {
            iid: TelemetryContext(
                audit_log=self.audit_log,
                run_id=self.run_id,
                generation=generation,
                island_id=iid,
            )
            for iid in island_ids
        }

        # Sample seeds sequentially from the snapshot — this is cheap
        # (no LLM, no DB), and keeping it serial avoids any RNG
        # threading concerns in the sampler.
        seeds_per_island: dict[int, list[Seed]] = {
            iid: self.sampler.draw_from_snapshot(
                island_id=iid, snapshot=snapshot, k=self.hp.k_seeds
            )
            for iid in island_ids
        }

        # Build pipeline tasks. `functools.partial` so the executor
        # gets zero-arg callables matching run_parallel's contract.
        tasks = [
            functools.partial(
                self._run_candidate_pipeline,
                iid,
                seeds_per_island[iid],
                telemetry_per_island[iid],
            )
            for iid in island_ids
        ]

        # Fan-out. Failures are returned as _PipelineFailure (caught
        # inside _run_candidate_pipeline); unexpected exceptions are
        # surfaced via run_parallel_collect_results's exception channel
        # and re-raised below — we don't want bugs hidden behind a
        # silent batch-success.
        raw_results = run_parallel_collect_results(
            tasks, max_workers=self.hp.max_parallel_candidates
        )

        # Sequential post-pass. The order of `island_ids` is stable
        # because pick_islands returns a concrete shuffled list; the
        # results list from run_parallel_collect_results preserves
        # submission order, so zip pairs each result with its island.
        events: list[IterationEvent] = []
        for iid, raw in zip(island_ids, raw_results):
            if isinstance(raw, Exception):
                # Unexpected non-LLMOutputError exception from inside a
                # worker. Re-raise so the bug surfaces rather than
                # silently dropping the candidate.
                raise raw
            if isinstance(raw, _PipelineFailure):
                events.append(self._process_pipeline_failure(generation, raw))
            else:  # _PipelineSuccess
                events.append(
                    self._process_pipeline_success(
                        generation, raw, telemetry_per_island[iid]
                    )
                )

        # One reset check per generation, not per candidate. The reset
        # sees the full batch of new inserts in the DB and ranks
        # islands accordingly. Attached to the last event in the batch
        # so test code can still find `event.reset_event` without
        # changing the IterationEvent shape.
        reset_event = self.islands.maybe_reset(generation)
        if reset_event is not None:
            self._log_island_reset(generation, reset_event)
            if events:
                # IterationEvent is a mutable dataclass — direct
                # assignment is fine and avoids a `dataclasses.replace`
                # allocation here.
                events[-1].reset_event = reset_event

        return events

    def run(self, max_generations: int) -> RunResult:
        """Drive up to `max_generations` generations.

        Sprint parallel-candidates: each generation produces up to
        `candidates_per_generation` candidates via the batched
        `step()`. The result.events list aggregates every IterationEvent
        from every generation (one per candidate produced), so a 5-
        generation run at N=8 produces up to 40 events.

        Bootstrap step: before the main loop, every island gets a copy
        of the trivial seed at gen 0 via `_bootstrap_islands()`. No-op
        on resume (existing alive candidates ⇒ skip).

        Sprint 4: the loop's start generation is derived from the DB
        after bootstrap — `db.latest_generation_in_run + 1`.

        Stops early on (a) a structural curator pause or (b) when
        `max_consecutive_failures` consecutive ALL-FAIL generations
        have occurred — a batch in which no candidate succeeded.
        Sprint parallel-candidates redefined the failure unit from
        "consecutive iterations" to "consecutive all-fail generations":
        at N=1 the two are identical; at N>1 partial failures within a
        batch do not increment the counter, which is appropriate since
        a single LLM-output failure on one of 8 candidates is normal
        and does not indicate a broken pipeline.

        Stamps the run's `stopped_reason` and `completed_at` on the Run
        row before returning.
        """
        self._bootstrap_islands()
        start_generation = self.db.latest_generation_in_run(self.run_id) + 1
        # Bootstrap inserts at generation 0, so post-bootstrap fresh runs
        # have start_generation = 1.
        start_generation = max(1, start_generation)
        result = RunResult()
        consecutive_failures = 0
        for generation in range(start_generation, max_generations + 1):
            events = self.step(generation)
            result.events.extend(events)

            # Sprint parallel-candidates: per-generation failure counter.
            # A generation succeeds (resets the counter) iff at least
            # one of its events carries a candidate_id (a candidate
            # made it into the DB). A generation fails iff every event
            # is a parse/cascade failure with no candidate_id. Empty
            # event lists (no work) are treated as no-progress and
            # increment the counter — this should never happen in
            # practice because pick_islands always returns at least
            # one island.
            any_succeeded = any(e.candidate_id is not None for e in events)
            if any_succeeded:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= self.hp.max_consecutive_failures:
                    result.stopped_reason = "consecutive_failures"
                    result.consecutive_failures_at_stop = consecutive_failures
                    self.db.complete_run(self.run_id, result.stopped_reason)
                    return result

            # PAUSE_FOR_HUMAN fires the moment any candidate in this
            # generation gets one. Scan the batch's events; first hit wins.
            paused_event = next(
                (
                    e
                    for e in events
                    if e.meta_decision is not None
                    and e.meta_decision.action == CuratorAction.PAUSE_FOR_HUMAN
                ),
                None,
            )
            if paused_event is not None:
                result.paused = True
                result.stopped_reason = "curator_pause"
                result.consecutive_failures_at_stop = consecutive_failures
                self.db.complete_run(self.run_id, result.stopped_reason)
                return result
        result.consecutive_failures_at_stop = consecutive_failures
        self.db.complete_run(self.run_id, result.stopped_reason)
        return result


__all__ = ["IterationEvent", "Orchestrator", "RunResult"]
