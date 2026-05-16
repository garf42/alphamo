"""Tests for Stage 4 (adversarial robustness).

Mocks `client.messages.parse` per framing so we can exercise the parallel
fan-out, the falsification-condition filter, and the deterministic
robustness-from-severity calculation without live LLM calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.errors import Stage4OutputError
from alphamo.evaluator.stage4_adversarial import (
    compute_robustness,
    stage4_adversarial,
)
from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS, FRAMINGS, stage4_system
from alphamo.schemas.findings import (
    RawFinding,
    RawFindingsBatch,
    Severity,
    StructuralConcern,
)
from tests.fixtures.exemplars import SATOSHI_FIXTURE
from tests.fixtures.parsed_message import FakeParsedMessage, make_truncation_error


# --------------------------------------------------------------------- shape

def test_stage4_has_eight_framings():
    """Sprint 2: three legacy framings, four Phase-2 additions, and
    timeline_plausibility (which replaced the legacy `scaling` framing —
    scaling's coverage is preserved by scaling_cliffs + mechanism_robustness,
    and timeline_plausibility fills the previously-absent time-to-value
    selection pressure gap)."""
    assert set(FRAMINGS) == {
        "regulatory",
        "economic",
        "operational",
        "mechanism_robustness",
        "hidden_dependencies",
        "scaling_cliffs",
        "legal_exposure",
        "timeline_plausibility",
    }
    assert len(DEFAULT_FRAMINGS) == 8


def test_stage4_system_prompt_includes_framing_text():
    """Each framing's system prompt embeds its own framing description."""
    for framing in FRAMINGS:
        sys_text = stage4_system(framing)
        assert FRAMINGS[framing][:50] in sys_text


def test_stage4_system_prompt_rejects_unknown_framing():
    with pytest.raises(KeyError):
        stage4_system("nonexistent")


# --------------------------------------------------------------------- Sprint 2 (Bug 3) prompt-shape regression guards
#
# These snapshot tests lock in the Sprint 2 reframe of Stage 4 prompts away
# from "Examine the candidate for X failure modes" (always-find bias,
# producing 22-41 concerns per seed regardless of seed quality) toward
# "Evaluate whether..." (yes/no, with explicit empty-list license, design
# target 3-10 concerns per candidate).
#
# If someone reverts the prompts toward always-find phrasing, these tests
# fail before the reverted prompts can ship.


def test_stage4_default_to_empty_is_first_discipline_rule():
    """Rule #1 must be the empty-default rule, prominently placed."""
    sys_text = stage4_system("regulatory")
    discipline_idx = sys_text.find("Discipline:\n")
    assert discipline_idx != -1, "Discipline section missing from system prompt"
    after_discipline = sys_text[discipline_idx:]
    rule_one_idx = after_discipline.find("\n1. ")
    assert rule_one_idx != -1, "rule numbering missing"
    rule_one = after_discipline[rule_one_idx:rule_one_idx + 200]
    assert "Default to empty concerns lists" in rule_one, (
        f"rule #1 must open with 'Default to empty concerns lists', got: {rule_one!r}"
    )


def test_stage4_severity_calibration_section_anchors_to_parent_goal():
    """A 'Severity calibration:' section must exist with HIGH/MEDIUM/LOW anchors."""
    sys_text = stage4_system("regulatory")
    assert "Severity calibration:" in sys_text
    # Each tier present with the parent-goal anchor language.
    assert "HIGH:" in sys_text and "$1B+" in sys_text
    assert "MEDIUM:" in sys_text and "below $1B" in sys_text
    assert "LOW:" in sys_text
    # The disambiguation cue is also present.
    assert "When in doubt between HIGH and MEDIUM" in sys_text


def test_each_framing_opens_with_evaluate_whether_pattern():
    """Every framing prompt must open with the 'Evaluate whether...' yes/no pattern."""
    for framing, text in FRAMINGS.items():
        assert text.startswith("Evaluate whether"), (
            f"framing {framing!r} does not open with 'Evaluate whether'; "
            f"actual opening: {text[:80]!r}"
        )


def test_each_framing_grants_explicit_empty_list_license():
    """Every framing must explicitly say 'return an empty concerns list' to make
    the empty case first-class, not a default the model might infer to avoid."""
    for framing, text in FRAMINGS.items():
        assert "return an empty concerns list" in text, (
            f"framing {framing!r} missing explicit empty-list license"
        )


