"""AlphaMo CLI entry point.

Subcommand surface:
  doctor                    — pre-flight env / dep / writeability check
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

Sprint 16 (launch surface): `.env` is auto-loaded at CLI startup so
operators don't have to remember to `source .env` before running. The
loader walks up from CWD; existing process-env variables are NOT
overridden, so CI / production deployments that set vars out-of-band
keep working unchanged. Opt out with `--no-dotenv`. `alphamo doctor`
reports which variables are set and from where.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import click

from alphamo import __version__
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


# ----------------------------------------------------------------- .env autoload


# Track where .env was loaded from so `alphamo doctor` can report it
# accurately. Populated by `_autoload_dotenv` on the very first
# invocation of any subcommand under the `cli` group.
_DOTENV_LOADED_FROM: Path | None = None


def _autoload_dotenv() -> None:
    """Load `.env` from CWD or any ancestor directory, without overriding.

    Sprint 16: the canonical launch path expects `.env` to live in the
    repo root carrying `FIREWORKS_API_KEY` (and optionally
    `ANTHROPIC_API_KEY`). Pre-Sprint-16 the operator had to `source .env`
    manually before invoking the CLI — easy to forget, and the failure
    surfaces deep inside `Orchestrator.__init__`. We now load it
    automatically at CLI startup via python-dotenv with `override=False`
    so process-env variables set out-of-band (CI / k8s / systemd) keep
    precedence.
    """
    global _DOTENV_LOADED_FROM
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        # python-dotenv ships in the project's pyproject.toml dependencies;
        # absence here means the install is incomplete. Don't crash the CLI
        # (some subcommands need no env vars at all — `init`, `show`, etc.);
        # `alphamo doctor` will flag the missing dep clearly.
        return
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)
        _DOTENV_LOADED_FROM = Path(dotenv_path).resolve()


@click.group()
@click.option(
    "--no-dotenv",
    "no_dotenv",
    is_flag=True,
    default=False,
    help=(
        "Skip the automatic `.env` autoload at CLI startup. Use in CI / "
        "production where process-env variables are set out-of-band and "
        "no `.env` file is expected. By default the CLI looks for `.env` "
        "starting in CWD and walking up the directory tree; existing "
        "environment variables take precedence over file values."
    ),
)
def cli(no_dotenv: bool) -> None:
    """AlphaMo — LLM-driven evolutionary search CLI.

    Quickstart:
      1. cp .env.example .env  &&  $EDITOR .env   # fill in FIREWORKS_API_KEY
      2. alphamo doctor                            # verify environment
      3. alphamo run --generations 30              # launch a production run

    Run `alphamo doctor` if anything looks off — it reports env-var state,
    Python version, dependency availability, and DB / audit path
    writeability with concrete fix suggestions for each gap.
    """
    # Reset the per-invocation `.env` source tracker. The module-level
    # global persists across CLI invocations within the same Python
    # process (test runners, library usage, REPL); each CLI call must
    # report ONLY what THIS invocation loaded, not state leftover from
    # an earlier call.
    global _DOTENV_LOADED_FROM
    _DOTENV_LOADED_FROM = None
    if not no_dotenv:
        _autoload_dotenv()


@cli.command()
@_DB_OPTION
@_AUDIT_OPTION
def doctor(db_path: Path, audit_path: Path) -> None:
    """Pre-flight environment check.

    Reports Python version, dependency availability, env-var state, and
    DB / audit path writeability. Exits 0 on green, 1 on any critical
    issue (missing required key, unwriteable path, wrong Python version),
    2 on warnings only (optional keys absent, etc.).

    Run before `alphamo run` to fail fast at the CLI rather than inside
    the orchestrator. Output is human-readable and stable enough to grep.
    """
    issues: list[str] = []
    warnings: list[str] = []

    click.echo("alphamo doctor — pre-flight check\n")

    # Python version
    py_version = ".".join(str(v) for v in sys.version_info[:3])
    py_ok = sys.version_info >= (3, 11)
    click.echo(f"  Python:       {py_version} {'OK' if py_ok else 'FAIL — requires >=3.11'}")
    if not py_ok:
        issues.append("Python version is below the >=3.11 floor declared in pyproject.toml")

    # Package version
    click.echo(f"  alphamo:      installed {__version__}  ({platform.python_implementation()})")

    # Required deps
    for modname, pip_name in (
        ("dotenv", "python-dotenv"),
        ("sqlalchemy", "sqlalchemy"),
        ("pydantic", "pydantic"),
        ("click", "click"),
        ("anthropic", "anthropic"),
        ("openai", "openai"),
    ):
        try:
            __import__(modname)
            click.echo(f"  dep:          {pip_name:<20} importable  OK")
        except ImportError:
            click.echo(f"  dep:          {pip_name:<20} MISSING     FAIL")
            issues.append(
                f"dependency `{pip_name}` is not importable — run `pip install -e '.[dev]'`"
            )

    # .env source
    if _DOTENV_LOADED_FROM is not None:
        click.echo(f"  .env:         loaded from {_DOTENV_LOADED_FROM}")
    else:
        click.echo("  .env:         not found  (will fall back to process env)")

    # Required env var — FIREWORKS_API_KEY (default Sprint-15 provider routing)
    fireworks_key = os.environ.get("FIREWORKS_API_KEY")
    if fireworks_key:
        masked = fireworks_key[:4] + "…" + fireworks_key[-4:] if len(fireworks_key) > 8 else "<short>"
        click.echo(f"  FIREWORKS_API_KEY: set ({masked})  OK")
    else:
        click.echo("  FIREWORKS_API_KEY: NOT SET  FAIL")
        issues.append(
            "FIREWORKS_API_KEY is required for the default Fireworks-routed "
            "configuration. Copy .env.example to .env, fill in the key, then "
            "re-run (or `export FIREWORKS_API_KEY=...`)."
        )

    # Optional env var — ANTHROPIC_API_KEY
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        masked = anthropic_key[:4] + "…" + anthropic_key[-4:] if len(anthropic_key) > 8 else "<short>"
        click.echo(f"  ANTHROPIC_API_KEY: set ({masked})  OK (optional)")
    else:
        click.echo("  ANTHROPIC_API_KEY: not set  (only needed when HP routes a component to anthropic)")
        warnings.append(
            "ANTHROPIC_API_KEY is unset — fine if all components route via Fireworks (the default)"
        )

    # DB path writeability
    db_parent = db_path.resolve().parent
    if db_parent.exists() and os.access(db_parent, os.W_OK):
        click.echo(f"  DB path:      {db_path}  (parent writeable)  OK")
    else:
        click.echo(f"  DB path:      {db_path}  parent missing or not writeable  FAIL")
        issues.append(
            f"DB path parent directory {db_parent!s} is not writeable — create it or pass --db <path>"
        )

    # Audit path writeability
    audit_parent = audit_path.resolve().parent
    if audit_parent.exists() and os.access(audit_parent, os.W_OK):
        click.echo(f"  Audit path:   {audit_path}  (parent writeable)  OK")
    elif not audit_parent.exists():
        click.echo(f"  Audit path:   {audit_path}  parent will be auto-created  OK")
    else:
        click.echo(f"  Audit path:   {audit_path}  parent not writeable  FAIL")
        issues.append(
            f"Audit path parent directory {audit_parent!s} is not writeable — pass --audit <path>"
        )

    # Summary
    click.echo("")
    if issues:
        click.echo(f"FAIL — {len(issues)} critical issue(s):")
        for issue in issues:
            click.echo(f"  - {issue}")
        if warnings:
            click.echo(f"\nAlso {len(warnings)} warning(s):")
            for w in warnings:
                click.echo(f"  - {w}")
        sys.exit(1)
    if warnings:
        click.echo(f"OK with {len(warnings)} warning(s):")
        for w in warnings:
            click.echo(f"  - {w}")
        sys.exit(2)
    click.echo("OK — all checks passed. Ready to run.")


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
    from alphamo.evaluator import EvaluatorCascade
    from alphamo.proposer import Proposer
    from alphamo.providers.factory import build_provider
    from alphamo.sampler import Sampler

    db = ProgramsDB(_db_url(db_path))
    # Sprint 14: routed through the provider factory. Default is the
    # Fireworks provider (requires FIREWORKS_API_KEY); change here if a
    # one-off `generate` invocation should use a different provider.
    provider = build_provider("fireworks")
    resolved_run_id = _resolve_run_id(db, run_id)

    seeds = Sampler(db, run_id=resolved_run_id).draw(island_id=island_id, k=k_seeds)
    if not seeds:
        raise click.ClickException(
            f"island {island_id} in run {resolved_run_id} is empty — insert candidates first"
        )

    click.echo(f"seeds: {[s.architecture.name for s in seeds]}")
    architecture = Proposer(provider).propose(seeds)
    click.echo(f"proposed: {architecture.name}")

    result = EvaluatorCascade(provider).evaluate(architecture)
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
@click.option(
    "--target-generation",
    "target_generation",
    type=int,
    default=None,
    help=(
        "Sprint 5: target generation for an EXTENDED resume. When combined "
        "with --resume, the resumed run continues from its current latest "
        "generation + 1 through this target (inclusive). Must be strictly "
        "greater than the resumed run's current latest generation. "
        "Requires --resume; errors if used standalone. When --resume is set "
        "but --target-generation is not, --generations is used as the target "
        "(backward-compat with Sprint 4 resume of crashed runs)."
    ),
)
@click.option("--num-islands", "num_islands", type=int, default=8, show_default=True)
@click.option(
    "--milestone-min-generation",
    "milestone_min_generation",
    type=int,
    default=25,
    show_default=True,
    help=(
        "Secondary gate on the milestone trigger — milestone only fires "
        "at generation >= this. Only takes effect when "
        "--curator-pause-enabled is set; otherwise the curator path is "
        "skipped entirely."
    ),
)
@click.option(
    "--curator-pause-enabled/--no-curator-pause-enabled",
    "curator_pause_enabled",
    default=False,
    show_default=True,
    help=(
        "Master switch for the milestone-triggered curator pause-for-"
        "human path. Default is disabled — unattended runs execute "
        "through to the defined generation count. Set to enable human-"
        "review-at-milestones behavior."
    ),
)
@click.option(
    "--candidates-per-generation",
    "candidates_per_generation",
    type=int,
    default=None,
    help=(
        "Sprint parallel-candidates: candidates produced per generation "
        "(one per island, capped at num_islands). Falls through to the "
        "Hyperparameters default (8) when omitted."
    ),
)
@click.option(
    "--max-parallel-candidates",
    "max_parallel_candidates",
    type=int,
    default=None,
    help=(
        "Sprint parallel-candidates: max concurrent pipeline runs per "
        "generation. The Stage 3 intra-candidate fan-out (9 framings @ "
        "4 workers) nests inside this. Falls through to the "
        "Hyperparameters default (4) when omitted."
    ),
)
@click.option(
    "--reset-every",
    "reset_every_generations",
    type=int,
    default=None,
    help=(
        "FunSearch-style island reset cadence in generations. Falls "
        "through to the Hyperparameters default (40) when omitted."
    ),
)
@click.option(
    "--resume",
    "resume_id",
    type=str,
    default=None,
    help="Continue an existing run by id. Skips the in-progress-run detection prompt.",
)
@click.option(
    "--no-resume",
    "no_resume",
    is_flag=True,
    default=False,
    help="Force a fresh run even if a resumable run is detected. Skips the prompt.",
)
@click.option(
    "--force-resume",
    "force_resume",
    is_flag=True,
    default=False,
    help=(
        "Sprint 5: override the stopped_reason block for runs stopped via "
        "`consecutive_failures` or `curator_pause`. Requires --resume; "
        "errors if used standalone."
    ),
)
@_DB_OPTION
@_AUDIT_OPTION
def run(
    generations: int,
    target_generation: int | None,
    num_islands: int,
    milestone_min_generation: int,
    curator_pause_enabled: bool,
    candidates_per_generation: int | None,
    max_parallel_candidates: int | None,
    reset_every_generations: int | None,
    resume_id: str | None,
    no_resume: bool,
    force_resume: bool,
    db_path: Path,
    audit_path: Path,
) -> None:
    """Run a production loop end-to-end with islands, red-team, and curator."""
    from alphamo.context.hyperparams import Hyperparameters
    from alphamo.meta.audit_log import AuditLog
    from alphamo.orchestrator import (
        Orchestrator,
        ResumeIncompatibleError,
    )

    if resume_id is not None and no_resume:
        raise click.ClickException("--resume and --no-resume are mutually exclusive")
    if target_generation is not None and resume_id is None:
        # Pre-empt the auto-detect path picking up a run that --target-generation
        # was implicitly meant to extend; require explicit --resume to bind
        # the target to a specific run.
        raise click.ClickException(
            "--target-generation requires --resume <run_id> — pass the run "
            "you want to extend explicitly"
        )
    if force_resume and resume_id is None:
        raise click.ClickException(
            "--force-resume requires --resume <run_id>"
        )

    db = ProgramsDB(_db_url(db_path))
    audit = AuditLog(audit_path)
    # Sprint 14: pass `client=None` so the orchestrator builds per-component
    # providers from Hyperparameters via the provider factory. Default
    # routing is Fireworks/DeepSeek V4 Flash everywhere; flip individual
    # components via the persisted HP JSON without a code change.
    client = None

    # Sprint 4 + 5: auto-detect-resumable-run prompt path. Skipped when the
    # user passed --resume or --no-resume explicitly. Considers both
    # incomplete (crashed) and extendable (max_generations stop) runs.
    if resume_id is None and not no_resume:
        incomplete = db.incomplete_runs()
        extendable = db.extendable_runs()
        # Pick the most recent resumable candidate. Crashed runs always
        # offered. Extendable runs offered only when --generations would
        # actually extend (i.e., > the run's current latest generation).
        chosen = None
        if incomplete:
            stale = incomplete[0]
            last_gen = db.latest_generation_in_run(stale.run_id)
            click.echo(
                f"WARN: Incomplete (crashed) run detected: {stale.run_id} "
                f"(created {stale.created_at.isoformat()}, "
                f"last completed generation {last_gen})"
            )
            if click.confirm("Resume crashed run?", default=False):
                chosen = stale.run_id
        if chosen is None and extendable:
            done = extendable[0]
            last_gen = db.latest_generation_in_run(done.run_id)
            if generations > last_gen:
                click.echo(
                    f"WARN: Extendable completed run detected: {done.run_id} "
                    f"(completed at generation {last_gen}; "
                    f"--generations={generations} would extend to gen {generations})"
                )
                if click.confirm("Extend completed run?", default=False):
                    chosen = done.run_id
        if chosen is not None:
            resume_id = chosen

    if resume_id is not None:
        try:
            orchestrator = Orchestrator.resume_run(
                db, client, audit, resume_id, force=force_resume
            )
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        except ResumeIncompatibleError as exc:
            raise click.ClickException(
                f"{exc} — start a fresh run with `alphamo run --no-resume`"
            ) from exc

        # Sprint 5: validate target_generation > current latest generation
        # before kicking off run(). Without this guard, the orchestrator
        # would silently exit with zero iterations (start_generation >
        # max_generations -> empty range -> mark complete).
        latest_gen = db.latest_generation_in_run(resume_id)
        effective_target = (
            target_generation if target_generation is not None else generations
        )
        if effective_target <= latest_gen:
            raise click.ClickException(
                f"--target-generation/--generations must be strictly greater "
                f"than the resumed run's current latest generation "
                f"(latest={latest_gen}, requested={effective_target})"
            )
        generations = effective_target
        click.echo(
            f"resuming run {resume_id} from generation {latest_gen + 1} "
            f"through {generations}"
        )
    else:
        # Sprint cli-hp-overrides: fall-through pattern for the parallel-
        # sprint HP fields. Pass only non-None values so the Pydantic
        # default kicks in for omitted flags, keeping CLI and HP defaults
        # from drifting (the HP default IS the source of truth at
        # --help time and at runtime).
        hp_overrides: dict[str, object] = dict(
            num_islands=num_islands,
            milestone_min_generation=milestone_min_generation,
            curator_pause_enabled=curator_pause_enabled,
        )
        if candidates_per_generation is not None:
            hp_overrides["candidates_per_generation"] = candidates_per_generation
        if max_parallel_candidates is not None:
            hp_overrides["max_parallel_candidates"] = max_parallel_candidates
        if reset_every_generations is not None:
            hp_overrides["reset_every_generations"] = reset_every_generations
        hp = Hyperparameters(**hp_overrides)
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
    from alphamo.evaluator import EvaluatorCascade
    from alphamo.handoff import build_handoff
    from alphamo.meta.audit_log import AuditLog
    from alphamo.providers.factory import build_provider

    db = ProgramsDB(_db_url(db_path))
    audit = AuditLog(audit_path)
    # Sprint 14: harvest re-cascade routes through the provider factory.
    # Default is Fireworks; the harvest output is one re-cascade call on
    # the top discovery, so cost is negligible and quality matches the
    # production run's routing.
    cascade = EvaluatorCascade(build_provider("fireworks"))

    resolved_run_id = run_id or db.latest_run_id()
    if resolved_run_id is None:
        raise click.ClickException("no runs in this DB — nothing to harvest")

    handoff = build_handoff(
        db, audit, cascade, num_islands=num_islands, run_id=resolved_run_id
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(handoff.model_dump_json(indent=2))
    click.echo(f"run: {resolved_run_id}")
    if handoff.winning_architecture is not None:
        w = handoff.winning_architecture
        click.echo(
            f"winner: {w.spec.name} "
            f"(island {w.island_of_origin}, generation {w.generation}, "
            f"fitness {w.fitness:.4f})"
        )
    else:
        click.echo(
            "winner: none — no generated candidate exceeded any seed baseline"
        )
    click.echo(
        f"top generated discoveries: {len(handoff.top_generated_discoveries)} | "
        f"seed baselines: {len(handoff.seed_baselines)} | "
        f"drift log: {len(handoff.drift_log)} entries | "
        f"eval count: {handoff.verification_trail.eval_count}"
    )
    if handoff.no_breakthrough_this_run:
        click.echo(
            "no_breakthrough_this_run: TRUE — see parent_goal_alignment for context"
        )
    click.echo(f"wrote {out_path}")


def _format_concern_lines(concerns: list, max_per_severity: int = 3) -> list[str]:
    """Render Stage 4 concerns into stdout-friendly lines, capped to keep
    the output readable. Up to `max_per_severity` shown per severity bucket.
    """
    by_severity: dict[str, list] = {"high": [], "medium": [], "low": []}
    for c in concerns:
        by_severity[c.severity.value].append(c)
    lines: list[str] = []
    for sev in ("high", "medium", "low"):
        bucket = by_severity[sev]
        if not bucket:
            continue
        lines.append(f"    {sev.upper()} concerns ({len(bucket)}):")
        for c in bucket[:max_per_severity]:
            claim = c.claim if len(c.claim) <= 220 else c.claim[:217] + "..."
            lines.append(f"      [{c.framing}] {claim}")
            falsifier = c.falsification_condition
            if len(falsifier) > 200:
                falsifier = falsifier[:197] + "..."
            lines.append(f"        falsifier: {falsifier}")
        if len(bucket) > max_per_severity:
            lines.append(
                f"      … +{len(bucket) - max_per_severity} more {sev.upper()} concerns"
            )
    return lines


def _print_seed_cascade_result(name: str, result) -> None:
    """Verbose stdout report of every stage's output for one seed."""
    import click

    click.echo(f"\n=== {name} ===")

    if result.stage1 is not None:
        s1 = result.stage1
        click.echo(
            f"  Stage 1 (Haiku — feasibility + middle-class):\n"
            f"    feasibility            = {s1.feasibility:.4f}\n"
            f"    middle_class_accessible = {s1.middle_class_accessible}\n"
            f"    reasoning: {s1.reasoning}"
        )
    if result.early_exit:
        click.echo(f"  EARLY EXIT: {result.early_exit}")

    if result.stage2 is not None:
        s2 = result.stage2
        click.echo(
            f"  Stage 2 (Sonnet — structural criteria):\n"
            f"    one_person_threshold     = {s2.one_person_threshold:.4f}\n"
            f"    billion_dollar_potential = {s2.billion_dollar_potential:.4f}\n"
            f"    labor_separation         = {s2.labor_separation:.4f}\n"
            f"    structural (aggregate)   = {s2.structural:.4f}\n"
            f"    reasoning: {s2.reasoning}"
        )

    if result.stage3 is not None:
        s3 = result.stage3
        framings_seen = sorted({c.framing for c in s3.concerns})
        n_high = sum(1 for c in s3.concerns if c.severity.value == "high")
        n_med = sum(1 for c in s3.concerns if c.severity.value == "medium")
        n_low = sum(1 for c in s3.concerns if c.severity.value == "low")
        click.echo(
            f"  Stage 3 (Opus — adversarial scrutiny across framings):\n"
            f"    robustness    = {s3.robustness:.4f}\n"
            f"    concerns      = {len(s3.concerns)} (high={n_high} medium={n_med} low={n_low})\n"
            f"    framings_with_concerns = {framings_seen}\n"
            f"    reasoning: {s3.reasoning}"
        )
        for line in _format_concern_lines(s3.concerns):
            click.echo(line)

    final = result.scores
    click.echo(
        f"  Final aggregate scores:\n"
        f"    feasibility            = {final.feasibility:.4f}\n"
        f"    structural             = {final.structural:.4f}\n"
        f"    robustness             = "
        + (f"{final.robustness:.4f}" if final.robustness is not None else "None")
        + "\n"
        f"    middle_class_accessible = {final.middle_class_accessible}"
    )



@cli.command("backfill-stage4")
@click.option(
    "--decay-k",
    "decay_k",
    type=float,
    default=0.50,
    show_default=True,
    help="Exponential-decay rate for the recomputed robustness scores.",
)
@_DB_OPTION
@_AUDIT_OPTION
def backfill_stage4(decay_k: float, db_path: Path, audit_path: Path) -> None:
    """Sprint 1 (Bug 1+2): populate stage4_findings + recomputed robustness
    on existing candidates from audit-log stage4_routine events.

    Idempotent — re-running skips candidates whose stage4_findings is
    already populated. Used to salvage run-006 (and any other pre-Sprint-1
    run) without re-issuing LLM calls.
    """
    from alphamo.meta.audit_log import AuditLog

    db = ProgramsDB(_db_url(db_path))
    audit = AuditLog(audit_path)
    events = audit.read_all()
    stats = db.backfill_stage4_from_audit(events, decay_k=decay_k)
    click.echo(
        f"updated={stats['updated']} "
        f"skipped_existing={stats['skipped_existing']} "
        f"skipped_missing={stats['skipped_missing']} "
        f"skipped_non_stage4={stats['skipped_non_stage4']}"
    )


if __name__ == "__main__":
    cli()
