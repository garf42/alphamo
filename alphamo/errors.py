"""Errors raised when an LLM call returns malformed or empty parsed output.

`client.messages.parse(...)` can fail in two ways for a structured-output
call:

  1. ParsedMessage.parsed_output is None — the model emitted no JSON-schema
     text block (refusal, tool-only turn, or stop_sequence cut-off before
     the structured payload).
  2. pydantic.ValidationError raised inside the SDK's parse_response — the
     model emitted text that won't validate against the schema. Most
     common cause: the response was truncated at max_tokens and the JSON
     ends mid-string.

Both failure modes are wrapped into a component-specific subclass of
LLMOutputError so the orchestrator can decide whether to continue
(transient — single failure) or halt (persistent — N consecutive).

Sprint 8: `parse_or_raise` also emits an `llm_usage` audit event on
success when a `TelemetryContext` is supplied. This is the single
instrumentation point covering every cascade stage + proposer + curator
+ research — adding telemetry here gives universal coverage with one
edit. Without it, prompt-caching work is unmeasurable (we can't tell if
`cached_system()` markers are actually producing cache hits).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

import pydantic

if TYPE_CHECKING:
    from alphamo.meta.audit_log import AuditLog


LLM_USAGE_TRIGGER = "llm_usage"


@dataclass(frozen=True)
class TelemetryContext:
    """Bundle of per-call attribution fields for the `llm_usage` audit event.

    Passed as one optional kwarg through call chains so individual
    function signatures don't need to thread four separate parameters.
    The orchestrator builds this in `step()` and `_bootstrap_islands()`;
    components (cascade, proposer, curator, research) forward it through
    to `parse_or_raise` unchanged.

    `generation` is None on bootstrap-side calls (the trivial seed is
    scored at gen 0 but the bootstrap path may emit before the loop
    enters). `island_id` is None on calls that aren't bound to a single
    island (meta-layer research, bootstrap, harvest re-cascade).
    """

    audit_log: "AuditLog"
    run_id: str
    generation: int | None = None
    island_id: int | None = None


class LLMOutputError(Exception):
    """Raised when an LLM-calling component fails to produce parsed output.

    Carries the response's stop_reason and content-block types so the
    failure is diagnosable without needing to log the full response body.
    `stop_reason="parse_error"` is used when the SDK raised a
    pydantic.ValidationError before the response object was available.
    """

    COMPONENT: str = "llm"

    def __init__(
        self,
        *,
        stop_reason: str | None = None,
        content_block_types: Iterable[str] = (),
        detail: str = "",
    ) -> None:
        self.stop_reason = stop_reason
        self.content_block_types = list(content_block_types)
        self.detail = detail
        msg = (
            f"{self.COMPONENT}: parsed output unavailable "
            f"(stop_reason={stop_reason!r}, "
            f"content_block_types={self.content_block_types})"
        )
        if detail:
            msg += f": {detail}"
        super().__init__(msg)

    @classmethod
    def from_response(cls, response: Any, detail: str = "") -> "LLMOutputError":
        """Build the error from a ParsedMessage-shaped response object."""
        stop_reason = getattr(response, "stop_reason", None)
        content = getattr(response, "content", None) or []
        types: list[str] = []
        for block in content:
            types.append(getattr(block, "type", type(block).__name__))
        return cls(
            stop_reason=stop_reason,
            content_block_types=types,
            detail=detail,
        )

    @classmethod
    def from_validation_error(
        cls,
        exc: pydantic.ValidationError,
        detail: str = "",
    ) -> "LLMOutputError":
        """Build the error from a pydantic.ValidationError raised inside the SDK.

        We don't have a ParsedMessage to inspect — the SDK raised before
        constructing one. stop_reason='parse_error' marks this case so the
        orchestrator can distinguish truncation/schema failures from
        explicit refusals if it ever cares to.
        """
        suffix = f"validation failed (likely truncation or schema mismatch): {str(exc)[:300]}"
        return cls(
            stop_reason="parse_error",
            content_block_types=[],
            detail=f"{detail}: {suffix}" if detail else suffix,
        )


class ProposerOutputError(LLMOutputError):
    COMPONENT = "proposer"


class CuratorOutputError(LLMOutputError):
    COMPONENT = "curator"


class Stage1OutputError(LLMOutputError):
    COMPONENT = "stage1_feasibility"


class Stage2OutputError(LLMOutputError):
    COMPONENT = "stage2_structured"


class Stage4OutputError(LLMOutputError):
    COMPONENT = "stage4_adversarial"


def parse_or_raise(
    client: Any,
    error_cls: type[LLMOutputError],
    *,
    detail: str = "",
    component: str | None = None,
    telemetry: TelemetryContext | None = None,
    **parse_kwargs: Any,
) -> Any:
    """Call client.messages.parse(...) and roll any output-side failure into error_cls.

    Catches both pydantic.ValidationError (truncation / schema mismatch
    raised inside parse_response) and parsed_output=None (refusal /
    tool-only turn). Returns the validated `parsed_output` instance on
    success.

    Sprint 8: when both `component` and `telemetry` are supplied, emits
    an `llm_usage` audit event with input/output token counts and
    cache_creation/cache_read token counts. Both are optional so legacy
    callers and tests (those without an audit log handy) continue to
    work unchanged. Telemetry only fires on the SUCCESS path — failure
    paths are covered by the existing `proposer_failure` /
    `cascade_failure` / `stage3_*` audit events from Sprint 4 + 7.
    """
    try:
        result = client.messages.parse(**parse_kwargs)
    except pydantic.ValidationError as exc:
        raise error_cls.from_validation_error(exc, detail=detail) from exc
    parsed = result.parsed_output
    if parsed is None:
        raise error_cls.from_response(result, detail=detail)
    if component is not None and telemetry is not None:
        _emit_llm_usage_event(
            component=component,
            telemetry=telemetry,
            model=parse_kwargs.get("model", "unknown"),
            response=result,
        )
    return parsed


def _emit_llm_usage_event(
    *,
    component: str,
    telemetry: TelemetryContext,
    model: str,
    response: Any,
) -> None:
    """Write one `llm_usage` audit event to the run's audit log.

    Defensive about response.usage shape: the SDK normally exposes
    `input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
    `cache_read_input_tokens` as attributes, but cache fields are 0 (or
    absent on older SDK versions) when caching wasn't used. `getattr`
    with default=0 absorbs both cases without crashing.

    Import of `AuditEvent` is local to avoid a cycle if `audit_log` ever
    starts importing from `errors`.
    """
    from alphamo.meta.audit_log import AuditEvent

    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    cache_creation = int(
        getattr(usage, "cache_creation_input_tokens", 0) or 0
    )
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    stop_reason = getattr(response, "stop_reason", "unknown") or "unknown"

    telemetry.audit_log.append(
        AuditEvent(
            timestamp=telemetry.audit_log.now(),
            run_id=telemetry.run_id,
            trigger=LLM_USAGE_TRIGGER,
            classification="routine",
            action="recorded",
            rationale=(
                f"component={component} model={model} "
                f"input={input_tokens} output={output_tokens} "
                f"cache_read={cache_read} cache_write={cache_creation}"
            ),
            payload={
                "component": component,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
                "generation": telemetry.generation,
                "island_id": telemetry.island_id,
                "stop_reason": stop_reason,
            },
        )
    )
