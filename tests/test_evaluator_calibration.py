"""Phase 01 calibration test.

Manually inserts the Satoshi/Rowling/Levels exemplars (plus two foils) and
verifies that top-k retrieval returns them in the expected order. This is the
test that gates phase 02 of the build sequence — if it fails, the DB is
miscalibrated and nothing downstream can be trusted.
"""

from __future__ import annotations

from alphamo.database import ProgramsDB
from tests.fixtures.exemplars import (
    ALL_FIXTURES,
    EXEMPLARS,
    FOILS,
    SATOSHI_FIXTURE,
)


def _names(rows) -> list[str]:
    return [row.architecture_spec["name"] for row in rows]


def test_insert_returns_id_and_positive_fitness(db: ProgramsDB, default_run: str) -> None:
    new_id = db.insert(
        SATOSHI_FIXTURE.architecture, SATOSHI_FIXTURE.scores, run_id=default_run
    )
    assert isinstance(new_id, int) and new_id > 0
    row = db.get(new_id)
    assert row.fitness > 0
    assert row.architecture_spec["name"] == "Satoshi"
    assert row.run_id == default_run


def test_top_k_returns_exemplars_in_order(db: ProgramsDB, default_run: str) -> None:
    for fixture in ALL_FIXTURES:
        db.insert(fixture.architecture, fixture.scores, run_id=default_run)

    top3 = db.top_k_in_island(island_id=0, k=3)

    assert _names(top3) == ["Satoshi", "Rowling", "Levels"]
    assert top3[0].fitness > top3[1].fitness > top3[2].fitness


def test_foils_filtered_by_middle_class_constraint(
    db: ProgramsDB, default_run: str
) -> None:
    ids = {
        fixture.architecture.name: db.insert(
            fixture.architecture, fixture.scores, run_id=default_run
        )
        for fixture in ALL_FIXTURES
    }

    for foil in FOILS:
        assert db.get(ids[foil.architecture.name]).fitness == 0.0

    for exemplar in EXEMPLARS:
        assert db.get(ids[exemplar.architecture.name]).fitness > 0.0

    top5 = db.top_k_in_island(island_id=0, k=5)
    assert _names(top5)[:3] == ["Satoshi", "Rowling", "Levels"]
    assert set(_names(top5)[3:]) == {f.architecture.name for f in FOILS}
