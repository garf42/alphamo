"""Anthropic provider — wraps `anthropic.Anthropic` and preserves Sprint 13 behavior.

This is the AlphaMo pre-Sprint-14 call shape unchanged: `client.messages.parse()`
with the SDK's `output_format=PydanticModel` post-parser callback, the same
two failure modes (truncation → pydantic.ValidationError; refusal/tool-only
turn → `parsed_output is None`), and the same `usage` field reads.

Existing tests mocking `client.messages.parse` continue to work because this
provider issues that exact call against `self._client`. The constructor
accepts any object with `.messages.parse(...)` — production passes an
`anthropic.Anthropic(max_retries=3)`; tests pass a `MagicMock()`.
"""

from __future__ import annotations

from typing import Any

import pydantic
from pydantic import BaseModel

from alphamo.providers.base import BaseProvider, NormalizedUsage


class AnthropicProvider(BaseProvider):
    """Wraps an Anthropic SDK client. Preserves Sprint 8/12/13 behavior byte-for-byte.

    The cache_control markers Sprint 12's `prepare_cached_blocks` produces
    are passed through unchanged — Anthropic's API consumes them
    directly.
    """

    PROVIDER_NAME = "anthropic"

    def __init__(self, client: Any) -> None:
        self._client = client

    def _parse_impl(
        self,
        *,
        error_cls,
        detail: str,
        model: str,
        max_tokens: int,
        system: Any,
        messages: list[dict[str, Any]],
        output_format: type[BaseModel],
        thinking: dict[str, Any] | None = None,
        **kw: Any,
    ) -> tuple[BaseModel, NormalizedUsage, str]:
        parse_kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_format=output_format,
            **kw,
        )
        if thinking is not None:
            parse_kwargs["thinking"] = thinking

        try:
            result = self._client.messages.parse(**parse_kwargs)
        except pydantic.ValidationError as exc:
            raise error_cls.from_validation_error(exc, detail=detail) from exc

        parsed = result.parsed_output
        if parsed is None:
            raise error_cls.from_response(result, detail=detail)

        usage_obj = getattr(result, "usage", None)
        usage = NormalizedUsage(
            input_tokens=int(getattr(usage_obj, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage_obj, "output_tokens", 0) or 0),
            cache_creation_input_tokens=int(
                getattr(usage_obj, "cache_creation_input_tokens", 0) or 0
            ),
            cache_read_input_tokens=int(
                getattr(usage_obj, "cache_read_input_tokens", 0) or 0
            ),
        )
        stop_reason = getattr(result, "stop_reason", "unknown") or "unknown"
        return parsed, usage, stop_reason
