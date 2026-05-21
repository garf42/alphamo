"""Provider abstraction: one `parse()` entry, two implementations.

Sprint 14: AlphaMo's LLM calls used to go through `parse_or_raise()` in
`alphamo.errors`, which was Anthropic-SDK-specific (it called
`client.messages.parse(...)` and read `response.usage.input_tokens` /
`cache_read_input_tokens`). This module is the new seam.

Every call site asks `provider.parse(...)` for a parsed Pydantic model.
Providers handle:
  - SDK call shape (Anthropic's `messages.parse` vs OpenAI's
    `chat.completions.create` + json_schema response_format)
  - Cache marker translation (Anthropic ephemeral cache_control vs
    Fireworks automatic-prefix caching — different request shapes,
    Sprint 12's `prepare_cached_blocks()` is the input both consume)
  - Reasoning/thinking config (Anthropic's `thinking={enabled, budget}`
    vs Fireworks DeepSeek's discrete `reasoning_effort` modes)
  - Token-usage normalization (different field names; one shared dataclass)
  - `llm_usage` audit emission (the Sprint 8 instrumentation point;
    payload keys are stable across providers)

`BaseProvider` is a real class — not a typing.Protocol — because we use
`isinstance(...)` checks at call sites to auto-wrap loose Anthropic
client objects (preserves the Sprint 8 `MagicMock(client).messages.parse`
test pattern unchanged). A runtime-checkable Protocol would pass a
MagicMock as a "provider" by accident.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from alphamo.errors import LLMOutputError, TelemetryContext


LLM_USAGE_TRIGGER = "llm_usage"


@dataclass(frozen=True)
class NormalizedUsage:
    """Provider-agnostic token-usage shape used by the audit log.

    Field names match the Anthropic SDK's usage object (the original
    instrumentation target in Sprint 8) so audit.jsonl byte-shape is
    preserved across the migration. Fireworks-side fields map as:
      - `prompt_tokens` → `input_tokens`
      - `completion_tokens` → `output_tokens`
      - `prompt_cache_hit_tokens` → `cache_read_input_tokens`
      - cache_creation has no Fireworks equivalent (caching is
        automatic on Fireworks, no client-driven creation event);
        always 0 on Fireworks-emitted events.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


class BaseProvider(ABC):
    """Common interface for LLM providers.

    Subclasses implement `_parse_impl()`, which is responsible for:
      - issuing the SDK call
      - translating provider-specific failures (e.g. truncation →
        pydantic.ValidationError, refusal → empty content) into the
        component-specific `error_cls` (an LLMOutputError subclass)
      - returning (parsed, usage, stop_reason)

    `parse()` is the call-site entry. It handles telemetry emission
    on success — failure paths are covered by the existing
    `proposer_failure` / `cascade_failure` / `stage3_*` audit events
    in the orchestrator.
    """

    PROVIDER_NAME: ClassVar[str] = "base"

    @abstractmethod
    def _parse_impl(
        self,
        *,
        error_cls: type["LLMOutputError"],
        detail: str,
        model: str,
        max_tokens: int,
        system: Any,
        messages: list[dict[str, Any]],
        output_format: type[BaseModel],
        thinking: dict[str, Any] | None = None,
        **kw: Any,
    ) -> tuple[BaseModel, NormalizedUsage, str]:
        """Return (parsed_model, usage, stop_reason) or raise error_cls.

        `system` is the Sprint 12 `prepare_cached_blocks` output —
        a list of {"type":"text","text":...,"cache_control":...} dicts.
        Providers translate it into their native request shape:
        Anthropic passes it through verbatim; Fireworks concatenates
        the texts and discards the cache_control markers (caching is
        automatic on Fireworks).
        """

    def parse(
        self,
        *,
        error_cls: type["LLMOutputError"],
        component: str | None = None,
        telemetry: "TelemetryContext | None" = None,
        detail: str = "",
        **parse_kwargs: Any,
    ) -> BaseModel:
        """Issue the call, emit telemetry on success, return parsed model.

        Mirrors the legacy `parse_or_raise()` signature so call-site
        migrations are 1:1 — drop the `client` positional, pass
        `error_cls=` instead of as a positional, keep everything else.
        """
        parsed, usage, stop_reason = self._parse_impl(
            error_cls=error_cls,
            detail=detail,
            **parse_kwargs,
        )
        if component is not None and telemetry is not None:
            _emit_llm_usage_event(
                provider_name=self.PROVIDER_NAME,
                component=component,
                telemetry=telemetry,
                model=parse_kwargs.get("model", "unknown"),
                usage=usage,
                stop_reason=stop_reason,
            )
        return parsed


def _emit_llm_usage_event(
    *,
    provider_name: str,
    component: str,
    telemetry: "TelemetryContext",
    model: str,
    usage: NormalizedUsage,
    stop_reason: str,
) -> None:
    """Write one `llm_usage` audit event.

    Payload key shape is the Sprint 8 contract — input_tokens /
    output_tokens / cache_creation_input_tokens / cache_read_input_tokens
    are byte-stable across providers so downstream consumers (audit
    scripts, the harvest's verification trail) don't need a provider
    branch. `provider` is a new top-level payload key so post-run
    analysis can split by provider in mixed-routing experiments.
    """
    from alphamo.meta.audit_log import AuditEvent

    telemetry.audit_log.append(
        AuditEvent(
            timestamp=telemetry.audit_log.now(),
            run_id=telemetry.run_id,
            trigger=LLM_USAGE_TRIGGER,
            classification="routine",
            action="recorded",
            rationale=(
                f"component={component} provider={provider_name} model={model} "
                f"input={usage.input_tokens} output={usage.output_tokens} "
                f"cache_read={usage.cache_read_input_tokens} "
                f"cache_write={usage.cache_creation_input_tokens}"
            ),
            payload={
                "component": component,
                "provider": provider_name,
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_creation_input_tokens": usage.cache_creation_input_tokens,
                "cache_read_input_tokens": usage.cache_read_input_tokens,
                "generation": telemetry.generation,
                "island_id": telemetry.island_id,
                "stop_reason": stop_reason,
            },
        )
    )


def ensure_provider(obj: Any) -> BaseProvider:
    """Auto-wrap a loose Anthropic-shaped client into an AnthropicProvider.

    Sprint 14 migration helper. Call sites' constructors and stage
    functions used to accept `client: anthropic.Anthropic`; they now
    accept `provider: BaseProvider`. This wrapper makes both shapes
    work so the existing `MagicMock()` test pattern (set
    `.messages.parse.return_value = …` and pass the mock directly) is
    preserved without touching ~20 test files.

    Anything inheriting from BaseProvider passes through unchanged.
    Anything else is treated as an Anthropic-shaped client object
    (whether `anthropic.Anthropic`, a MagicMock with `.messages.parse`,
    or a custom shim) and wrapped.
    """
    if isinstance(obj, BaseProvider):
        return obj
    from alphamo.providers.anthropic_provider import AnthropicProvider

    return AnthropicProvider(obj)
