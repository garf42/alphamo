"""Sprint 11: full Opus removal, bounded Sonnet thinking, reset cadence 10 → 40.

Tests pin the new routing + thinking + cadence defaults so a future
Sprint that drifts any of them gets an immediate test failure rather
than silent regression.

Sprint 11 is a cost-driven change. Empirical baseline: run_80ae6e59
showed Stage 3 (Opus) at $22.51 of $28.37 total (79%) over 30 gens;
extrapolated to 200 gens that's ~$190 per run, unaffordable. Sonnet
swap (60% cost ratio at current Opus 4.7 / Sonnet 4.6 pricing)
projects ~$115-135 per 200-gen run. Quality preservation across all
9 Stage 3 framings + bounded thinking for proposer + Stage 3.

No live LLM calls.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from alphamo.context.hyperparams import Hyperparameters
from alphamo.evaluator import stage1_feasibility as s1_mod
from alphamo.evaluator import stage2_structured as s2_mod
from alphamo.evaluator._common import (
    HAIKU_MODEL,
    OPUS_MODEL,
    SONNET_MODEL,
)
from alphamo.evaluator.stage4_adversarial import (
    STAGE3_THINKING_BUDGET_TOKENS,
    stage4_adversarial,
)
from alphamo.meta.audit_log import AuditLog
from alphamo.meta.curator import Curator
from alphamo.prompts.proposer_prompt import PROPOSER_VERSION
from alphamo.proposer import Proposer, PROPOSER_THINKING_BUDGET_TOKENS


# ---------------------------------------------------------------- routing


def test_proposer_default_model_is_sonnet_under_sprint11():
    """Sprint 11: proposer moves Opus → Sonnet (no-Opus directive)."""
    assert Proposer(MagicMock()).model == SONNET_MODEL


def test_stage3_default_model_is_sonnet_under_sprint11():
    """Sprint 11: Stage 3 adversarial scrutiny moves Opus → Sonnet
    as part of the full Opus removal. Quality risk concentrated on
    `current_moment_dependency` framing per Sprint 11 audit; other 8
    framings rely on durable knowledge."""
    sig = inspect.signature(stage4_adversarial)
    assert sig.parameters["model"].default == SONNET_MODEL


def test_stage1_default_model_stays_haiku_under_sprint11():
    """Sprint 11 audit recommendation: Stage 1 stays on Haiku.
    The cheap-fast-filter task doesn't benefit from a model promotion;
    moving to Sonnet would 3× the cost of an already-trivial line item
    ($0 of the $0.47 stages-1+2+curator total in run_80ae6e59).

    Sprint 14: the stage functions gained a `model=` kwarg so the
    cascade can pass per-stage HP routing through. The Sprint-11
    invariant is now pinned via the default-parameter value, not the
    inlined kwarg in the parse() call.
    """
    sig = inspect.signature(s1_mod.stage1_feasibility)
    assert sig.parameters["model"].default == HAIKU_MODEL


def test_stage2_default_model_stays_sonnet_under_sprint11():
    """Sprint 11: Stage 2 routing unchanged at Sonnet."""
    sig = inspect.signature(s2_mod.stage2_structured)
    assert sig.parameters["model"].default == SONNET_MODEL


def test_curator_default_model_stays_sonnet_under_sprint11(tmp_path):
    """Sprint 7 routing for curator unchanged at Sonnet."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    curator = Curator(MagicMock(), audit, run_id="test_run")
    assert curator.model == SONNET_MODEL


def test_no_opus_references_in_routing_defaults(tmp_path):
    """Structural guard: with Sprint 11's full Opus removal, no
    component should default to OPUS_MODEL. This catches a future
    sprint accidentally re-introducing Opus as a default.

    Per-call `model=` overrides are still legal (tests / ad-hoc
    research can pass OPUS_MODEL explicitly) — this test only pins
    the *defaults*.

    Sprint 12: research module deleted, so it's no longer one of the
    components under check. Curator, proposer, and Stage 3 remain."""
    proposer = Proposer(MagicMock())
    assert proposer.model != OPUS_MODEL

    s3_sig = inspect.signature(stage4_adversarial)
    assert s3_sig.parameters["model"].default != OPUS_MODEL

    audit = AuditLog(tmp_path / "audit.jsonl")
    curator = Curator(MagicMock(), audit, run_id="t")
    assert curator.model != OPUS_MODEL


