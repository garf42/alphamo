
# AlphaMo Corpus

Structural substrate for the AlphaMo proposer. Built on the
AlphaFold-lineage design principle: the substrate encodes
templates + invariants the model reasons within, not a primitive
vocabulary the model composes from.

## Layers

- **Layer A** (`layer-a/*.md`) — Catalog of value-capture
  architectures, deeply decomposed into raw structural features.
  Each file is one entry produced by the
  `architecture-decomposition` skill (RAD). Includes both
  successes and failures.
- **Layer B** (`layer-b.md`, not yet built) — Current 2026
  force-topology map. Refreshes quarterly.
- **Layer C** (`layer-c.md`) — Substrate invariants: time-invariant
  structural constraints any value-capture architecture must
  satisfy. The AlphaFold-architectural-priors analog.
- **Layer D** (`layer-d.md`, not yet built) — Anti-patterns
  consolidated from Layer A negative-pair clusters. Built after
  Layer A is substantially complete.

## Build process

Layer A entries are produced by running the RAD skill
(`skills/architecture-decomposition/SKILL.md`) on architectures
from the curated list (`architecture-list.md`). Each entry
contains a canonical YAML record (the corpus content the
proposer consumes) plus a prose synthesis (QA ergonomics, not
part of the corpus).

Construction happens in Claude chat sessions and is committed to
this branch incrementally. AlphaMo's runtime consumes the
canonical YAML content from each layer file as cache-friendly
stable prefix.

## Schema discipline

- Bracket-prefix confidence tags `[E]`/`[I]`/`[C]`/`[U]` on every
  field value
- No primitive-vocabulary labels (moats, 7 Powers, VRIN, etc.)
- No pattern-name labels ("rented-infrastructure pattern", etc.)
- Forces split into `forces-emergence` (F-prefix) and
  `forces-accumulated` (G-prefix); critical for architectures
  older than ~10 years
- Negative pairs required, including the "reveals" field

See the skill file for full protocol.

## Current state

- Layer A: 2 entries (medvi, bloomberg-terminal) plus this
  session's batch
- Layer C: complete (6 substrate invariants)
- Layer A list curated at ~63 candidates
- Layer B, Layer D: pending

## Target

Final corpus ~60-100K tokens fitting AlphaMo proposer's cache
budget with room for per-generation working context. Sprint 12
of AlphaMo integrates the corpus into proposer and Stage 3
evaluator system prompts.
