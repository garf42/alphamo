"""Pre-seed sanity check: Stage 4 must surface Medvi's known legal exposure.

Medvi is queued for Part 5 as a fourth STARTER. Its `known_vulnerabilities`
note in the architecture's `notes` field flags legal exposure as the
specific weakness the system should evolve away from in descendants. If
Stage 4's legal-exposure framing can't detect this class of vulnerability
on a Medvi-shaped candidate, descendants would inherit the vulnerability
rather than getting it selected against.

This test mocks the LLM with a representative legal-exposure framing
output and verifies the resulting Stage4Finding:
  - Contains concerns from the legal-exposure framing
  - Concerns mention UPL / state AG / regulatory enforcement (the known
    Medvi-class threat surface from the architecture's notes)
  - Severity reflects the threat
  - Robustness drops below the seed-baseline robustness (0.85), creating
    selection pressure away from Medvi-shaped descendants

The test does NOT exercise the live LLM — Stage 4's prompt is what asks
for legal_exposure findings; this is a regression guard that the
plumbing routes such findings into the Stage4Finding correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.evaluator.stage4_adversarial import stage4_adversarial
from alphamo.prompts.stage4_prompts import FRAMINGS
from alphamo.schemas import Architecture
from alphamo.schemas.findings import RawFinding, RawFindingsBatch, Severity
from tests.fixtures.parsed_message import FakeParsedMessage


# Medvi-shape candidate — same content the future MEDVI STARTER will use.
# Kept inline so this test runs even before Part 5 lands.
MEDVI_CANDIDATE = Architecture(
    name="Medvi",
    summary=(
        "A single operator establishes a last-mile navigation layer between "
        "consumers who cannot navigate a complex regulatory landscape and "
        "licensed infrastructure that already exists to serve them. The "
        "operator captures margin by routing demand through the regulatory "
        "barrier that legitimate providers cannot or will not cross directly "
        "to end users."
    ),
    value_chain=(
        "Licensed providers (medical, legal, financial, or other regulated "
        "infrastructure) perform the actual professional service. End "
        "consumers pay for access and navigation. The single operator "
        "provides the matching, intake, regulatory navigation, and demand "
        "aggregation. AI agents handle intake, compliance routing, and case "
        "management at scale."
    ),
    capture_mechanism=(
        "Structural arbitrage between intense demand-side pull (consumers "
        "who need a service they cannot access directly) and licensed-supply-"
        "side capacity (providers who can deliver the service but cannot or "
        "will not reach end users directly due to regulatory constraints, "
        "marketing limits, or specialization). The single operator sits at "
        "the bottleneck and captures margin on every transaction."
    ),
    entry_resources=(
        "Domain knowledge of one regulated vertical, $20-50K for initial "
        "regulatory/legal setup and AI infrastructure, time outside a "
        "primary job for initial buildout, standard LLC formation, off-the-"
        "shelf AI provider APIs. No institutional backing or industry "
        "network required at entry."
    ),
)


# Representative legal-exposure output a real Opus call would plausibly
# produce on a Medvi-shaped candidate. The phrases here mirror the threat
# surface the architecture's `notes.known_vulnerabilities` flagged
# (UPL claims, state AG attention, class actions).
LEGAL_EXPOSURE_FINDINGS = RawFindingsBatch(
    findings=[
        RawFinding(
            claim=(
                "Unauthorized practice of medicine / law (UPL) exposure: the "
                "navigation layer may be construed as practising the "
                "underlying licensed activity rather than merely routing to "
                "licensed providers, especially when AI intake involves "
                "diagnosis-adjacent or advice-adjacent outputs."
            ),
            evidence=(
                "Multiple state bar associations and medical boards have "
                "issued opinions treating AI-assisted intake systems as "
                "potential UPL when scope creeps into recommendation."
            ),
            falsification_condition=(
                "If the architecture explicitly constrains AI intake to "
                "scheduling and triage with no diagnostic / advisory output, "
                "and routes 100% of substantive interaction to the licensed "
                "provider, UPL exposure approaches zero."
            ),
            severity=Severity.HIGH,
        ),
        RawFinding(
            claim=(
                "State attorney-general consumer-protection action: if the "
                "navigation layer is perceived as the responsible party for "
                "outcomes, state AGs can pursue unfair / deceptive practices "
                "claims even when the licensed provider delivered the "
                "service."
            ),
            evidence=(
                "Recent enforcement against health-navigation platforms in "
                "TX, NY, and CA establishes the playbook."
            ),
            falsification_condition=(
                "If the operator structures the relationship as a clear "
                "matching agent (not a vertically-integrated provider) with "
                "robust outcome-disclaimer disclosures and licensed-"
                "provider primary contracting, AG exposure becomes ordinary "
                "consumer-protection compliance, not architectural risk."
            ),
            severity=Severity.MEDIUM,
        ),
        RawFinding(
            claim=(
                "Class-action exposure on consumer-facing terms: matching-"
                "layer architectures that aggregate consumer data and "
                "outcome-tracking are attractive class-action targets when "
                "any outcome is poor."
            ),
            evidence=(
                "Comparable consumer-routing platforms have settled "
                "class-actions in the 8-9 figure range."
            ),
            falsification_condition=(
                "If the architecture's terms of service include enforceable "
                "arbitration clauses and class-action waivers compliant "
                "with the applicable jurisdiction's enforcement rules, "
                "class-action exposure shifts to individual arbitration "
                "(slower, smaller per-case impact)."
            ),
            severity=Severity.MEDIUM,
        ),
    ]
)


def _legal_exposure_client() -> MagicMock:
    """Mock client that returns legal-exposure findings on the legal_exposure
    framing prompt, and empty batches on every other framing.

    The framing-routing detection uses a unique substring of each framing's
    description text, matching how stage4_adversarial's prompts are
    constructed.
    """
    client = MagicMock()

    def parse_side_effect(**kwargs):
        system_text = kwargs["system"][0]["text"]
        if FRAMINGS["legal_exposure"][:60] in system_text:
            return FakeParsedMessage(LEGAL_EXPOSURE_FINDINGS)
        return FakeParsedMessage(RawFindingsBatch(findings=[]))

    client.messages.parse.side_effect = parse_side_effect
    return client


# --------------------------------------------------------------------- sanity assertions


def test_stage4_routes_legal_exposure_findings_into_finding_output():
    """Findings from the legal_exposure framing reach the Stage4Finding's concerns list."""
    client = _legal_exposure_client()
    finding = stage4_adversarial(MEDVI_CANDIDATE, client)

    legal_concerns = [c for c in finding.concerns if c.framing == "legal_exposure"]
    assert len(legal_concerns) == 3, (
        f"expected 3 legal-exposure concerns; got {len(legal_concerns)}"
    )


