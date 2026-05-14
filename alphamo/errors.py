"""Errors raised when an LLM call returns malformed or empty parsed output.

`client.messages.parse(...).parsed_output` is `Optional[ResponseFormatT]`.
A None return means the model emitted no JSON-schema text block — typically
a refusal, a tool-only turn, or a stop_sequence cut-off before the
structured payload landed. Each LLM-calling component raises a subclass of
LLMOutputError when this happens so the orchestrator can decide whether to
continue (transient) or halt (persistent).
"""

from __future__ import annotations

from typing import Any, Iterable


class LLMOutputError(Exception):
    """Raised when client.messages.parse(...).parsed_output is None.

    Carries the response's stop_reason and content-block types so the
    failure is diagnosable without needing to log the full response body.
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
            f"{self.COMPONENT}: parsed_output is None "
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


class ProposerOutputError(LLMOutputError):
    COMPONENT = "proposer"


class CuratorOutputError(LLMOutputError):
    COMPONENT = "curator"


class RedTeamOutputError(LLMOutputError):
    COMPONENT = "redteam"


class ResearchOutputError(LLMOutputError):
    COMPONENT = "research"
