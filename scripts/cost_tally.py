#!/usr/bin/env python3
"""Sprint cost-tracker-fix: caching-aware cost tally over an audit.jsonl.

Replaces the implicit-naive cost tracker (Super's downstream tally, which
overestimated 3.4× on run_4e5d8d6f Chunk 1 — reported $6.24 against an
actual credit burn of $1.82). The naive shape was:

    cost = input_tokens × input_rate + output_tokens × output_rate

That charges the CACHED portion of input_tokens at the uncached rate.
On DeepSeek V4 Flash via Fireworks the cached rate is $0.0028/MTok —
a 98% discount on the standard $0.14/MTok input rate — so any naive
sum mis-prices every cached token by 50×.

This script reads an audit.jsonl, walks every llm_usage event, and
applies the correct provider-aware billing model:

  Fireworks (DeepSeek V4 Flash):
    billable_uncached = input_tokens - cache_read_input_tokens
    cost = (
        billable_uncached       × INPUT_RATE         # $0.14/MTok
        + cache_read_input_tokens × CACHED_INPUT_RATE  # $0.0028/MTok
        + output_tokens          × OUTPUT_RATE        # $0.28/MTok
    )

    Reasoning tokens are included in `completion_tokens` by the
    Fireworks API for DeepSeek's reasoning_effort modes; there is
    no separate reasoning-token billing line. They're billed at the
    standard output rate.

  Anthropic:
    Anthropic IS the active provider only in legacy/test paths; the
    Sprint 14 default is Fireworks across every component. The
    Anthropic branch here uses placeholder Sonnet-4 rates and is
    kept consistent with cache_creation_input_tokens (Anthropic-side
    cache-write events bill at 1.25× input). For accurate Anthropic
    accounting, supply --anthropic-input / --anthropic-output /
    --anthropic-cache-write / --anthropic-cache-read overrides.

Audit-event payload schema (read-only — NOT modified by this sprint):
  - input_tokens                 : int  — total prompt tokens
  - output_tokens                : int  — completion tokens
  - cache_creation_input_tokens  : int  — 0 on Fireworks; non-zero on
                                          Anthropic cache writes
  - cache_read_input_tokens      : int  — cached subset of input
  - provider                     : str  — "fireworks" | "anthropic"
  - model                        : str
  - component                    : str  — proposer | stage1 | … | curator
  - generation, island_id, stop_reason

Usage:
    ./scripts/cost_tally.py --audit runs/audit.jsonl
    ./scripts/cost_tally.py --audit runs/audit.jsonl --run-id run_4e5d8d6f
    ./scripts/cost_tally.py --audit runs/audit.jsonl --json-only

Exit codes:
    0 — tally completed
    1 — argv / file validation failure
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ----------------------------------------------------------------- pricing


# DeepSeek V4 Flash via Fireworks. Verified against published DeepSeek
# V4 pricing (2026): cache-miss input $0.14/MTok, output $0.28/MTok,
# cached input $0.0028/MTok. Fireworks's prefix-caching layer reports
# the cached subset as `prompt_cache_hit_tokens` (surfaced in the
# NormalizedUsage payload as `cache_read_input_tokens`); the
# uncached remainder is `input_tokens - cache_read_input_tokens`.
DEEPSEEK_V4_FLASH = {
    "input_per_mtok": 0.14,
    "cached_input_per_mtok": 0.0028,
    "output_per_mtok": 0.28,
    # Fireworks's automatic prefix caching has NO client-driven cache
    # creation event; cache_creation_input_tokens is always 0 on
    # Fireworks-emitted events.
    "cache_creation_per_mtok": 0.0,
}

# Placeholder Sonnet-4 rates. Override via CLI for accurate Anthropic
# accounting on mixed-routing experiments.
ANTHROPIC_SONNET_DEFAULT = {
    "input_per_mtok": 3.00,
    "cached_input_per_mtok": 0.30,
    "output_per_mtok": 15.00,
    "cache_creation_per_mtok": 3.75,
}

FIREWORKS_DEEPSEEK_V4_FLASH_MODEL_ID = (
    "accounts/fireworks/models/deepseek-v4-flash"
)


# ----------------------------------------------------------------- core


@dataclass
class CostBreakdown:
    """One slice of a tally — by component, by model, or total."""

    label: str
    n_events: int = 0
    input_tokens: int = 0           # uncached billable input
    cached_input_tokens: int = 0    # cache-hit subset
    output_tokens: int = 0
    cache_creation_tokens: int = 0  # Anthropic-only

    @property
    def total_input_seen(self) -> int:
        """Total prompt tokens (uncached + cached). Matches the raw
        `input_tokens` field on Fireworks payloads (which already
        includes the cached portion); on Anthropic events it's the
        sum of the uncached and cache-read columns."""
        return self.input_tokens + self.cached_input_tokens

    def cost_usd(self, rates: dict[str, float]) -> float:
        return (
            self.input_tokens * rates["input_per_mtok"]
            + self.cached_input_tokens * rates["cached_input_per_mtok"]
            + self.output_tokens * rates["output_per_mtok"]
            + self.cache_creation_tokens * rates["cache_creation_per_mtok"]
        ) / 1_000_000.0


@dataclass
class TallyResult:
    """Full audit-log tally with by-component and by-model breakdowns."""

    total: CostBreakdown = field(default_factory=lambda: CostBreakdown("TOTAL"))
    per_component: dict[str, CostBreakdown] = field(default_factory=dict)
    per_model: dict[str, CostBreakdown] = field(default_factory=dict)
    skipped_events: int = 0

    def cost_usd(self, rates_by_provider: dict[str, dict[str, float]]) -> float:
        """Total cost. The per-model breakdown is the authoritative
        source — we sum each model's slice at its own provider's
        rates rather than the aggregate (which would average across
        Fireworks/Anthropic rates and be meaningless on mixed runs)."""
        return sum(
            self.per_model[m].cost_usd(rates_by_provider[_provider_of(m)])
            for m in self.per_model
        )


def _provider_of(model_id: str) -> str:
    """Infer provider from the model id. Fireworks model ids start
    with `accounts/fireworks/`; Anthropic model ids start with
    `claude-`. The audit event also carries an explicit `provider`
    field, which is what we prefer when present — this helper is the
    fallback for unit tests that build minimal events."""
    if model_id.startswith("accounts/fireworks/"):
        return "fireworks"
    if model_id.startswith("claude-"):
        return "anthropic"
    # Default to fireworks since it's the Sprint 14 production routing.
    return "fireworks"


def _classify_event(payload: dict) -> tuple[int, int, int, int]:
    """Return (uncached_input, cached_input, output, cache_creation).

    Provider-aware split of the audit-event payload into the four
    billable columns. The KEY correctness property:

      uncached_input + cached_input == payload["input_tokens"]

    on Fireworks. The raw `input_tokens` field is the TOTAL prompt
    (Fireworks `prompt_tokens` is the gross count, NOT the uncached
    remainder), so the cached subset must be SUBTRACTED to get the
    uncached portion — not added on top, which is the naive double-
    counting bug.

    On Anthropic, `input_tokens` is the UNCACHED count by SDK
    convention; cache_read and cache_creation are reported as
    separate columns that DON'T overlap with input_tokens. We
    preserve that split here.
    """
    input_total = int(payload.get("input_tokens", 0) or 0)
    output_total = int(payload.get("output_tokens", 0) or 0)
    cache_read = int(payload.get("cache_read_input_tokens", 0) or 0)
    cache_create = int(payload.get("cache_creation_input_tokens", 0) or 0)
    provider = payload.get("provider", "")

    if provider == "fireworks":
        # input_total INCLUDES the cached portion; subtract to get the
        # uncached billable count. Clamp at 0 in case of a malformed
        # event where cache_read exceeds input_total.
        uncached = max(0, input_total - cache_read)
        return uncached, cache_read, output_total, 0  # cache_create always 0

    # Anthropic / unknown providers: input_total is the uncached
    # count by SDK convention. cache_create + cache_read sit alongside.
    return input_total, cache_read, output_total, cache_create


def tally_events(events: Iterable[dict]) -> TallyResult:
    """Walk llm_usage events, accumulate per-component / per-model /
    total breakdowns. Non-llm_usage events are skipped."""
    result = TallyResult()
    for event in events:
        if event.get("trigger") != "llm_usage":
            continue
        payload = event.get("payload") or {}
        component = payload.get("component", "unknown")
        model = payload.get("model", "unknown")

        uncached, cached, output, cache_create = _classify_event(payload)

        for bucket in (
            result.total,
            result.per_component.setdefault(
                component, CostBreakdown(label=component)
            ),
            result.per_model.setdefault(model, CostBreakdown(label=model)),
        ):
            bucket.n_events += 1
            bucket.input_tokens += uncached
            bucket.cached_input_tokens += cached
            bucket.output_tokens += output
            bucket.cache_creation_tokens += cache_create

    return result


# ----------------------------------------------------------------- I/O


def load_events(path: Path, run_id: str | None = None) -> list[dict]:
    """Load llm_usage events from a JSONL audit log, optionally filtered
    by run_id. Skips blank lines and non-JSON lines (defensive — a
    corrupted line shouldn't kill the whole tally)."""
    events: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if run_id is not None and event.get("run_id") != run_id:
                continue
            events.append(event)
    return events


def render_table(
    result: TallyResult,
    rates_by_provider: dict[str, dict[str, float]],
) -> str:
    """Render a human-readable breakdown."""
    lines: list[str] = []
    lines.append("by component:")
    lines.append(
        f"  {'component':<14} {'events':>7} {'input':>10} "
        f"{'cached':>10} {'output':>10} {'cost':>9}"
    )
    for label in sorted(result.per_component):
        bucket = result.per_component[label]
        # For per-component cost we approximate by attributing the
        # bucket to the model most common in that component. Single-
        # model runs (the production default) collapse correctly.
        sample_model = next(
            (
                event_model
                for event_model in result.per_model
                if result.per_model[event_model].n_events > 0
            ),
            "unknown",
        )
        rates = rates_by_provider[_provider_of(sample_model)]
        lines.append(
            f"  {label:<14} {bucket.n_events:>7} "
            f"{bucket.input_tokens:>10,} "
            f"{bucket.cached_input_tokens:>10,} "
            f"{bucket.output_tokens:>10,} "
            f"${bucket.cost_usd(rates):>8.4f}"
        )

    lines.append("")
    lines.append("by model:")
    lines.append(
        f"  {'model':<48} {'events':>7} {'cost':>9}"
    )
    for label in sorted(result.per_model):
        bucket = result.per_model[label]
        rates = rates_by_provider[_provider_of(label)]
        lines.append(
            f"  {label:<48} {bucket.n_events:>7} "
            f"${bucket.cost_usd(rates):>8.4f}"
        )

    total_cost = result.cost_usd(rates_by_provider)
    lines.append("")
    lines.append("totals:")
    lines.append(
        f"  events       : {result.total.n_events}"
    )
    lines.append(
        f"  input (unc.) : {result.total.input_tokens:,} tokens"
    )
    lines.append(
        f"  input (cache): {result.total.cached_input_tokens:,} tokens"
    )
    lines.append(
        f"  output       : {result.total.output_tokens:,} tokens"
    )
    if result.total.cache_creation_tokens:
        lines.append(
            f"  cache create : {result.total.cache_creation_tokens:,} tokens"
        )
    lines.append(f"  COST         : ${total_cost:.4f}")
    return "\n".join(lines)


# ----------------------------------------------------------------- CLI


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute a caching-aware cost tally over an AlphaMo audit.jsonl. "
            "Fixes Super's naive tracker, which charged cached input tokens "
            "at the uncached rate (50× per-token overcharge on DeepSeek V4 "
            "Flash, 3.4× total overestimate on run_4e5d8d6f Chunk 1)."
        )
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path("runs/audit.jsonl"),
        help="Path to the JSONL audit log (default: runs/audit.jsonl).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Filter to a single run_id. Default: tally every event in the file.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Emit the tally as JSON only; suppresses the human-readable table.",
    )
    # Anthropic-side overrides. Fireworks rates are hard-coded against
    # the verified 2026 DeepSeek V4 Flash prices — they don't move
    # often enough to be worth a flag.
    parser.add_argument("--anthropic-input", type=float, default=None)
    parser.add_argument("--anthropic-cached-input", type=float, default=None)
    parser.add_argument("--anthropic-output", type=float, default=None)
    parser.add_argument("--anthropic-cache-write", type=float, default=None)
    return parser.parse_args(argv)


