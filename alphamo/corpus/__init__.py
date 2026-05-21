"""AlphaMo corpus package — Sprint 12.

The corpus is a 4-layer structural substrate the proposer and Stage 3
evaluator reason within (not text the model is asked to re-read each
call). The loader produces two routing-targeted subsets that get
injected as stable cached prefixes on the proposer and Stage 3 system
prompts.

Public API:
  - load_proposer_subset() -> str
  - load_stage3_subset() -> str
  - CORPUS_VERSION
"""

from alphamo.corpus.loader import (
    CORPUS_VERSION,
    compile_layer_a_index,
    load_proposer_subset,
    load_stage3_subset,
)

__all__ = [
    "CORPUS_VERSION",
    "compile_layer_a_index",
    "load_proposer_subset",
    "load_stage3_subset",
]