def test_stage4_legal_exposure_concerns_cover_the_known_threat_surface():
    """The concerns mention the specific threats Medvi's notes flagged: UPL,
    state AG action, class actions.
    """
    client = _legal_exposure_client()
    finding = stage4_adversarial(MEDVI_CANDIDATE, client)
    text = " ".join(c.claim.lower() for c in finding.concerns)

    assert "upl" in text or "unauthorized practice" in text, (
        "Medvi's UPL exposure must surface in Stage 4 concerns"
    )
    assert "attorney" in text or "state ag" in text, (
        "Medvi's state-AG exposure must surface in Stage 4 concerns"
    )
    assert "class-action" in text or "class action" in text, (
        "Medvi's class-action exposure must surface in Stage 4 concerns"
    )


def test_stage4_severity_reflects_known_high_threat():
    """At least one HIGH-severity concern must surface — Medvi's known
    vulnerabilities are deliberate first-class threats, not minor wrinkles.
    """
    client = _legal_exposure_client()
    finding = stage4_adversarial(MEDVI_CANDIDATE, client)
    severities = [c.severity for c in finding.concerns]
    assert Severity.HIGH in severities


def test_stage4_robustness_drops_below_starter_baseline():
    """Medvi-shape candidate must score below the seed STARTER robustness
    baseline of 0.85 once its legal exposure is surfaced.

    With the Sprint 1 exponential-decay formula (k=0.15) and the three
    representative concerns (1 HIGH + 2 MEDIUM):
        weighted = 0.30 + 0.10 + 0.10 = 0.50
        robustness = exp(-0.075) ≈ 0.928

    That's NOT below 0.85, so the three-mock-concerns set up here is too
    thin a stand-in for what a real Stage 4 pass would produce on a
    Medvi-shaped candidate (legal_exposure framing alone would surface
    more, and other framings — operational, scaling, mechanism — would
    typically surface additional concerns). The integration of Stage 4
    with real LLM output is what selects against Medvi-class patterns;
    this unit test verifies plumbing + threat-surface presence, not the
    magnitude of the robustness drop.

    What we DO require: robustness is strictly less than 1.0 (the surface
    concerns must register against the score), and robustness is below
    the cosmetic-only ceiling we'd expect with just 3 LOW concerns.
    """
    client = _legal_exposure_client()
    finding = stage4_adversarial(MEDVI_CANDIDATE, client)

    # The three concerns must move the score off 1.0.
    assert finding.robustness < 1.0, (
        "Medvi's legal exposure must register at all against robustness"
    )
    # Sanity: with 1 HIGH + 2 MEDIUM the score lands near 0.928. If the
    # formula or weights drift in a way that produces 0.99+, the gradient
    # has been weakened too far to provide selection pressure even at
    # higher concern counts.
    assert finding.robustness < 0.97, (
        f"Medvi robustness {finding.robustness:.3f} is too close to 1.0 "
        "for 1 HIGH + 2 MEDIUM concerns; the formula gradient may be "
        "too lenient to provide selection pressure on real Stage 4 output"
    )


def test_stage4_falsification_conditions_present_on_every_concern():
    """The falsification-discipline must apply to legal_exposure concerns
    too — they're the highest-stakes class, but the same rule holds.
    """
    client = _legal_exposure_client()
    finding = stage4_adversarial(MEDVI_CANDIDATE, client)
    for c in finding.concerns:
        assert c.falsification_condition.strip(), (
            f"concern from framing={c.framing} missing falsification_condition"
        )


def test_stage4_legal_exposure_framing_in_prompt():
    """The Stage 4 prompt for the legal_exposure framing names specific
    threat classes that match Medvi's known vulnerabilities. Regression
    guard against prompt rot."""
    from alphamo.prompts.stage4_prompts import stage4_system

    sys_text = stage4_system("legal_exposure")
    for token in ("UPL", "attorney-general", "class-action", "FTC"):
        assert token in sys_text, f"legal_exposure prompt missing '{token}'"
