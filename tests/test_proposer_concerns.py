"""Sprint 6: tests for closed-RL-loop proposer + component-synthesis framing.

Two coupled changes under test:
  - format_concerns_for_proposer: grouping by framing, severity-based
    truncation, FAILED_FRAMINGS_SENTINEL filtering, None/empty handling.
  - render_seeds: emits the condensed concerns block per candidate.
  - PROPOSER_SYSTEM language: component-synthesis terminology in place
    of pattern-retrieval terminology.
  - PROPOSER_VERSION bumped past v1.

No live LLM calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alphamo.evaluator.stage4_adversarial import FAILED_FRAMINGS_SENTINEL
from alphamo.prompts.proposer_prompt import (
    CONCERNS_BUDGET_CHARS,
    PROPOSER_SYSTEM,
    PROPOSER_VERSION,
    format_concerns_for_proposer,
    render_seeds,
)
from alphamo.proposer import Proposer
from alphamo.sampler import Seed
from alphamo.schemas import Architecture, Scores
from alphamo.schemas.findings import Severity, StructuralConcern
from tests.fixtures.parsed_message import FakeParsedMessage


# ---------------------------------------------------------------- helpers


def _concern(framing: str, severity: Severity, claim: str = "stub claim") -> StructuralConcern:
    return StructuralConcern(
        framing=framing,
        claim=claim,
        evidence="stub evidence",
        falsification_condition="stub falsifier",
        severity=severity,
    )


def _arch(name: str = "test-arch") -> Architecture:
    return Architecture(
        name=name,
        summary="summary",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources="er",
    )


def _scores() -> Scores:
    return Scores(
        feasibility=0.85, structural=0.86, robustness=0.21,
        middle_class_accessible=True,
    )


def _seed(findings: list[StructuralConcern] | None = None) -> Seed:
    return Seed(
        architecture=_arch(),
        scores=_scores(),
        fitness=0.639,
        stage4_findings=findings,
    )


# ---------------------------------------------------------------- PROPOSER_VERSION


def test_proposer_version_advanced_past_v1():
    """Sprint 6 bumped PROPOSER_VERSION so trajectories under the new
    closed-RL-loop + component-synthesis framing are distinguishable
    from pre-Sprint-6 trajectories in the DB."""
    assert PROPOSER_VERSION != "v1", (
        "PROPOSER_VERSION still says 'v1' — Sprint 6 must bump this "
        "since the prompt construction shape changed materially "
        "(concerns now included, framing reframed)"
    )


# ---------------------------------------------------------------- format_concerns_for_proposer


def test_format_concerns_returns_empty_string_for_none():
    """Bootstrap-era trivial seed candidates have stage4_findings=None
    (or rather, the trivial seed has been scored and has whatever
    findings the cascade produced; for early-exit cascade results
    we get None). Either way, no concerns block emitted."""
    assert format_concerns_for_proposer(None) == ""


def test_format_concerns_returns_empty_string_for_empty_list():
    """Stage 3 ran clean — no concerns. No concerns block emitted."""
    assert format_concerns_for_proposer([]) == ""


def test_format_concerns_filters_out_failed_framings_sentinel():
    """Sprint 4's `_meta` sentinel concerns are forensic metadata, not
    a structural critique. They must not appear in the proposer's view."""
    findings = [
        StructuralConcern(
            framing=FAILED_FRAMINGS_SENTINEL,
            claim="framings_failed",
            evidence="economic",
            falsification_condition="all framings complete",
            severity=Severity.LOW,
        ),
    ]
    # Only the sentinel: result is empty.
    assert format_concerns_for_proposer(findings) == ""


def test_format_concerns_groups_by_framing():
    findings = [
        _concern("regulatory", Severity.HIGH, "reg high 1"),
        _concern("economic", Severity.HIGH, "econ high 1"),
        _concern("regulatory", Severity.MEDIUM, "reg med 1"),
        _concern("economic", Severity.MEDIUM, "econ med 1"),
    ]
    rendered = format_concerns_for_proposer(findings)
    assert "Adversarial scrutiny findings (Stage 3):" in rendered
    # Each framing has its own subsection.
    assert "  regulatory:" in rendered
    assert "  economic:" in rendered
    # Severity tag appears inline with the claim text.
    assert "[HIGH] reg high 1" in rendered
    assert "[HIGH] econ high 1" in rendered
    assert "[MEDIUM] reg med 1" in rendered
    assert "[MEDIUM] econ med 1" in rendered


def test_format_concerns_keeps_claim_text_verbatim():
    """Claims must not be paraphrased or truncated mid-string — the
    proposer needs the cascade's actual critique to perform component
    diagnosis."""
    long_claim = (
        "The single-person constraint breaks structurally between "
        "$20M-80M annual cash flow because back-office obligations of "
        "holding 10,000+ severed mineral interests grow with portfolio "
        "size and cannot be algorithmically discharged."
    )
    rendered = format_concerns_for_proposer(
        [_concern("scaling_cliffs", Severity.HIGH, long_claim)]
    )
    assert long_claim in rendered


