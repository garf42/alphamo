#!/usr/bin/env python3
"""Evaluator-cascade variance test (Sprint 17.1 diagnostic).

Re-runs the full evaluator cascade N times on M candidates drawn from the
same DB, then reports per-stage and aggregate-fitness distributions. This
is the variance test specified in §4.1 of the evaluator diagnostic audit
— it answers "is the evaluator noisy?" by measuring within-candidate
score stdev across independent trials on byte-identical input.

Usage:
    # Three candidates (Proptax + mid-fitness + recent-low), 5 trials each.
    export FIREWORKS_API_KEY=fw_...
    ./scripts/variance_test.py --candidate-ids 77 123 456

    # Custom DB path, fewer trials:
    ./scripts/variance_test.py --db-path /path/to/run.db --trials 3 --candidate-ids 77

    # JSON-only output for piping into jq / a notebook:
    ./scripts/variance_test.py --candidate-ids 77 123 --json-only

Side effects:
    None. The cascade is invoked WITHOUT a TelemetryContext so no
    `llm_usage` audit events fire and the production audit.jsonl is
    untouched. The DB is opened read-only-conceptually (we call
    `db.get(candidate_id)` and read `architecture_spec`; no inserts).
    Fireworks API costs apply at ~$0.05/trial × candidates × trials —
    see §4.2 of the audit for the breakdown.

Exit codes:
    0  — every candidate × trial completed
    1  — argv / env validation failure (missing key, bad path, no candidates)
    2  — at least one cascade invocation raised an LLMOutputError; partial
         results still printed for the successful runs.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any

# Autoload .env from CWD or any ancestor — mirrors the alphamo CLI
# (Sprint 16). Process-env values keep precedence; existing
# FIREWORKS_API_KEY exported in the shell wins over a .env value.
try:
    from dotenv import find_dotenv, load_dotenv
    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(_dotenv_path, override=False)
except ImportError:
    # python-dotenv is in pyproject's runtime deps. If it's missing the
    # install is incomplete; surface clearly rather than silently failing.
    print(
        "warning: python-dotenv unavailable — .env autoload skipped. "
        "Run `pip install -e '.[dev]'` to fix.",
        file=sys.stderr,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="variance_test",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/tmp/ops-run-25gen.db"),
        help="Path to the SQLite DB containing the candidates to re-evaluate. "
             "Default: /tmp/ops-run-25gen.db",
    )
    parser.add_argument(
        "--candidate-ids",
        nargs="+",
        type=int,
        required=True,
        help="Candidate row IDs to re-evaluate. Recommended: the dominant "
             "candidate, one mid-fitness candidate, one recent low-fitness "
             "candidate. Example: --candidate-ids 77 123 456",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of independent cascade invocations per candidate. "
             "Default: 5",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="fireworks",
        choices=["fireworks", "anthropic"],
        help="Provider routing override. Default: fireworks (matches the "
             "Sprint-15 default HP). Use 'anthropic' to re-evaluate via "
             "Claude — requires ANTHROPIC_API_KEY.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Emit only the raw JSON result on stdout. Suppresses the "
             "formatted table — useful for piping into jq or a notebook.",
    )
    return parser.parse_args()


def _format_optional_float(v: Any, fmt: str = "{:.4f}") -> str:
    return fmt.format(v) if isinstance(v, (int, float)) else "—"


def _per_trial_record(result: Any, fitness: float) -> dict[str, Any]:
    """Flatten a CascadeResult into a JSON-serialisable dict."""
    scores = result.scores
    return {
        "feasibility": scores.feasibility,
        "structural": scores.structural,
        "robustness": scores.robustness,
        "middle_class_accessible": scores.middle_class_accessible,
        "early_exit": result.early_exit,
        "fitness": fitness,
        "stage1_reasoning": (
            result.stage1.reasoning if result.stage1 is not None else None
        ),
        "stage2_reasoning": (
            result.stage2.reasoning if result.stage2 is not None else None
        ),
        "stage3_reasoning": (
            result.stage3.reasoning if result.stage3 is not None else None
        ),
        "stage3_n_concerns": (
            len(result.stage3.concerns) if result.stage3 is not None else None
        ),
    }


def _summarise(per_trial: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean / stdev / min / max for the numeric fields where defined."""
    summary: dict[str, Any] = {"n_trials": len(per_trial)}
    for field in ("feasibility", "structural", "robustness", "fitness"):
        values = [t[field] for t in per_trial if isinstance(t[field], (int, float))]
        if values:
            summary[field] = {
                "mean": statistics.mean(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "n_present": len(values),
            }
        else:
            summary[field] = None
    summary["n_full_cascade"] = sum(
        1 for t in per_trial if t["robustness"] is not None
    )
    summary["n_early_exit"] = sum(
        1 for t in per_trial if t["early_exit"] is not None
    )
    return summary


def _print_table(report: dict[str, Any]) -> None:
    """Human-readable per-candidate table + global ordering check."""
    print(f"\n{'='*88}")
    print(f"Evaluator-cascade variance test  —  provider={report['provider']}, "
          f"trials per candidate={report['trials']}")
    print(f"DB: {report['db_path']}")
    print(f"{'='*88}\n")

    # Per-candidate detail.
    for cand in report["candidates"]:
        cid = cand["candidate_id"]
        if cand.get("error"):
            print(f"id={cid}  ERROR: {cand['error']}")
            print("-" * 88)
            continue

        arch = cand["architecture"]
        print(f"id={cid}  name='{arch['name']}'  "
              f"DB-stored fitness={cand['db_fitness']:.4f}  "
              f"generation={cand['db_generation']}")
        print(f"  summary: {arch['summary'][:120]}{'…' if len(arch['summary']) > 120 else ''}")
        print()
        print(f"  {'trial':>5}  {'feas':>7}  {'struct':>7}  {'rob':>7}  "
              f"{'fitness':>8}  {'mca':>4}  {'exit':>22}  {'n_conc':>6}")
        for i, t in enumerate(cand["trials"], 1):
            print(f"  {i:>5}  "
                  f"{_format_optional_float(t['feasibility'], '{:.4f}'):>7}  "
                  f"{_format_optional_float(t['structural'], '{:.4f}'):>7}  "
                  f"{_format_optional_float(t['robustness'], '{:.4f}'):>7}  "
                  f"{_format_optional_float(t['fitness'], '{:.4f}'):>8}  "
                  f"{'Y' if t['middle_class_accessible'] else 'N':>4}  "
                  f"{(t['early_exit'] or '-'):>22}  "
                  f"{(t['stage3_n_concerns'] if t['stage3_n_concerns'] is not None else '-'):>6}")
        summary = cand["summary"]
        print(f"  {'-'*5}")
        for field in ("feasibility", "structural", "robustness", "fitness"):
            s = summary[field]
            if s is None:
                print(f"  {field:>11}: (no trials produced a value)")
            else:
                print(f"  {field:>11}: mean={s['mean']:.4f}  "
                      f"stdev={s['stdev']:.4f}  "
                      f"range=[{s['min']:.4f}, {s['max']:.4f}]  "
                      f"n={s['n_present']}/{summary['n_trials']}")
        print(f"  {'full cascade':>11}: "
              f"{summary['n_full_cascade']}/{summary['n_trials']} trials reached Stage 3")
        if summary["n_early_exit"] > 0:
            print(f"  {'early_exit':>11}: {summary['n_early_exit']}/{summary['n_trials']} trials short-circuited")
        print("-" * 88)

    # Ranking-preservation table — flips signal that the evaluator can't
    # reliably distinguish the candidates being measured.
    scored = [c for c in report["candidates"] if not c.get("error")]
    if len(scored) >= 2 and report["trials"] >= 2:
        print("\nRanking by per-trial fitness (lower-indexed = higher fitness):\n")
        header = "  trial  " + "  ".join(f"id={c['candidate_id']:>5}" for c in scored)
        print(header)
        for t_idx in range(report["trials"]):
            fits = []
            for c in scored:
                if t_idx < len(c["trials"]):
                    fits.append((c["candidate_id"], c["trials"][t_idx]["fitness"]))
                else:
                    fits.append((c["candidate_id"], float("-inf")))
            ranking = sorted(fits, key=lambda kv: kv[1], reverse=True)
            rank_of = {cid: r for r, (cid, _) in enumerate(ranking, 1)}
            row = f"  {t_idx + 1:>5}  " + "  ".join(
                f"rank={rank_of[c['candidate_id']]}  ({c['trials'][t_idx]['fitness']:.3f})"
                for c in scored
            )
            print(row)
        # Did ranks vary?
        ranking_signatures = set()
        for t_idx in range(report["trials"]):
            fits = sorted(
                ((c["candidate_id"], c["trials"][t_idx]["fitness"]) for c in scored),
                key=lambda kv: kv[1], reverse=True,
            )
            ranking_signatures.add(tuple(cid for cid, _ in fits))
        print()
        if len(ranking_signatures) == 1:
            print(f"  → Ranking PRESERVED across all {report['trials']} trials.")
        else:
            print(f"  → Ranking VARIED — {len(ranking_signatures)} distinct orderings "
                  f"observed across {report['trials']} trials. Evaluator cannot "
                  f"reliably distinguish these candidates.")

    print(f"\n{'='*88}\n")


def main() -> int:
    args = _parse_args()

    # Lazy alphamo imports so --help doesn't import the world.
    from alphamo.context.hyperparams import Hyperparameters
    from alphamo.database import ProgramsDB, aggregate_fitness
    from alphamo.errors import LLMOutputError
    from alphamo.evaluator import EvaluatorCascade
    from alphamo.providers.factory import build_provider
    from alphamo.schemas import Architecture

    if not args.db_path.exists():
        print(f"error: DB not found at {args.db_path}. "
              f"Pass --db-path <path> to point at your run's SQLite file.",
              file=sys.stderr)
        return 1

    # Env-var pre-flight. Match the alphamo factory's error message style.
    if args.provider == "fireworks" and not os.environ.get("FIREWORKS_API_KEY"):
        print("error: FIREWORKS_API_KEY is not set. Two fix paths:\n"
              "  1. (canonical) copy .env.example to .env, fill in the key, re-run.\n"
              "  2. (shell) export FIREWORKS_API_KEY=<your-key> before running.\n"
              "Or pass --provider anthropic to use the Anthropic SDK (needs ANTHROPIC_API_KEY).",
              file=sys.stderr)
        return 1
    if args.provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: ANTHROPIC_API_KEY is not set; required for --provider anthropic.",
              file=sys.stderr)
        return 1

    db = ProgramsDB(f"sqlite:///{args.db_path}")
    hp = Hyperparameters()

    # One provider instance is reused across all three stages — matches
    # the production single-provider routing (default Sprint-15 HP).
    provider = build_provider(args.provider)
    cascade = EvaluatorCascade(
        stage1_provider=provider,
        stage2_provider=provider,
        stage3_provider=provider,
        stage1_model=hp.model_stage1,
        stage2_model=hp.model_stage2,
        stage3_model=hp.model_stage3,
        stage3_reasoning_effort=hp.reasoning_effort_stage3,
        stage1_threshold=hp.stage1_threshold,
        stage2_threshold=hp.stage2_threshold,
        stage4_decay_k=hp.stage4_decay_k,
    )

    report: dict[str, Any] = {
        "provider": args.provider,
        "trials": args.trials,
        "db_path": str(args.db_path),
        "candidates": [],
    }
    had_errors = False

    for cid in args.candidate_ids:
        try:
            row = db.get(cid)
        except KeyError as exc:
            report["candidates"].append({"candidate_id": cid, "error": str(exc)})
            had_errors = True
            continue

        arch = Architecture(**row.architecture_spec)
        per_trial: list[dict[str, Any]] = []
        for t in range(args.trials):
            if not args.json_only:
                print(f"  id={cid} trial {t + 1}/{args.trials}…",
                      end=" ", flush=True, file=sys.stderr)
            try:
                result = cascade.evaluate(arch)
                fitness = aggregate_fitness(result.scores)
                per_trial.append(_per_trial_record(result, fitness))
                if not args.json_only:
                    print(f"fitness={fitness:.4f} "
                          f"(exit={result.early_exit or 'none'})",
                          file=sys.stderr)
            except LLMOutputError as exc:
                per_trial.append({
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    "feasibility": None, "structural": None,
                    "robustness": None, "middle_class_accessible": None,
                    "early_exit": "llm_output_error", "fitness": None,
                    "stage1_reasoning": None, "stage2_reasoning": None,
                    "stage3_reasoning": None, "stage3_n_concerns": None,
                })
                had_errors = True
                if not args.json_only:
                    print(f"ERROR — {type(exc).__name__}", file=sys.stderr)

        report["candidates"].append({
            "candidate_id": cid,
            "db_fitness": row.fitness,
            "db_generation": row.generation,
            "db_island_id": row.island_id,
            "architecture": row.architecture_spec,
            "trials": per_trial,
            "summary": _summarise([t for t in per_trial if "error" not in t]),
        })

    if not args.json_only:
        _print_table(report)

    print(json.dumps(report, indent=2, default=str))
    return 2 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
