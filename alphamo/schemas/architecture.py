"""Pydantic schema for a candidate value-capture architecture."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Architecture(BaseModel):
    """Structural description of a value-capture configuration."""

    name: str
    summary: str
    value_chain: str
    capture_mechanism: str
    entry_resources: str
    notes: dict[str, str] = Field(default_factory=dict)
