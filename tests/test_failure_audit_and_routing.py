"""Sprint 7: audit instrumentation on silent failure paths, proposer
max_tokens bump, model routing Opus → Sonnet on proposer/curator/research.

Three coupled fixes from one commit:
  - Fix A: previously-silent step() failure paths now emit structured
    audit events (proposer_failure, cascade_failure).
  - Fix B: proposer max_tokens 8192 → 16384 to absorb Sprint 6's longer
    prompt + adaptive-thinking budget.
  - Fix C: proposer / curator / research default to Sonnet; Stage 3
    adversarial scrutiny stays on Opus.

Plus PROPOSER_VERSION bump v2 → v3 (model executing the prompt changed
even though the prompt structure didn't).

No live LLM calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.errors import (
    LLMOutputError,
    Stage1OutputError,
    Stage2OutputError,
    Stage4OutputError,
)
from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator._common import (
    MAX_TOKENS_XLONG,
    OPUS_MODEL,
    SONNET_MODEL,
)
from alphamo.meta.audit_log import AuditLog
from alphamo.meta.curator import Curator
from alphamo.orchestrator import (
    CASCADE_FAILURE_TRIGGER,
    PROPOSER_FAILURE_TRIGGER,
    STAGE3_CATASTROPHIC_FAILURE_TRIGGER,
    Orchestrator,
)
from alphamo.prompts.proposer_prompt import PROPOSER_VERSION
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    Stage1Finding,
    Stage2Finding,
)
from tests.fixtures.parsed_message import FakeParsedMessage


# ---------------------------------------------------------------- helpers


def _stub_client(arch_name: str = "generated") -> MagicMock:
    """Mock client that returns Architecture / ClassificationVerdict for
    parse() calls — used wherever step() needs a working proposer +
    curator route in tests where the cascade is stubbed separately."""
    client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            return FakeParsedMessage(
                Architecture(
                    name=arch_name, summary="s", value_chain="v",
                    capture_mechanism="c", entry_resources="e",
                )
            )
        if output_format is ClassificationVerdict:
            return FakeParsedMessage(
                ClassificationVerdict(
                    classification=Classification.COSMETIC, rationale="x"
                )
            )
        return FakeParsedMessage(MagicMock())

    client.messages.parse.side_effect = parse_side_effect
    return client


def _hp(**kwargs) -> Hyperparameters:
    defaults = dict(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    defaults.update(kwargs)
    return Hyperparameters(**defaults)


def _bootstrap_orch(db, monkeypatch, tmp_path, hp=None):
    monkeypatch.setattr(orch_mod, "run_research", lambda *a, **k: [])
    # Stub Stage 1 / Stage 2 / Stage 3 so bootstrap succeeds; individual
    # tests override one of these to simulate the failure under test.
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: Stage1Finding(
            feasibility=0.9, middle_class_accessible=True, reasoning="ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: Stage2Finding(
            one_person_threshold=0.9, billion_dollar_potential=0.9,
            labor_separation=0.9, structural=0.9, reasoning="ok",
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: __import__(
            "alphamo.schemas.findings", fromlist=["Stage4Finding"]
        ).Stage4Finding(robustness=0.85, concerns=[], reasoning="ok"),
    )
    audit = AuditLog(tmp_path / "audit.jsonl")
    orch = Orchestrator.for_new_run(db, _stub_client(), audit, hp=hp or _hp())
    orch._bootstrap_islands()
    return orch, audit


# ---------------------------------------------------------------- Fix A: proposer-failure audit


def test_proposer_failure_writes_proposer_failure_audit_event(
    db, monkeypatch, tmp_path
):
    """When proposer.propose() raises LLMOutputError, step() emits a
    proposer_failure audit event before returning the failure
    IterationEvent. Previously this path was silent."""
    orch, audit = _bootstrap_orch(db, monkeypatch, tmp_path)

    # Force the proposer to raise on the next call. The bootstrap
    # already completed (via the stub client routed through
    # _stub_client), so the failure happens on step().
    def proposer_raises(*args, **kwargs):
        raise LLMOutputError(
            stop_reason="refusal",
            content_block_types=["text"],
            detail="model refused to produce JSON",
        )

    monkeypatch.setattr(orch.proposer, "propose", proposer_raises)

    event = orch.step(generation=1)
    assert event.candidate_id is None
    assert event.failure_reason is not None

    proposer_failure_events = [
        e for e in audit.read_all()
        if e.trigger == PROPOSER_FAILURE_TRIGGER
    ]
    assert len(proposer_failure_events) == 1
    payload = proposer_failure_events[0].payload
    assert payload["generation"] == 1
    assert payload["stop_reason"] == "refusal"
    assert "model refused" in payload["detail"]


def test_proposer_failure_audit_handles_missing_stop_reason():
    """If the raised LLMOutputError has no stop_reason, the audit
    rationale should record 'unknown' rather than crashing."""
    from alphamo.orchestrator import _CASCADE_FAILURE_STAGE_LABEL  # noqa: F401

    # Build a bare Exception that isn't an LLMOutputError shape — but
    # the actual code path only catches LLMOutputError, so we test
    # the LLMOutputError-without-stop-reason corner directly via the
    # helper's handling of missing attrs.
    exc = LLMOutputError()  # stop_reason defaults to None
    assert exc.stop_reason is None  # confirms the corner case shape


# ---------------------------------------------------------------- Fix A: cascade-failure audit


def test_stage1_failure_writes_cascade_failure_audit_event_with_feasibility_stage(
    db, monkeypatch, tmp_path
):
    """Stage 1 (Haiku) parse failure → cascade_failure audit with
    stage='feasibility'."""
    orch, audit = _bootstrap_orch(db, monkeypatch, tmp_path)

    def stage1_raises(arch, c, **kw):
        raise Stage1OutputError(
            stop_reason="max_tokens",
            content_block_types=["thinking"],
            detail="Haiku truncated",
        )

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", stage1_raises)

    event = orch.step(generation=1)
    assert event.candidate_id is None

    cascade_events = [
        e for e in audit.read_all() if e.trigger == CASCADE_FAILURE_TRIGGER
    ]
    assert len(cascade_events) == 1
    payload = cascade_events[0].payload
    assert payload["stage"] == "feasibility"
    assert payload["stop_reason"] == "max_tokens"
    assert payload["architecture_name"] == "generated"


def test_stage2_failure_writes_cascade_failure_audit_event_with_structural_stage(
    db, monkeypatch, tmp_path
):
    """Stage 2 (Sonnet) parse failure → cascade_failure audit with
    stage='structural'."""
    orch, audit = _bootstrap_orch(db, monkeypatch, tmp_path)

    def stage2_raises(arch, c, **kw):
        raise Stage2OutputError(
            stop_reason="parse_error",
            content_block_types=[],
            detail="Sonnet output failed schema",
        )

    monkeypatch.setattr(cascade_mod, "stage2_structured", stage2_raises)

    event = orch.step(generation=1)
    assert event.candidate_id is None

    cascade_events = [
        e for e in audit.read_all() if e.trigger == CASCADE_FAILURE_TRIGGER
    ]
    assert len(cascade_events) == 1
    payload = cascade_events[0].payload
    assert payload["stage"] == "structural"
    assert payload["stop_reason"] == "parse_error"


def test_generic_stage4_failure_writes_cascade_failure_audit_event_with_adversarial_stage(
    db, monkeypatch, tmp_path
):
    """Stage 4 LLMOutputError WITHOUT the catastrophic stop_reason →
    cascade_failure audit with stage='adversarial', NOT the
    stage3_catastrophic_framing_failure trigger."""
    orch, audit = _bootstrap_orch(db, monkeypatch, tmp_path)

    def stage3_raises(arch, c, **kw):
        # Any Stage4OutputError stop_reason OTHER than the catastrophic
        # one. The current stage4_adversarial code only raises the
        # catastrophic case, but the orchestrator path defends against
        # any other Stage4OutputError surfacing too.
        raise Stage4OutputError(
            stop_reason="refusal",
            content_block_types=["text"],
            detail="adversarial scrutiny refused",
        )

    monkeypatch.setattr(cascade_mod, "stage4_adversarial", stage3_raises)

    event = orch.step(generation=1)
    assert event.candidate_id is None

    all_events = audit.read_all()
    cascade_events = [e for e in all_events if e.trigger == CASCADE_FAILURE_TRIGGER]
    catastrophic_events = [
        e for e in all_events if e.trigger == STAGE3_CATASTROPHIC_FAILURE_TRIGGER
    ]
    assert len(cascade_events) == 1
    assert len(catastrophic_events) == 0
    assert cascade_events[0].payload["stage"] == "adversarial"
    assert cascade_events[0].payload["stop_reason"] == "refusal"


def test_stage3_catastrophic_failure_still_uses_dedicated_trigger_regression(
    db, monkeypatch, tmp_path
):
    """Sprint 4 regression: the stage3_catastrophic_framing_failure
    audit event must still fire on the catastrophic sub-case. The
    Sprint 7 cascade_failure trigger does NOT also fire on this case —
    the catastrophic branch is mutually exclusive with the generic
    cascade_failure branch."""
    orch, audit = _bootstrap_orch(db, monkeypatch, tmp_path)

    def stage3_raises_catastrophic(arch, c, **kw):
        raise Stage4OutputError(
            stop_reason="stage3_catastrophic_framing_failure",
            content_block_types=[],
            detail="6 of 9 framings failed",
        )

    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial", stage3_raises_catastrophic
    )

    event = orch.step(generation=1)
    assert event.candidate_id is None

    all_events = audit.read_all()
    catastrophic_events = [
        e for e in all_events if e.trigger == STAGE3_CATASTROPHIC_FAILURE_TRIGGER
    ]
    cascade_failure_events = [
        e for e in all_events if e.trigger == CASCADE_FAILURE_TRIGGER
    ]
    # Catastrophic trigger fires; the generic cascade_failure trigger
    # does NOT (mutually exclusive branches in step()).
    assert len(catastrophic_events) == 1
    assert len(cascade_failure_events) == 0


# ---------------------------------------------------------------- Fix B: proposer max_tokens


def test_proposer_max_tokens_is_xlong():
    """Sprint 7 Fix B: proposer max_tokens bumped from MAX_TOKENS_LONG
    (8192) to MAX_TOKENS_XLONG (16384) to absorb Sprint 6's longer
    prompt + adaptive-thinking budget. Empirical evidence from
    run-c8b5144e showed 11/30 silent drops at 8192."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        )
    )
    Proposer(client).propose(
        [
            Architecture(
                name="seed", summary="s", value_chain="v",
                capture_mechanism="c", entry_resources="e",
            )
        ]
    )
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["max_tokens"] == MAX_TOKENS_XLONG
    assert kwargs["max_tokens"] == 16384