def test_each_framing_says_empty_results_are_correct():
    """The 'Empty results are correct when...' clause must appear in every
    framing — reinforces the same message in a different sentence shape."""
    for framing, text in FRAMINGS.items():
        assert "Empty results are correct" in text, (
            f"framing {framing!r} missing 'Empty results are correct' clause"
        )


def test_no_framing_uses_legacy_examine_for_failure_modes_phrasing():
    """The old 'Examine the candidate for X failure modes' phrasing was the
    proximate cause of the always-find bias. Lock against accidental revert."""
    for framing, text in FRAMINGS.items():
        assert "Examine the candidate for" not in text, (
            f"framing {framing!r} reverted to legacy 'Examine the candidate for' phrasing"
        )


def test_legacy_scaling_framing_removed():
    """`scaling` was retired in Sprint 2; its coverage is preserved by
    scaling_cliffs + mechanism_robustness. Lock against accidental revival."""
    assert "scaling" not in FRAMINGS


def test_timeline_plausibility_framing_covers_both_assessments():
    """timeline_plausibility must examine BOTH unnecessary slowness vs
    mechanism floor AND middle-class cash-flow viability — the framing
    fails as designed if either assessment drops out."""
    text = FRAMINGS["timeline_plausibility"]
    # Both assessments must be named explicitly.
    assert "UNNECESSARY SLOWNESS" in text, (
        "timeline_plausibility lost the mechanism-floor-gap assessment"
    )
    assert "MIDDLE-CLASS FINANCIAL VIABILITY" in text, (
        "timeline_plausibility lost the cash-flow-viability assessment"
    )
    # Severity calibration is anchored, including the centuries-long tail.
    assert "3x+ the floor" in text or "3x the floor" in text
    assert "centuries-long" in text or "century" in text or "150 years" in text
    # Mechanism-floor exemption is named so legitimately-long mechanisms
    # (cultivar IP, etc.) don't get penalized for matching their own floor.
    assert "cultivar" in text.lower() or "breeding" in text.lower()


# --------------------------------------------------------------------- compute_robustness
#
# Sprint 1 (Bug 1): formula switched from linear deduction to exponential
# decay: robustness = exp(-decay_k * weighted_concern_sum). With the default
# k=0.15 and severity weights HIGH=0.30, MEDIUM=0.10, LOW=0.03:


def test_compute_robustness_clean_returns_one():
    assert compute_robustness([]) == 1.0


def _concern(severity: Severity, framing: str = "regulatory") -> StructuralConcern:
    return StructuralConcern(
        framing=framing,
        claim="c", evidence="e",
        falsification_condition="if x", severity=severity,
    )


def test_compute_robustness_single_high():
    # exp(-0.15 * 0.30) = 0.9560
    assert compute_robustness([_concern(Severity.HIGH)]) == pytest.approx(0.9560, abs=1e-3)


def test_compute_robustness_single_medium():
    # exp(-0.15 * 0.10) = 0.9851
    assert compute_robustness([_concern(Severity.MEDIUM)]) == pytest.approx(0.9851, abs=1e-3)


def test_compute_robustness_single_low():
    # exp(-0.15 * 0.03) = 0.9955
    assert compute_robustness([_concern(Severity.LOW)]) == pytest.approx(0.9955, abs=1e-3)


def test_compute_robustness_five_high():
    # exp(-0.15 * 1.5) = 0.7985
    assert compute_robustness([_concern(Severity.HIGH)] * 5) == pytest.approx(0.7985, abs=1e-3)


def test_compute_robustness_does_not_clamp_to_zero_under_realistic_load():
    """Bug 1 regression guard: 4 HIGH concerns no longer collapse to 0.0."""
    r = compute_robustness([_concern(Severity.HIGH)] * 4)
    assert r > 0.0
    # exp(-0.15 * 1.2) = 0.8353
    assert r == pytest.approx(0.8353, abs=1e-3)


def test_compute_robustness_run006_low_end():
    """15 HIGH + 25 MED → graded score, not 0."""
    concerns = [_concern(Severity.HIGH)] * 15 + [_concern(Severity.MEDIUM)] * 25
    # weighted = 15*0.30 + 25*0.10 = 7.0; exp(-1.05) = 0.3499
    assert compute_robustness(concerns) == pytest.approx(0.3499, abs=1e-3)


