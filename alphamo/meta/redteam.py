"""Red-team agent: structural critique of milestone candidates.

Runs the candidate through one or more adversarial framings (regulatory,
economic, operational, scaling) and aggregates findings. Falsification-free
findings are dropped so the curator sees only well-formed criticism.
"""

from __future__ import annotations

from typing import Any

from alphamo.errors import RedTeamOutputError
from alphamo.evaluator._common import MAX_TOKENS_LONG, OPUS_MODEL, cached_system
from alphamo.prompts.redteam_prompts import (
    DEFAULT_FRAMINGS,
    redteam_system,
    render_candidate,
)
from alphamo.schemas import Architecture
from alphamo.schemas.findings import MetaFinding, RawFindingsBatch


def _enforce_falsification(findings: list[MetaFinding]) -> list[MetaFinding]:
    """Drop findings whose falsification_condition is blank.

    Without a falsifier the curator cannot distinguish structural from
    cosmetic — these are validation failures, not findings.
    """
    return [f for f in findings if f.falsification_condition.strip()]


def red_team_candidate(
    architecture: Architecture,
    client: Any,
    framings: list[str] | None = None,
    model: str = OPUS_MODEL,
) -> list[MetaFinding]:
    """Run the red-team agent across one or more framings; aggregate findings."""
    framings = framings if framings is not None else DEFAULT_FRAMINGS
    all_findings: list[MetaFinding] = []
    for framing in framings:
        result = client.messages.parse(
            model=model,
            max_tokens=MAX_TOKENS_LONG,
            thinking={"type": "adaptive"},
            system=cached_system(redteam_system(framing)),
            messages=[{"role": "user", "content": render_candidate(architecture)}],
            output_format=RawFindingsBatch,
        )
        batch = result.parsed_output
        if batch is None:
            raise RedTeamOutputError.from_response(
                result, detail=f"framing={framing!r}"
            )
        for raw in batch.findings:
            all_findings.append(
                MetaFinding(source="redteam", framing=framing, **raw.model_dump())
            )
    return _enforce_falsification(all_findings)