# ---------------------------------------------------------------- thinking config


def test_proposer_bounded_thinking_budget_is_6000():
    """Sprint 11 pins the proposer's bounded thinking budget. 6000
    leaves ~10K for output within the 16384 cap; large enough for
    the component-synthesis prompt's reasoning load."""
    assert PROPOSER_THINKING_BUDGET_TOKENS == 6000


def test_stage3_bounded_thinking_budget_is_4000():
    """Sprint 11 pins the Stage 3 bounded thinking budget. 4000
    leaves ~4K for concerns JSON output within the 8192 cap; the
    concerns list is typically 500-1500 tokens so the budget is
    comfortable."""
    assert STAGE3_THINKING_BUDGET_TOKENS == 4000


def _stage3_capture_kwargs():
    """Helper: stub a client that records every parse() kwargs dict
    and returns an empty RawFindingsBatch. Used by the Stage 3
    thinking-config tests so we can inspect what the SDK was called
    with."""
    from alphamo.schemas.findings import RawFindingsBatch
    from tests.fixtures.parsed_message import FakeParsedMessage

    captured: list[dict] = []

    def _record(**kwargs):
        captured.append(kwargs)
        return FakeParsedMessage(RawFindingsBatch(findings=[]))

    client = MagicMock()
    client.messages.parse.side_effect = _record
    return client, captured


def test_stage3_thinking_config_uses_bounded_form():
    """Sprint 11: Stage 3 thinking moves adaptive → bounded
    `{"type": "enabled", "budget_tokens": 4000}`. Predictable cost
    across 1800+ framing calls per 200-gen run; eliminates the
    Sonnet-adaptive thinking-spike failure class.

    Passes all 9 default framings so the 5-of-9 threshold is cleared
    cleanly; the test only cares about the parse() kwargs, not the
    aggregated Stage 3 output.
    """
    from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
    from alphamo.schemas import Architecture

    client, captured = _stage3_capture_kwargs()

    stage4_adversarial(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framings=DEFAULT_FRAMINGS,
    )
    # 9 framings → 9 parse calls; thinking config is identical across all.
    assert len(captured) == len(DEFAULT_FRAMINGS)
    for kwargs in captured:
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 4000}


def test_stage3_thinking_does_not_use_adaptive():
    """Regression: Sprint 10's adaptive form (Opus 4.7-only) is gone
    on Stage 3. The bounded `enabled` form is back, now valid on
    Sonnet 4.6."""
    from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
    from alphamo.schemas import Architecture

    client, captured = _stage3_capture_kwargs()

    stage4_adversarial(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framings=DEFAULT_FRAMINGS,
    )
    for kwargs in captured:
        assert kwargs["thinking"].get("type") != "adaptive"


def test_stage3_call_does_not_include_output_config():
    """Under bounded thinking, output_config is irrelevant. Stage 3
    parse calls must not include it."""
    from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
    from alphamo.schemas import Architecture

    client, captured = _stage3_capture_kwargs()

    stage4_adversarial(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framings=DEFAULT_FRAMINGS,
    )
    for kwargs in captured:
        assert "output_config" not in kwargs


# ---------------------------------------------------------------- reset cadence


def test_reset_every_generations_default_is_40():
    """Sprint 11: cadence raised 10 → 40 for 200-gen target. Cadence
    10 produced reset-propagation diversity issues at longer scales
    (only ~10 gens between resets is insufficient for within-island
    evolution to produce meaningful differentiation)."""
    assert Hyperparameters().reset_every_generations == 40


def test_reset_cadence_description_mentions_sprint11_rationale():
    """The hyperparam docstring should explain why cadence 40 was
    chosen — so a future reader understands the trade-off without
    needing to dig through commit history."""
    field = Hyperparameters.model_fields["reset_every_generations"]
    description = (field.description or "").lower()
    assert "200" in description or "sprint 11" in description
    assert "40" in description


# ---------------------------------------------------------------- PROPOSER_VERSION


def test_proposer_version_at_least_v6_under_sprint11():
    """Sprint 11 bumped PROPOSER_VERSION v5 → v6. Sprint 12 bumped
    again to v7 (corpus integration). This regression guard accepts
    v6 or later — the Sprint 11 invariant (must have advanced past
    v5) is preserved across Sprint 12's further bump."""
    assert PROPOSER_VERSION not in ("v1", "v2", "v3", "v4", "v5")
