"""AlphaMo CLI entry point.

Subcommand surface:
  init / show               — db setup and one-row inspection
  top                       — per-island top-k inspection (was 'query' before
                              run boundaries; renamed because 'query' now
                              lists runs)
  query                     — list all runs, or dump one run's JSON
  insert / generate         — manual or LLM-driven single-candidate insertion
                              into an existing run
  islands                   — per-island fitness / diversity for one run
  run / harvest             — production runs and structured handoff

Only `alphamo run` creates new runs. Seeding (gen-0 from the canonical
exemplar library) is the first action of every run — there is no separate
`seed` command. Other subcommands operate against an existing run, either
the one passed via --run or the latest run in the DB; they error out when
the DB has no runs yet.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from alphamo.database import ProgramsDB
from alphamo.schemas import Architecture, Scores

_DB_OPTION = click.option(
    "--db",
    "db_path",
    type=click.Path(dir_okay=False, path_type=Path),
    envvar="ALPHAMO_DB",
    default="alphamo.db",
    show_default=True,
    help="Path to the SQLite database file. Also reads ALPHAMO_DB.",
)

_AUDIT_OPTION = click.option(
    "--audit",
    "audit_path",
    type=click.Path(dir_okay=False, path_type=Path),
    envvar="ALPHAMO_AUDIT",
    default="runs/audit.jsonl",
    show_default=True,
    help="Path to the JSONL drift log. Also reads ALPHAMO_AUDIT.",
)


def _db_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def _resolve_run_id(db: ProgramsDB, run_id: str | None) -> str:
    """Resolve the run_id for subcommands that operate against an existing run.

    Validates `run_id` if given; otherwise falls back to the most recent run.
    Errors if neither is available — the CLI never auto-creates runs except
    via `alphamo run`. This keeps every Run row paired with a known starting
    point and a (eventually) `stopped_reason` written by the orchestrator.
    """
    if run_id is not None:
        try:
            db.get_run(run_id)
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        return run_id
    latest = db.latest_run_id()
    if latest is None:
        raise click.ClickException(
            "no runs in this DB — start one with `alphamo run`, or pass --run <run_id>"
        )
    return latest


@click.group()
def cli() -> None:
    """AlphaMo — interactive programs DB CLI."""


@cli.command()
@_DB_OPTION
def init(db_path: Path) -> None:
    """Create the SQLite file and schema."""
    ProgramsDB(_db_url(db_path))
    click.echo(f"initialised {db_path}")


@cli.command()
@click.option("--name", required=True)
@click.option("--summary", required=True)
@click.option("--value-chain", required=True)
@click.option("--capture-mechanism", required=True)
@click.option("--entry-resources", required=True)
@click.option("--feasibility", type=float, required=True)
@click.option("--structural", type=float, required=True)
@click.option("--exemplar-similarity", type=float, required=True)
@click.option(
    "--middle-class-accessible/--not-middle-class-accessible",
    "middle_class_accessible",
    default=True,
    show_default=True,
)
@click.option("--island", "island_id", type=int, default=0, show_default=True)
@click.option("--generation", type=int, default=0, show_default=True)
@click.option(
    "--run",
    "run_id",
    type=str,
    default=None,
    help="Run id to associate the row with. Defaults to latest run. "
    "Errors if the DB has no runs — start one with `alphamo run` first.",
)
@_DB_OPTION
def insert(
    name: str,
    summary: str,
    value_chain: str,
    capture_mechanism: str,
    entry_resources: str,
    feasibility: float,
    structural: float,
    exemplar_similarity: float,
    middle_class_accessible: bool,
    island_id: int,
    generation: int,
    run_id: str | None,
    db_path: Path,
) -> None:
    """Insert one candidate."""
    db = ProgramsDB(_db_url(db_path))
    architecture = Architecture(
        name=name,
        summary=summary,
        value_chain=value_chain,
        capture_mechanism=capture_mechanism,
        entry_resources=entry_resources,
    )
    scores = Scores(
        feasibility=feasibility,
        structural=structural,
        exemplar_similarity=exemplar_similarity,
        middle_class_accessible=middle_class_accessible,
    )
    resolved_run_id = _resolve_run_id(db, run_id)
    new_id = db.insert(
        architecture,
        scores,
        run_id=resolved_run_id,
        island_id=island_id,
        generation=generation,
    )
    row = db.get(new_id)
    click.echo(f"inserted id={new_id} run={resolved_run_id} fitness={row.fitness:.3f}")


@cli.command()
@click.option("--island", "island_id", type=int, default=0, show_default=True)
@click.option("--k", type=int, default=5, show_default=True)
@click.option(
    "--run",
    "run_id",
    type=str,
    default=None,
    help="Restrict to one run. Defaults to all runs (no filter).",
)
@_DB_OPTION
def top(island_id: int, k: int, run_id: str | None, db_path: Path) -> None:
    """Print top-k candidates in an island, highest fitness first."""
    db = ProgramsDB(_db_url(db_path))
    rows = db.top_k_in_island(island_id=island_id, k=k, run_id=run_id)
    if not rows:
        scope = f"run {run_id}" if run_id else "any run"
        click.echo(f"(no candidates in island {island_id} for {scope})")
        return
    click.echo(f"{'id':>4}  {'run':<14}  {'fitness':>8}  name")
    click.echo("-" * 60)
    for row in rows:
        name = row.architecture_spec.get("name", "?")
        click.echo(f"{row.id:>4}  {(row.run_id or ''):<14}  {row.fitness:>8.3f}  {name}")


@cli.command()
@click.argument("run_id", type=str, required=False)
@_DB_OPTION
def query(run_id: str | None, db_path: Path) -> None:
    """List runs in the DB. With a run_id argument, dump that run's full JSON."""
    db = ProgramsDB(_db_url(db_path))
    if run_id is not None:
        try:
            run = db.get_run(run_id)
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        payload = {
            "run_id": run.run_id,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "last_resumed_at": run.last_resumed_at.isoformat() if run.last_resumed_at else None,
            "stopped_reason": run.stopped_reason,
            "parent_goal_version": run.parent_goal_version,
            "verifier_version": run.verifier_version,
            "hyperparameters": run.hyperparameters,
            "notes": run.notes,
            "alive_candidates": db.count_candidates_in_run(run.run_id, status="alive"),
            "total_candidates": db.count_candidates_in_run(run.run_id),
        }
        click.echo(json.dumps(payload, indent=2))
        return

    runs = db.list_runs()
    if not runs:
        click.echo("(no runs in this DB)")
        return
    header = f"{'run_id':<14}  {'created_at':<25}  {'pg':<8}  {'ver':<8}  {'stopped':<22}  {'alive':>6}  {'total':>6}"
    click.echo(header)
    click.echo("-" * len(header))
    for run in runs:
        alive = db.count_candidates_in_run(run.run_id, status="alive")
        total = db.count_candidates_in_run(run.run_id)
        click.echo(
            f"{run.run_id:<14}  "
            f"{run.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'):<25}  "
            f"{run.parent_goal_version:<8}  "
            f"{run.verifier_version:<8}  "
            f"{(run.stopped_reason or '(running)'):<22}  "
            f"{alive:>6}  {total:>6}"
        )