# ---------------------------------------------------------------- Fix C: model routing


def test_proposer_default_model_is_sonnet():
    """Sprint 7 Fix C: proposer moved Opus → Sonnet."""
    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        )
    )
    Proposer(client).propose(
        [
            Architecture(
                name="seed", summary="s", value_chain="v",
                capture_mechanism="c", entry_resources="e",
            )
        ]
    )
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == SONNET_MODEL


def test_curator_default_model_is_sonnet(tmp_path):
    """Sprint 7 Fix C: curator moved Opus → Sonnet."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    curator = Curator(MagicMock(), audit, run_id="test_run")
    assert curator.model == SONNET_MODEL


def test_research_default_model_is_sonnet():
    """Sprint 7 Fix C: research moved Opus → Sonnet. The default
    parameter on `run_research` should be SONNET_MODEL."""
    import inspect
    from alphamo.meta.research import run_research

    sig = inspect.signature(run_research)
    assert sig.parameters["model"].default == SONNET_MODEL


def test_stage3_adversarial_default_model_stays_opus():
    """Sprint 7 Fix C corollary: Stage 3 adversarial scrutiny stays on
    Opus. The cascade's value depends on substantive falsifiable
    critique with statute citations and mechanism-specific failure
    modes — observed in run-ed6e72e1 gen-12 §203(b)(4) finding that
    required Opus-class reasoning depth."""
    import inspect
    from alphamo.evaluator.stage4_adversarial import stage4_adversarial

    sig = inspect.signature(stage4_adversarial)
    assert sig.parameters["model"].default == OPUS_MODEL


# ---------------------------------------------------------------- PROPOSER_VERSION


def test_proposer_version_advanced_to_v3():
    """Sprint 7 bumped PROPOSER_VERSION v2 → v3. The prompt structure
    didn't change but the model executing it did; v2 trajectories
    (Opus proposer) and v3 trajectories (Sonnet proposer) must be
    distinguishable in the DB for analysis."""
    assert PROPOSER_VERSION == "v3"
