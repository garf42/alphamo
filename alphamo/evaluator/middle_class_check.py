"""The middle-class entry filter — a *filter*, not a score.

Wraps the stage-1 finding's `middle_class_accessible` field so the cascade
and the islands manager can both ask the same question without re-running
the LLM. This matches the modal's "Filter, not penalty" rule on the
evaluator node.
"""

from __future__ import annotations

from alphamo.schemas.findings import Stage1Finding


def passes_middle_class_filter(finding: Stage1Finding) -> bool:
    """True iff the candidate's entry resources are middle-class accessible."""
    return finding.middle_class_accessible
