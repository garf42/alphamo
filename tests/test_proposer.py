"""Unit tests for the LLM proposer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import ProposerOutputError
from alphamo.evaluator._common import OPUS_MODEL
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from tests.fixtures.exemplars import ROWLING_FIXTURE, SATOSHI_FIXTURE
from tests.fixtures.parsed_message import (
    FakeContentBlock,
    FakeParsedMessage,
    make_truncation_error,
)


def _fake_architecture() -> Architecture:
    return Architecture(
        name="Test candidate",
        summary="A test architecture.",
        value_chain="Test value chain.",
        capture_mechanism="Test capture mechanism.",
        entry_resources="Test entry resources.",
    )


def _client_returning(parsed_output) -> MagicMock:
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(parsed_output)
    return client


def test_propose_returns_architecture():
    client = _client_returning(_fake_architecture())
    result = Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    assert isinstance(result, Architecture)
    assert result.name == "Test candidate"


def test_propose_passes_seeds_in_user_message():
    client = _client_returning(_fake_architecture())
    Proposer(client).propose([SATOSHI_FIXTURE.architecture, ROWLING_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    user_content = kwargs["messages"][0]["content"]
    assert "Satoshi" in user_content
    assert "Rowling" in user_content


def test_propose_uses_opus_model_by_default():
    client = _client_returning(_fake_architecture())
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == OPUS_MODEL


def test_propose_includes_adaptive_thinking():
    client = _client_returning(_fake_architecture())
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["thinking"] == {"type": "adaptive"}


def test_propose_sets_output_format_to_architecture():
    client = _client_returning(_fake_architecture())
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["output_format"] is Architecture


def test_propose_model_can_be_overridden():
    client = _client_returning(_fake_architecture())
    Proposer(client, model="claude-haiku-4-5").propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == "claude-haiku-4-5"


def test_propose_raises_proposer_output_error_when_parsed_is_none():
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        parsed_output=None,
        stop_reason="refusal",
        content=[FakeContentBlock("text"), FakeContentBlock("tool_use")],
    )
    with pytest.raises(ProposerOutputError) as exc_info:
        Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    assert exc_info.value.stop_reason == "refusal"
    assert exc_info.value.content_block_types == ["text", "tool_use"]


def test_propose_raises_proposer_output_error_on_truncated_json():
    """SDK-side pydantic.ValidationError (truncation) must surface as ProposerOutputError."""
    client = MagicMock()
    client.messages.parse.side_effect = make_truncation_error()
    with pytest.raises(ProposerOutputError) as exc_info:
        Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    assert exc_info.value.stop_reason == "parse_error"
    assert "validation failed" in exc_info.value.detail
    assert exc_info.value.__cause__ is not None


# ----------------------------------------------------------- Phase 2 Change 1:
# per-dimension scores rendered into the proposer prompt (AlphaEvolve §2.2).


def _seed(arch_fixture, fitness: float = 0.9) -> "Seed":
    """Build a Seed record from a test fixture."""
    from alphamo.sampler import Seed

    return Seed(
        architecture=arch_fixture.architecture,
        scores=arch_fixture.scores,
        fitness=fitness,
    )


def test_propose_renders_per_dimension_scores_in_prompt():
    """Each seed must appear with a score header (AlphaEvolve §2.2 / Fig 3b)."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    seeds = [_seed(SATOSHI_FIXTURE), _seed(ROWLING_FIXTURE)]
    Proposer(client).propose(seeds)

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    # A score header line precedes each seed's architecture content.
    assert "Scores —" in user_content
    # Each per-dimension score appears as a labeled value.
    for axis in (
        "feasibility:",
        "structural:",
        "exemplar_similarity:",
        "middle_class_accessible:",
        "fitness:",
    ):
        assert axis in user_content, f"missing score axis: {axis}"
    # Verify the actual values for Satoshi appear in the prompt.
    s = SATOSHI_FIXTURE.scores
    assert f"feasibility: {s.feasibility:.3f}" in user_content
    assert f"structural: {s.structural:.3f}" in user_content


def test_propose_score_header_appears_before_architecture_content():
    """AlphaEvolve format: score header comes BEFORE the program/architecture."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    Proposer(client).propose([_seed(SATOSHI_FIXTURE)])

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    score_idx = user_content.find("Scores —")
    summary_idx = user_content.find("Summary:")
    assert score_idx != -1 and summary_idx != -1
    assert score_idx < summary_idx, (
        "Score header must appear before architecture content"
    )


def test_proposer_system_prompt_mentions_multi_objective_view():
    """PROPOSER_SYSTEM must instruct the LLM about the multi-objective signal."""
    from alphamo.prompts.proposer_prompt import PROPOSER_SYSTEM

    lowered = PROPOSER_SYSTEM.lower()
    # Some phrasing that conveys "multiple objectives / dimensions / scores".
    assert any(
        phrase in lowered
        for phrase in ("multi-objective", "multi-metric", "different dimension", "which dimension")
    ), "PROPOSER_SYSTEM should reference the multi-objective score view"


def test_propose_prompt_is_stable_for_same_seeds():
    """Same seeds in same order must produce the same prompt bytes."""
    client_a = MagicMock()
    client_a.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    client_b = MagicMock()
    client_b.messages.parse.return_value = FakeParsedMessage(_fake_architecture())

    seeds = [_seed(SATOSHI_FIXTURE), _seed(ROWLING_FIXTURE)]
    Proposer(client_a).propose(seeds)
    Proposer(client_b).propose(seeds)

    content_a = client_a.messages.parse.call_args[1]["messages"][0]["content"]
    content_b = client_b.messages.parse.call_args[1]["messages"][0]["content"]
    assert content_a == content_b


def test_propose_back_compat_architectures_only():
    """Callers passing list[Architecture] still work (no score headers, but functional)."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    # No score headers in the Architecture-only path.
    assert "Scores —" not in user_content
    # But the seed name still appears.
    assert "Satoshi" in user_content
