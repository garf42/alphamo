"""Sprint 16: launch-surface tests.

Pins the canonical "how do I launch AlphaMo?" answer:

  1. The `alphamo` CLI auto-loads `.env` from CWD or any ancestor directory
     without overriding existing process-env vars.
  2. The `alphamo doctor` subcommand fails fast (exit 1) when required
     env vars are missing, succeeds (exit 0) when everything's in place,
     and reports warnings (exit 2) for non-critical issues.
  3. The provider factory's `FIREWORKS_API_KEY` error message points
     operators at `.env.example` and `alphamo doctor` rather than just
     saying "load it via terminal."
  4. `.env.example` and `Makefile` exist at the repo root.

No live API calls; the doctor subcommand never hits a provider.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from alphamo.main import cli


_REPO_ROOT = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------- repo-level


def test_env_example_exists_at_repo_root():
    """The `.env.example` template is the canonical reference for which
    environment variables AlphaMo needs. It MUST live at the repo root
    so a fresh clone surfaces it via `ls`."""
    path = _REPO_ROOT / ".env.example"
    assert path.exists()
    content = path.read_text()
    assert "FIREWORKS_API_KEY" in content
    assert "ANTHROPIC_API_KEY" in content


def test_makefile_exists_with_doctor_and_run_targets():
    """The Makefile is the discoverability surface for common workflows.
    The two targets that must always exist are `doctor` (pre-flight) and
    `run` (the canonical launch invocation)."""
    path = _REPO_ROOT / "Makefile"
    assert path.exists()
    content = path.read_text()
    assert "doctor:" in content
    assert "run:" in content
    assert "install-dev:" in content


def test_pyproject_declares_python_dotenv_dependency():
    """python-dotenv backs the CLI's `.env` autoload. It must be in
    pyproject's runtime dependencies (not dev-only) since the autoload
    runs on every `alphamo` invocation regardless of test context."""
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text()
    assert re.search(r'"python-dotenv', pyproject)


# ----------------------------------------------------------------- .env autoload


def test_cli_autoloads_dotenv_from_cwd(tmp_path, monkeypatch):
    """Drop a `.env` in a temp dir, cd into it, invoke `alphamo doctor`,
    and confirm the file's FIREWORKS_API_KEY value was loaded into the
    process environment (visible to doctor's check)."""
    env_file = tmp_path / ".env"
    env_file.write_text("FIREWORKS_API_KEY=fw_via_autoload_12345abcdef\n")

    monkeypatch.chdir(tmp_path)
    # Ensure the variable is NOT in the process env to start — otherwise
    # the "override=False" semantics would mask whether autoload fired.
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    # Doctor exits 2 (warnings only) on a green Fireworks + missing
    # Anthropic config — that's the expected state when only
    # FIREWORKS_API_KEY is set via .env.
    assert result.exit_code in (0, 2), (
        f"doctor unexpectedly failed; output:\n{result.output}"
    )
    assert "loaded from" in result.output
    assert str(env_file.resolve()) in result.output
    assert "FIREWORKS_API_KEY: set" in result.output


def test_cli_dotenv_does_not_override_existing_env_vars(tmp_path, monkeypatch):
    """`.env` autoload uses python-dotenv's override=False so a
    process-env value (set out-of-band by CI / k8s / shell export)
    takes precedence over a `.env` file value. This is the invariant
    that lets the same code path work in dev (where .env is the source
    of truth) and in production (where the .env file may not exist or
    may carry stale values)."""
    env_file = tmp_path / ".env"
    env_file.write_text("FIREWORKS_API_KEY=from_dotenv_should_lose\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FIREWORKS_API_KEY", "from_process_env_should_win")

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    # Doctor masks the key — the masked form starts with the first
    # 4 chars and ends with the last 4. Process-env value wins.
    assert "from" in result.output  # head of "from_process_env_should_win"
    assert "_win" in result.output  # tail of the same string
    # The .env value's distinctive substring is not present.
    assert "_lose" not in result.output


def test_cli_no_dotenv_flag_skips_autoload(tmp_path, monkeypatch):
    """`--no-dotenv` lets CI / production opt out of the autoload
    entirely. Useful when `.env` shouldn't exist (and its absence
    shouldn't cost a filesystem walk) or when the operator wants
    auditable control over which env vars are visible."""
    env_file = tmp_path / ".env"
    env_file.write_text("FIREWORKS_API_KEY=from_dotenv_must_not_load\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["--no-dotenv", "doctor"])
    # FIREWORKS_API_KEY was not loaded → doctor reports it missing.
    assert "FIREWORKS_API_KEY: NOT SET" in result.output
    assert "loaded from" not in result.output


# ----------------------------------------------------------------- doctor


def test_doctor_fails_loudly_when_fireworks_key_missing(monkeypatch, tmp_path):
    """The whole point of `alphamo doctor` is fail-fast on the env-var
    error that would otherwise surface deep inside `Orchestrator.__init__`.
    Exit code 1 (critical), human-readable issue list, fix-suggestion
    pointing at `.env.example`."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["--no-dotenv", "doctor"])
    assert result.exit_code == 1
    assert "FIREWORKS_API_KEY: NOT SET" in result.output
    assert "FAIL" in result.output
    assert ".env.example" in result.output


def test_doctor_succeeds_with_warnings_when_only_fireworks_key_set(
    monkeypatch, tmp_path
):
    """The default Sprint-15 routing sends every component through
    Fireworks, so FIREWORKS_API_KEY is sufficient. ANTHROPIC_API_KEY
    being unset is a warning (exit 2), not a failure (exit 1)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw_key_for_test_only_no_real_calls")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["--no-dotenv", "doctor"])
    assert result.exit_code == 2
    assert "FIREWORKS_API_KEY: set" in result.output
    assert "ANTHROPIC_API_KEY: not set" in result.output
    assert "OK with 1 warning" in result.output


def test_doctor_returns_zero_when_both_keys_set(monkeypatch, tmp_path):
    """Exit 0 only when every required AND every optional env var is
    set AND every dep is importable AND the paths are writeable."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw_key_for_test_only_no_real_calls")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk_ant_test_only_no_real_calls")

    runner = CliRunner()
    result = runner.invoke(cli, ["--no-dotenv", "doctor"])
    assert result.exit_code == 0
    assert "OK — all checks passed" in result.output


def test_doctor_masks_api_keys_in_output(monkeypatch, tmp_path):
    """The doctor's output is fine to paste into a debug channel —
    keys must be masked (first 4 + … + last 4 chars). Pin the
    masking so a future refactor doesn't accidentally print the raw
    secret."""
    monkeypatch.chdir(tmp_path)
    secret = "fw_supersecret_value_abcdefgh_12345"
    monkeypatch.setenv("FIREWORKS_API_KEY", secret)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["--no-dotenv", "doctor"])
    assert secret not in result.output  # full secret never appears
    # Masked form has head and tail visible.
    assert secret[:4] in result.output
    assert secret[-4:] in result.output


def test_doctor_reports_dotenv_source(monkeypatch, tmp_path):
    """When `.env` IS loaded, doctor must say so AND name the path so
    operators can tell `printenv` and `.env` apart without guessing."""
    env_file = tmp_path / ".env"
    env_file.write_text("FIREWORKS_API_KEY=fw_from_dotenv_for_source_test\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert "loaded from" in result.output
    assert str(env_file.resolve()) in result.output


# ----------------------------------------------------------------- factory error


def test_factory_error_points_at_dotenv_and_doctor(monkeypatch):
    """When `build_provider("fireworks")` blows up on missing key, the
    error message must reference the three fix paths
    (`.env`, `export`, HP override) and the `alphamo doctor` checker.
    Pre-Sprint-16 it said only 'load it via terminal'."""
    from alphamo.providers.factory import build_provider, reset_provider_cache

    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    reset_provider_cache()

    with pytest.raises(RuntimeError) as exc_info:
        build_provider("fireworks")
    msg = str(exc_info.value)
    assert ".env" in msg
    assert "alphamo doctor" in msg
    assert "ANTHROPIC_API_KEY" in msg  # HP-override fix path mentioned


# ----------------------------------------------------------------- README quickstart


def test_readme_documents_doctor_and_run_quickstart():
    """The README is the canonical text answer to "how do I launch?".
    Pin that doctor + run appear in the quickstart and that the env-var
    table mentions FIREWORKS_API_KEY."""
    readme = (_REPO_ROOT / "README.md").read_text()
    assert "alphamo doctor" in readme
    assert "alphamo run" in readme
    assert "FIREWORKS_API_KEY" in readme
    assert ".env.example" in readme
