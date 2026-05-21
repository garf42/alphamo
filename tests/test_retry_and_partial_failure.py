"""Sprint 4: API-failure resilience tests for Fix 1 (SDK retry) and Fix 2
(graceful partial framing failure).

Fix 1 — verifies that all production-side anthropic.Anthropic() construction
sites pass `max_retries=3`. The SDK's built-in retry handles 408/409/429/
500+/connection errors with exponential backoff and Retry-After honoring;
we just need to configure it. No custom retry layer.

Fix 2 — verifies that Stage 3 adversarial scrutiny tolerates partial framing
failures up to a 5/9-success threshold (STAGE3_MIN_SUCCESSFUL_FRAMINGS).
Below threshold, the cascade raises and the orchestrator counts the iteration
as a failure (existing `consecutive_failures` path).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from alphamo._concurrent import run_parallel, run_parallel_collect_results
from alphamo.errors import Stage4OutputError
from alphamo.evaluator.stage4_adversarial import (
    FAILED_FRAMINGS_SENTINEL,
    STAGE3_MIN_SUCCESSFUL_FRAMINGS,
    stage4_adversarial,
)
from alphamo.prompts.stage4_prompts import DEFAULT_FRAMINGS, FRAMINGS
from alphamo.schemas import Architecture
from alphamo.schemas.findings import (
    RawFinding,
    RawFindingsBatch,
    Severity,
)
from tests.fixtures.parsed_message import FakeParsedMessage


# ---------------------------------------------------------------- Fix 1


_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_all_production_anthropic_clients_pass_max_retries():
    """Every production-side anthropic.Anthropic() must construct with
    max_retries=3 so transient API failures don't propagate.

    Greps the production source tree for `anthropic.Anthropic(` and
    verifies every call passes max_retries. This is a lightweight
    structural check — a unit test that mocks the SDK can't catch a
    missed construction site.
    """
    pattern = re.compile(r"anthropic\.Anthropic\((.*?)\)")
    bad_sites: list[str] = []
    for path in (_REPO_ROOT / "alphamo").rglob("*.py"):
        text = path.read_text()
        for match in pattern.finditer(text):
            args = match.group(1)
            if "max_retries" not in args:
                # Allow the `client or anthropic.Anthropic(max_retries=3)`
                # idiom and similar — caught by the inner check above.
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                line = text[line_start:line_end].strip()
                bad_sites.append(f"{path.relative_to(_REPO_ROOT)}: {line}")
    assert not bad_sites, (
        "Production sites must construct anthropic.Anthropic with "
        "max_retries set; offenders:\n  " + "\n  ".join(bad_sites)
    )


def test_pydantic_validation_error_is_not_retried_by_provider():
    """AnthropicProvider wraps pydantic.ValidationError into LLMOutputError
    without retry — schema mismatches don't benefit from retry.

    Sprint 14: this test moved from `parse_or_raise` to
    `AnthropicProvider.parse` after the provider abstraction landed.
    The Anthropic SDK's built-in retry layer only retries API-side
    errors; schema failures raised by pydantic.ValidationError inside
    `client.messages.parse(...)` must surface immediately so the
    orchestrator's consecutive_failures gate catches them.
    """
    import pydantic

    from alphamo.errors import LLMOutputError
    from alphamo.providers import AnthropicProvider

    class _Schema(pydantic.BaseModel):
        x: int

    client = MagicMock()
    # First call raises ValidationError; if there were a retry layer
    # under our control, a second call would be made. We verify
    # provider.parse() calls parse() exactly once.
    client.messages.parse.side_effect = pydantic.ValidationError.from_exception_data(
        title="ValidationError", line_errors=[]
    )

    provider = AnthropicProvider(client)
    with pytest.raises(LLMOutputError):
        provider.parse(
            error_cls=LLMOutputError,
            model="claude-haiku-4-5",
            max_tokens=128,
            system=[],
            messages=[{"role": "user", "content": "hi"}],
            output_format=_Schema,
        )
    assert client.messages.parse.call_count == 1


def test_sdk_max_retries_setting_threshold_documented():
    """Codifies the policy choice: max_retries=3 (4 total attempts).

    A pure-Python guard against accidental changes — the value is small,
    the doc is in commit messages, this test pins the number to one
    canonical location."""
    expected_max_retries = 3
    pattern = re.compile(r"max_retries\s*=\s*(\d+)")
    found_values: set[int] = set()
    for path in (_REPO_ROOT / "alphamo").rglob("*.py"):
        for match in pattern.finditer(path.read_text()):
            found_values.add(int(match.group(1)))
    assert found_values == {expected_max_retries}, (
        f"All max_retries occurrences in alphamo/ must equal "
        f"{expected_max_retries}; found {sorted(found_values)}"
    )


# ---------------------------------------------------------------- Fix 2 — run_parallel_collect_results


def test_run_parallel_collect_results_separates_successes_and_failures():
    """Order-preserving partition: each result slot is either the task's
    return value or the Exception it raised."""

    def succeed_with(value):
        return lambda: value

    def fail_with(exc):
        def task():
            raise exc
        return task

    tasks = [
        succeed_with("a"),
        fail_with(ValueError("oops")),
        succeed_with("c"),
        fail_with(RuntimeError("kaboom")),
    ]
    results = run_parallel_collect_results(tasks)
    assert len(results) == 4
    assert results[0] == "a"
    assert isinstance(results[1], ValueError)
    assert results[2] == "c"
    assert isinstance(results[3], RuntimeError)


def test_run_parallel_still_raises_on_first_failure_regression():
    """Existing callers of run_parallel must not get the collect-results
    behavior accidentally. run_parallel raises on first failure."""

    def boom():
        raise RuntimeError("from run_parallel")

    with pytest.raises(RuntimeError, match="from run_parallel"):
        run_parallel([boom, lambda: "never reached"])


# ---------------------------------------------------------------- Fix 2 — stage4_adversarial


def _candidate() -> Architecture:
    return Architecture(
        name="test-candidate",
        summary="s",
        value_chain="vc",
        capture_mechanism="cm",
        entry_resources="er",
    )


def _make_framing_client(failed_framings: set[str]) -> MagicMock:
    """Mock client that fails (raises) on the listed framings and returns
    an empty RawFindingsBatch on the others.

    Each framing's system prompt is uniquely identifiable by a prefix of
    its FRAMINGS[framing] text — same routing trick the live stage uses
    via `stage4_system(framing)`.
    """
    client = MagicMock()

    def parse_side_effect(**kwargs):
        # Sprint 12: system is now a list of cached blocks; concat all
        # text fields so framing-prefix matching still works.
        system_text = " ".join(b["text"] for b in kwargs["system"])
        for framing, prose in FRAMINGS.items():
            if prose[:60] in system_text:
                if framing in failed_framings:
                    # Simulate a post-SDK-retry failure surfacing from
                    # parse_or_raise as an LLMOutputError. Use a generic
                    # Exception here because the inner _run_framing wraps
                    # whatever parse() raises into Stage4OutputError.
                    raise RuntimeError(f"framing {framing!r} failed")
                return FakeParsedMessage(RawFindingsBatch(findings=[], assessment=None))
        # No framing matched — return clean (shouldn't happen in our tests).
        return FakeParsedMessage(RawFindingsBatch(findings=[], assessment=None))

    client.messages.parse.side_effect = parse_side_effect
    return client


def test_stage3_with_zero_failed_framings_unaffected_regression():
    """Sanity: pre-Sprint-4 behavior preserved when no framings fail —
    no sentinel concern, normal robustness computed from real concerns."""
    client = _make_framing_client(failed_framings=set())
    finding = stage4_adversarial(_candidate(), client)

    sentinel = [c for c in finding.concerns if c.framing == FAILED_FRAMINGS_SENTINEL]
    assert sentinel == []
    # Clean run: no concerns surfaced, robustness should be 1.0.
    assert finding.robustness == 1.0
    assert "PARTIAL COVERAGE" not in finding.reasoning


def test_stage3_with_one_failed_framing_continues_with_survivors():
    """1 of 9 failed: candidate still scored from the surviving 8.
    Sentinel concern records the failed framing."""
    client = _make_framing_client(failed_framings={"economic"})
    finding = stage4_adversarial(_candidate(), client)

    sentinel = [c for c in finding.concerns if c.framing == FAILED_FRAMINGS_SENTINEL]
    assert len(sentinel) == 1
    assert "economic" in sentinel[0].evidence
    assert "PARTIAL COVERAGE" in finding.reasoning
    assert "8 of 9" in finding.reasoning or "1 of 9" in finding.reasoning
    # 8 framings returned clean → no real concerns → sentinel doesn't
    # count toward weight → robustness stays at 1.0.
    assert finding.robustness == 1.0


def test_stage3_with_four_failed_framings_continues_at_threshold_boundary():
    """4 of 9 failed (5 succeeded) = exactly at the threshold. Continue."""
    failed = {"regulatory", "economic", "operational", "timeline_plausibility"}
    assert len(DEFAULT_FRAMINGS) - len(failed) == STAGE3_MIN_SUCCESSFUL_FRAMINGS
    client = _make_framing_client(failed_framings=failed)
    finding = stage4_adversarial(_candidate(), client)

    sentinel = [c for c in finding.concerns if c.framing == FAILED_FRAMINGS_SENTINEL]
    assert len(sentinel) == 1
    failed_listed = set(sentinel[0].evidence.split(", "))
    assert failed_listed == failed


def test_stage3_with_five_failed_framings_raises_catastrophic_failure():
    """5 of 9 failed (only 4 succeeded) = below threshold. Raise."""
    failed = {
        "regulatory", "economic", "operational",
        "timeline_plausibility", "mechanism_robustness",
    }
    assert len(DEFAULT_FRAMINGS) - len(failed) < STAGE3_MIN_SUCCESSFUL_FRAMINGS
    client = _make_framing_client(failed_framings=failed)
    with pytest.raises(Stage4OutputError) as exc_info:
        stage4_adversarial(_candidate(), client)
    assert exc_info.value.stop_reason == "stage3_catastrophic_framing_failure"
    assert "min required" in exc_info.value.detail


def test_stage3_all_framings_failed_raises_catastrophic_failure():
    """0 of 9 succeeded = degenerate case; raise catastrophic failure."""
    client = _make_framing_client(failed_framings=set(DEFAULT_FRAMINGS))
    with pytest.raises(Stage4OutputError) as exc_info:
        stage4_adversarial(_candidate(), client)
    assert exc_info.value.stop_reason == "stage3_catastrophic_framing_failure"


def test_sentinel_concern_is_filtered_from_robustness_computation():
    """The `_meta` sentinel must not contribute weight to robustness even
    though it's persisted on the candidate row."""
    from alphamo.evaluator.stage4_adversarial import (
        compute_robustness,
        _failed_framings_sentinel,
    )
    from alphamo.schemas.findings import StructuralConcern

    real_high = StructuralConcern(
        framing="regulatory", claim="c", evidence="e",
        falsification_condition="f", severity=Severity.HIGH,
    )
    sentinel = _failed_framings_sentinel(["economic"])
    with_sentinel = compute_robustness([real_high, sentinel])
    without_sentinel = compute_robustness([real_high])
    assert with_sentinel == without_sentinel


