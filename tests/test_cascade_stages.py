"""Per-stage output-error tests for the cascade.

The cascade stage functions previously returned `response.parsed_output`
without a None check and would crash inside EvaluatorCascade if the model
ever returned no parseable JSON or if the SDK raised pydantic.ValidationError
on truncation. These tests pin the new behaviour: each stage raises its
component-specific subclass of LLMOutputError, which the orchestrator's
existing `except LLMOutputError` already handles.

Sprint 2 redesign: the legacy Stage 3 (exemplar similarity) was retired,
so only Stage 1 and Stage 2 have dedicated parse-time error tests here.
Adversarial scrutiny (now conceptually Stage 3, code-named
stage4_adversarial) has its own dedicated test file.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import (
    Stage1OutputError,
    Stage2OutputError,
)
from alphamo.evaluator.stage1_feasibility import stage1_feasibility
from alphamo.evaluator.stage2_structured import stage2_structured
from alphamo.schemas.findings import Stage1Finding, Stage2Finding
from tests.fixtures.exemplars import SATOSHI_FIXTURE
from tests.fixtures.parsed_message import (
    FakeContentBlock,
    FakeParsedMessage,
    make_truncation_error,
)


def _client_returning(parsed_output) -> MagicMock:
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(parsed_output)
    return client


def test_stage1_returns_parsed_output_on_success():
    finding = Stage1Finding(
        feasibility=0.9, middle_class_accessible=True, reasoning="ok"
    )
    result = stage1_feasibility(
        SATOSHI_FIXTURE.architecture, _client_returning(finding)
    )
    assert isinstance(result, Stage1Finding)
    assert result.feasibility == 0.9


def test_stage1_raises_when_parsed_is_none():
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        parsed_output=None,
        stop_reason="refusal",
        content=[FakeContentBlock("text")],
    )
    with pytest.raises(Stage1OutputError) as exc_info:
        stage1_feasibility(SATOSHI_FIXTURE.architecture, client)
    assert exc_info.value.stop_reason == "refusal"


def test_stage1_raises_on_truncated_json():
    client = MagicMock()
    client.messages.parse.side_effect = make_truncation_error()
    with pytest.raises(Stage1OutputError) as exc_info:
        stage1_feasibility(SATOSHI_FIXTURE.architecture, client)
    assert exc_info.value.stop_reason == "parse_error"


def test_stage2_returns_parsed_output_on_success():
    """Sprint Stage 2 PAJAMA: the function now returns evidence (no
    structural float). Verify that the call-side wiring still returns
    the parsed Pydantic model verbatim — the cascade is what runs
    compute_structural on it later. Asserting on a few representative
    evidence fields proves the model was correctly threaded through."""
    from tests.fixtures.stage2_evidence import passing_stage2_finding
    from alphamo.schemas.findings import AutomationPlausibility, TAMEstimate

    finding = passing_stage2_finding(reasoning="cascade-stages unit test")
    result = stage2_structured(
        SATOSHI_FIXTURE.architecture, _client_returning(finding)
    )
    assert isinstance(result, Stage2Finding)
    # Evidence-field round-trip checks (representative subset).
    assert result.automation_plausibility == AutomationPlausibility.REQUIRES_CUSTOM_ENGINEERING
    assert result.tam_estimate == TAMEstimate.OVER_100B
    assert result.one_person_operable is True
    assert result.reasoning == "cascade-stages unit test"


def test_stage2_raises_when_parsed_is_none():
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        parsed_output=None, stop_reason="max_tokens"
    )
    with pytest.raises(Stage2OutputError):
        stage2_structured(SATOSHI_FIXTURE.architecture, client)


def test_stage2_raises_on_truncated_json():
    client = MagicMock()
    client.messages.parse.side_effect = make_truncation_error()
    with pytest.raises(Stage2OutputError) as exc_info:
        stage2_structured(SATOSHI_FIXTURE.architecture, client)
    assert exc_info.value.stop_reason == "parse_error"


def test_stage_errors_are_subclasses_of_llm_output_error():
    """Orchestrator catches LLMOutputError; stage errors must inherit from it."""
    from alphamo.errors import LLMOutputError

    assert issubclass(Stage1OutputError, LLMOutputError)
    assert issubclass(Stage2OutputError, LLMOutputError)