def test_format_concerns_sorts_by_severity_within_framing():
    """HIGH appears before MEDIUM within a single framing's section."""
    findings = [
        _concern("regulatory", Severity.MEDIUM, "reg med"),
        _concern("regulatory", Severity.HIGH, "reg high"),
    ]
    rendered = format_concerns_for_proposer(findings)
    high_idx = rendered.find("reg high")
    med_idx = rendered.find("reg med")
    assert high_idx < med_idx


def test_format_concerns_drops_low_severity_entirely():
    """LOW concerns are dropped from the proposer view by policy — the
    proposer should focus on HIGH/MEDIUM. LOW remains persisted on the
    candidate row."""
    findings = [
        _concern("regulatory", Severity.HIGH, "reg high"),
        _concern("regulatory", Severity.LOW, "reg low (should be dropped)"),
    ]
    rendered = format_concerns_for_proposer(findings)
    assert "reg high" in rendered
    assert "reg low" not in rendered
    # Dropped concerns counted in the truncation note.
    assert "1 additional concern(s) truncated" in rendered


def test_format_concerns_truncates_medium_to_budget():
    """When the section exceeds CONCERNS_BUDGET_CHARS, MEDIUM concerns
    are dropped until the section fits; HIGH concerns are kept; the
    drop count is appended."""
    # Build concerns whose rendered size adds up to clearly exceed
    # the default 4000-char budget. ~50 MEDIUM concerns at ~200 chars
    # each = ~10K chars, comfortably over.
    long_claim = "x" * 200
    findings = (
        [_concern("regulatory", Severity.HIGH, long_claim)]
        + [_concern("economic", Severity.MEDIUM, f"med-{i}: {long_claim}") for i in range(50)]
    )
    rendered = format_concerns_for_proposer(findings, max_chars=4000)
    # HIGH concern survives.
    assert "regulatory:" in rendered
    assert long_claim in rendered
    # Some MEDIUM concerns dropped.
    assert "additional concern(s) truncated" in rendered


def test_format_concerns_keeps_all_high_even_if_over_budget():
    """When HIGH-only already exceeds budget, all HIGH concerns are
    still kept — the proposer must see every HIGH critique."""
    long_claim = "x" * 1000
    findings = [
        _concern("regulatory", Severity.HIGH, f"high-{i}: {long_claim}")
        for i in range(10)
    ]
    rendered = format_concerns_for_proposer(findings, max_chars=500)
    # All 10 HIGH claims appear despite blowing the budget.
    for i in range(10):
        assert f"high-{i}:" in rendered


def test_format_concerns_no_truncation_note_when_nothing_dropped():
    """Clean case: all HIGH/MEDIUM fit under budget, no LOW present →
    no truncation note appended."""
    findings = [
        _concern("regulatory", Severity.HIGH, "reg high"),
        _concern("economic", Severity.MEDIUM, "econ med"),
    ]
    rendered = format_concerns_for_proposer(findings)
    assert "truncated" not in rendered


# ---------------------------------------------------------------- render_seeds integration


def test_render_seeds_includes_concerns_section_when_present():
    """The full proposer user message includes the per-candidate
    concerns section."""
    findings = [
        _concern(
            "mechanism_robustness", Severity.HIGH,
            "Online comparable-sale platforms compressed the moat since 2018."
        ),
        _concern(
            "scaling_cliffs", Severity.HIGH,
            "Back-office labor breaks the labor separation between $20M-80M revenue."
        ),
    ]
    seed = _seed(findings=findings)
    rendered = render_seeds([seed])
    assert "Adversarial scrutiny findings (Stage 3):" in rendered
    assert "mechanism_robustness:" in rendered
    assert "scaling_cliffs:" in rendered
    assert "Online comparable-sale platforms" in rendered
    assert "Back-office labor" in rendered


def test_render_seeds_omits_concerns_section_when_findings_none():
    """Trivial-seed bootstrap case: no concerns to show → no concerns
    section in the rendered output. The candidate's architecture and
    scores still appear normally."""
    seed = _seed(findings=None)
    rendered = render_seeds([seed])
    assert "Adversarial scrutiny findings" not in rendered
    # Architecture content still appears.
    assert "Summary: summary" in rendered


def test_render_seeds_omits_concerns_section_when_findings_empty_list():
    """Clean Stage 3 pass case: empty findings list → no concerns
    section. Distinct from `None` only in the persistence layer; for
    the proposer's view they're the same."""
    seed = _seed(findings=[])
    rendered = render_seeds([seed])
    assert "Adversarial scrutiny findings" not in rendered


def test_render_seeds_handles_mixed_concern_presence_across_candidates():
    """Per-candidate decisions: one candidate has concerns, another
    doesn't. Render handles each independently."""
    with_concerns = Seed(
        architecture=_arch("with-concerns"),
        scores=_scores(),
        fitness=0.5,
        stage4_findings=[_concern("regulatory", Severity.HIGH, "reg")],
    )
    without_concerns = Seed(
        architecture=_arch("without-concerns"),
        scores=_scores(),
        fitness=0.6,
        stage4_findings=None,
    )
    rendered = render_seeds([with_concerns, without_concerns])
    # Concerns section appears once (for the first candidate).
    assert rendered.count("Adversarial scrutiny findings") == 1
    # Both architecture blocks present.
    assert "Candidate 1: with-concerns" in rendered
    assert "Candidate 2: without-concerns" in rendered


