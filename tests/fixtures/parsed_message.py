"""Typed stand-in for anthropic.types.parsed_message.ParsedMessage in tests.

We tried `MagicMock(spec=ParsedMessage)`; spec= correctly blocks
`.parsed` access (the original bug) but also blocks `.stop_reason` and
`.content`, which are Pydantic-field-declared attributes spec= does not
introspect. A typed fixture class is cleaner and more honest about what
the production code actually reads off a parsed response.

__slots__ is the structural guarantee: any attribute the production code
reads that isn't in the slot list will raise AttributeError instead of
silently returning a MagicMock child — which is exactly the false-green
pattern that hid the original .parsed-vs-.parsed_output bug.
"""

from __future__ import annotations

from typing import Any


class FakeContentBlock:
    """Minimal content-block shape: just enough for the .type attribute."""

    __slots__ = ("type", "text")

    def __init__(self, type_: str = "text", text: str = "") -> None:
        self.type = type_
        self.text = text


class FakeParsedMessage:
    """Production code reads: .parsed_output, .stop_reason, .content[*].type.
    Sprint 8: .usage is also read for telemetry — see `usage` slot.

    Nothing else. Anything else raises AttributeError via __slots__.
    """

    __slots__ = ("parsed_output", "stop_reason", "content", "usage")

    def __init__(
        self,
        parsed_output: Any,
        *,
        stop_reason: str | None = "end_turn",
        content: list[FakeContentBlock] | None = None,
        usage: Any = None,
    ) -> None:
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason
        self.content = content if content is not None else [FakeContentBlock()]
        # Sprint 8: telemetry. Tests that want to assert against usage
        # set this in __init__ or after construction. Defaults to None,
        # which `_emit_llm_usage_event` treats as "no usage data" and
        # records all token counts as zero.
        self.usage = usage


def make_truncation_error() -> Any:
    """Build a real pydantic.ValidationError to simulate SDK-side JSON truncation.

    The SDK's parse_response calls TypeAdapter(output_format).validate_json(text)
    inside its post-parser callback. When the response was truncated at
    max_tokens the text ends mid-string, validate_json raises
    pydantic.ValidationError, and that exception flies out of
    client.messages.parse(...) before any ParsedMessage exists. Setting
    `client.messages.parse.side_effect = make_truncation_error()` on a
    MagicMock reproduces that exception path faithfully.
    """
    import pydantic
    from pydantic import BaseModel, TypeAdapter

    class _Probe(BaseModel):
        name: str
        summary: str

    try:
        TypeAdapter(_Probe).validate_json('{"name": "Proprietary Ben')
    except pydantic.ValidationError as exc:
        return exc
    raise RuntimeError("expected pydantic.ValidationError")
