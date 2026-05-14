"""Meta-curator: classifies findings as structural vs cosmetic.

The curator is the only component that sees both the inner loop and the
meta layer, and the only one allowed to modify persistent context. Phase 05
implements the conservative wrong-direction-first policy: any structural
finding pauses for human review. Phase 06 may add LLM-driven action
selection (recalibrate vs reframe vs pause).

Curator output goes to the orchestrator and to the audit log — NEVER to
the proposer. This is the structural isolation that prevents meta-level
drift from contaminating object-level optimization.
"""

from __future__ import annotations

from typing import Any

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.errors import CuratorOutputError
from alphamo.evaluator._common import MAX_TOKENS_MEDIUM, OPUS_MODEL, cached_system
from alphamo.meta.audit_log import AuditEvent, AuditLog
from alphamo.schemas.findings import (
    Classification,
    ClassificationVerdict,
    ClassifiedFinding,
    CuratorAction,
    CuratorDecision,
    MetaFinding,
)

CURATOR_SYSTEM = f"""\
You are the meta-curator for an evolutionary search over value-capture \
architectures. You receive findings from the research and red-team agents \
and classify each as STRUCTURAL or COSMETIC.

Rubric:
- STRUCTURAL: would a thoughtful operator pause the build on this finding? \
Examples: competitor has shipped equivalent · regulatory regime changed · \
verifier fundamentally measures wrong thing · candidate violates parent goal \
constraint we hadn't formalized.
- COSMETIC: refinements, edge cases, marginal improvements, things that could \
be addressed later without restructuring.

Discipline:
1. Default to COSMETIC unless clearly structural. Wrong-direction-first: \
over-pausing wastes the loop, under-pausing ships systems with hidden flaws — \
calibrate toward the latter risk.
2. Use the falsification_condition: if it is plausibly true today, the finding \
is cosmetic.
3. You do NOT propose architectures and you do NOT see seeds. You only \
classify findings.

The parent goal you are guarding:

{PARENT_GOAL}\
"""


def _render_finding_for_classification(finding: MetaFinding) -> str:
    framing_str = f" ({finding.framing} framing)" if finding.framing else ""
    return (
        f"Finding from {finding.source}{framing_str}, severity={finding.severity.value}:\n"
        f"Claim: {finding.claim}\n"
        f"Evidence: {finding.evidence}\n"
        f"Falsification condition: {finding.falsification_condition}"
    )


class Curator:
    """Classifies findings, decides actions, writes the audit trail."""

    def __init__(
        self,
        client: Any,
        audit_log: AuditLog,
        model: str = OPUS_MODEL,
    ) -> None:
        self.client = client
        self.audit_log = audit_log
        self.model = model

    def classify(self, finding: MetaFinding) -> ClassificationVerdict:
        result = self.client.messages.parse(
            model=self.model,
            max_tokens=MAX_TOKENS_MEDIUM,
            thinking={"type": "adaptive"},
            system=cached_system(CURATOR_SYSTEM),
            messages=[
                {
                    "role": "user",
                    "content": _render_finding_for_classification(finding),
                }
            ],
            output_format=ClassificationVerdict,
        )
        parsed = result.parsed_output
        if parsed is None:
            raise CuratorOutputError.from_response(result)
        return parsed

    def curate(
        self, findings: list[MetaFinding], trigger: str
    ) -> CuratorDecision:
        """Classify every finding, derive a decision, log to the drift log."""
        classified: list[ClassifiedFinding] = []
        for finding in findings:
            verdict = self.classify(finding)
            classified.append(
                ClassifiedFinding(
                    finding=finding,
                    classification=verdict.classification,
                    rationale=verdict.rationale,
                )
            )

        structural = [
            c for c in classified if c.classification == Classification.STRUCTURAL
        ]

        if not structural:
            action = CuratorAction.CONTINUE
            rationale = (
                f"reviewed {len(classified)} finding(s); none structural — "
                f"continuing inner loop"
            )
            audit_classification = "no_action"
        else:
            action = CuratorAction.PAUSE_FOR_HUMAN
            rationale = (
                f"{len(structural)} structural finding(s); pausing for human "
                f"review per wrong-direction-first policy"
            )
            audit_classification = "structural"

        decision = CuratorDecision(
            action=action, classified=classified, rationale=rationale
        )

        self.audit_log.append(
            AuditEvent(
                timestamp=AuditLog.now(),
                trigger=trigger,
                classification=audit_classification,
                action=action.value,
                rationale=rationale,
                payload={"findings": [c.model_dump(mode="json") for c in classified]},
            )
        )
        return decision
