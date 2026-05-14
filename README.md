# AlphaMo

LLM-driven evolutionary search system in the FunSearch / AlphaEvolve lineage,
augmented with research and red-team meta-agents. Targets the parent goal of
characterising structural configurations in which a single individual captures
$1B+ in value from a middle-class-accessible starting position.

See `alphamoarchitecture.html` (linked from the task) for the full design.

## Status

**Phase 01 — skeleton + Programs DB + CLI + exemplar test.**
Subsequent phases (evaluator cascade, sampler/proposer, islands, meta layer)
are scaffolded as empty stubs and will be filled in next.

## Install

```bash
pip install -e '.[dev]'
```

## Use

```bash
alphamo init --db alphamo.db
alphamo insert --db alphamo.db --name Satoshi ...
alphamo query --db alphamo.db --island 0 --k 5
alphamo show 1 --db alphamo.db
```

## Test

```bash
pytest -q
```
