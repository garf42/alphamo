"""Live end-to-end test for the sampler + proposer pipeline.

Skipped by default — set both ANTHROPIC_API_KEY and RUN_LIVE_TESTS=1 to run.
Costs approximately one Opus call (~$0.05) plus one cascade evaluation.
"""

from __future__ import annotations

import os

import pytest

from alphamo.evaluator import EvaluatorCascade
from alphamo.proposer import Proposer
from alphamo.sampler import Sampler
from alphamo.schemas import Architecture
from tests.fixtures.exemplars import EXEMPLARS

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="set ANTHROPIC_API_KEY and RUN_LIVE_TESTS=1 to run live proposer tests",
    ),
]


@pytest.fixture(scope="module")
def anthropic_client():
    import anthropic

    # max_retries=3 — match production client construction (see Sprint
    # 4 commit) so live test fixtures don't fail spuriously on transient
    # API errors.
    return anthropic.Anthropic(max_retries=3)


def test_single_generation_step(anthropic_client, db, default_run):
    """Draw seeds, propose a new architecture, evaluate — must not raise."""
    for fixture in EXEMPLARS:
        db.insert(fixture.architecture, fixture.scores, run_id=default_run)

    seeds = Sampler(db, run_id=default_run).draw(island_id=0, k=2)
    assert len(seeds) > 0, "no seeds drawn — island seeding failed"

    architecture = Proposer(anthropic_client).propose(seeds)
    assert isinstance(architecture, Architecture)
    assert architecture.name
    assert architecture.summary
    assert architecture.value_chain
    assert architecture.capture_mechanism
    assert architecture.entry_resources

    result = EvaluatorCascade(anthropic_client).evaluate(architecture)
    assert result.stage1 is not None
    assert 0.0 <= result.scores.feasibility <= 1.0