def test_orchestrator_emits_partial_failure_audit_event_when_stage3_partial(
    db, monkeypatch, tmp_path
):
    """When Stage 3 ran with partial coverage, orchestrator emits a
    dedicated `stage3_partial_framing_failure` audit event."""
    from alphamo import orchestrator as orch_mod
    from alphamo.context.hyperparams import Hyperparameters
    from alphamo.evaluator import cascade as cascade_mod
    from alphamo.meta.audit_log import AuditLog
    from alphamo.orchestrator import Orchestrator
    from alphamo.schemas.findings import Stage1Finding, Stage2Finding
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: Stage1Finding(
            feasibility=0.9, middle_class_accessible=True, reasoning="ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: Stage2Finding(
            one_person_threshold=0.9, billion_dollar_potential=0.9,
            labor_separation=0.9, structural=0.9, reasoning="ok",
        ),
    )
    # Stub stage3 (the renamed stage4_adversarial) to fail only the
    # "economic" framing for every call. The trivial-seed bootstrap and
    # the iteration's candidate both flow through this.
    monkeypatch.setattr(
        cascade_mod, "stage4_adversarial",
        lambda a, c, **kw: stage4_adversarial(
            a, _make_framing_client({"economic"})
        ),
    )

    from tests.fixtures.parsed_message import FakeParsedMessage
    from alphamo.schemas import Architecture
    from alphamo.schemas.findings import (
        Classification, ClassificationVerdict,
    )

    proposer_client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            return FakeParsedMessage(
                Architecture(
                    name="generated", summary="s", value_chain="vc",
                    capture_mechanism="cm", entry_resources="er",
                )
            )
        if output_format is ClassificationVerdict:
            return FakeParsedMessage(
                ClassificationVerdict(
                    classification=Classification.COSMETIC, rationale="x"
                )
            )
        return FakeParsedMessage(MagicMock())

    proposer_client.messages.parse.side_effect = parse_side_effect

    audit = AuditLog(tmp_path / "audit.jsonl")
    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, proposer_client, audit, hp=hp)
    orch._bootstrap_islands()
    orch.step(generation=1)

    partial_events = [
        e for e in audit.read_all()
        if e.trigger == "stage3_partial_framing_failure"
    ]
    assert len(partial_events) >= 1
    sample = partial_events[0]
    assert "economic" in sample.payload["failed_framings"]


