"""Unit tests for the LLM proposer."""

from __future__ import annotations

from unittest.mock import MagicMock

from alphamo.evaluator._common import OPUS_MODEL
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from tests.fixtures.exemplars import ROWLING_FIXTURE, SATOSHI_FIXTURE


def _fake_architecture() -> Architecture:
    return Architecture(
        name="Test candidate",
        summary="A test architecture.",
        value_chain="Test value chain.",
        capture_mechanism="Test capture mechanism.",
        entry_resources="Test entry resources.",
    )


def test_propose_returns_architecture():
    client = MagicMock()
    client.messages.parse.return_value.parsed = _fake_architecture()
    result = Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    assert isinstance(result, Architecture)
    assert result.name == "Test candidate"


def test_propose_passes_seeds_in_user_message():
    client = MagicMock()
    client.messages.parse.return_value.parsed = _fake_architecture()
    Proposer(client).propose([SATOSHI_FIXTURE.architecture, ROWLING_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    user_content = kwargs["messages"][0]["content"]
    assert "Satoshi" in user_content
    assert "Rowling" in user_content


def test_propose_uses_opus_model_by_default():
    client = MagicMock()
    client.messages.parse.return_value.parsed = _fake_architecture()
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == OPUS_MODEL


def test_propose_includes_adaptive_thinking():
    client = MagicMock()
    client.messages.parse.return_value.parsed = _fake_architecture()
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["thinking"] == {"type": "adaptive"}


def test_propose_sets_output_format_to_architecture():
    client = MagicMock()
    client.messages.parse.return_value.parsed = _fake_architecture()
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["output_format"] is Architecture


def test_propose_model_can_be_overridden():
    client = MagicMock()
    client.messages.parse.return_value.parsed = _fake_architecture()
    Proposer(client, model="claude-haiku-4-5").propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == "claude-haiku-4-5"
