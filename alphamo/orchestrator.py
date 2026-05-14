"""Main loop coordinator: wires sampler + proposer + cascade + islands + meta.

One Orchestrator drives a run. Each iteration:
  1. Pick an island (uniform).
  2. Draw k seeds via softmax-weighted sampling.
  3. Propose a new architecture via Opus.
  4. Score it through the cascade.
  5. Insert into the DB.
  6. If the new fitness is at or above the milestone threshold, fire the
     red-team agent and pass findings to the curator.
  7. Apply the islands manager's reset cadence.
  8. On scheduled intervals (or stall detection), fire the research agent
     and pass findings to the curator.

Termination: max_generations reached, OR curator returns PAUSE_FOR_HUMAN
on a structural finding.

The orchestrator never lets meta-layer state into the proposer's prompt —
that isolation is enforced by the seam between Proposer (which reads only
Architecture seeds) and Curator (which writes only to the audit log).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import anthropic

from alphamo.context.hyperparams import Hyperparameters
from alphamo.database import ProgramsDB
from alphamo.evaluator import EvaluatorCascade
from alphamo.evaluator.exemplar_library import STARTERS
from alphamo.islands import IslandsManager, ResetEvent
from alphamo.meta.audit_log import AuditLog
from alphamo.meta.curator import Curator
from alphamo.meta.redteam import red_team_candidate
from alphamo.meta.research import run_research
from alphamo.prompts.research_prompts import Trigger
from alphamo.proposer import Proposer
from alphamo.sampler import Sampler
from alphamo.schemas import Architecture
from alphamo.schemas.findings import CuratorAction, CuratorDecision


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


@dataclass
class RunResult:
    """What the orchestrator returns after a run."""

    events: list[IterationEvent] = field(default_factory=list)
    paused: bool = False
    stopped_reason: str = "max_generations"


class Orchestrator:
    """Drives one production run end-to-end."""

    def __init__(
        self,
        db: ProgramsDB,
        client: anthropic.Anthropic,
        audit_log: AuditLog,
        hp: Hyperparameters | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.client = client
        self.audit_log = audit_log
        self.hp = hp or Hyperparameters()
        self.rng = rng or random.Random()

        self.islands = IslandsManager(
            db,
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
        )
        self.proposer = Proposer(client)
        self.cascade = EvaluatorCascade(
            client,
            stage1_threshold=self.hp.stage1_threshold,
            stage2_threshold=self.hp.stage2_threshold,
        )
        self.curator = Curator(client, audit_log)

    def seed_if_empty(self) -> bool:
        """Seed all islands with the canonical STARTERS if the DB has none alive."""
        if self.db.count_candidates(status="alive") > 0:
            return False
        self.islands.seed_all_islands(STARTERS)
        return True

    def detect_stall(self) -> bool:
        """True if max fitness has barely moved over the last `stall_window` generations."""
        history = self.db.fitness_history(self.hp.stall_window)
        if len(history) < self.hp.stall_window:
            return False
        return max(history) - min(history) < self.hp.stall_epsilon

    def _maybe_red_team(
        self,
        generation: int,
        architecture: Architecture,
        fitness: float,
    ) -> tuple[str, CuratorDecision] | None:
        if fitness < self.hp.milestone_fitness:
            return None
        findings = red_team_candidate(architecture, self.client)
        decision = self.curator.curate(findings, trigger=Trigger.MILESTONE_CANDIDATE)
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
        """Run one inner-loop generation. Returns an audit record."""
        island_id = self.islands.pick_island()
        seeds = self.sampler.draw(island_id=island_id, k=self.hp.k_seeds)
        if not seeds:
            return IterationEvent(
                generation=generation,
                island_id=island_id,
                skipped_reason="empty_island",
            )

        architecture = self.proposer.propose(seeds)
        result = self.cascade.evaluate(architecture)
        candidate_id = self.db.insert(
            architecture,
            result.scores,
            island_id=island_id,
            generation=generation,
        )
        row = self.db.get(candidate_id)

        meta_trigger: str | None = None
        meta_decision: CuratorDecision | None = None
        red_team_outcome = self._maybe_red_team(generation, architecture, row.fitness)
        if red_team_outcome is not None:
            meta_trigger, meta_decision = red_team_outcome
        else:
            research_outcome = self._maybe_research(generation)
            if research_outcome is not None:
                meta_trigger, meta_decision = research_outcome

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
        )

    def run(self, max_generations: int) -> RunResult:
        """Drive up to `max_generations` iterations. Stops early on PAUSE."""
        self.seed_if_empty()
        result = RunResult()
        for generation in range(1, max_generations + 1):
            event = self.step(generation)
            result.events.append(event)
            if (
                event.meta_decision is not None
                and event.meta_decision.action == CuratorAction.PAUSE_FOR_HUMAN
            ):
                result.paused = True
                result.stopped_reason = "curator_pause"
                return result
        return result


__all__ = ["IterationEvent", "Orchestrator", "RunResult"]
