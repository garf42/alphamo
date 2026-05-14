"""Unit tests for the LLM proposer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import ProposerOutputError
from alphamo.evaluator._common import OPUS_MODEL
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from tests.fixtures.exemplars import ROWLING_FIXTURE, SATOSHI_FIXTURE
from tests.fixtures.parsed_message import FakeContentBlock, FakeParsedMessage


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
