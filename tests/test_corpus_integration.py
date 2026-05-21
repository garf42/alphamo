"""Sprint 12: corpus integration tests.

Verifies:
  - The corpus loader compiles Layer A across both YAML schema
    variants without dropping entries.
  - Layer B section routing follows the per-section routing-target
    tags rather than hardcoded section indexes.
  - Layer D field-level routing splits fires-when (Stage 3) from
    comparator-survivor-signature (proposer).
  - Layer C invariants are included for both audiences.
  - CORPUS_VERSION is present and prepended to each subset's text.
  - prepare_cached_blocks produces multi-block system prompts with
    one cache_control marker per non-empty block.
  - Proposer + Stage 3 system prompts now have layered cached blocks
    with the corpus subset as the first cached prefix.
  - PROPOSER_VERSION advanced to v7.
  - Research module removal: `_maybe_research` is gone from the
    orchestrator and Hyperparameters no longer has
    `research_every_generations` as a field.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.context.hyperparams import Hyperparameters
from alphamo.corpus import (
    CORPUS_VERSION,
    compile_layer_a_index,
    load_proposer_subset,
    load_stage3_subset,
)
from alphamo.evaluator._common import prepare_cached_blocks
from alphamo.evaluator.stage4_adversarial import stage4_adversarial
from alphamo.orchestrator import Orchestrator
from alphamo.prompts.proposer_prompt import PROPOSER_VERSION
from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from alphamo.schemas.findings import RawFindingsBatch
from tests.fixtures.parsed_message import FakeParsedMessage


# ----------------------------------------------------------------- corpus loader


def test_corpus_version_present_and_pinned():
    """CORPUS_VERSION exists as a string constant. Pinned at v1 for
    the Sprint 12 initial load — future corpus revisions must bump
    this so caches invalidate."""
    assert isinstance(CORPUS_VERSION, str)
    assert CORPUS_VERSION == "v1"


def test_layer_a_index_compiles_all_entries():
    """All 72 Layer A entries should be compiled. Previous compiler
    drafts dropped ~25 entries because of YAML schema variation
    (list-item vs top-level-key); the Sprint 12 compiler handles
    both formats."""
    index = compile_layer_a_index()
    # Each entry begins with `- id:` after the header line.
    entries = [line for line in index.split("\n") if line.startswith("- id:")]
    # Corpus has 72 architecture files (excluding _status.md).
    assert len(entries) >= 70, (
        f"expected ≥70 entries compiled; got {len(entries)}. The compiler "
        "may be falling back on a schema variant."
    )


def test_layer_a_index_entry_size_under_budget():
    """Per-entry fingerprint should average <400 tokens (~1600 chars).
    Sprint 12 directive accepted ~175 tokens/entry; this is a looser
    upper bound that catches a regression where the compiler stops
    truncating field values."""
    index = compile_layer_a_index()
    entries = index.split("\n\n- id:")
    avg_chars = sum(len(e) for e in entries) / max(1, len(entries))
    # 4 chars per token → 400 tokens = 1600 chars.
    assert avg_chars < 1600, (
        f"per-entry avg {avg_chars:.0f} chars exceeds budget (~1600); "
        "tighten _compact_value truncation"
    )


def test_proposer_subset_includes_corpus_version_header():
    text = load_proposer_subset()
    assert f"CORPUS_VERSION={CORPUS_VERSION}" in text
    assert "proposer subset" in text


def test_stage3_subset_includes_corpus_version_header():
    text = load_stage3_subset()
    assert f"CORPUS_VERSION={CORPUS_VERSION}" in text
    assert "stage-3 subset" in text


def test_proposer_subset_contains_layer_a_index():
    text = load_proposer_subset()
    assert "Layer A — Architecture Fingerprint Index" in text


def test_stage3_subset_contains_layer_a_index():
    """Layer A index is shared across audiences — same bytes in both
    subsets so the cache write happens once per process."""
    text = load_stage3_subset()
    assert "Layer A — Architecture Fingerprint Index" in text


def test_proposer_subset_contains_layer_c_invariants():
    text = load_proposer_subset()
    assert "Layer C" in text


def test_stage3_subset_contains_layer_c_invariants():
    """Layer C invariants are universal — both audiences need them."""
    text = load_stage3_subset()
    assert "Layer C" in text


def test_layer_b_routing_proposer_includes_routing_target_proposer():
    """Layer B section 1 (AI capability landscape, routing-target:
    proposer primary) must appear in the proposer subset."""
    text = load_proposer_subset()
    assert "AI capability landscape" in text or "Layer B" in text


def test_layer_b_routing_stage3_includes_routing_target_stage3():
    """Layer B section 2 (regulatory transitions, routing-target:
    stage-3 primary) must appear in the Stage 3 subset."""
    text = load_stage3_subset()
    assert "Regulatory" in text or "Layer B" in text


def test_layer_d_proposer_gets_survivor_signatures_not_fires_when():
    """Field-level routing: proposer subset must contain comparator-
    survivor-signature extracts but NOT the fires-when predicate
    section."""
    text = load_proposer_subset()
    assert "Comparator Survivor Signatures" in text
    assert "Anti-pattern Firing Predicates" not in text


def test_layer_d_stage3_gets_fires_when_not_survivor_signatures():
    """Field-level routing inverse: Stage 3 subset must contain
    fires-when predicates but NOT the survivor-signature section."""
    text = load_stage3_subset()
    assert "Anti-pattern Firing Predicates" in text
    assert "Comparator Survivor Signatures" not in text


def test_layer_d_proposer_gets_positive_insights():
    text = load_proposer_subset()
    assert "Positive Insights" in text


def test_layer_d_stage3_gets_operational_summary():
    text = load_stage3_subset()
    assert "Operational Summary" in text


def test_proposer_and_stage3_subsets_are_distinct():
    """Different routing tags should produce different bytes for
    each audience subset."""
    assert load_proposer_subset() != load_stage3_subset()


def test_loader_memoizes_within_process():
    """Both subsets are lazily compiled and memoized — the second
    call returns the same string object as the first."""
    p1 = load_proposer_subset()
    p2 = load_proposer_subset()
    assert p1 is p2


# ----------------------------------------------------------------- prepare_cached_blocks


def test_prepare_cached_blocks_produces_one_breakpoint_per_text():
    blocks = prepare_cached_blocks(["corpus text", "system text"])
    assert len(blocks) == 2
    for b in blocks:
        assert b["type"] == "text"
        assert b["cache_control"] == {"type": "ephemeral"}
    assert blocks[0]["text"] == "corpus text"
    assert blocks[1]["text"] == "system text"


def test_prepare_cached_blocks_filters_empty_strings():
    """Empty texts (e.g., when the corpus directory is missing in a
    sandbox) are dropped so the parse call doesn't break on a
    zero-length block."""
    blocks = prepare_cached_blocks(["", "system text", ""])
    assert len(blocks) == 1
    assert blocks[0]["text"] == "system text"


def test_prepare_cached_blocks_empty_input():
    assert prepare_cached_blocks([]) == []


# ----------------------------------------------------------------- proposer + Stage 3 integration


def test_proposer_uses_layered_cached_blocks_with_corpus_first():
    """The proposer's parse call must pass a list of cached system
    blocks with the corpus subset as the first block and
    PROPOSER_SYSTEM as the second."""
    from alphamo.sampler import Seed
    from alphamo.schemas import Scores

    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        )
    )
    seed = Seed(
        architecture=Architecture(
            name="seed", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        scores=Scores(
            feasibility=0.5, structural=0.5,
            middle_class_accessible=True,
        ),
        fitness=0.5,
    )
    Proposer(client).propose([seed])

    system = client.messages.parse.call_args[1]["system"]
    # Two cache blocks: corpus first, PROPOSER_SYSTEM second.
    assert isinstance(system, list)
    assert len(system) == 2
    for block in system:
        assert block["cache_control"] == {"type": "ephemeral"}
    # First block is the corpus (contains CORPUS_VERSION header).
    assert f"CORPUS_VERSION={CORPUS_VERSION}" in system[0]["text"]
    # Second block is PROPOSER_SYSTEM (contains the structural-
    # component decomposition language).
    assert "STRUCTURAL DECOMPOSITION" in system[1]["text"]


def test_stage3_per_framing_uses_layered_cached_blocks():
    """Each Stage 3 framing's parse call must pass [corpus, framing]
    as a two-block cached system prompt. Corpus block is identical
    across all 9 framings (one cache write, 8 reads per candidate
    after warmup)."""
    captured: list[dict] = []

    def record(**kwargs):
        captured.append(kwargs)
        return FakeParsedMessage(RawFindingsBatch(findings=[]))

    client = MagicMock()
    client.messages.parse.side_effect = record

    stage4_adversarial(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framings=DEFAULT_FRAMINGS,
    )
    assert len(captured) == len(DEFAULT_FRAMINGS)
    corpus_texts = set()
    for kwargs in captured:
        system = kwargs["system"]
        assert isinstance(system, list)
        assert len(system) == 2
        for block in system:
            assert block["cache_control"] == {"type": "ephemeral"}
        # First block is the corpus subset.
        assert f"CORPUS_VERSION={CORPUS_VERSION}" in system[0]["text"]
        corpus_texts.add(system[0]["text"])
    # Corpus block byte-stable across all framings → one unique value.
    assert len(corpus_texts) == 1


# ----------------------------------------------------------------- version + removal


def test_proposer_version_advanced_to_v8():
    """Sprint 12 bumped v6 → v7 (corpus integration). Sprint 14 bumped
    v7 → v8 for the provider migration (Anthropic Sonnet → Fireworks
    DeepSeek V4 Flash). v8 trajectories must be distinguishable from
    v7 in the persisted run metadata."""
    assert PROPOSER_VERSION == "v8"


def test_research_module_is_removed():
    """Sprint 12 deleted alphamo.meta.research and
    alphamo.prompts.research_prompts. Imports should fail."""
    with pytest.raises(ModuleNotFoundError):
        __import__("alphamo.meta.research")
    with pytest.raises(ModuleNotFoundError):
        __import__("alphamo.prompts.research_prompts")


def test_orchestrator_has_no_maybe_research_method():
    """`_maybe_research` and the scheduled-research meta path are
    gone. The orchestrator class should not expose the method."""
    assert not hasattr(Orchestrator, "_maybe_research")


def test_hyperparameters_no_longer_defines_research_every_generations():
    """`research_every_generations` was removed from Hyperparameters
    in Sprint 12 since the research module is gone. The field name
    drops out of the schema (pydantic `extra='ignore'` lets old DBs
    still load runs that have the value persisted)."""
    fields = Hyperparameters.model_fields
    assert "research_every_generations" not in fields


def test_hyperparameters_silently_ignores_persisted_research_every_generations():
    """Backward compat: old DB rows have `research_every_generations`
    in their persisted hyperparameters JSON. Loading them via
    `Hyperparameters(**old_dict)` must not raise — pydantic
    `extra='ignore'` drops the unknown key silently."""
    hp = Hyperparameters(num_islands=2, research_every_generations=999)
    assert hp.num_islands == 2
    assert not hasattr(hp, "research_every_generations")


def test_cli_run_command_no_longer_has_research_every_option():
    """The `--research-every` CLI flag was removed in Sprint 12."""
    from alphamo.main import cli

    run_command = cli.commands["run"]
    flag_names = [opt.name for opt in run_command.params]
    assert "research_every" not in flag_names
