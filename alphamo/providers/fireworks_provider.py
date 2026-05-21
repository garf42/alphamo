"""Fireworks provider — OpenAI-SDK client pointed at Fireworks, DeepSeek V4 Flash.

Fireworks exposes an OpenAI-compatible chat-completions surface at
`https://api.fireworks.ai/inference/v1`. Structured output is enforced
via `response_format={"type":"json_schema","json_schema":{...}}` with
the Pydantic model's `model_json_schema()` as the schema body — the
inference engine constrains generation to the schema. We then parse the
returned text with `output_format.model_validate_json()` to surface any
final schema-shape failures.

Caching on Fireworks is automatic — the API finds the longest cached
prefix and reuses it, no client-driven markers. We strip the Sprint 12
`cache_control` keys before sending and concatenate the cached text
blocks into a single system message. The cache hot-path still fires
because the corpus block stays byte-stable across the run.

Reasoning on DeepSeek V4 has three discrete modes (Non-think / Think
High / Think Max). We surface this as `reasoning_effort` and pass it
through `extra_body` so the OpenAI SDK doesn't validate it — Fireworks
honors the field directly. Mapping from our Anthropic-side
`thinking={"type":"enabled","budget_tokens":N}` config is done in the
call site (proposer.py / stage4_adversarial.py / curator.py read the
new HP fields), not here — this provider just passes through whatever
`reasoning_effort` value the caller supplied.
"""

from __future__ import annotations

import json
from typing import Any

import pydantic
from pydantic import BaseModel

from alphamo.providers.base import BaseProvider, NormalizedUsage

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
FIREWORKS_DEFAULT_MODEL = "accounts/fireworks/models/deepseek-v4-flash"


def _flatten_system_to_text(system: Any) -> str:
    """Strip Sprint 12 cache_control markers; concatenate text blocks.

    Anthropic-shaped input: list of {"type":"text","text":"…","cache_control":…}
    dicts. Fireworks does not consume cache_control — caching is automatic
    on prefix match. We just need the concatenated text for the system
    message; the corpus block being byte-stable across the run keeps the
    cache hot regardless.

    Bare-string input (e.g. legacy callers, simple system prompts) passes
    through unchanged.
    """
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        parts: list[str] = []
        for block in system:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n\n".join(parts)
    return ""


