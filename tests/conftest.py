"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from alphamo.database import ProgramsDB


@pytest.fixture()
def db(tmp_path: Path) -> ProgramsDB:
    """A fresh Programs DB backed by a per-test temp SQLite file."""
    return ProgramsDB(f"sqlite:///{tmp_path / 'alphamo.db'}")


@pytest.fixture()
def default_run(db: ProgramsDB) -> str:
    """A run row for tests that do direct db.insert without an orchestrator.

    Production code requires run_id on every insert; tests that exercise
    DB ops directly need a run to charge their inserts against. This
    fixture provides one with empty hyperparameters and 'test' versions.
    """
    return db.create_run(
        hyperparameters={},
        parent_goal_version="test",
        verifier_version="test",
        notes="default test run (from conftest)",
    )
