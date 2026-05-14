"""Live calibration test for the LLM-backed cascade.

This is the load-bearing phase-02 test from the architecture's build
sequence:

    "Validate by scoring the manual exemplars — known exemplars must score
    high; obvious non-exemplars (wealth-required configurations) must
    score low. This is the load-bearing test."

Skipped by default — set both ANTHROPIC_API_KEY and RUN_LIVE_TESTS=1 to
run. Each invocation costs a few cents (3 exemplars × 3 stages + 2 foils
× 1 stage with Haiku/Sonnet/Opus).
"""

from __future__ import annotations

import os

import pytest

from alphamo.evaluator import EvaluatorCascade
from tests.fixtures.exemplars import EXEMPLARS, FOILS

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="set ANTHROPIC_API_KEY and RUN_LIVE_TESTS=1 to run live cascade tests",
    ),
]


@pytest.fixture(scope="module")
def cascade() -> EvaluatorCascade:
    return EvaluatorCascade()


@pytest.mark.parametrize("fixture", EXEMPLARS, ids=lambda f: f.architecture.name)
def test_exemplar_scores_above_threshold(cascade: EvaluatorCascade, fixture) -> None:
    """Known exemplars must score 0.7+ on every axis and pass middle-class."""
    result = cascade.evaluate(fixture.architecture)

    assert result.early_exit is None, (
        f"{fixture.architecture.name} short-circuited at {result.early_exit}: "
        f"feasibility={result.scores.feasibility:.2f} "
        f"structural={result.scores.structural:.2f}"
    )
    assert result.scores.middle_class_accessible is True
    assert result.scores.feasibility >= 0.7, result.stage1.reasoning
    assert result.scores.structural >= 0.7, result.stage2 and result.stage2.reasoning
    assert result.scores.exemplar_similarity >= 0.7, (
        result.stage3 and result.stage3.reasoning
    )


@pytest.mark.parametrize("fixture", FOILS, ids=lambda f: f.architecture.name)
def test_foils_fail_middle_class_filter(cascade: EvaluatorCascade, fixture) -> None:
    """Wealth-required configurations must fail the middle-class filter."""
    result = cascade.evaluate(fixture.architecture)

    assert result.scores.middle_class_accessible is False, result.stage1.reasoning
    assert result.early_exit == "middle_class_filter"
    assert result.scores.structural == 0.0
    assert result.scores.exemplar_similarity == 0.0