def test_compute_robustness_run006_high_end():
    """25 HIGH + 28 MED + 4 LOW → graded score in the low-but-nonzero range."""
    concerns = (
        [_concern(Severity.HIGH)] * 25
        + [_concern(Severity.MEDIUM)] * 28
        + [_concern(Severity.LOW)] * 4
    )
    # weighted = 25*0.30 + 28*0.10 + 4*0.03 = 7.5 + 2.8 + 0.12 = 10.42
    # exp(-0.15 * 10.42) = exp(-1.563) = 0.2096
    assert compute_robustness(concerns) == pytest.approx(0.2096, abs=1e-3)


def test_compute_robustness_mixed_severity():
    concerns = [
        _concern(Severity.HIGH),
        _concern(Severity.MEDIUM),
        _concern(Severity.MEDIUM),
        _concern(Severity.LOW),
    ]
    # weighted = 0.30 + 0.10 + 0.10 + 0.03 = 0.53; exp(-0.0795) = 0.9236
    assert compute_robustness(concerns) == pytest.approx(0.9236, abs=1e-3)


def test_compute_robustness_decay_k_parameter_is_tunable():
    """Higher k punishes the same concern count more aggressively."""
    concerns = [_concern(Severity.HIGH)] * 5
    r_default = compute_robustness(concerns, decay_k=0.15)
    r_stricter = compute_robustness(concerns, decay_k=0.50)
    r_lenient = compute_robustness(concerns, decay_k=0.05)
    assert r_stricter < r_default < r_lenient


def test_compute_robustness_never_exceeds_one_or_drops_to_zero():
    """exp(-k*x) lives in (0, 1] for non-negative k, x; no clamping artifacts."""
    assert compute_robustness([]) == 1.0
    huge = [_concern(Severity.HIGH)] * 1000
    r = compute_robustness(huge)
    assert 0.0 < r < 1e-10  # asymptotic, never exactly 0


# --------------------------------------------------------------------- LLM-mock paths


def _client_with_framing_responses(
    per_framing: dict[str, RawFindingsBatch],
) -> MagicMock:
    """Mock client routing parse() calls to the right framing's batch.

    Inspects the cached system prompt text to identify which framing was
    invoked; each framing's system prompt contains a unique substring.
    """
    client = MagicMock()

    def parse_side_effect(**kwargs):
        system_text = kwargs["system"][0]["text"]
        for framing, batch in per_framing.items():
            framing_text = FRAMINGS[framing]
            # Use a distinct slice of the framing description to disambiguate.
            if framing_text[:60] in system_text:
                return FakeParsedMessage(batch)
        return FakeParsedMessage(RawFindingsBatch(findings=[]))

    client.messages.parse.side_effect = parse_side_effect
    return client


def test_stage4_runs_all_eight_framings():
    """Every framing in DEFAULT_FRAMINGS produces exactly one LLM call."""
    client = _client_with_framing_responses({})
    stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    assert client.messages.parse.call_count == 8


def test_stage4_returns_score_and_concerns_on_clean_pass():
    """All framings returning empty → robustness=1.0, empty concerns, all framings noted clean."""
    client = _client_with_framing_responses({})
    finding = stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    assert finding.robustness == 1.0
    assert finding.concerns == []
    assert "no structural concerns" in finding.reasoning.lower()


def test_stage4_aggregates_concerns_across_framings():
    """Concerns from multiple framings appear in the combined list, framing-tagged."""
    batches = {
        "regulatory": RawFindingsBatch(
            findings=[
                RawFinding(
                    claim="reg risk",
                    evidence="case law",
                    falsification_condition="if licensure clear",
                    severity=Severity.HIGH,
                )
            ]
        ),
        "legal_exposure": RawFindingsBatch(
            findings=[
                RawFinding(
                    claim="UPL exposure",
                    evidence="recent enforcement",
                    falsification_condition="if scope narrow",
                    severity=Severity.MEDIUM,
                )
            ]
        ),
    }
    client = _client_with_framing_responses(batches)
    finding = stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    framings = {c.framing for c in finding.concerns}
    assert framings == {"regulatory", "legal_exposure"}
    # weighted = 0.30 (HIGH) + 0.10 (MEDIUM) = 0.40
    # exp(-0.15 * 0.40) = 0.9418
    assert finding.robustness == pytest.approx(0.9418, abs=1e-3)


