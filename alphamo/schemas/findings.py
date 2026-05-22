"""Structured per-stage evaluator output and meta-layer findings.

Phase 02 added Stage{1,2,3}Finding for the evaluator cascade.
Phase 05 adds RawFinding (LLM output) → MetaFinding (Python-side, tagged
with source and framing) → ClassifiedFinding → CuratorDecision.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Stage1Finding(BaseModel):
    """Stage 1 — cheap feasibility + middle-class accessibility filter."""

    feasibility: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How plausible is this architecture as a value-capture configuration? "
            "1.0 = clearly coherent; 0.0 = malformed or contradictory."
        ),
    )
    middle_class_accessible: bool = Field(
        description=(
            "True iff the entry_resources describe a starting position reachable "
            "from middle-class personal resources with no privileged starting "
            "conditions (no family wealth, no institutional backing, no pre-existing "
            "industry network, no bespoke legal structuring)."
        ),
    )
    reasoning: str = Field(
        description="One or two sentences. Why this score and accessibility verdict.",
    )


class AutomationPlausibility(str, Enum):
    """4-way categorical for Stage 2's one-person-threshold evidence.

    Sprint Stage 2 PAJAMA. The model reports the most automatable
    category that describes the architecture's mechanism; Python
    maps each category to a fixed numeric weight in
    `compute_structural`. Allowed values are LLM-side-validated by
    the json_schema response_format — an out-of-enum response is a
    parse error rather than a fallback-to-default.
    """

    ALREADY_AUTOMATED = "already_automated"
    AUTOMATABLE_WITH_EXISTING_TOOLS = "automatable_with_existing_tools"
    REQUIRES_CUSTOM_ENGINEERING = "requires_custom_engineering"
    REQUIRES_HUMAN_JUDGMENT = "requires_human_judgment"


class TAMEstimate(str, Enum):
    """5-way categorical bucket for Stage 2's billion-dollar-potential evidence.

    Sprint Stage 2 PAJAMA. The model places the architecture's
    addressable market into the smallest bucket it has evidence for.
    'unquantifiable' is the honest fallback when the architecture
    doesn't carry enough signal to estimate — it produces a low
    market-component score in `compute_structural`, encouraging the
    proposer to either be specific about the market or accept the
    penalty for vagueness.

    The bucket strings include literal '<', '>', and '$' characters so
    the persisted JSON is human-readable; Pydantic's enum-as-string
    semantics carry the symbols through unchanged.
    """

    SUB_1B = "<$1B"
    ONE_TO_10B = "$1B-$10B"
    TEN_TO_100B = "$10B-$100B"
    OVER_100B = ">$100B"
    UNQUANTIFIABLE = "unquantifiable"


class Stage2Finding(BaseModel):
    """Stage 2 — evidence extraction for the three load-bearing structural criteria.

    Sprint Stage 2 PAJAMA: the model's role changed from scorer to
    evidence extractor. Pre-PAJAMA the model returned four floats
    (one_person_threshold, billion_dollar_potential, labor_separation,
    structural) which Python read directly; the variance test
    (commit bcdb86c, 3 candidates × 5 trials) showed the same model
    on the same input returning structural values from 0.000 to
    0.950 (stdev 0.406-0.457). Under PAJAMA the model returns
    structured categorical / list / boolean evidence and
    `evaluator.stage2_structured.compute_structural()` derives the
    scalar deterministically — mirroring the Stage 3 pattern where
    `compute_robustness()` is the source of truth for the scalar.

    Field layout matches the three sub-criteria from PARENT_GOAL v2:

    one-person threshold (single individual is the capture node):
      - labor_dependency_points: specific named operations that need
        sustained human labor (empty list = fully autonomous)
      - automation_plausibility: 4-way categorical of how
        automatable the architecture is
      - one_person_operable: bottom-line judgment

    billion-dollar potential:
      - target_market_named / target_market_description: did the
        architecture identify a SPECIFIC addressable market
      - tam_estimate: 5-way categorical bucket
      - capture_mechanism_identified / capture_mechanism_description:
        is there a named, specific value-capture mechanism
      - nonlinear_scaling_path: does value grow faster than operator
        effort

    labor separation (operational labor done by parties other than
    the capture node):
      - autonomous_value_sources: specific mechanisms that generate
        value without operator labor
      - active_labor_requirements: specific operations that need
        operator time
      - separation_achieved: bottom-line judgment

    Free-text `reasoning` is retained for audit-trail / debug but is
    NOT consumed by `compute_structural`.
    """

    # --- one-person threshold ---
    labor_dependency_points: list[str] = Field(
        description=(
            "Specific operations that require sustained human labor. Each "
            "entry should name a concrete operation (e.g. 'manual client "
            "onboarding', 'FDA 510(k) clearance per device variant'), "
            "not a category (e.g. 'various manual tasks'). Empty list "
            "= fully autonomous architecture."
        ),
    )
    automation_plausibility: AutomationPlausibility = Field(
        description=(
            "How automatable is the architecture's described mechanism. "
            "Categorical; must be one of the four AutomationPlausibility "
            "enum values."
        ),
    )
    one_person_operable: bool = Field(
        description=(
            "Bottom-line judgment: can a single individual operate this "
            "at $1B+ scale?"
        ),
    )

    # --- billion-dollar potential ---
    target_market_named: bool = Field(
        description=(
            "Did the architecture identify a SPECIFIC addressable market "
            "(not 'businesses' or 'consumers')?"
        ),
    )
    target_market_description: str = Field(
        description=(
            "Brief description of the named market, for audit trail. "
            "Empty string when target_market_named is False."
        ),
    )
    tam_estimate: TAMEstimate = Field(
        description=(
            "Addressable-market size bucket. Categorical; must be one of "
            "the five TAMEstimate enum values. 'unquantifiable' when the "
            "architecture's description doesn't support an estimate."
        ),
    )
    capture_mechanism_identified: bool = Field(
        description=(
            "Is there a NAMED, SPECIFIC value-capture mechanism (not "
            "just a generic label like 'SaaS subscription')?"
        ),
    )
    capture_mechanism_description: str = Field(
        description=(
            "Brief description of the capture mechanism, for audit "
            "trail. Empty string when capture_mechanism_identified is "
            "False."
        ),
    )
    nonlinear_scaling_path: bool = Field(
        description=(
            "Does the architecture describe a path where captured value "
            "grows faster than the operator's effort or operational "
            "cost?"
        ),
    )

    # --- labor separation ---
    autonomous_value_sources: list[str] = Field(
        description=(
            "Specific mechanisms that generate value WITHOUT the "
            "operator's active labor (e.g. 'automated matching algorithm "
            "runs 24/7', 'regulatory data corpus appreciates as it "
            "accumulates'). Empty list when no such mechanism exists."
        ),
    )
    active_labor_requirements: list[str] = Field(
        description=(
            "Specific operations that DO require the operator's active "
            "time. Same specificity discipline as labor_dependency_points."
        ),
    )
    separation_achieved: bool = Field(
        description=(
            "Bottom-line: does value creation decouple from operator "
            "labor input at scale?"
        ),
    )

    # --- justification (audit/debug only) ---
    reasoning: str = Field(
        description=(
            "Two to four sentences justifying your overall read across "
            "the three criteria. NOT used in scoring — compute_structural "
            "ignores this field entirely."
        ),
    )


class Severity(str, Enum):
    """Per-finding severity tag from the research / Stage 4 adversarial agents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RawFinding(BaseModel):
    """LLM-facing schema for a single research or red-team finding.

    `source` and `framing` are NOT part of the LLM output — the Python
    wrapper sets them when promoting a RawFinding to a MetaFinding.
    """

    claim: str = Field(description="The finding itself, one or two sentences.")
    evidence: str = Field(
        description=(
            "Direct citation, URL, or concise reasoning supporting the claim."
        ),
    )
    falsification_condition: str = Field(
        description=(
            "A concrete fact that, if true, would make this finding NOT a "
            "problem. Required — empty strings will be dropped at validation."
        ),
    )
    severity: Severity = Field(
        description="low / medium / high. High = blocks the parent goal as stated."
    )


