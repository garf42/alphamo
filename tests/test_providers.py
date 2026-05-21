"""Sprint 14: provider-abstraction tests.

No live LLM calls. Mocks the underlying SDK clients to verify:
  - FireworksProvider builds OpenAI-shape requests with response_format
    json_schema enforcement; concatenates cached system blocks and
    strips Anthropic cache_control markers; passes reasoning_effort via
    extra_body.
  - <think> tag stripping fallback works when the model leaks reasoning
    into the structured-output channel.
  - Token usage normalization from OpenAI's prompt_tokens / completion_tokens
    shape into the shared NormalizedUsage; reads prompt_cache_hit_tokens
    on the Fireworks shape and falls back to prompt_tokens_details.cached_tokens
    on the OpenAI shape.
  - Audit-event payload keys are byte-stable across providers (Sprint 8
    contract).
  - AnthropicProvider preserves the Sprint 13 call shape — same
    parse_kwargs passthrough, same parsed_output/None error path, same
    pydantic.ValidationError → from_validation_error path.
  - All 5 production Pydantic output models emit json_schema() without
    failure (catches schema-feature regressions before any live call).
  - Provider factory raises a helpful error when FIREWORKS_API_KEY is
    unset.
  - Orchestrator's _build_component_providers respects the legacy
    `client` parameter (auto-wrap) and otherwise routes per HP.
  - Hyperparameters per-component routing defaults (Sprint 14 decision).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pydantic
import pytest

from alphamo.context.hyperparams import Hyperparameters
from alphamo.errors import LLMOutputError, Stage1OutputError, TelemetryContext
from alphamo.meta.audit_log import AuditLog
from alphamo.providers import (
    AnthropicProvider,
    BaseProvider,
    FIREWORKS_DEFAULT_MODEL,
    FireworksProvider,
    NormalizedUsage,
    ensure_provider,
)
from alphamo.providers.base import _emit_llm_usage_event
from alphamo.providers.factory import build_provider, reset_provider_cache
from alphamo.providers.fireworks_provider import (
    _flatten_system_to_text,
    _strip_leading_think,
)
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import (
    ClassificationVerdict,
    RawFindingsBatch,
    Stage1Finding,
    Stage2Finding,
)


# --------------------------------------------------------------------- helpers


class _FakeOpenAIUsage:
    def __init__(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        prompt_cache_hit_tokens: int | None = None,
        cached_tokens: int | None = None,
    ) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        if prompt_cache_hit_tokens is not None:
            self.prompt_cache_hit_tokens = prompt_cache_hit_tokens
        if cached_tokens is not None:
            self.prompt_tokens_details = type(
                "Details", (), {"cached_tokens": cached_tokens}
            )()


def _fake_openai_response(
    json_content: str,
    *,
    finish_reason: str = "stop",
    usage: _FakeOpenAIUsage | None = None,
):
    """Build a stand-in for openai.types.chat.ChatCompletion."""
    message = type("Message", (), {"content": json_content})()
    choice = type("Choice", (), {"message": message, "finish_reason": finish_reason})()
    return type(
        "Completion",
        (),
        {"choices": [choice], "usage": usage if usage is not None else _FakeOpenAIUsage()},
    )()


def _fireworks_with_mock_create(side_effect_or_return):
    """Wire up a FireworksProvider whose underlying openai client's
    chat.completions.create is mocked to the given side_effect or
    return_value. `client=` bypasses the factory's openai.OpenAI()
    construction so this works without FIREWORKS_API_KEY set."""
    mock_client = MagicMock()
    if callable(side_effect_or_return) and not isinstance(
        side_effect_or_return, BaseException
    ):
        mock_client.chat.completions.create.side_effect = side_effect_or_return
    else:
        mock_client.chat.completions.create.return_value = side_effect_or_return
    return FireworksProvider(client=mock_client), mock_client


# --------------------------------------------------------------------- ensure_provider


def test_ensure_provider_passes_through_baseprovider_instance():
    p = AnthropicProvider(MagicMock())
    assert ensure_provider(p) is p


def test_ensure_provider_wraps_loose_anthropic_client():
    raw = MagicMock()
    wrapped = ensure_provider(raw)
    assert isinstance(wrapped, AnthropicProvider)


# --------------------------------------------------------------------- FireworksProvider request shape


def test_fireworks_provider_strips_cache_control_and_concatenates_system_blocks():
    provider, mock_client = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": 0.7, "middle_class_accessible": true, "reasoning": "ok"}')
    )
    system_blocks = [
        {"type": "text", "text": "CORPUS BLOCK", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "SYSTEM BLOCK", "cache_control": {"type": "ephemeral"}},
    ]
    provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system=system_blocks,
        messages=[{"role": "user", "content": "hello"}],
        output_format=Stage1Finding,
    )
    kwargs = mock_client.chat.completions.create.call_args[1]
    sys_msg = kwargs["messages"][0]
    assert sys_msg["role"] == "system"
    assert "CORPUS BLOCK" in sys_msg["content"]
    assert "SYSTEM BLOCK" in sys_msg["content"]
    # cache_control keys must not survive into the OpenAI request.
    serialized = json.dumps(kwargs["messages"])
    assert "cache_control" not in serialized
    assert "ephemeral" not in serialized


def test_fireworks_provider_passes_reasoning_effort_via_extra_body():
    provider, mock_client = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": 0.7, "middle_class_accessible": true, "reasoning": "ok"}')
    )
    provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
        reasoning_effort="high",
    )
    kwargs = mock_client.chat.completions.create.call_args[1]
    # Sprint 14 hotfix: extra_body carries `reasoning_effort` ONLY.
    # Fireworks rejects requests that set both `thinking` and
    # `reasoning_effort` (HTTP 400 under reasoning_effort="max").
    # reasoning_effort alone controls DeepSeek V4's thinking mode.
    assert kwargs["extra_body"] == {"reasoning_effort": "high"}


def test_fireworks_provider_passes_reasoning_effort_max_without_thinking_field():
    """Sprint 14 hotfix regression guard: reasoning_effort='max' must
    NOT pair with an explicit thinking field — Fireworks rejects the
    combination with HTTP 400 ("cannot specify both 'thinking' and
    'reasoning_effort'"). reasoning_effort alone controls mode."""
    provider, mock_client = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": 0.7, "middle_class_accessible": true, "reasoning": "ok"}')
    )
    provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
        reasoning_effort="max",
    )
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert kwargs["extra_body"] == {"reasoning_effort": "max"}
    assert "thinking" not in kwargs["extra_body"]


