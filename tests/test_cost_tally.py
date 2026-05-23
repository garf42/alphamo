"""Sprint cost-tracker-fix: pin the caching-aware billing math.

Super's downstream tally reported $6.24 against an actual $1.82 credit
burn on run_4e5d8d6f Chunk 1 — a 3.4× overestimate. Root cause: the
naive `input_tokens × $0.14/M + output_tokens × $0.28/M` formula
charged the cached portion of input_tokens at the UNCACHED rate.

These tests pin the corrected math against the actual Fireworks /
DeepSeek V4 Flash billing model:
  - Cache-miss input    : $0.14/MTok
  - Cached input        : $0.0028/MTok  (98% discount)
  - Output              : $0.28/MTok    (reasoning tokens included)

Audit-event payload schema is read-only — these tests verify only
the consumer-side fix, not any change to the emission side.
"""

from __future__ import annotations

import json

import pytest

from scripts.cost_tally import (
    DEEPSEEK_V4_FLASH,
    FIREWORKS_DEEPSEEK_V4_FLASH_MODEL_ID,
    CostBreakdown,
    _classify_event,
    _provider_of,
    load_events,
    tally_events,
)


# ----------------------------------------------------------------- payload classification


def test_fireworks_input_tokens_includes_cached_portion_subtract_to_get_uncached():
    """The core correctness property: on Fireworks payloads, the raw
    `input_tokens` is the TOTAL prompt count (matches Fireworks's
    `prompt_tokens`); the cached subset must be SUBTRACTED to get
    the billable uncached portion. The naive tracker added them
    instead, double-counting cache_read."""
    payload = {
        "provider": "fireworks",
        "input_tokens": 40_000,
        "output_tokens": 500,
        "cache_read_input_tokens": 36_600,
        "cache_creation_input_tokens": 0,
    }
    uncached, cached, output, cache_create = _classify_event(payload)
    # Uncached = 40,000 - 36,600 = 3,400
    assert uncached == 3_400
    assert cached == 36_600
    assert output == 500
    assert cache_create == 0
    # Sum invariant: uncached + cached == raw input_tokens.
    assert uncached + cached == payload["input_tokens"]


def test_fireworks_cache_creation_always_zero():
    """Fireworks uses automatic prefix caching — no client-driven cache
    creation. The provider always reports cache_creation_input_tokens=0;
    the tally should never charge a cache-write fee on Fireworks events."""
    payload = {
        "provider": "fireworks",
        "input_tokens": 1000,
        "output_tokens": 100,
        "cache_read_input_tokens": 800,
        "cache_creation_input_tokens": 0,
    }
    _, _, _, cache_create = _classify_event(payload)
    assert cache_create == 0