def _coerce_user_content_to_text(content: Any) -> str:
    """OpenAI's chat-completions content is `str | list[dict]`; AlphaMo
    passes plain strings in `render_candidate(...)` / `render_seeds(...)`.
    Defensive coercion for the list-of-blocks variant if any caller ever
    starts producing it."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


class FireworksProvider(BaseProvider):
    """OpenAI-SDK client targeting Fireworks. Default model: DeepSeek V4 Flash.

    `api_key` is read from the `FIREWORKS_API_KEY` env var via the
    factory; pass `api_key=` directly only in tests.

    `max_retries` is plumbed through to the OpenAI SDK (its built-in
    retry layer covers 408/409/429/500+ and connection/timeout errors
    with exponential backoff, matching the Anthropic SDK's behavior at
    `max_retries=3`).
    """

    PROVIDER_NAME = "fireworks"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = FIREWORKS_BASE_URL,
        max_retries: int = 3,
        client: Any = None,
    ) -> None:
        if client is not None:
            self._client = client
            return
        import openai

        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
        )

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
        reasoning_effort: str | None = None,
        **kw: Any,
    ) -> tuple[BaseModel, NormalizedUsage, str]:
        system_text = _flatten_system_to_text(system)
        oai_messages: list[dict[str, Any]] = []
        if system_text:
            oai_messages.append({"role": "system", "content": system_text})
        for m in messages:
            oai_messages.append(
                {
                    "role": m["role"],
                    "content": _coerce_user_content_to_text(m["content"]),
                }
            )

        schema = output_format.model_json_schema()
        request_kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=oai_messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": output_format.__name__,
                    "schema": schema,
                },
            },
        )
        # `extra_body` is the OpenAI-SDK escape hatch for provider-
        # specific fields. Fireworks consumes `reasoning_effort` here;
        # it controls thinking mode by itself (Non-think / High / Max).
        # The legacy Anthropic `thinking={...}` field arrives unused
        # at this provider; silently ignored.
        #
        # Sprint 14 hotfix: we previously also sent
        # `extra_body["thinking"] = {"type": "enabled"}` for
        # explicitness, but Fireworks rejects requests that set both
        # `thinking` and `reasoning_effort` (HTTP 400: "cannot specify
        # both 'thinking' and 'reasoning_effort'"). The error was
        # tolerated at `reasoning_effort="high"` but enforced strictly
        # at `"max"`. `reasoning_effort` alone is sufficient; thinking
        # mode is implied.
        extra_body: dict[str, Any] = {}
        if reasoning_effort is not None:
            extra_body["reasoning_effort"] = reasoning_effort
        if extra_body:
            request_kwargs["extra_body"] = extra_body

        # Allow callers to pass through additional OpenAI-SDK fields
        # (temperature, top_p, etc.) we don't currently use, without
        # breaking the abstraction.
        for k, v in kw.items():
            if k not in request_kwargs:
                request_kwargs[k] = v

        try:
            response = self._client.chat.completions.create(**request_kwargs)
        except Exception as exc:  # noqa: BLE001
            raise error_cls(
                stop_reason="api_error",
                content_block_types=[],
                detail=(
                    f"{detail}: {type(exc).__name__}: {str(exc)[:300]}"
                    if detail
                    else f"{type(exc).__name__}: {str(exc)[:300]}"
                ),
            ) from exc

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise error_cls(
                stop_reason="no_choices",
                content_block_types=[],
                detail=detail or "response.choices is empty",
            )
        message = choices[0].message
        content = getattr(message, "content", None)
        finish_reason = getattr(choices[0], "finish_reason", "unknown") or "unknown"
        if not content:
            raise error_cls(
                stop_reason=finish_reason,
                content_block_types=[],
                detail=detail or "response.choices[0].message.content is empty",
            )

        try:
            parsed = output_format.model_validate_json(content)
        except pydantic.ValidationError as exc:
            try:
                # Some Fireworks responses prepend `<think>` blocks even
                # when reasoning_effort is set; strip a leading think
                # block and retry validation once before giving up.
                stripped = _strip_leading_think(content)
                if stripped != content:
                    parsed = output_format.model_validate_json(stripped)
                else:
                    raise
            except (pydantic.ValidationError, json.JSONDecodeError):
                raise error_cls.from_validation_error(exc, detail=detail) from exc

        usage_obj = getattr(response, "usage", None)
        input_tokens = int(getattr(usage_obj, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)
        # Fireworks/DeepSeek surfaces cached-prefix tokens as
        # prompt_cache_hit_tokens (DeepSeek-native field name).
        # Some deployments place it under prompt_tokens_details.cached_tokens
        # (OpenAI-compat shape); read both with fallback.
        cache_read = int(getattr(usage_obj, "prompt_cache_hit_tokens", 0) or 0)
        if cache_read == 0:
            details = getattr(usage_obj, "prompt_tokens_details", None)
            cache_read = int(getattr(details, "cached_tokens", 0) or 0)

        usage = NormalizedUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            # Fireworks caching is automatic — no client-driven
            # creation event. Always 0 on this provider.
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cache_read,
        )
        return parsed, usage, finish_reason


def _strip_leading_think(content: str) -> str:
    """Strip a leading `<think>…</think>` block if present.

    DeepSeek reasoning models can emit a think block before the JSON
    payload. Fireworks's grammar-mode enforcement should suppress this
    when response_format is set, but we defensively strip anyway —
    one retry only, so legitimate JSON-shape failures still surface.
    """
    text = content.lstrip()
    if not text.startswith("<think>"):
        return content
    end = text.find("</think>")
    if end == -1:
        return content
    return text[end + len("</think>"):].lstrip()