@cli.command()
@click.argument("candidate_id", type=int)
@_DB_OPTION
def show(candidate_id: int, db_path: Path) -> None:
    """Print the full JSON record for one candidate."""
    db = ProgramsDB(_db_url(db_path))
    try:
        row = db.get(candidate_id)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc
    payload = {
        "id": row.id,
        "run_id": row.run_id,
        "architecture_spec": row.architecture_spec,
        "scores": row.scores,
        "fitness": row.fitness,
        "island_id": row.island_id,
        "generation": row.generation,
        "parent_ids": row.parent_ids,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    click.echo(json.dumps(payload, indent=2))


@cli.command()
@click.option("--island", "island_id", type=int, default=0, show_default=True)
@click.option("--k-seeds", "k_seeds", type=int, default=2, show_default=True)
@click.option("--generation", type=int, default=1, show_default=True)
@click.option(
    "--run",
    "run_id",
    type=str,
    default=None,
    help="Run id to draw seeds from and insert into. Defaults to latest run.",
)
@_DB_OPTION
def generate(
    island_id: int, k_seeds: int, generation: int, run_id: str | None, db_path: Path
) -> None:
    """Draw seeds from an island, propose a new candidate, evaluate, and insert."""
    import anthropic

    from alphamo.evaluator import EvaluatorCascade
    from alphamo.proposer import Proposer
    from alphamo.sampler import Sampler

    db = ProgramsDB(_db_url(db_path))
    client = anthropic.Anthropic()
    resolved_run_id = _resolve_run_id(db, run_id)

    seeds = Sampler(db, run_id=resolved_run_id).draw(island_id=island_id, k=k_seeds)
    if not seeds:
        raise click.ClickException(
            f"island {island_id} in run {resolved_run_id} is empty — insert candidates first"
        )

    click.echo(f"seeds: {[s.architecture.name for s in seeds]}")
    architecture = Proposer(client).propose(seeds)
    click.echo(f"proposed: {architecture.name}")

    result = EvaluatorCascade(client).evaluate(architecture)
    new_id = db.insert(
        architecture,
        result.scores,
        run_id=resolved_run_id,
        island_id=island_id,
        generation=generation,
    )
    row = db.get(new_id)
    click.echo(f"inserted id={new_id} run={resolved_run_id} fitness={row.fitness:.3f}")
    if result.early_exit:
        click.echo(f"early exit: {result.early_exit}")


@cli.command()
@click.option("--num-islands", "num_islands", type=int, default=8, show_default=True)
@click.option(
    "--run",
    "run_id",
    type=str,
    default=None,
    help="Restrict to one run. Defaults to latest run.",
)
@_DB_OPTION
def islands(num_islands: int, run_id: str | None, db_path: Path) -> None:
    """Print per-island fitness and diversity statistics for a run."""
    from alphamo.islands import IslandsManager

    db = ProgramsDB(_db_url(db_path))
    resolved_run_id = _resolve_run_id(db, run_id)
    mgr = IslandsManager(db, run_id=resolved_run_id, num_islands=num_islands)
    means = db.mean_fitness_per_island(num_islands, run_id=resolved_run_id)
    diversity = mgr.diversity_summary()

    click.echo(f"run: {resolved_run_id}")
    click.echo(f"{'island':>6}  {'mean_fit':>9}  {'diversity':>10}  top")
    click.echo("-" * 60)
    for i in range(num_islands):
        top = db.top_k_in_island(island_id=i, k=1, run_id=resolved_run_id)
        top_name = top[0].architecture_spec.get("name", "?") if top else "(empty)"
        click.echo(
            f"{i:>6}  {means[i]:>9.3f}  {diversity[i]:>10.3f}  {top_name}"
        )


@cli.command()
@click.option("--generations", type=int, default=50, show_default=True)
@click.option("--num-islands", "num_islands", type=int, default=8, show_default=True)
@click.option(
    "--milestone-min-generation",
    "milestone_min_generation",
    type=int,
    default=25,
    show_default=True,
    help="Red-team trigger requires generation >= this (warmup gate).",
)
@click.option(
    "--milestone-delta",
    "milestone_fitness_delta",
    type=float,
    default=0.02,
    show_default=True,
    help="Red-team trigger requires fitness > seed_baseline_fitness + this.",
)
@click.option("--research-every", "research_every", type=int, default=50, show_default=True)
@click.option(
    "--resume",
    "resume_id",
    type=str,
    default=None,
    help="Continue an existing run by id. Otherwise a fresh run is created.",
)
@_DB_OPTION
@_AUDIT_OPTION
def run(
    generations: int,
    num_islands: int,
    milestone_min_generation: int,
    milestone_fitness_delta: float,
    research_every: int,
    resume_id: str | None,
    db_path: Path,
    audit_path: Path,
) -> None:
    """Run a production loop end-to-end with islands, red-team, and curator."""
    import anthropic

    from alphamo.context.hyperparams import Hyperparameters
    from alphamo.meta.audit_log import AuditLog
    from alphamo.orchestrator import Orchestrator

    db = ProgramsDB(_db_url(db_path))
    audit = AuditLog(audit_path)
    client = anthropic.Anthropic()

    if resume_id is not None:
        try:
            orchestrator = Orchestrator.resume_run(db, client, audit, resume_id)
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"resuming run {resume_id}")
    else:
        hp = Hyperparameters(
            num_islands=num_islands,
            milestone_min_generation=milestone_min_generation,
            milestone_fitness_delta=milestone_fitness_delta,
            research_every_generations=research_every,
        )
        orchestrator = Orchestrator.for_new_run(db, client, audit, hp=hp)
        click.echo(f"started run {orchestrator.run_id}")

    result = orchestrator.run(max_generations=generations)

    click.echo(
        f"completed {len(result.events)} iteration(s) for {orchestrator.run_id}; "
        f"stopped: {result.stopped_reason}"
        + (" (paused for human)" if result.paused else "")
    )
    for event in result.events[-10:]:
        if event.skipped_reason:
            click.echo(
                f"gen {event.generation:>3} island {event.island_id} "
                f"skipped ({event.skipped_reason})"
            )
            continue
        marker = f"exit={event.early_exit}" if event.early_exit else "scored"
        meta = f" meta={event.meta_trigger}" if event.meta_trigger else ""
        fitness = f"{event.fitness:.3f}" if event.fitness is not None else "  -  "
        click.echo(
            f"gen {event.generation:>3} island {event.island_id} "
            f"id={event.candidate_id} fitness={fitness} "
            f"{marker}{meta} :: {event.architecture_name}"
        )


