"""The verifier — multi-objective scorer derived from the parent goal's anchors.

The verifier in AlphaMo IS the EvaluatorCascade: a three-stage Haiku → Sonnet →
Opus pipeline that scores each candidate on feasibility, structural fit, and
exemplar similarity, gated by the middle-class-accessible filter. The verifier
definition lives here as a re-export so the persistent context module can be
imported as one cohesive unit; the implementation is in alphamo/evaluator/.
"""

from __future__ import annotations

from alphamo.evaluator import CascadeResult, EvaluatorCascade
from alphamo.evaluator.exemplar_library import EXEMPLARS

VERIFIER_ANCHOR = "PARENT_GOAL v1 + exemplar_library v1"

__all__ = ["EvaluatorCascade", "CascadeResult", "EXEMPLARS", "VERIFIER_ANCHOR"]
