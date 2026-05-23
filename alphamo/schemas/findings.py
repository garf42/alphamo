"""Structured per-stage evaluator output and meta-layer findings.

Phase 02 added Stage{1,2,3}Finding for the evaluator cascade.
Phase 05 adds RawFinding (LLM output) → MetaFinding (Python-side, tagged
with source and framing) → ClassifiedFinding → CuratorDecision.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RevenueType(str, Enum):
    """7-way categorical for Stage 1's revenue-mechanism evidence.

    Sprint Stage 1 PAJAMA. The model classifies the architecture's
    revenue-collection mechanism into the closest matching bucket;
    `compute_feasibility` maps each bucket to a fixed numeric weight.
    """

    RECURRING = "recurring"
    TRANSACTIONAL = "transactional"
    ASSET_APPRECIATION = "asset_appreciation"
    LICENSING = "licensing"
    ARBITRAGE = "arbitrage"
    HYBRID = "hybrid"
    UNCLEAR = "unclear"


class BuyerAccessibility(str, Enum):
    """5-way categorical for Stage 1's buyer-identification evidence.

    Sprint Stage 1 PAJAMA. The model classifies who pays and how
    accessible that buyer is to a middle-class-starting operator —
    direct B2C / B2B paths score higher than intermediated or
    government-contract paths.
    """

    DIRECT_TO_CONSUMER = "direct_to_consumer"
    DIRECT_TO_BUSINESS = "direct_to_business"
    REQUIRES_INTERMEDIARY = "requires_intermediary"
    REQUIRES_GOVERNMENT_CONTRACT = "requires_government_contract"
    UNCLEAR = "unclear"


class CapitalRequired(str, Enum):
    """6-way categorical for Stage 1's capital-requirement evidence.

    Sprint Stage 1 PAJAMA. The buckets align with the PARENT_GOAL
    middle-class-entry constraint ($10K-$50K savings range): "none"
    and "under_10k" are clearly middle-class-accessible from a
    capital perspective; "over_1m" effectively rules it out.
    "unquantifiable" is the honest-vagueness bucket when the
    architecture's description doesn't support an estimate.
    """

    NONE = "none"
    UNDER_10K = "under_10k"
    BETWEEN_10K_AND_100K = "10k_to_100k"
    BETWEEN_100K_AND_1M = "100k_to_1m"
    OVER_1M = "over_1m"
    UNQUANTIFIABLE = "unquantifiable"


class RegulatorySeverity(str, Enum):
    """4-way categorical for Stage 1's regulatory-burden evidence.

    Sprint Stage 1 PAJAMA. Aggregate assessment of regulatory
    burden — separate from `regulatory_blockers` (which counts
    specific named barriers). `compute_feasibility` applies a base
    penalty per severity tier, plus a small per-blocker increment,
    so two-axis evidence about regulatory friction produces a
    bounded score impact rather than a winner-take-all flip.
    """

    NONE = "none"
    MANAGEABLE = "manageable"
    SIGNIFICANT = "significant"
    PROHIBITIVE = "prohibitive"


class Stage1Finding(BaseModel):
    """Stage 1 — evidence extraction for basic feasibility.

    Sprint Stage 1 PAJAMA: the model's role changed from scorer to
    evidence extractor (same pattern as Stage 2 PAJAMA and Stage 3's
    long-standing pattern). Pre-PAJAMA the model returned a single
    `feasibility: float` which Python read directly; the variance test
    (commit bcdb86c) showed feasibility stdev 0.239-0.278 across 5
    trials on the same candidate, and the hard threshold at
    stage1_threshold=0.4 turned that noise into bimodal early-exit
    behaviour (CarbonSentry: 4 of 5 trials exited early because
    feasibility randomly landed below 0.4).

    Under PAJAMA the model returns structured categorical / boolean /
    list evidence; `evaluator.stage1_feasibility.compute_feasibility`
    maps it to a deterministic scalar in [0.0, 1.0]. The cascade then
    routes the candidate through a soft-penalty zone (not a hard
    threshold) so per-trial variance in the evidence doesn't produce
    cliffs in the fitness output.

    `middle_class_accessible` is **retained from the pre-PAJAMA
    schema** — it's a load-bearing boolean (the PARENT_GOAL's third
    constraint is a structural filter, not a soft preference) and is
    consumed unchanged by `passes_middle_class_filter` for the hard
    fitness-to-zero gate at `cascade.py`. The bool is independent of
    the feasibility-zone logic.

    Six evidence dimensions plus the MC boolean and the audit-only
    reasoning string. The additive scoring (rather than Stage 2's
    multiplicative) was chosen specifically to make the result
    noise-resistant: a single field flip shifts the score by at most
    ~0.15 rather than 70% on a 0.3× boolean multiplier.
    """

    # --- revenue mechanism ---
    revenue_mechanism_identified: bool = Field(
        description=(
            "Does the architecture name a specific way it gets paid? "
            "'Generic SaaS' or 'consulting' alone is too vague to count "
            "as identified; named mechanisms like 'per-transaction take "
            "rate', 'annual subscription with usage tiers', 'IP licensing "
            "royalty stream' do count."
        ),
    )
    revenue_mechanism_description: str = Field(
        description=(
            "Brief description of the revenue mechanism, for audit "
            "trail. Empty string when revenue_mechanism_identified is "
            "False."
        ),
    )
    revenue_type: RevenueType = Field(
        description=(
            "Categorical classification of the revenue mechanism. Must "
            "be one of the seven RevenueType values."
        ),
    )

    # --- buyer identification ---
    buyer_identified: bool = Field(
        description=(
            "Does the architecture name who pays? 'Businesses' or "
            "'consumers' alone is too vague; named buyer cohorts like "
            "'SMB e-commerce operators', 'mid-market law firms', or "
            "'regulated healthcare providers' count as identified."
        ),
    )
    buyer_description: str = Field(
        description=(
            "Brief description of the buyer cohort, for audit trail. "
            "Empty string when buyer_identified is False."
        ),
    )
    buyer_accessibility: BuyerAccessibility = Field(
        description=(
            "How accessible the buyer is to a middle-class-starting "
            "operator. Categorical; must be one of the five "
            "BuyerAccessibility values."
        ),
    )

    # --- capital requirements ---
    capital_required: CapitalRequired = Field(
        description=(
            "Approximate capital required to build and launch the "
            "architecture, BEFORE first revenue. Categorical bucket; "
            "must be one of the six CapitalRequired values. "
            "'unquantifiable' is the honest fallback when the "
            "architecture's description doesn't support an estimate."
        ),
    )
    capital_justification: str = Field(
        description=(
            "Brief description of what requires the capital, for audit "
            "trail. Examples: 'cloud infrastructure + legal setup', "
            "'initial inventory + warehouse lease'. Empty string only "
            "when capital_required is 'none'."
        ),
    )

    # --- regulatory landscape ---
    regulatory_blockers: list[str] = Field(
        description=(
            "Specific named regulatory barriers, one per entry. Good: "
            "'state-by-state insurance licensing', 'FDA 510(k) "
            "clearance', 'FINRA broker-dealer registration', 'CFPB "
            "licensure for consumer lending'. Bad: 'various regulations', "
            "'compliance burden'. Empty list = no identified blockers."
        ),
    )
    regulatory_severity: RegulatorySeverity = Field(
        description=(
            "Aggregate severity of the regulatory burden. Categorical; "
            "must be one of the four RegulatorySeverity values. "
            "Distinct from regulatory_blockers: severity is the bottom-"
            "line read; blockers is the specifics."
        ),
    )

    # --- feasibility risks (distinct from regulatory) ---
    feasibility_risks: list[str] = Field(
        description=(
            "Specific execution risks to basic viability, distinct from "
            "regulatory blockers. Good: 'depends on Google Maps API "
            "access that could be revoked', 'requires unrolled "
            "Pinterest scrape dataset that doesn't exist publicly', "
            "'value capture requires a partnership Apple has never "
            "granted'. Bad: 'might be hard to build'. Empty list = no "
            "identified risks beyond ordinary execution."
        ),
    )

    # --- existing-market signal ---
    existing_market_validation: bool = Field(
        description=(
            "Is there evidence that someone is already paying for "
            "something similar? Reflects market existence, not "
            "competitive saturation — a $10B existing market is a "
            "VALIDATION signal even when crowded, since it proves "
            "buyer willingness-to-pay."
        ),
    )

    # --- the PARENT_GOAL load-bearing filter (preserved across PAJAMA) ---
    middle_class_accessible: bool = Field(
        description=(
            "True iff the entry_resources describe a starting position "
            "reachable from middle-class personal resources with no "
            "privileged starting conditions (no family wealth, no "
            "institutional backing, no pre-existing industry network, "
            "no bespoke legal structuring). This is a STRUCTURAL FILTER "
            "per PARENT_GOAL: False here triggers a hard fitness-to-zero "
            "gate at the cascade level, regardless of the rest of the "
            "evidence."
        ),
    )

    # --- justification (audit/debug only) ---
    reasoning: str = Field(
        description=(
            "One or two sentences justifying the overall read across "
            "the evidence dimensions. NOT used in scoring — "
            "compute_feasibility ignores this field entirely."
        ),
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
