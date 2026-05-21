"""LLM-output failure types and the telemetry-context dataclass.

Sprint 14: `parse_or_raise` and `_emit_llm_usage_event` moved into
`alphamo.providers`. The SDK call now goes through `BaseProvider.parse`,
which dispatches to AnthropicProvider or FireworksProvider; the audit-
event emission lives in `providers/base.py`. The two output-side
failure modes (truncation → pydantic.ValidationError; refusal /
tool-only turn → empty parsed output) are handled inside each provider.

This module keeps the failure-type hierarchy and the TelemetryContext
dataclass — both are domain types that don't depend on a specific
SDK. Components import them from here regardless of which provider
they're routed to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

import pydantic

# Re-export so legacy `from alphamo.errors import LLM_USAGE_TRIGGER` still
# resolves. The constant's authoritative home is providers/base.py.
from alphamo.providers.base import LLM_USAGE_TRIGGER  # noqa: F401

if TYPE_CHECKING:
    from alphamo.meta.audit_log import AuditLog


@dataclass(frozen=True)
class TelemetryContext:
    """Per-call attribution fields for the `llm_usage` audit event.

    Bundled into one optional kwarg so individual function signatures
    don't thread four separate parameters. The orchestrator builds this
    in `step()` and `_bootstrap_islands()`; components (cascade,
    proposer, curator) forward it through to `provider.parse(...)`
    unchanged.

    `generation` is None on bootstrap-side calls (the trivial seed is
    scored at gen 0 but the bootstrap path may emit before the loop
    enters). `island_id` is None on calls that aren't bound to a single
    island (bootstrap, harvest re-cascade).
    """

    audit_log: "AuditLog"
    run_id: str
    generation: int | None = None
    island_id: int | None = None


class LLMOutputError(Exception):
    """Raised when an LLM-calling component fails to produce parsed output.

    Carries the response's stop_reason and content-block types so the
    failure is diagnosable without needing to log the full response body.
    `stop_reason="parse_error"` is used when validation raised before
    the response object was usable; `stop_reason="api_error"` when the
    SDK raised before any response was received (Fireworks provider).
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

        Either the Anthropic SDK's `parse_response` raised mid-parse, or
        the Fireworks provider's `model_validate_json` rejected the
        response text. stop_reason='parse_error' marks both cases.
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