def test_orchestrator_emits_catastrophic_failure_audit_event_when_stage3_below_threshold(
    db, monkeypatch, tmp_path
):
    """When Stage 3 below threshold raises, orchestrator emits the
    `stage3_catastrophic_framing_failure` audit event AND the iteration
    counts as a failure (no candidate inserted)."""
    from alphamo import orchestrator as orch_mod
    from alphamo.context.hyperparams import Hyperparameters
    from alphamo.evaluator import cascade as cascade_mod
    from alphamo.meta.audit_log import AuditLog
    from alphamo.orchestrator import Orchestrator
    from alphamo.schemas.findings import Stage1Finding, Stage2Finding
    monkeypatch.setattr(
        cascade_mod, "stage1_feasibility",
        lambda a, c, **kw: Stage1Finding(
            feasibility=0.9, middle_class_accessible=True, reasoning="ok"
        ),
    )
    monkeypatch.setattr(
        cascade_mod, "stage2_structured",
        lambda a, c, **kw: Stage2Finding(
            one_person_threshold=0.9, billion_dollar_potential=0.9,
            labor_separation=0.9, structural=0.9, reasoning="ok",
        ),
    )

    # Sprint 14: bootstrap no longer invokes the cascade (the trivial
    # seed gets a hard-coded model-independent Scores), so every
    # stage3 invocation is for the step()'s generated candidate. Fail
    # 6 of 9 framings unconditionally so catastrophic failure raises.
    def stage3_always_catastrophic(a, c, **kw):
        failed = {
            "regulatory", "economic", "operational",
            "timeline_plausibility", "mechanism_robustness",
            "hidden_dependencies",
        }
        return stage4_adversarial(a, _make_framing_client(failed))

    monkeypatch.setattr(cascade_mod, "stage4_adversarial", stage3_always_catastrophic)

    from tests.fixtures.parsed_message import FakeParsedMessage
    from alphamo.schemas import Architecture
    from alphamo.schemas.findings import Classification, ClassificationVerdict

    proposer_client = MagicMock()

    def parse_side_effect(**kwargs):
        output_format = kwargs.get("output_format")
        if output_format is Architecture:
            return FakeParsedMessage(
                Architecture(
                    name="generated", summary="s", value_chain="vc",
                    capture_mechanism="cm", entry_resources="er",
                )
            )
        if output_format is ClassificationVerdict:
            return FakeParsedMessage(
                ClassificationVerdict(
                    classification=Classification.COSMETIC, rationale="x"
                )
            )
        return FakeParsedMessage(MagicMock())

    proposer_client.messages.parse.side_effect = parse_side_effect

    audit = AuditLog(tmp_path / "audit.jsonl")
    hp = Hyperparameters(
        num_islands=2,
        reset_every_generations=1000,
        research_every_generations=1000,
        milestone_min_generation=10_000,
    )
    orch = Orchestrator.for_new_run(db, proposer_client, audit, hp=hp)
    orch._bootstrap_islands()
    event = orch.step(generation=1)

    # Iteration counts as a failure: no candidate inserted, failure
    # reason set, candidate_id is None.
    assert event.candidate_id is None
    assert event.failure_reason is not None
    assert "stage3_catastrophic" in event.failure_reason

    catastrophic_events = [
        e for e in audit.read_all()
        if e.trigger == "stage3_catastrophic_framing_failure"
    ]
    assert len(catastrophic_events) == 1
    payload = catastrophic_events[0].payload
    assert payload["island_id"] is not None
    assert "architecture" in payload
