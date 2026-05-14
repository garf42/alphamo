# Research references

This directory contains the primary source papers that AlphaMo's 
architecture is based on. All design decisions should anchor on 
these sources rather than reasoning forward from prior 
conversation.

## Papers

- `funsearch-2023-romera-paredes.pdf` — Romera-Paredes et al., 
  "Mathematical discoveries from program search with large language 
  models," Nature 2023. The foundational architecture: islands 
  model, k=2 best-shot prompting, within-island signature 
  clustering with Boltzmann selection, periodic m/2 island reset.
  
- `alphaevolve-2025-novikov.pdf` — Novikov et al., "AlphaEvolve: 
  A coding agent for scientific and algorithmic discovery," 
  DeepMind technical report 2025. The successor: rich context 
  in prompts with per-metric scores, multi-metric optimization, 
  evaluation cascade, MAP-Elites + islands hybrid.

## How AlphaMo relates

| Component | Source basis | AlphaMo location |
|---|---|---|
| Islands + reset | FunSearch §1, §A.1 | alphamo/islands.py |
| k=2 best-shot prompting | FunSearch §1 | alphamo/sampler.py, alphamo/prompts/proposer_prompt.py |
| Within-island signature clustering | FunSearch §A.1, Fig E.3 | alphamo/sampler.py (Phase 2) |
| Boltzmann cluster selection | FunSearch Eq. 1 | alphamo/sampler.py (Phase 2) |
| Per-dimension scores in prompt | AlphaEvolve §2.2, Fig 3b | alphamo/prompts/proposer_prompt.py (Phase 2) |
| Multi-metric framing | AlphaEvolve §2.4 | alphamo/evaluator/cascade.py + Phase 2 prompts |
| Evaluation cascade | AlphaEvolve §2.4 | alphamo/evaluator/cascade.py |
| Append-only database with islands | FunSearch §A.1 + Phase 1 run_id | alphamo/database/ |

## Departures from source

These are AlphaMo extensions not present in either source paper. 
Each carries some novel-territory risk; design decisions involving 
these should be made carefully:

- LLM-based evaluator (rather than deterministic). Both source 
  papers use a stateless deterministic evaluator (e.g., 
  count cap-set size). AlphaMo's evaluator is itself an LLM 
  cascade. This introduces score variance and Goodhart pressure 
  that the source architecture doesn't have to defend against.
  
- Meta layer (research + red-team + curator). Neither paper has 
  components that update the verifier or parent goal during a 
  run. AlphaMo adds these because the parent-goal domain is 
  verifier-poor.
  
- Run-scoped state. Both source papers operate against a 
  persistent program database without explicit run boundaries. 
  AlphaMo's Phase 1 adds run_id to support reproducibility and 
  resume.
