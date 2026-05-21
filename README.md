# AlphaMo

LLM-driven evolutionary search system in the FunSearch / AlphaEvolve lineage,
augmented with research and red-team meta-agents. Targets the parent goal of
characterising structural configurations in which a single individual captures
$1B+ in value from a middle-class-accessible starting position.

See `alphamoarchitecture.html` (linked from the task) for the full design.

## Quickstart

```bash
# 1. Install
pip install -e '.[dev]'

# 2. Configure (one-time)
cp .env.example .env
$EDITOR .env                  # fill in FIREWORKS_API_KEY

# 3. Verify (fail fast if anything's off)
alphamo doctor

# 4. Launch
alphamo run --generations 30
```

The `alphamo` CLI auto-loads `.env` from the current directory (and any
parent) at startup. Existing process-env variables take precedence, so CI
and production deployments that set vars out-of-band are unaffected. Opt
out with `--no-dotenv` if you don't want any `.env` file consulted.

`alphamo doctor` is the canonical pre-flight check. Run it whenever a
launch fails for a surprising reason — it reports Python version,
dependency availability, `.env` source, env-var state (with masked key
previews), and DB / audit path writeability, with concrete fix suggestions
for each gap.

Equivalent Makefile shortcuts: `make install-dev`, `make doctor`, `make run`.

## Environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `FIREWORKS_API_KEY` | **Yes** under default Hyperparameters routing — every LLM-calling component goes to Fireworks/DeepSeek V4 Flash. | Provider auth. |
| `ANTHROPIC_API_KEY` | No, unless a Hyperparameters override routes a component to `provider_*="anthropic"`. | Provider auth. |
| `ALPHAMO_DB` | No — defaults to `./alphamo.db`. | SQLite path. |
| `ALPHAMO_AUDIT` | No — defaults to `./runs/audit.jsonl`. | JSONL audit log path. |
| `RUN_LIVE_TESTS` | No — only for opting into live-API marker tests during development. | Test gating. |

See `.env.example` for the full template with annotated defaults.

## Configuration

All run-time tuning lives in `alphamo.context.hyperparams.Hyperparameters`,
persisted on each Run row. Notable Sprint-15 defaults:

- **Islands**: 8, with FunSearch reset cadence every 40 generations.
- **Sampler**: cluster-level Boltzmann at `cluster_temperature_t0=0.1`,
  within-cluster Boltzmann at `sampling_temperature=0.1` (sharp
  exploitation; lower values = more deterministic argmax).
- **Provider routing**: every component → Fireworks DeepSeek V4 Flash.
  Override `Hyperparameters.provider_proposer / _stage1 / _stage2 /
  _stage3 / _curator` to flip individual components to "anthropic".
- **Reasoning effort**: `"high"` on proposer, Stage 3, curator
  (DeepSeek V4 modes: `none` / `high` / `max`). `"max"` is reserved
  for cases where concurrent-load mitigation has been added —
  default-on caused a 60% candidate-failure rate under
  concurrent-load pressure (Sprint 14 hotfix history).
- **Curator pause**: **disabled by default**
  (`curator_pause_enabled=False`). Production unattended runs execute
  through to the requested generation count. Set to `True` on the HP
  to opt in to milestone-triggered human-review pauses.

## CLI surface

```
alphamo doctor                       # pre-flight env check
alphamo init [--db PATH]             # create empty SQLite + schema
alphamo run [--generations N]        # start / extend a production run
alphamo harvest [--run ID --out PATH] # build handoff document
alphamo top --island I --k N         # per-island top-k inspection
alphamo islands --run ID             # per-island fitness + diversity
alphamo query [RUN_ID]               # list runs or dump one's JSON
alphamo show CANDIDATE_ID            # full JSON for one candidate
alphamo insert ...                   # manual candidate insertion (rare)
alphamo generate --island I --run ID # one-shot LLM-driven candidate
alphamo backfill-stage4 [--decay-k K] # rebuild stage4_findings from audit
```

All subcommands accept `--db` / `--audit` to override the defaults; both
also read `ALPHAMO_DB` / `ALPHAMO_AUDIT` from the environment.

## Tests

```bash
pytest -q              # full suite (~445 tests, ~20s)
```

Live-API tests (Anthropic side, marker `live`) are skipped unless
`ANTHROPIC_API_KEY` is set AND `RUN_LIVE_TESTS=1`. There is no
parallel live-API test path for Fireworks yet — smoke-test a real run
manually via `alphamo run --generations 5` after `alphamo doctor`
reports clean.

## Where things live

- `alphamo/orchestrator.py` — run loop coordinator.
- `alphamo/sampler.py` — FunSearch within-island clustered Boltzmann draw.
- `alphamo/islands.py` — m=8 islands, FunSearch reset.
- `alphamo/proposer.py` — proposer LLM call.
- `alphamo/evaluator/` — 3-stage cascade (Stage 1 feasibility, Stage 2
  structural, Stage 3 adversarial scrutiny with 9 framings).
- `alphamo/providers/` — Anthropic / Fireworks abstraction; `factory.py`
  resolves names from Hyperparameters to concrete providers.
- `alphamo/meta/curator.py` — milestone-triggered classify-and-pause
  meta layer (off by default).
- `alphamo/database/` — SQLAlchemy schema + ProgramsDB ops with
  idempotent ALTER-TABLE migrations.
- `corpus/` — 4-layer compositional substrate (Layer A architecture
  fingerprints, B current developments, C invariants, D anti-patterns).
- `runs/` — per-run audit JSONL files (gitignored).

See the module docstrings for design rationale.
