"""Unit tests for the LLM proposer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import ProposerOutputError
from alphamo.evaluator._common import SONNET_MODEL
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


def test_propose_uses_sonnet_model_by_default():
    """Sprint 7: proposer default moved Opus → Sonnet. The component-
    synthesis prompt structure (Sprint 6) constrains the task enough
    for Sonnet to perform comparably at lower cost."""
    client = _client_returning(_fake_architecture())
    Proposer(client).propose([SATOSHI_FIXTURE.architecture])
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == SONNET_MODEL


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
    """Each scored candidate must appear with a score header (AlphaEvolve §2.2 / Fig 3b).

    Sprint 2: exemplar_similarity was retired; the score header now shows
    feasibility, structural, robustness (when present), middle_class_accessible,
    and fitness.
    """
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    seeds = [_seed(SATOSHI_FIXTURE), _seed(ROWLING_FIXTURE)]
    Proposer(client).propose(seeds)

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    assert "Scores —" in user_content
    for axis in (
        "feasibility:",
        "structural:",
        "robustness:",
        "middle_class_accessible:",
        "fitness:",
    ):
        assert axis in user_content, f"missing score axis: {axis}"
    # Sprint 2: exemplar_similarity must NOT appear in the score header.
    assert "exemplar_similarity:" not in user_content
    s = SATOSHI_FIXTURE.scores
    assert f"feasibility: {s.feasibility:.3f}" in user_content
    assert f"structural: {s.structural:.3f}" in user_content


def test_propose_score_header_appears_before_candidate_architecture_content():
    """AlphaEvolve format: score header comes BEFORE the candidate's architecture.

    The prompt has two sections (Sprint 2): reference exemplars first, then
    candidates to mutate. This test scopes to the candidate section — it
    locates the candidate header `--- Candidate 1:` and verifies the score
    header precedes the candidate's own Summary line.
    """
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    Proposer(client).propose([_seed(SATOSHI_FIXTURE)])

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    candidate_idx = user_content.find("--- Candidate 1:")
    assert candidate_idx != -1, "candidate section header missing"
    section = user_content[candidate_idx:]
    score_idx = section.find("Scores —")
    summary_idx = section.find("Summary:")
    assert score_idx != -1 and summary_idx != -1
    assert score_idx < summary_idx, (
        "Score header must appear before architecture content within the candidate section"
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


def test_proposer_prompt_omits_reference_exemplars():
    """Sprint 3: the proposer prompt must not include a global reference
    exemplar section. The proposer sees only island-local candidates.
    """
    from alphamo.prompts.proposer_prompt import PROPOSER_SYSTEM

    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    Proposer(client).propose([_seed(SATOSHI_FIXTURE)])

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    # No reference-exemplar section.
    assert "REFERENCE EXEMPLAR" not in user_content.upper()
    assert "Reference exemplar" not in user_content
    # The 4 retired curated seed names must NOT appear in the user-turn
    # prompt as fixed reference content (they may appear as test inputs
    # if SATOSHI_FIXTURE was passed; the assertion is on the prompt
    # SECTION headers and framing, not on every byte).
    assert "structural insight" not in user_content.lower()
    assert "known fragilities" not in user_content.lower()

    # The system prompt also stops promising reference exemplars.
    sys_lower = PROPOSER_SYSTEM.lower()
    assert "reference exemplar" not in sys_lower
    assert "reference patterns" not in sys_lower


def test_proposer_prompt_contains_only_island_candidates():
    """User-turn prompt's CANDIDATE section count matches the seeds passed in."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    seeds = [_seed(SATOSHI_FIXTURE), _seed(ROWLING_FIXTURE)]
    Proposer(client).propose(seeds)

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    # Two Candidate dividers; no extra "Reference Exemplar" sections.
    assert user_content.count("--- Candidate 1:") == 1
    assert user_content.count("--- Candidate 2:") == 1
    assert user_content.count("--- Candidate 3:") == 0


def test_propose_raises_on_empty_seeds():
    """Sprint 3 invariant: empty seed lists are invalid (post-bootstrap,
    every island has at least one alive row to draw from)."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(_fake_architecture())
    with pytest.raises(ValueError, match="invariant violation"):
        Proposer(client).propose([])


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
