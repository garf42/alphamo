"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from alphamo.database import ProgramsDB


@pytest.fixture()
def db(tmp_path: Path) -> ProgramsDB:
    """A fresh Programs DB backed by a per-test temp SQLite file."""
    return ProgramsDB(f"sqlite:///{tmp_path / 'alphamo.db'}")