def test_fireworks_no_cache_hit_charges_all_input_at_uncached_rate():
    """When cache_read_input_tokens == 0 (first call, cache miss, or
    sub-cache-threshold prefix), the full input_tokens count is
    billable at the uncached rate."""
    payload = {
        "provider": "fireworks",
        "input_tokens": 5000,
        "output_tokens": 200,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    uncached, cached, output, _ = _classify_event(payload)
    assert uncached == 5000
    assert cached == 0
    assert output == 200


def test_fireworks_malformed_cache_exceeds_input_clamps_at_zero():
    """Defensive guard: if a malformed event reports cache_read >
    input_total (which shouldn't happen but might from a future
    provider-shape change), uncached clamps at 0 rather than going
    negative and producing a negative cost."""
    payload = {
        "provider": "fireworks",
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_input_tokens": 200,  # impossible but defensively handled
        "cache_creation_input_tokens": 0,
    }
    uncached, cached, _, _ = _classify_event(payload)
    assert uncached == 0
    assert cached == 200


def test_anthropic_input_tokens_is_uncached_count_by_sdk_convention():
    """Anthropic's SDK reports `input_tokens` as the UNCACHED portion
    and surfaces cache_read / cache_creation as separate columns —
    opposite of Fireworks's gross-prompt-tokens convention. The
    classifier must respect this so Anthropic events aren't
    accidentally double-discounted."""
    payload = {
        "provider": "anthropic",
        "input_tokens": 1_200,           # uncached only
        "output_tokens": 400,
        "cache_read_input_tokens": 8_000,
        "cache_creation_input_tokens": 2_000,
    }
    uncached, cached, output, cache_create = _classify_event(payload)
    assert uncached == 1_200
    assert cached == 8_000
    assert output == 400
    assert cache_create == 2_000


# ----------------------------------------------------------------- pricing


def test_deepseek_v4_flash_pricing_constants_match_verified_published_rates():
    """Pin the pricing constants. Updating these should be a deliberate
    code change accompanied by a docstring note on when/where verified."""
    assert DEEPSEEK_V4_FLASH["input_per_mtok"] == 0.14
    assert DEEPSEEK_V4_FLASH["cached_input_per_mtok"] == 0.0028
    assert DEEPSEEK_V4_FLASH["output_per_mtok"] == 0.28
    assert DEEPSEEK_V4_FLASH["cache_creation_per_mtok"] == 0.0


def test_cost_breakdown_applies_each_rate_to_its_column():
    """Hand-computed: 100K uncached + 1M cached + 50K output on
    DeepSeek V4 Flash:
      cost = 100_000 × 0.14/M + 1_000_000 × 0.0028/M + 50_000 × 0.28/M
           = 0.014 + 0.0028 + 0.014
           = 0.0308 USD"""
    bucket = CostBreakdown(
        label="t",
        n_events=1,
        input_tokens=100_000,
        cached_input_tokens=1_000_000,
        output_tokens=50_000,
        cache_creation_tokens=0,
    )
    cost = bucket.cost_usd(DEEPSEEK_V4_FLASH)
    assert cost == pytest.approx(0.0308, abs=1e-6)


def test_naive_billing_overestimates_when_cache_hit_is_large():
    """The diagnostic invariant. With a high cache-hit ratio, the
    naive formula (charging cached tokens at the uncached rate) over-
    estimates by approximately the cached_input_tokens × discount
    delta.

    Setup: 50K uncached + 500K cached + 20K output.
    Naive:   (50_000 + 500_000) × 0.14/M + 20_000 × 0.28/M
           = 0.077 + 0.0056 = 0.0826 USD
    Correct: 50_000 × 0.14/M + 500_000 × 0.0028/M + 20_000 × 0.28/M
           = 0.007 + 0.0014 + 0.0056 = 0.014 USD
    Ratio:   0.0826 / 0.014 ≈ 5.9× over."""
    correct = CostBreakdown(
        label="t",
        input_tokens=50_000, cached_input_tokens=500_000,
        output_tokens=20_000,
    )
    correct_cost = correct.cost_usd(DEEPSEEK_V4_FLASH)
    # Naive simulation: treat cached_input as uncached input.
    naive = CostBreakdown(
        label="t",
        input_tokens=550_000, cached_input_tokens=0,
        output_tokens=20_000,
    )
    naive_cost = naive.cost_usd(DEEPSEEK_V4_FLASH)
    assert naive_cost > correct_cost
    assert naive_cost / correct_cost > 5.0


def test_provider_inference_from_model_id():
    assert _provider_of(FIREWORKS_DEEPSEEK_V4_FLASH_MODEL_ID) == "fireworks"
    assert _provider_of("accounts/fireworks/models/something-else") == "fireworks"
    assert _provider_of("claude-sonnet-4-6") == "anthropic"
    assert _provider_of("claude-opus-4-7") == "anthropic"
    # Unknown defaults to fireworks (Sprint 14 production routing).
    assert _provider_of("mystery") == "fireworks"


# ----------------------------------------------------------------- tally + I/O


def _llm_usage_event(**payload_overrides):
    """Build one llm_usage event matching the audit-log payload shape."""
    payload = dict(
        component="stage3",
        provider="fireworks",
        model=FIREWORKS_DEEPSEEK_V4_FLASH_MODEL_ID,
        input_tokens=40_000,
        output_tokens=500,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=36_600,
        generation=1, island_id=0, stop_reason="stop",
    )
    payload.update(payload_overrides)
    return {
        "timestamp": "2026-05-23T00:00:00+00:00",
        "run_id": "run_test",
        "trigger": "llm_usage",
        "classification": "routine",
        "action": "recorded",
        "rationale": "test stub",
        "payload": payload,
    }


def test_tally_aggregates_per_component_and_per_model():
    events = [
        _llm_usage_event(component="proposer", input_tokens=10_000, output_tokens=2_000,
                         cache_read_input_tokens=8_000),
        _llm_usage_event(component="stage1", input_tokens=5_000, output_tokens=200,
                         cache_read_input_tokens=4_500),
        # 3 stage3 framings under the same cached corpus
        _llm_usage_event(component="stage3", input_tokens=37_000, output_tokens=400,
                         cache_read_input_tokens=36_600),
        _llm_usage_event(component="stage3", input_tokens=37_500, output_tokens=450,
                         cache_read_input_tokens=36_600),
        _llm_usage_event(component="stage3", input_tokens=37_200, output_tokens=420,
                         cache_read_input_tokens=36_600),
    ]
    result = tally_events(events)
    assert result.total.n_events == 5
    assert set(result.per_component) == {"proposer", "stage1", "stage3"}
    assert result.per_component["stage3"].n_events == 3
    # Each component's uncached + cached sums to the raw input_tokens
    # sum, the invariant that catches double-counting bugs.
    proposer = result.per_component["proposer"]
    assert proposer.input_tokens + proposer.cached_input_tokens == 10_000
    stage3 = result.per_component["stage3"]
    assert stage3.input_tokens + stage3.cached_input_tokens == 37_000 + 37_500 + 37_200


def test_tally_skips_non_llm_usage_events():
    events = [
        _llm_usage_event(),
        {"trigger": "stage4_routine", "payload": {"candidate_id": 1}},
        {"trigger": "island_reset", "payload": {"generation": 10}},
        _llm_usage_event(component="proposer"),
    ]
    result = tally_events(events)
    assert result.total.n_events == 2
    assert set(result.per_component) == {"stage3", "proposer"}


def test_load_events_filters_by_run_id(tmp_path):
    path = tmp_path / "audit.jsonl"
    events = [
        {"trigger": "llm_usage", "run_id": "run_A", "payload": {}},
        {"trigger": "llm_usage", "run_id": "run_B", "payload": {}},
        {"trigger": "llm_usage", "run_id": "run_A", "payload": {}},
    ]
    with path.open("w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    all_events = load_events(path)
    assert len(all_events) == 3

    filtered = load_events(path, run_id="run_A")
    assert len(filtered) == 2
    assert all(e["run_id"] == "run_A" for e in filtered)


def test_load_events_tolerates_corrupt_lines(tmp_path):
    """A truncated / corrupt JSONL line must not kill the whole tally.
    The audit log is written under a threading.Lock as of Sprint
    parallel-candidates so corruption shouldn't happen in normal runs,
    but defensive parsing keeps the tool useful on legacy logs."""
    path = tmp_path / "audit.jsonl"
    with path.open("w") as f:
        f.write(json.dumps({"trigger": "llm_usage", "payload": {}}) + "\n")
        f.write("not json at all\n")
        f.write("\n")  # blank
        f.write(json.dumps({"trigger": "llm_usage", "payload": {}}) + "\n")
    events = load_events(path)
    assert len(events) == 2


# ----------------------------------------------------------------- end-to-end


def test_end_to_end_total_matches_hand_computed_cost():
    """One Stage 3-shaped generation (8 candidates × 9 framings = 72
    Stage 3 calls, all hitting the cached 36,600-token corpus prefix
    after the first) plus 8 proposer calls and 8 Stage 1/2 calls.

    Computed by hand below; pinning the result so any regression in
    the math (e.g. accidentally re-introducing the naive shape) trips
    this test."""
    events = []
    # 8 proposer calls: 5K uncached input, 500 output
    for _ in range(8):
        events.append(_llm_usage_event(
            component="proposer", input_tokens=5_000, output_tokens=500,
            cache_read_input_tokens=0,
        ))
    # 8 stage1 calls: 4K total prompt, 3K cached, 200 output
    for _ in range(8):
        events.append(_llm_usage_event(
            component="stage1", input_tokens=4_000, output_tokens=200,
            cache_read_input_tokens=3_000,
        ))
    # 8 stage2 calls: 5K total prompt, 4K cached, 600 output
    for _ in range(8):
        events.append(_llm_usage_event(
            component="stage2", input_tokens=5_000, output_tokens=600,
            cache_read_input_tokens=4_000,
        ))
    # 72 stage3 framings: 38K total prompt, 36,600 cached, 400 output
    for _ in range(72):
        events.append(_llm_usage_event(
            component="stage3", input_tokens=38_000, output_tokens=400,
            cache_read_input_tokens=36_600,
        ))

    result = tally_events(events)

    # Hand-computed totals:
    # uncached input  = 8×5000 + 8×1000 + 8×1000 + 72×1400 = 40K+8K+8K+100,800 = 156,800
    # cached input    = 8×0    + 8×3000 + 8×4000 + 72×36,600 = 0+24K+32K+2,635,200 = 2,691,200
    # output          = 8×500 + 8×200 + 8×600 + 72×400 = 4K+1.6K+4.8K+28.8K = 39,200
    assert result.total.input_tokens == 156_800
    assert result.total.cached_input_tokens == 2_691_200
    assert result.total.output_tokens == 39_200

    rates_by_provider = {"fireworks": DEEPSEEK_V4_FLASH, "anthropic": {}}
    cost = result.cost_usd(rates_by_provider)
    # Hand-computed:
    #   156,800 × 0.14 / 1M = 0.021952
    #   2,691,200 × 0.0028 / 1M = 0.0075354
    #   39,200 × 0.28 / 1M = 0.010976
    # Total = 0.040463
    assert cost == pytest.approx(0.040463, abs=1e-5)


def test_naive_vs_corrected_on_realistic_chunk_replicates_3x_overestimate():
    """Synthetic chunk shaped to match run_4e5d8d6f Chunk 1's reported
    discrepancy ($6.24 naive vs $1.82 actual = 3.4×). Builds events
    with a realistic ~90% cache-hit ratio on Stage 3 and verifies
    that the naive formula produces ~3-4× the corrected total.

    This isn't a calibration against the actual chunk — we don't have
    the audit log here — but pins the directional behaviour of the
    fix on a chunk-sized workload."""
    events = []
    # ~25 generations × 8 candidates = 200 candidates.
    # Each candidate runs 1 proposer + 1 stage1 + 1 stage2 + ~9 stage3
    # framings (when reaching Stage 3). Assume 50% reach Stage 3.
    n_candidates = 200
    for i in range(n_candidates):
        # proposer: 5K input, 0 cache (varies per-island), 500 output
        events.append(_llm_usage_event(
            component="proposer", input_tokens=5_000,
            cache_read_input_tokens=2_500, output_tokens=500,
        ))
        events.append(_llm_usage_event(
            component="stage1", input_tokens=4_000,
            cache_read_input_tokens=3_500, output_tokens=200,
        ))
        if i % 2 == 0:  # 50% reach Stage 2
            events.append(_llm_usage_event(
                component="stage2", input_tokens=5_000,
                cache_read_input_tokens=4_500, output_tokens=600,
            ))
            # 9 Stage 3 framings under the cached corpus
            for _ in range(9):
                events.append(_llm_usage_event(
                    component="stage3", input_tokens=38_000,
                    cache_read_input_tokens=36_600, output_tokens=400,
                ))
    correct = tally_events(events)
    rates = {"fireworks": DEEPSEEK_V4_FLASH, "anthropic": {}}
    correct_cost = correct.cost_usd(rates)

    # Naive recomputation: pretend cached_input is uncached.
    naive_total = CostBreakdown(
        label="naive",
        input_tokens=correct.total.input_tokens + correct.total.cached_input_tokens,
        cached_input_tokens=0,
        output_tokens=correct.total.output_tokens,
    )
    naive_cost = naive_total.cost_usd(DEEPSEEK_V4_FLASH)

    ratio = naive_cost / correct_cost
    # Directional: the corrected total is dramatically lower than the
    # naive one. The exact ratio depends on the cache-hit ratio across
    # components; this synthetic chunk's Stage-3-heavy shape produces
    # ~10× (matching the observed real-run 3.4× as a LOWER bound — the
    # real run had less aggressive cache hit ratios than this fixture).
    # What's load-bearing is `ratio >> 1.0`: the fix actually removes
    # cost, not just shifts the books.
    assert ratio > 3.0, f"expected naive/correct > 3.0, got {ratio:.2f}"
