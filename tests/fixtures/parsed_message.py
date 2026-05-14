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

    Nothing else. Anything else raises AttributeError via __slots__.
    """

    __slots__ = ("parsed_output", "stop_reason", "content")

    def __init__(
        self,
        parsed_output: Any,
        *,
        stop_reason: str | None = "end_turn",
        content: list[FakeContentBlock] | None = None,
    ) -> None:
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason
        self.content = content if content is not None else [FakeContentBlock()]
