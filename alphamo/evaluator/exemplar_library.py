"""Trivial seed architecture used as the gen-0 baseline in every island.

Sprint 3 redesign (FunSearch/AlphaEvolve alignment): the four curated
existence-proof seeds (Satoshi, Rowling, Levels, Medvi) are gone. They
acted as quality anchors that biased the proposer toward seed-shaped
patterns and produced cross-island convergence even after the Sprint 2
removal of similarity-as-fitness.

FunSearch (Nature 2023): "Each island is initialized with a copy of the
user-provided initial program and is evolved separately." The seed is a
quality FLOOR to be exceeded, not a quality ANCHOR to mimic. FunSearch's
cap_set example uses `return 0.0` — type-correct but valueless.

Our analog: a deliberately weak Solo Service Provider that passes the
middle-class filter and Stage 1 coherence (so it's a real scored
candidate) but fails labor_separation and billion_dollar_potential by
design (so it's clearly inadequate and obviously needs to be
out-evolved). Expected aggregate fitness in the 0.25-0.40 range.

The seed is inserted into every island at generation 0 by the
orchestrator's `_bootstrap_islands()` step. From generation 1 onward
the within-island FunSearch sampler draws k=2 candidates from the
current island and the proposer mutates them — no global reference
library, no per-generation prompt anchoring to seed patterns.
"""

from __future__ import annotations

from alphamo.schemas import Architecture

TRIVIAL_SEED = Architecture(
    name="Generic Solo Service Provider",
    summary=(
        "A single person provides a service to customers in exchange for "
        "fees. The operator personally performs the service."
    ),
    value_chain="Operator -> Customer (direct).",
    capture_mechanism=(
        "Fee-for-service revenue collected from customers."
    ),
    entry_resources=(
        "Skill in the service domain, time, basic business registration "
        "($500-2000)."
    ),
    notes={
        "design_intent": (
            "Operator is the operations. No labor separation, no scaling "
            "mechanism, no IP, no leverage. Maximum value capture limited "
            "by operator's available hours. Coherent starting point "
            "intended to be exceeded by evolution, not a target to mimic."
        ),
    },
)

# Single-entry list, preserving the SEED_REFERENCES symbol used by
# downstream projection code (handoff, prompt builders). Length 1 — the
# trivial baseline. NOT the four curated seeds; those were retired in
# Sprint 3.
SEED_REFERENCES: list[Architecture] = [TRIVIAL_SEED]

# Backward-compatible alias retained for any importer that still uses
# EXEMPLARS. Same single-entry list.
EXEMPLARS: list[Architecture] = SEED_REFERENCES