@cli.command()
@click.option("--num-islands", "num_islands", type=int, default=8, show_default=True)
@click.option(
    "--run",
    "run_id",
    type=str,
    default=None,
    help="Run id to harvest. Defaults to the most recent run in the DB.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default="runs/handoff.json",
    show_default=True,
)
@_DB_OPTION
@_AUDIT_OPTION
def harvest(
    num_islands: int,
    run_id: str | None,
    out_path: Path,
    db_path: Path,
    audit_path: Path,
) -> None:
    """Build the handoff document for a finished run."""
    import anthropic

    from alphamo.evaluator import EvaluatorCascade
    from alphamo.handoff import build_handoff
    from alphamo.meta.audit_log import AuditLog

    db = ProgramsDB(_db_url(db_path))
    audit = AuditLog(audit_path)
    cascade = EvaluatorCascade(anthropic.Anthropic())

    resolved_run_id = run_id or db.latest_run_id()
    if resolved_run_id is None:
        raise click.ClickException("no runs in this DB — nothing to harvest")

    handoff = build_handoff(
        db, audit, cascade, num_islands=num_islands, run_id=resolved_run_id
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(handoff.model_dump_json(indent=2))
    click.echo(
        f"run: {resolved_run_id}\n"
        f"winner: {handoff.winning_architecture.spec.name} "
        f"(island {handoff.winning_architecture.island_of_origin}, "
        f"generation {handoff.winning_architecture.generation})"
    )
    click.echo(
        f"alternates: {len(handoff.alternates)} | "
        f"drift log: {len(handoff.drift_log)} entries | "
        f"eval count: {handoff.verification_trail.eval_count}"
    )
    click.echo(f"wrote {out_path}")


if __name__ == "__main__":
    cli()