class RawFindingsBatch(BaseModel):
    """LLM-facing schema for an entire research or red-team pass."""

    findings: list[RawFinding] = Field(
        description=(
            "Zero or more findings. Empty list is a first-class output — emit "
            "it when an honest pass surfaces nothing material."
        ),
    )
    # Sprint 14 follow-up v2: `assessment` is REQUIRED (no default).
    # The model MUST emit the field on every call — string when
    # findings is empty, explicit null when findings is non-empty.
    # Making it required pushes the field into the JSON-schema's
    # `required` array sent to Fireworks, so the model can't structurally
    # opt out by omission (which the optional+default-null v1 shape
    # allowed — empirically, the model honored the opt-out and skipped
    # the field on every clean pass). The aggregator's existing falsy
    # filter (`if assessment:`) handles both cases correctly: explicit
    # null is still falsy, so framings with concerns don't pollute the
    # clean-assessments surface; real explanation strings on clean
    # framings get surfaced into `Stage4Finding.reasoning`.
    #
    # Why a field rather than a LOW-severity finding with a
    # `no_vulnerability` tag: a clean assessment is metadata about
    # the framing's evaluation, not a concern. Synthesising it as a
    # LOW finding would either contaminate `compute_robustness`
    # (severity weight 0.03 silently reduces robustness for a clean
    # result — wrong incentive) or require filtering logic of the
    # same complexity as this field.
    assessment: str | None = Field(
        ...,
        description=(
            "Required on every call. Write a brief explanation of why "
            "the architecture has no identifiable vulnerability on this "
            "framing's dimension when findings is empty; write null when "
            "findings is non-empty. The aggregator surfaces non-null "
            "assessments on clean framings into Stage 4 reasoning so the "
            "closed-RL-loop gets positive signal alongside concerns."
        ),
    )


