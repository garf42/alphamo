"""Sprint cli-hp-overrides: CLI flags for parallel-sprint HP fields.

Pins:
  1. `alphamo run --help` surfaces the three new flags
     (--candidates-per-generation, --max-parallel-candidates, --reset-every)
     so operators can discover them.
  2. When provided, the flags override the corresponding HP fields on
     the persisted run row.
  3. When omitted, the flags fall through to the Hyperparameters
     defaults — the persisted run row carries the HP default, not a
     stale hardcoded CLI default.

No LLM calls. The test invokes the CLI through Click's CliRunner with
a mocked Orchestrator.run() so the production loop never starts; we
verify the orchestrator was constructed with the expected hp values.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from alphamo.context.hyperparams import Hyperparameters
from alphamo.database import ProgramsDB
from alphamo.main import cli


# ----------------------------------------------------------------- --help


def test_run_help_lists_three_parallel_sprint_flags():
    """All three flags must be visible in --help with their HP-default
    fallback documented. Operators discover these via the help text."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--no-dotenv", "run", "--help"])
    assert result.exit_code == 0, result.output
    assert "--candidates-per-generation" in result.output
    assert "--max-parallel-candidates" in result.output
    assert "--reset-every" in result.output
    # HP-default fall-through documented for each.
    assert "default (8)" in result.output  # candidates_per_generation
    assert "default (4)" in result.output  # max_parallel_candidates
    assert "default (40)" in result.output  # reset_every_generations


# ----------------------------------------------------------------- flag flow-through


def _run_cli_with_no_op_orchestrator(
    tmp_path: Path,
    flags: list[str],
):
    """Invoke `alphamo run` with the production loop short-circuited.

    Monkeypatches `Orchestrator.run` to a no-op AND
    `_build_component_providers` to return MagicMocks, so the CLI
    builds the Hyperparameters + Orchestrator without needing a real
    Fireworks API key. We then inspect the persisted run row.

    Returns (cli_result, persisted_hp_dict).
    """
    from unittest.mock import MagicMock

    from alphamo import orchestrator as orch_mod
    from alphamo.orchestrator import Orchestrator, RunResult

    db_path = tmp_path / "alphamo.db"
    audit_path = tmp_path / "audit.jsonl"

    # Mock the provider factory output — each of the 5 components gets
    # a MagicMock provider so the Orchestrator constructor completes
    # without touching the network.
    def fake_build_providers(client, hp):
        m = MagicMock()
        return (m, m, m, m, m)

    runner = CliRunner()
    with (
        patch.object(orch_mod, "_build_component_providers", fake_build_providers),
        patch.object(Orchestrator, "run", lambda self, max_generations: RunResult()),
    ):
        # --no-resume forces a fresh run so we exercise the HP-build
        # branch (and avoid the auto-detect prompt path).
        result = runner.invoke(
            cli,
            [
                "--no-dotenv", "run",
                "--no-resume",
                "--generations", "1",
                "--db", str(db_path),
                "--audit", str(audit_path),
            ]
            + flags,
        )
    assert result.exit_code == 0, result.output

    # Pick up the freshly-created run row and read its persisted HP.
    db = ProgramsDB(f"sqlite:///{db_path}")
    runs = db.list_runs()
    assert len(runs) == 1
    return result, runs[0].hyperparameters


def test_omitting_flags_falls_through_to_hp_defaults(tmp_path):
    """When none of the three flags are provided, the persisted run
    must carry the Hyperparameters() defaults — verifying the
    fall-through path (rather than a stale CLI-side hardcoded
    default that could drift)."""
    _, persisted_hp = _run_cli_with_no_op_orchestrator(tmp_path, [])
    defaults = Hyperparameters()
    assert persisted_hp["candidates_per_generation"] == defaults.candidates_per_generation
    assert persisted_hp["max_parallel_candidates"] == defaults.max_parallel_candidates
    assert persisted_hp["reset_every_generations"] == defaults.reset_every_generations


def test_candidates_per_generation_flag_overrides_hp_default(tmp_path):
    _, persisted_hp = _run_cli_with_no_op_orchestrator(
        tmp_path, ["--candidates-per-generation", "4"]
    )
    assert persisted_hp["candidates_per_generation"] == 4


def test_max_parallel_candidates_flag_overrides_hp_default(tmp_path):
    _, persisted_hp = _run_cli_with_no_op_orchestrator(
        tmp_path, ["--max-parallel-candidates", "2"]
    )
    assert persisted_hp["max_parallel_candidates"] == 2


def test_reset_every_flag_overrides_hp_default(tmp_path):
    """The CLI flag short-name `--reset-every` maps to the longer HP
    field `reset_every_generations`."""
    _, persisted_hp = _run_cli_with_no_op_orchestrator(
        tmp_path, ["--reset-every", "20"]
    )
    assert persisted_hp["reset_every_generations"] == 20


def test_all_three_flags_combined(tmp_path):
    """Mixed overrides: each non-None flag wins, omitted fields still
    fall through. Pin the realistic launch shape."""
    _, persisted_hp = _run_cli_with_no_op_orchestrator(
        tmp_path,
        [
            "--candidates-per-generation", "6",
            "--max-parallel-candidates", "3",
            "--reset-every", "30",
        ],
    )
    assert persisted_hp["candidates_per_generation"] == 6
    assert persisted_hp["max_parallel_candidates"] == 3
    assert persisted_hp["reset_every_generations"] == 30
    # Untouched fields still match HP defaults (sanity).
    defaults = Hyperparameters()
    assert persisted_hp["num_islands"] == defaults.num_islands