def test_fireworks_provider_omits_extra_body_when_no_reasoning_effort():
    provider, mock_client = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": 0.7, "middle_class_accessible": true, "reasoning": "ok"}')
    )
    provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert "extra_body" not in kwargs


def test_fireworks_provider_sets_response_format_json_schema():
    provider, mock_client = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": 0.7, "middle_class_accessible": true, "reasoning": "ok"}')
    )
    provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    kwargs = mock_client.chat.completions.create.call_args[1]
    rf = kwargs["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["name"] == "Stage1Finding"
    # The schema body is the Pydantic model_json_schema output verbatim.
    assert rf["json_schema"]["schema"] == Stage1Finding.model_json_schema()


def test_fireworks_provider_silently_drops_top_level_anthropic_thinking_field():
    """The legacy Anthropic `thinking={'type':'enabled','budget_tokens':N}`
    field arrives at the Fireworks provider when both forms are passed
    at the call site. Provider must NOT forward it as a top-level field
    (would error in the OpenAI SDK validator) AND must NOT echo it into
    extra_body (Fireworks rejects requests with both `thinking` and
    `reasoning_effort` set — Sprint 14 hotfix). Only reasoning_effort
    survives in extra_body."""
    provider, mock_client = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": 0.7, "middle_class_accessible": true, "reasoning": "ok"}')
    )
    provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
        thinking={"type": "enabled", "budget_tokens": 4000},
        reasoning_effort="high",
    )
    kwargs = mock_client.chat.completions.create.call_args[1]
    # The Anthropic-shape top-level `thinking` must not survive.
    assert "thinking" not in kwargs
    # extra_body carries reasoning_effort only — no thinking field.
    assert kwargs["extra_body"] == {"reasoning_effort": "high"}
    assert "thinking" not in kwargs["extra_body"]