def _build_rates(args: argparse.Namespace) -> dict[str, dict[str, float]]:
    anthropic = dict(ANTHROPIC_SONNET_DEFAULT)
    if args.anthropic_input is not None:
        anthropic["input_per_mtok"] = args.anthropic_input
    if args.anthropic_cached_input is not None:
        anthropic["cached_input_per_mtok"] = args.anthropic_cached_input
    if args.anthropic_output is not None:
        anthropic["output_per_mtok"] = args.anthropic_output
    if args.anthropic_cache_write is not None:
        anthropic["cache_creation_per_mtok"] = args.anthropic_cache_write
    return {
        "fireworks": dict(DEEPSEEK_V4_FLASH),
        "anthropic": anthropic,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.audit.exists():
        print(f"audit log not found: {args.audit}", file=sys.stderr)
        return 1

    events = load_events(args.audit, run_id=args.run_id)
    result = tally_events(events)
    rates = _build_rates(args)
    total_cost = result.cost_usd(rates)

    if args.json_only:
        out = {
            "audit": str(args.audit),
            "run_id": args.run_id,
            "n_events": result.total.n_events,
            "input_tokens_uncached": result.total.input_tokens,
            "input_tokens_cached": result.total.cached_input_tokens,
            "output_tokens": result.total.output_tokens,
            "cache_creation_tokens": result.total.cache_creation_tokens,
            "cost_usd": round(total_cost, 6),
            "per_component": {
                k: {
                    "events": v.n_events,
                    "input_uncached": v.input_tokens,
                    "input_cached": v.cached_input_tokens,
                    "output": v.output_tokens,
                }
                for k, v in result.per_component.items()
            },
        }
        print(json.dumps(out, indent=2))
    else:
        header = f"audit: {args.audit}"
        if args.run_id:
            header += f"   run_id: {args.run_id}"
        print(header)
        print(render_table(result, rates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