class MetaFinding(BaseModel):
    """Python-side finding: a RawFinding tagged with its source and framing."""

    source: str = Field(description='"research" or "stage4_adversarial".')
    framing: str | None = Field(
        default=None,
        description="Adversarial framing tag (regulatory, economic, …) or None.",
    )
    claim: str
    evidence: str
    falsification_condition: str
    severity: Severity


class StructuralConcern(BaseModel):
    """One concern surfaced by Stage 4 adversarial scrutiny.

    Same shape as RawFinding plus a `framing` tag identifying which of the
    eight adversarial lenses surfaced it. Persisted alongside Stage 4 output
    on the candidate and projected into the handoff trail.
    """

    framing: str = Field(
        description="Which Stage 4 framing surfaced this concern.",
    )
    claim: str
    evidence: str
    falsification_condition: str
    severity: Severity


class Stage4Finding(BaseModel):
    """Stage 4 — adversarial robustness scoring + concerns."""

    robustness: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Aggregate robustness, derived deterministically from the "
            "severity of structural concerns surfaced across all framings. "
            "1.0 = airtight (no concerns); decays linearly with severity-"
            "weighted concern count."
        ),
    )
    concerns: list[StructuralConcern] = Field(
        description=(
            "Every well-formed concern surfaced across all framings. "
            "Falsification-condition-less concerns are dropped before this "
            "list is assembled."
        ),
    )
    reasoning: str = Field(
        description=(
            "One or two sentences summarising which framings produced "
            "concerns and which came back clean."
        ),
    )
    # Sprint 15 (Q2): structured per-framing "no vulnerability" text
    # from clean passes. Mirrors the dict already aggregated inside
    # stage4_adversarial. Persisted to the new stage4_assessments JSON
    # column on the candidate row so the closed-RL-loop has positive
    # signal alongside the negative-signal concern list. Defaults to
    # an empty dict so previously-serialised Stage4Finding instances
    # deserialise cleanly (backward-compat).
    framing_assessments: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Per-framing 'no identifiable vulnerability' explanation text "
            "from clean framings on this candidate. Empty dict when no "
            "framing came back clean OR when this is a legacy Stage4Finding "
            "predating Sprint 15."
        ),
    )


class Classification(str, Enum):
    """Curator's verdict on a single finding."""

    STRUCTURAL = "structural"
    COSMETIC = "cosmetic"


class ClassificationVerdict(BaseModel):
    """LLM output for one classification decision."""

    classification: Classification = Field(
        description=(
            "STRUCTURAL = warrants pausing the build / updating context. "
            "COSMETIC = note and continue. Default cosmetic unless clearly structural."
        ),
    )
    rationale: str = Field(
        description="One or two sentences justifying the classification."
    )


class ClassifiedFinding(BaseModel):
    """A finding paired with the curator's classification."""

    finding: MetaFinding
    classification: Classification
    rationale: str


class CuratorAction(str, Enum):
    """The action returned by Curator.curate()."""

    CONTINUE = "continue"
    RECALIBRATE_VERIFIER = "recalibrate_verifier"
    REFRAME_PARENT_GOAL = "reframe_parent_goal"
    PAUSE_FOR_HUMAN = "pause_for_human"


class CuratorDecision(BaseModel):
    """Final output of the curator for one batch of findings."""

    action: CuratorAction
    classified: list[ClassifiedFinding]
    rationale: str