# --------------------------------------------------------------------- FireworksProvider response handling


def test_fireworks_provider_parses_valid_json_response():
    payload = '{"feasibility": 0.9, "middle_class_accessible": true, "reasoning": "looks fine"}'
    provider, _ = _fireworks_with_mock_create(_fake_openai_response(payload))
    result = provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    assert isinstance(result, Stage1Finding)
    assert result.feasibility == 0.9
    assert result.middle_class_accessible is True


def test_fireworks_provider_strips_leading_think_block_on_retry():
    payload = (
        "<think>I should weigh the structural factors before responding…</think>\n"
        '{"feasibility": 0.5, "middle_class_accessible": false, "reasoning": "x"}'
    )
    provider, _ = _fireworks_with_mock_create(_fake_openai_response(payload))
    result = provider.parse(
        error_cls=Stage1OutputError,
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    assert isinstance(result, Stage1Finding)
    assert result.middle_class_accessible is False


def test_fireworks_provider_raises_on_empty_content():
    provider, _ = _fireworks_with_mock_create(
        _fake_openai_response("", finish_reason="length")
    )
    with pytest.raises(Stage1OutputError) as exc:
        provider.parse(
            error_cls=Stage1OutputError,
            model=FIREWORKS_DEFAULT_MODEL,
            max_tokens=2048,
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            output_format=Stage1Finding,
        )
    assert exc.value.stop_reason == "length"


def test_fireworks_provider_raises_on_validation_failure():
    """Schema mismatch wraps into the component error_cls — matches the
    Anthropic side's pydantic.ValidationError handling."""
    provider, _ = _fireworks_with_mock_create(
        _fake_openai_response('{"feasibility": "not_a_number", "middle_class_accessible": true, "reasoning": "x"}')
    )
    with pytest.raises(Stage1OutputError) as exc:
        provider.parse(
            error_cls=Stage1OutputError,
            model=FIREWORKS_DEFAULT_MODEL,
            max_tokens=2048,
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            output_format=Stage1Finding,
        )
    assert exc.value.stop_reason == "parse_error"


def test_fireworks_provider_wraps_sdk_exception():
    """Network / SDK-side errors wrap into error_cls with api_error
    stop_reason so the orchestrator's existing LLMOutputError handling
    catches them."""
    def boom(**_):
        raise RuntimeError("connection reset")

    provider, _ = _fireworks_with_mock_create(boom)
    with pytest.raises(Stage1OutputError) as exc:
        provider.parse(
            error_cls=Stage1OutputError,
            model=FIREWORKS_DEFAULT_MODEL,
            max_tokens=2048,
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            output_format=Stage1Finding,
        )
    assert exc.value.stop_reason == "api_error"


# --------------------------------------------------------------------- usage normalization


def test_fireworks_usage_reads_prompt_cache_hit_tokens_when_present():
    usage = _FakeOpenAIUsage(
        prompt_tokens=1000,
        completion_tokens=200,
        prompt_cache_hit_tokens=800,
    )
    provider, _ = _fireworks_with_mock_create(
        _fake_openai_response(
            '{"feasibility": 0.5, "middle_class_accessible": true, "reasoning": "x"}',
            usage=usage,
        )
    )
    parsed, normalized_usage, stop_reason = provider._parse_impl(
        error_cls=Stage1OutputError,
        detail="",
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    assert normalized_usage.input_tokens == 1000
    assert normalized_usage.output_tokens == 200
    assert normalized_usage.cache_read_input_tokens == 800
    # Fireworks has no client-driven cache_creation event.
    assert normalized_usage.cache_creation_input_tokens == 0


def test_fireworks_usage_falls_back_to_prompt_tokens_details_cached_tokens():
    usage = _FakeOpenAIUsage(
        prompt_tokens=500,
        completion_tokens=100,
        cached_tokens=300,
    )
    provider, _ = _fireworks_with_mock_create(
        _fake_openai_response(
            '{"feasibility": 0.5, "middle_class_accessible": true, "reasoning": "x"}',
            usage=usage,
        )
    )
    _, normalized_usage, _ = provider._parse_impl(
        error_cls=Stage1OutputError,
        detail="",
        model=FIREWORKS_DEFAULT_MODEL,
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    assert normalized_usage.cache_read_input_tokens == 300


# --------------------------------------------------------------------- audit-event parity


def test_audit_event_payload_keys_stable_across_providers(tmp_path):
    """The Sprint 8 audit contract — input_tokens / output_tokens /
    cache_read_input_tokens / cache_creation_input_tokens — survives
    the Sprint 14 provider migration. Verified by emitting one event
    from each provider name and diffing the payload key sets."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    telemetry = TelemetryContext(
        audit_log=audit, run_id="r", generation=1, island_id=0
    )
    usage = NormalizedUsage(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=7,
    )
    _emit_llm_usage_event(
        provider_name="anthropic",
        component="proposer",
        telemetry=telemetry,
        model="claude-sonnet-4-6",
        usage=usage,
        stop_reason="end_turn",
    )
    _emit_llm_usage_event(
        provider_name="fireworks",
        component="proposer",
        telemetry=telemetry,
        model=FIREWORKS_DEFAULT_MODEL,
        usage=usage,
        stop_reason="stop",
    )
    events = audit.read_all()
    assert len(events) == 2
    a, f = events
    # Same payload key set across providers — Sprint 8 contract.
    assert set(a.payload.keys()) == set(f.payload.keys())
    # `provider` is the new key from Sprint 14.
    assert a.payload["provider"] == "anthropic"
    assert f.payload["provider"] == "fireworks"
    # Token-count keys byte-stable.
    for k in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        assert k in a.payload
        assert k in f.payload


# --------------------------------------------------------------------- schema emission


@pytest.mark.parametrize(
    "model_cls",
    [Stage1Finding, Stage2Finding, RawFindingsBatch, Architecture, ClassificationVerdict],
)
def test_all_production_models_emit_json_schema(model_cls):
    """Every model used as `output_format=` must emit a JSON schema
    without crashing. This catches a Pydantic-side schema-feature
    regression before any live Fireworks call surfaces it."""
    schema = model_cls.model_json_schema()
    # Schema must be JSON-serializable so it can be sent in the request body.
    json.dumps(schema)
    # Schema must declare its root type.
    assert schema.get("type") == "object" or "$defs" in schema or "properties" in schema


# --------------------------------------------------------------------- factory


def test_factory_unknown_provider_name_raises():
    with pytest.raises(ValueError, match="unknown provider"):
        build_provider("openai-direct")


def test_factory_fireworks_requires_api_key(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    reset_provider_cache()
    with pytest.raises(RuntimeError, match="FIREWORKS_API_KEY"):
        build_provider("fireworks")


def test_factory_caches_by_name(monkeypatch):
    """Two build_provider('anthropic') calls return the same instance —
    keeps the underlying SDK client warm so per-component routing on
    the same provider shares cache state."""
    reset_provider_cache()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    a = build_provider("anthropic")
    b = build_provider("anthropic")
    assert a is b
    reset_provider_cache()


# --------------------------------------------------------------------- _flatten_system_to_text


def test_flatten_system_to_text_bare_string_passthrough():
    assert _flatten_system_to_text("just text") == "just text"


def test_flatten_system_to_text_list_of_dict_blocks():
    blocks = [
        {"type": "text", "text": "a"},
        {"type": "text", "text": "b", "cache_control": {"type": "ephemeral"}},
    ]
    assert _flatten_system_to_text(blocks) == "a\n\nb"


def test_flatten_system_to_text_skips_empty_strings():
    blocks = [{"type": "text", "text": ""}, {"type": "text", "text": "real"}]
    assert _flatten_system_to_text(blocks) == "real"


def test_flatten_system_to_text_handles_other_input_as_empty():
    assert _flatten_system_to_text(None) == ""


# --------------------------------------------------------------------- _strip_leading_think


def test_strip_leading_think_removes_block():
    assert _strip_leading_think("<think>reasoning</think>\n{}").strip() == "{}"


def test_strip_leading_think_noop_when_absent():
    assert _strip_leading_think("{\"x\": 1}") == "{\"x\": 1}"


def test_strip_leading_think_noop_when_unclosed():
    """Pathological case — half a think block. Leave content untouched
    rather than swallowing the whole rest of the string."""
    content = "<think>never closed{}"
    assert _strip_leading_think(content) == content


# --------------------------------------------------------------------- HP defaults


def test_hyperparameters_default_provider_routing_is_fireworks():
    """Sprint 14: all five LLM-calling components default to Fireworks."""
    hp = Hyperparameters()
    assert hp.provider_proposer == "fireworks"
    assert hp.provider_stage1 == "fireworks"
    assert hp.provider_stage2 == "fireworks"
    assert hp.provider_stage3 == "fireworks"
    assert hp.provider_curator == "fireworks"


def test_hyperparameters_default_model_is_deepseek_v4_flash():
    hp = Hyperparameters()
    assert hp.model_proposer == FIREWORKS_DEFAULT_MODEL
    assert hp.model_stage1 == FIREWORKS_DEFAULT_MODEL
    assert hp.model_stage2 == FIREWORKS_DEFAULT_MODEL
    assert hp.model_stage3 == FIREWORKS_DEFAULT_MODEL
    assert hp.model_curator == FIREWORKS_DEFAULT_MODEL


def test_hyperparameters_default_reasoning_effort_is_high():
    """Sprint 14 default is "high". The follow-up "max" bump was
    reverted after Super's smoke caught a 60% candidate-failure
    rate (3-of-9 to 4-of-9 Stage 3 framings succeeding under
    "max"; concurrent-load pressure exhausted the OpenAI SDK's
    retry budget). "high" ran 5/5 clean on the same setup. "max"
    remains overridable per-HP if a future sprint addresses the
    concurrency mitigation; default-on caused too many failures."""
    hp = Hyperparameters()
    assert hp.reasoning_effort_proposer == "high"
    assert hp.reasoning_effort_stage3 == "high"
    assert hp.reasoning_effort_curator == "high"


def test_hyperparameters_silently_ignores_pre_sprint14_routing_fields():
    """Backward compat: persisted hyperparameters JSON from older runs
    won't have the new routing fields. Loading them must not raise."""
    hp = Hyperparameters(num_islands=4, reset_every_generations=20)
    assert hp.num_islands == 4
    # The new fields fall back to defaults.
    assert hp.provider_proposer == "fireworks"


# --------------------------------------------------------------------- orchestrator routing


def test_build_component_providers_legacy_client_path_auto_wraps(tmp_path):
    """When the legacy `client` arg is supplied, every component shares
    the same auto-wrapped provider — bypasses HP per-component routing
    so the Sprint 8 MagicMock test pattern works unchanged."""
    from alphamo.orchestrator import _build_component_providers

    raw_client = MagicMock()
    hp = Hyperparameters()
    p1, p2, p3, p4, p5 = _build_component_providers(raw_client, hp)
    # All five components share one provider instance.
    assert p1 is p2 is p3 is p4 is p5
    assert isinstance(p1, AnthropicProvider)


def test_build_component_providers_passthrough_baseprovider():
    """If the caller already wrapped its client in a provider, reuse it."""
    from alphamo.orchestrator import _build_component_providers

    p = AnthropicProvider(MagicMock())
    hp = Hyperparameters()
    p1, p2, p3, p4, p5 = _build_component_providers(p, hp)
    assert p1 is p


def test_build_component_providers_routes_per_hp_when_client_none(monkeypatch):
    """When `client=None`, each component gets its own provider via
    the factory based on hp.provider_*. Verified by mocking the
    factory to inspect the names requested."""
    from alphamo import orchestrator as orch_mod

    requested: list[str] = []

    def fake_factory(name, **kw):
        requested.append(name)
        return AnthropicProvider(MagicMock())

    monkeypatch.setattr(orch_mod, "build_provider", fake_factory)
    hp = Hyperparameters(
        provider_proposer="anthropic",
        provider_stage1="fireworks",
        provider_stage2="fireworks",
        provider_stage3="anthropic",
        provider_curator="fireworks",
    )
    orch_mod._build_component_providers(None, hp)
    assert requested == [
        "anthropic",
        "fireworks",
        "fireworks",
        "anthropic",
        "fireworks",
    ]


# --------------------------------------------------------------------- AnthropicProvider regression sanity


def test_anthropic_provider_call_shape_matches_legacy_parse_or_raise():
    """Regression guard: AnthropicProvider passes the kwargs through
    to `client.messages.parse(...)` in the exact shape the Sprint 13
    `parse_or_raise()` produced. If this diverges, every existing
    MagicMock test silently observes the wrong call shape."""
    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Stage1Finding(
            feasibility=0.5, middle_class_accessible=True, reasoning="x"
        )
    )
    provider = AnthropicProvider(client)
    provider.parse(
        error_cls=Stage1OutputError,
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=[{"type": "text", "text": "S", "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
        thinking={"type": "enabled", "budget_tokens": 1000},
    )
    kwargs = client.messages.parse.call_args[1]
    assert kwargs["model"] == "claude-haiku-4-5"
    assert kwargs["max_tokens"] == 2048
    # cache_control markers passed through verbatim — Anthropic API
    # consumes them directly.
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 1000}
    assert kwargs["output_format"] is Stage1Finding


def test_anthropic_provider_omits_thinking_when_not_supplied():
    """thinking=None must NOT appear in the kwargs forwarded to the SDK
    — the Anthropic SDK rejects `thinking=None` on models that don't
    support thinking (Stage 1 Haiku path)."""
    from tests.fixtures.parsed_message import FakeParsedMessage

    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Stage1Finding(
            feasibility=0.5, middle_class_accessible=True, reasoning="x"
        )
    )
    provider = AnthropicProvider(client)
    provider.parse(
        error_cls=Stage1OutputError,
        model="claude-haiku-4-5",
        max_tokens=2048,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        output_format=Stage1Finding,
    )
    kwargs = client.messages.parse.call_args[1]
    assert "thinking" not in kwargs


# --------------------------------------------------------------------- Sprint 14 follow-up: prompt + schema + aggregator


def test_raw_findings_batch_assessment_field_is_required():
    """Sprint 14 follow-up v2: `assessment` was promoted from optional
    (default None) to required (Field(...)). The model MUST emit the
    field on every call — explicit null when findings is non-empty,
    a string when findings is empty. Making the field required puts
    it in the JSON-schema `required` array, blocking the model from
    structurally opting out by omission (which the v1 default-null
    shape allowed, and which the model honored on every clean pass)."""
    # Required: omission raises.
    with pytest.raises(pydantic.ValidationError):
        RawFindingsBatch(findings=[])  # type: ignore[call-arg]
    # Explicit null when findings is non-empty — valid.
    from alphamo.schemas.findings import RawFinding, Severity

    batch = RawFindingsBatch(
        findings=[
            RawFinding(
                claim="c", evidence="e",
                falsification_condition="if X",
                severity=Severity.LOW,
            )
        ],
        assessment=None,
    )
    assert batch.assessment is None
    # Explicit string when findings is empty — valid.
    batch = RawFindingsBatch(
        findings=[],
        assessment="no regulatory exposure: architecture is operator-licensed throughout",
    )
    assert batch.assessment.startswith("no regulatory exposure")


def test_raw_findings_batch_schema_marks_assessment_as_required():
    """Regression guard for the v2 shape — the schema emitted to
    Fireworks must list `assessment` in `required`. The optional shape
    (where assessment was absent from required) is what let the model
    skip the field structurally. If a future Pydantic upgrade or
    field-default refactor silently demotes this back to optional,
    the audit-log assessments stop appearing again with no error."""
    schema = RawFindingsBatch.model_json_schema()
    assert "assessment" in schema["required"]
    assert "findings" in schema["required"]


def test_stage4_prompts_include_citation_discipline_instruction():
    """The per-framing system prompt must instruct the model to avoid
    fabricated statute citations — describe principles rather than
    cite section numbers it isn't certain about."""
    from alphamo.prompts.stage4_prompts import (
        DEFAULT_FRAMINGS,
        stage4_system,
    )

    for framing in DEFAULT_FRAMINGS:
        prompt = stage4_system(framing)
        assert "CITATION DISCIPLINE" in prompt
        assert "certain it exists" in prompt
        # Reference to the alternative pattern the discipline allows.
        assert (
            "federal consumer protection authority" in prompt
            or "describe the legal principle" in prompt
        )


def test_stage4_prompts_include_explicit_assessment_instruction():
    """Every framing's system prompt must instruct the model to
    populate the `assessment` field on clean passes — explicit 'no
    concerns' is more valuable than silence for the closed-RL-loop."""
    from alphamo.prompts.stage4_prompts import (
        DEFAULT_FRAMINGS,
        stage4_system,
    )

    for framing in DEFAULT_FRAMINGS:
        prompt = stage4_system(framing)
        assert "EXPLICIT ASSESSMENT" in prompt
        assert "`assessment`" in prompt
        assert "no identifiable vulnerability" in prompt


def test_stage4_aggregator_surfaces_clean_framing_assessments_in_reasoning():
    """When some framings return clean with an assessment, the
    aggregator's reasoning string must include 'Clean-framing
    assessments —' followed by per-framing text. This is the
    closed-RL-loop signal that the framing actively evaluated and
    found nothing, rather than being silent."""
    from alphamo.evaluator.stage4_adversarial import stage4_adversarial
    from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
    from tests.fixtures.parsed_message import FakeParsedMessage

    # Build a client whose framings return clean (empty findings) WITH
    # assessment text. All 9 framings clean → no concerns generated.
    assessment_template = (
        "the architecture's mechanism is structurally sound under "
        "this framing because X, Y, Z"
    )

    def parse_side_effect(**kwargs):
        return FakeParsedMessage(
            RawFindingsBatch(findings=[], assessment=assessment_template),
            stop_reason="end_turn",
        )

    client = MagicMock()
    client.messages.parse.side_effect = parse_side_effect

    result = stage4_adversarial(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framings=DEFAULT_FRAMINGS,
    )

    assert "Clean-framing assessments —" in result.reasoning
    # Every clean framing's assessment text appears in the reasoning.
    for framing in DEFAULT_FRAMINGS:
        assert framing in result.reasoning


def test_stage4_aggregator_skips_assessment_section_when_no_assessments():
    """If no clean framing populated `assessment`, the reasoning
    string must NOT include the 'Clean-framing assessments' header.
    Avoids dangling empty section text in the audit log when the
    model ignores the new instruction (old DB rows / pre-prompt
    bump / models that don't honor the field)."""
    from alphamo.evaluator.stage4_adversarial import stage4_adversarial
    from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS
    from tests.fixtures.parsed_message import FakeParsedMessage

    def parse_side_effect(**kwargs):
        # All clean, with explicit null assessments — under the
        # required-field schema (v2), null is the model's way of
        # saying "no useful explanation to surface". The aggregator
        # must skip these (None is falsy) and NOT emit the
        # "Clean-framing assessments —" header.
        return FakeParsedMessage(
            RawFindingsBatch(findings=[], assessment=None), stop_reason="end_turn"
        )

    client = MagicMock()
    client.messages.parse.side_effect = parse_side_effect

    result = stage4_adversarial(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framings=DEFAULT_FRAMINGS,
    )
    assert "Clean-framing assessments" not in result.reasoning


def test_run_framing_returns_concerns_and_assessment_tuple():
    """Sprint 14 follow-up: _run_framing now returns (concerns,
    assessment). The aggregator depends on this tuple shape."""
    from alphamo.evaluator.stage4_adversarial import _run_framing
    from alphamo.schemas.findings import RawFinding, Severity
    from tests.fixtures.parsed_message import FakeParsedMessage

    def parse_side_effect(**kwargs):
        return FakeParsedMessage(
            RawFindingsBatch(
                findings=[
                    RawFinding(
                        claim="c", evidence="e",
                        falsification_condition="if X",
                        severity=Severity.MEDIUM,
                    )
                ],
                assessment=None,
            ),
            stop_reason="end_turn",
        )

    client = MagicMock()
    client.messages.parse.side_effect = parse_side_effect

    result = _run_framing(
        Architecture(
            name="g", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        ),
        client,
        framing="regulatory",
        model=FIREWORKS_DEFAULT_MODEL,
    )
    assert isinstance(result, tuple)
    assert len(result) == 2
    concerns, assessment = result
    assert len(concerns) == 1
    assert concerns[0].framing == "regulatory"
    assert assessment is None