def test_proposer_user_message_includes_concern_text_end_to_end():
    """End-to-end: the proposer's parse() call receives the concerns
    in the user message, not just rendered to a local string."""
    findings = [
        _concern(
            "current_moment_dependency", Severity.HIGH,
            "Cell-tower ground-lease buyout market saturated since 2005-2022."
        ),
    ]
    seed = _seed(findings=findings)

    client = MagicMock()
    client.messages.parse.return_value = FakeParsedMessage(
        Architecture(
            name="proposed", summary="s", value_chain="v",
            capture_mechanism="c", entry_resources="e",
        )
    )
    Proposer(client).propose([seed])

    user_content = client.messages.parse.call_args[1]["messages"][0]["content"]
    assert "Adversarial scrutiny findings (Stage 3):" in user_content
    assert "current_moment_dependency:" in user_content
    assert "Cell-tower ground-lease buyout market" in user_content


# ---------------------------------------------------------------- PROPOSER_SYSTEM reframe


def test_proposer_system_mentions_structural_components():
    """Smoke test for the reframe: PROPOSER_SYSTEM must reference
    structural components / component synthesis / decomposition as
    the proposer's working method."""
    lowered = PROPOSER_SYSTEM.lower()
    assert "structural component" in lowered
    assert "synthesize" in lowered or "synthesis" in lowered
    # Decomposition step is explicit.
    assert "decomposition" in lowered or "decompose" in lowered


def test_proposer_system_lists_the_six_components():
    """The system prompt enumerates the six structural components so
    the model has a fixed vocabulary for decomposition:
    capture geometry, labor separation, scaling vector,
    defensibility, entry cost, failure-mode geometry."""
    for component in (
        "capture geometry",
        "labor separation",
        "scaling vector",
        "defensibility",
        "entry-cost",
        "failure-mode",
    ):
        assert component in PROPOSER_SYSTEM.lower(), (
            f"PROPOSER_SYSTEM missing '{component}' component enumeration"
        )


def test_proposer_system_instructs_not_to_retrieve_known_patterns():
    """The reframe explicitly warns against pattern retrieval —
    asking for component-built architectures, not renamed business
    patterns."""
    lowered = PROPOSER_SYSTEM.lower()
    assert "do not retrieve a known business pattern" in lowered


def test_proposer_system_includes_stage3_finding_instruction():
    """The system prompt tells the model that each candidate is
    annotated with Stage 3 adversarial findings — so the model
    expects them in the user turn and uses them for diagnosis."""
    lowered = PROPOSER_SYSTEM.lower()
    assert "stage 3 adversarial finding" in lowered


def test_proposer_system_retains_load_bearing_constraints():
    """The four load-bearing constraints (middle-class entry, single
    entity, $1B+ potential, labor separation) must remain in the
    system prompt — they're the structural identity of the
    parent goal."""
    for constraint in (
        "Middle-class accessible entry",
        "Single individual or single legal entity",
        "$1B+",
        "Operational labor is performed by parties other than the capture node",
    ):
        assert constraint in PROPOSER_SYSTEM, (
            f"PROPOSER_SYSTEM lost the '{constraint}' constraint"
        )


# ---------------------------------------------------------------- sampler integration


def test_seed_carries_stage4_findings_from_db_row(db, default_run):
    """Sprint 6: Sampler-built Seed objects now carry the candidate's
    stage4_findings, so the proposer sees them downstream."""
    from alphamo.sampler import _row_to_seed

    findings_payload = [
        {
            "framing": "regulatory",
            "claim": "test claim text",
            "evidence": "ev",
            "falsification_condition": "f",
            "severity": "high",
        },
    ]
    cand_id = db.insert(
        _arch(),
        _scores(),
        run_id=default_run,
        island_id=0,
        generation=1,
        stage4_findings=findings_payload,
    )
    row = db.get(cand_id)
    seed = _row_to_seed(row)
    assert seed.stage4_findings is not None
    assert len(seed.stage4_findings) == 1
    assert seed.stage4_findings[0].framing == "regulatory"
    assert seed.stage4_findings[0].claim == "test claim text"


def test_seed_stage4_findings_none_for_legacy_row(db, default_run):
    """Pre-Sprint-1 candidates (no stage4_findings column populated)
    produce Seed(stage4_findings=None)."""
    from alphamo.sampler import _row_to_seed

    cand_id = db.insert(
        _arch(),
        _scores(),
        run_id=default_run,
        island_id=0,
        generation=1,
        # no stage4_findings argument
    )
    row = db.get(cand_id)
    seed = _row_to_seed(row)
    assert seed.stage4_findings is None
