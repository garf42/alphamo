"""Sprint 8: token-usage telemetry through parse_or_raise.

Tests verify the `llm_usage` audit event fires from each call site
(proposer, Stage 1, Stage 2, each Stage 3 framing, curator, research)
with the correct component label, usage fields, and generation/island
attribution. The instrumentation point is a single function
(`parse_or_raise`) — these tests confirm the plumbing through each
upstream caller is correct.

No live LLM calls; the Anthropic SDK is mocked end-to-end.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo import orchestrator as orch_mod
from alphamo.context.hyperparams import Hyperparameters
from alphamo.errors import (
    LLMOutputError,
    LLM_USAGE_TRIGGER,
    TelemetryContext,
)
from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator._common import (
    HAIKU_MODEL,
    OPUS_MODEL,
    SONNET_MODEL,
)
from alphamo.evaluator.stage1_feasibility import stage1_feasibility
from alphamo.evaluator.stage2_structured import stage2_structured
from alphamo.evaluator.stage4_adversarial import stage4_adversarial
from alphamo.meta.audit_log import AuditLog
from alphamo.meta.curator import Curator
from alphamo.orchestrator import Orchestrator
from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
from alphamo.proposer import Proposer
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    MetaFinding,
    RawFinding,
    RawFindingsBatch,
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage4Finding,
)
from tests.fixtures.parsed_message import FakeParsedMessage


# ---------------------------------------------------------------- helpers


class _FakeUsage:
    """Mimics anthropic.types.usage shape — attributes the SDK exposes.

    Sprint 8's _emit_llm_usage_event reads input_tokens, output_tokens,
    cache_creation_input_tokens, cache_read_input_tokens via getattr
    with default=0. This helper sets all four so tests can assert
    against the emitted payload.
    """

    def __init__(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
    ) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens
        self.cache_read_input_tokens = cache_read_input_tokens


def _client_for(parsed_output, usage: _FakeUsage | None = None) -> MagicMock:
    """Build a client whose parse() returns a FakeParsedMessage with the
    given parsed_output and optional usage attached to the message."""
    if usage is None:
        usage = _FakeUsage()
    response = FakeParsedMessage(parsed_output, stop_reason="end_turn")
    response.usage = usage
    client = MagicMock()
    client.messages.parse.return_value = response
    return client


def _telemetry(audit: AuditLog, run_id: str = "test_run") -> TelemetryContext:
    return TelemetryContext(
        audit_log=audit,
        run_id=run_id,
        generation=7,
        island_id=3,
    )


def _arch() -> Architecture:
    return Architecture(
        name="test-arch", summary="s", value_chain="v",
        capture_mechanism="c", entry_resources="e",
    )


def _stage1_finding() -> Stage1Finding:
    return Stage1Finding(
        feasibility=0.9, middle_class_accessible=True, reasoning="ok"
    )


def _stage2_finding() -> Stage2Finding:
    return Stage2Finding(
        one_person_threshold=0.9, billion_dollar_potential=0.9,
        labor_separation=0.9, structural=0.9, reasoning="ok",
    )


# ---------------------------------------------------------------- per-call-site coverage


def test_stage1_emits_llm_usage_event_with_component_stage1(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_for(
        _stage1_finding(),
        usage=_FakeUsage(input_tokens=500, output_tokens=120),
    )
    stage1_feasibility(_arch(), client, telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert len(usage_events) == 1
    payload = usage_events[0].payload
    assert payload["component"] == "stage1"
    assert payload["model"] == HAIKU_MODEL
    assert payload["input_tokens"] == 500
    assert payload["output_tokens"] == 120
    # Sprint 8 spec: cache fields are zero when not used (Stage 1 system
    # prompt is below Haiku's 2048-token cache minimum — confirmed in
    # the prompt-caching audit). The event still fires with zeroes.
    assert payload["cache_creation_input_tokens"] == 0
    assert payload["cache_read_input_tokens"] == 0
    assert payload["generation"] == 7
    assert payload["island_id"] == 3


def test_stage2_emits_llm_usage_event_with_component_stage2(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_for(
        _stage2_finding(),
        usage=_FakeUsage(input_tokens=620, output_tokens=180),
    )
    stage2_structured(_arch(), client, telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert len(usage_events) == 1
    assert usage_events[0].payload["component"] == "stage2"
    assert usage_events[0].payload["model"] == SONNET_MODEL


def test_stage3_emits_llm_usage_event_per_framing_with_component_stage3_framing(
    tmp_path,
):
    """Each of the 9 Stage 3 framings emits its own llm_usage event
    with component=f"stage3_{framing}". 9 framings → 9 events per
    Stage 3 invocation."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_for(
        RawFindingsBatch(findings=[]),
        usage=_FakeUsage(
            input_tokens=1500, output_tokens=200,
            cache_read_input_tokens=1350,  # post-warm-up cache hit
        ),
    )
    stage4_adversarial(_arch(), client, telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert len(usage_events) == len(DEFAULT_FRAMINGS)
    components = {e.payload["component"] for e in usage_events}
    expected = {f"stage3_{f}" for f in DEFAULT_FRAMINGS}
    assert components == expected
    # Sprint 11: Stage 3 moved Opus → Sonnet. Every framing call
    # records the Sonnet model and the cache_read.
    for event in usage_events:
        assert event.payload["model"] == SONNET_MODEL
        assert event.payload["cache_read_input_tokens"] == 1350


def test_proposer_emits_llm_usage_event_with_component_proposer(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_for(
        _arch(),
        usage=_FakeUsage(
            input_tokens=1300, output_tokens=450,
            cache_creation_input_tokens=1268,  # first call: cache write
        ),
    )
    proposer = Proposer(client)
    proposer.propose([_arch()], telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert len(usage_events) == 1
    payload = usage_events[0].payload
    assert payload["component"] == "proposer"
    # Sprint 11: proposer moved Opus → Sonnet (full Opus removal).
    assert payload["model"] == SONNET_MODEL
    assert payload["cache_creation_input_tokens"] == 1268


def test_curator_emits_llm_usage_event_with_component_curator(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_for(
        ClassificationVerdict(
            classification=Classification.COSMETIC, rationale="x"
        ),
        usage=_FakeUsage(input_tokens=700, output_tokens=80),
    )
    curator = Curator(client, audit, run_id="test_run")
    finding = MetaFinding(
        source="stage4_adversarial",
        framing="regulatory",
        claim="c", evidence="e",
        falsification_condition="f", severity=Severity.LOW,
    )
    curator.classify(finding, telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert len(usage_events) == 1
    assert usage_events[0].payload["component"] == "curator"


# Sprint 12: research module deleted. The pre-deletion test
# `test_research_emits_llm_usage_event_with_component_research` is
# removed because there's no `run_research` function to invoke. The
# `component="research"` label is no longer emitted by any code path
# — leaving the test would assert against a permanent absence.


# ---------------------------------------------------------------- generation / island attribution


def test_llm_usage_event_carries_generation_and_island_id_from_step(
    db, monkeypatch, tmp_path
):
    """End-to-end: an orchestrator step() invocation threads generation
    and island_id through the TelemetryContext to every llm_usage event
    emitted during that step."""
    def stage1_with_usage(arch, c, **kw):
        # Have to capture telemetry from kwargs and forward to a fake
        # usage event manually since we're mocking out the parse call.
        # Use the real stage1_feasibility instead — we'll mock client.
        return _stage1_finding()

    monkeypatch.setattr(cascade_mod, "stage1_feasibility", stage1_with_usage)
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: _stage2_finding(),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85, concerns=[], reasoning="ok"
        ),
    )

    # Proposer + curator use the real parse_or_raise path; their
    # llm_usage events should carry the step's generation + island.
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = MagicMock()
    counter = {"n": 0}

    def parse_side_effect(**kwargs):
        counter["n"] += 1
        output_format = kwargs.get("output_format")
        response = FakeParsedMessage(None, stop_reason="end_turn")
        response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
        if output_format is Architecture:
            response = FakeParsedMessage(
                Architecture(
                    name=f"gen-{counter['n']}", summary="s",
                    value_chain="v", capture_mechanism="c",
                    entry_resources="e",
                ),
                stop_reason="end_turn",
            )
            response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
            return response
        if output_format is ClassificationVerdict:
            response = FakeParsedMessage(
                ClassificationVerdict(
                    classification=Classification.COSMETIC, rationale="x"
                ),
                stop_reason="end_turn",
            )
            response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
            return response
        return FakeParsedMessage(MagicMock())

    client.messages.parse.side_effect = parse_side_effect

    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, client, audit, hp=hp)
    orch._bootstrap_islands()
    # Force a deterministic island choice for the test.
    orch.islands.pick_island = lambda: 1  # type: ignore[assignment]
    orch.step(generation=5)

    proposer_events = [
        e for e in audit.read_all()
        if e.trigger == LLM_USAGE_TRIGGER and e.payload["component"] == "proposer"
    ]
    assert len(proposer_events) >= 1
    payload = proposer_events[0].payload
    assert payload["generation"] == 5
    assert payload["island_id"] == 1


def test_bootstrap_emits_llm_usage_with_generation_zero(
    db, monkeypatch, tmp_path
):
    """Bootstrap-side llm_usage events carry generation=0 and
    island_id=None per the orchestrator's bootstrap_telemetry."""
    # Wire a real cascade so the bootstrap path runs through the real
    # parse_or_raise that emits the events.
    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        response = FakeParsedMessage(None, stop_reason="end_turn")
        response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
        if output_format is Stage1Finding:
            response = FakeParsedMessage(_stage1_finding(), stop_reason="end_turn")
        elif output_format is Stage2Finding:
            response = FakeParsedMessage(_stage2_finding(), stop_reason="end_turn")
        elif output_format is RawFindingsBatch:
            response = FakeParsedMessage(
                RawFindingsBatch(findings=[]), stop_reason="end_turn"
            )
        elif output_format is Architecture:
            response = FakeParsedMessage(
                Architecture(
                    name="g", summary="s", value_chain="v",
                    capture_mechanism="c", entry_resources="e",
                ),
                stop_reason="end_turn",
            )
        else:
            response = FakeParsedMessage(MagicMock(), stop_reason="end_turn")
        response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
        return response

    audit = AuditLog(tmp_path / "audit.jsonl")
    client = MagicMock()
    client.messages.parse.side_effect = parse_side_effect

    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, client, audit, hp=hp)
    orch._bootstrap_islands()

    bootstrap_usage = [
        e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER
    ]
    # Bootstrap fires Stage 1 + Stage 2 + 9 Stage 3 framings = 11 events.
    assert len(bootstrap_usage) == 11
    for event in bootstrap_usage:
        assert event.payload["generation"] == 0
        assert event.payload["island_id"] is None


# ---------------------------------------------------------------- corner cases


def test_no_telemetry_kwarg_means_no_event_emitted(tmp_path):
    """Telemetry is opt-in. Calls without a telemetry kwarg (legacy
    or test-only invocations) emit no llm_usage event — the audit log
    stays clean."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    client = _client_for(
        _stage1_finding(),
        usage=_FakeUsage(input_tokens=500, output_tokens=120),
    )
    # No telemetry= kwarg → no event.
    stage1_feasibility(_arch(), client)

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert usage_events == []


def test_llm_usage_event_handles_missing_cache_fields_on_old_sdk(tmp_path):
    """Defensive shape: if the SDK response lacks
    cache_creation_input_tokens / cache_read_input_tokens (older SDK
    versions before prompt-caching telemetry), the helper records
    zero rather than crashing."""
    audit = AuditLog(tmp_path / "audit.jsonl")

    class _UsageWithoutCacheFields:
        # Only the legacy fields; no cache_creation_input_tokens or
        # cache_read_input_tokens attributes.
        input_tokens = 500
        output_tokens = 120

    response = FakeParsedMessage(_stage1_finding(), stop_reason="end_turn")
    response.usage = _UsageWithoutCacheFields()
    client = MagicMock()
    client.messages.parse.return_value = response

    stage1_feasibility(_arch(), client, telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert len(usage_events) == 1
    payload = usage_events[0].payload
    assert payload["cache_creation_input_tokens"] == 0
    assert payload["cache_read_input_tokens"] == 0
    assert payload["input_tokens"] == 500


def test_llm_usage_event_skipped_on_parse_failure(tmp_path):
    """Telemetry only fires on the SUCCESS path of parse_or_raise.
    parse failures (LLMOutputError raised) are covered by the existing
    proposer_failure / cascade_failure audit events from Sprint 4 + 7
    — the llm_usage trigger isn't doubled up on the failure path."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    response = FakeParsedMessage(parsed_output=None, stop_reason="refusal")
    response.usage = _FakeUsage(input_tokens=500, output_tokens=0)
    client = MagicMock()
    client.messages.parse.return_value = response

    with pytest.raises(LLMOutputError):
        stage1_feasibility(_arch(), client, telemetry=_telemetry(audit))

    usage_events = [e for e in audit.read_all() if e.trigger == LLM_USAGE_TRIGGER]
    assert usage_events == []


# ---------------------------------------------------------------- existing audit events unchanged


def test_existing_stage4_routine_audit_still_fires_with_telemetry_enabled(
    db, monkeypatch, tmp_path
):
    """Sprint 4 regression: with Sprint 8 telemetry wired in, the
    existing stage4_routine audit event still fires on every Stage 3
    candidate. New llm_usage events are ADDITIONAL, not replacement."""
    from alphamo.orchestrator import STAGE4_AUDIT_TRIGGER
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: _stage1_finding(),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: _stage2_finding(),
    )
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.85, concerns=[], reasoning="ok"
        ),
    )

    audit = AuditLog(tmp_path / "audit.jsonl")
    client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        response = FakeParsedMessage(None, stop_reason="end_turn")
        response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
        if output_format is Architecture:
            response = FakeParsedMessage(
                Architecture(
                    name="g", summary="s", value_chain="v",
                    capture_mechanism="c", entry_resources="e",
                ),
                stop_reason="end_turn",
            )
            response.usage = _FakeUsage(input_tokens=100, output_tokens=50)
        return response

    client.messages.parse.side_effect = parse_side_effect

    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, client, audit, hp=hp)
    orch._bootstrap_islands()
    orch.step(generation=1)

    events = audit.read_all()
    stage4_routine_events = [e for e in events if e.trigger == STAGE4_AUDIT_TRIGGER]
    assert len(stage4_routine_events) >= 1
