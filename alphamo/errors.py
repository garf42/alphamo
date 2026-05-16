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
"""

from __future__ import annotations

from typing import Any, Iterable

import pydantic


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


class ResearchOutputError(LLMOutputError):
    COMPONENT = "research"


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
    **parse_kwargs: Any,
) -> Any:
    """Call client.messages.parse(...) and roll any output-side failure into error_cls.

    Catches both pydantic.ValidationError (truncation / schema mismatch
    raised inside parse_response) and parsed_output=None (refusal /
    tool-only turn). Returns the validated `parsed_output` instance on
    success.
    """
    try:
        result = client.messages.parse(**parse_kwargs)
    except pydantic.ValidationError as exc:
        raise error_cls.from_validation_error(exc, detail=detail) from exc
    parsed = result.parsed_output
    if parsed is None:
        raise error_cls.from_response(result, detail=detail)
    return parsed