def test_stage4_robustness_score_in_zero_one_range():
    """Stage 4 must emit robustness inside (0, 1] regardless of concern count.

    Sprint 1: with exponential decay, 24 HIGH concerns produce
    exp(-0.15 * 7.2) = 0.339 — graded, not collapsed. The score asymptotes
    toward zero but never reaches it under any realistic concern count.
    """
    batches = {
        framing: RawFindingsBatch(
            findings=[
                RawFinding(
                    claim="c", evidence="e",
                    falsification_condition="if x",
                    severity=Severity.HIGH,
                )
            ] * 3
        )
        for framing in DEFAULT_FRAMINGS
    }
    client = _client_with_framing_responses(batches)
    finding = stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    assert 0.0 < finding.robustness <= 1.0
    # 24 HIGH × 0.30 = 7.2 weighted; exp(-1.08) = 0.3396
    assert finding.robustness == pytest.approx(0.3396, abs=1e-3)


def test_stage4_drops_falsification_less_concerns():
    """A concern emitted by the LLM without a falsification_condition must be dropped."""
    batches = {
        "regulatory": RawFindingsBatch(
            findings=[
                RawFinding(
                    claim="good concern", evidence="e",
                    falsification_condition="if x",
                    severity=Severity.MEDIUM,
                ),
                RawFinding(
                    claim="dropped concern", evidence="e",
                    falsification_condition="   ",  # blank
                    severity=Severity.HIGH,
                ),
            ]
        )
    }
    client = _client_with_framing_responses(batches)
    finding = stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    assert [c.claim for c in finding.concerns] == ["good concern"]
    # Robustness reflects only the good concern: weighted=0.10; exp(-0.015)=0.9851
    assert finding.robustness == pytest.approx(0.9851, abs=1e-3)


def test_stage4_runs_framings_in_parallel():
    """Wall-clock for 8 framings at max_workers=4 ≈ 2 rounds, well under serial.

    Each framing sleeps 0.1s before returning an empty batch.
    """
    import time

    client = MagicMock()

    def slow_parse(**kwargs):
        time.sleep(0.1)
        return FakeParsedMessage(RawFindingsBatch(findings=[]))

    client.messages.parse.side_effect = slow_parse

    started = time.monotonic()
    stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    elapsed = time.monotonic() - started

    # Serial = 0.8s. Parallel with max_workers=4 ≈ 0.2s. 0.5s gives slack.
    assert elapsed < 0.5, f"Stage 4 took {elapsed:.2f}s; expected <0.5s parallel"


def test_stage4_raises_stage4_output_error_on_truncation():
    """SDK-side pydantic.ValidationError from any framing surfaces as Stage4OutputError."""
    client = MagicMock()
    client.messages.parse.side_effect = make_truncation_error()
    with pytest.raises(Stage4OutputError):
        stage4_adversarial(SATOSHI_FIXTURE.architecture, client)


def test_stage4_concerns_carry_framing_tag():
    """Every concern in the output knows which framing surfaced it."""
    batches = {
        "scaling_cliffs": RawFindingsBatch(
            findings=[
                RawFinding(
                    claim="hits AUM wall", evidence="reg threshold",
                    falsification_condition="if AUM stays below 100M",
                    severity=Severity.HIGH,
                )
            ]
        )
    }
    client = _client_with_framing_responses(batches)
    finding = stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    assert len(finding.concerns) == 1
    assert finding.concerns[0].framing == "scaling_cliffs"


def test_stage4_reasoning_lists_framings_with_concerns_and_clean_framings():
    """The reasoning string summarises which framings produced concerns and which were clean."""
    batches = {
        "regulatory": RawFindingsBatch(
            findings=[
                RawFinding(
                    claim="c", evidence="e",
                    falsification_condition="f", severity=Severity.LOW,
                )
            ]
        )
    }
    client = _client_with_framing_responses(batches)
    finding = stage4_adversarial(SATOSHI_FIXTURE.architecture, client)
    assert "regulatory" in finding.reasoning
    assert any(
        framing in finding.reasoning
        for framing in ("legal_exposure", "economic", "operational")
    )
