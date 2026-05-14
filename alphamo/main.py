"""AlphaMo CLI entry point.

Phase 01 surface: init / insert / query / show.
Phase 03 surface: generate — draw seeds, propose, evaluate, insert.
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


def _db_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


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
    new_id = db.insert(
        architecture, scores, island_id=island_id, generation=generation
    )
    row = db.get(new_id)
    click.echo(f"inserted id={new_id} fitness={row.fitness:.3f}")


@cli.command()
@click.option("--island", "island_id", type=int, default=0, show_default=True)
@click.option("--k", type=int, default=5, show_default=True)
@_DB_OPTION
def query(island_id: int, k: int, db_path: Path) -> None:
    """Print top-k candidates in an island, highest fitness first."""
    db = ProgramsDB(_db_url(db_path))
    rows = db.top_k_in_island(island_id=island_id, k=k)
    if not rows:
        click.echo(f"(no candidates in island {island_id})")
        return
    click.echo(f"{'id':>4}  {'fitness':>8}  name")
    click.echo("-" * 40)
    for row in rows:
        name = row.architecture_spec.get("name", "?")
        click.echo(f"{row.id:>4}  {row.fitness:>8.3f}  {name}")


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
@_DB_OPTION
def generate(island_id: int, k_seeds: int, generation: int, db_path: Path) -> None:
    """Draw seeds from an island, propose a new candidate, evaluate, and insert."""
    import anthropic

    from alphamo.evaluator import EvaluatorCascade
    from alphamo.proposer import Proposer
    from alphamo.sampler import Sampler

    db = ProgramsDB(_db_url(db_path))
    client = anthropic.Anthropic()

    seeds = Sampler(db).draw(island_id=island_id, k=k_seeds)
    if not seeds:
        raise click.ClickException(
            f"island {island_id} is empty — insert some candidates first"
        )

    click.echo(f"seeds: {[s.name for s in seeds]}")
    architecture = Proposer(client).propose(seeds)
    click.echo(f"proposed: {architecture.name}")

    result = EvaluatorCascade(client).evaluate(architecture)
    new_id = db.insert(
        architecture,
        result.scores,
        island_id=island_id,
        generation=generation,
    )
    row = db.get(new_id)
    click.echo(f"inserted id={new_id} fitness={row.fitness:.3f}")
    if result.early_exit:
        click.echo(f"early exit: {result.early_exit}")


if __name__ == "__main__":
    cli()
