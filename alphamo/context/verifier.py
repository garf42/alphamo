"""The verifier — multi-objective scorer derived from the parent goal's anchors.

The verifier in AlphaMo IS the EvaluatorCascade: a three-stage Haiku → Sonnet →
Opus pipeline that scores each candidate on feasibility, structural fit, and
exemplar similarity, gated by the middle-class-accessible filter. The verifier
definition lives here as a re-export so the persistent context module can be
imported as one cohesive unit; the implementation is in alphamo/evaluator/.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL_VERSION
from alphamo.evaluator import CascadeResult, EvaluatorCascade
from alphamo.evaluator.exemplar_library import EXEMPLARS

# Bump when the cascade prompts or exemplar library change in a way that
# would alter scoring of an identical candidate. Persisted on every Run row.
VERIFIER_VERSION = "v1"

VERIFIER_ANCHOR = f"PARENT_GOAL {PARENT_GOAL_VERSION} + exemplar_library {VERIFIER_VERSION}"

__all__ = [
    "EvaluatorCascade",
    "CascadeResult",
    "EXEMPLARS",
    "VERIFIER_ANCHOR",
    "VERIFIER_VERSION",
]
