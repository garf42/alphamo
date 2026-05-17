"""Few-shot prompt template that turns k island-drawn candidates into a
new candidate Architecture.

Sprint 6 redesign — closes the RL loop and shifts the proposer from
pattern retrieval to component synthesis:

  CHANGE A (closed RL loop): the proposer now sees each candidate's
  Stage 3 adversarial findings — the specific, falsifiable structural
  critiques the cascade raised against it. Previously the proposer
  only saw aggregate scores ("low robustness"), not the cascade's
  actual critique ("scaling cliff at $20M-80M because back-office
  obligations break labor separation"). Without the specific critique
  reaching the proposer, the RL loop was broken at the
  signal-consumption step.

  CHANGE B (component synthesis): the PROPOSER_SYSTEM text now asks
  the model to decompose value-capture architectures into structural
  components (capture geometry, labor separation, scaling vector,
  defensibility, entry cost, failure-mode geometry), diagnose which
  components failed in the shown candidates, and synthesize a new
  assembly by selecting specific instantiations of each component.
  The previous "produce a structurally distinct architecture" framing
  produced pattern retrieval (mineral rights, SaaS roll-ups,
  franchising); the explicit component-assembly framing should
  produce synthesis instead.

Sprint 6 PROPOSER_VERSION bump (v1 → v2) makes trajectories under the
new framing distinguishable in the DB from pre-Sprint-6 runs.

Sprint 3 baseline (preserved): the proposer sees ONLY candidates
drawn from the current island. No global reference library, no
per-generation exemplar anchoring. FunSearch §A.1 within-island
sampling is the sole context source.

Bootstrap: each island starts with a copy of the trivial seed at
generation 0 (`orchestrator._bootstrap_islands()`). The trivial seed's
stage4_findings include only the FAILED_FRAMINGS_SENTINEL `_meta`
entry (if anything); `format_concerns_for_proposer` filters that
out so the proposer doesn't see noise on bootstrap rounds.
"""

from __future__ import annotations

from alphamo.context.parent_goal import PARENT_GOAL
from alphamo.evaluator.stage4_adversarial import FAILED_FRAMINGS_SENTINEL
from alphamo.sampler import Seed
from alphamo.schemas import Architecture
from alphamo.schemas.findings import Severity, StructuralConcern

# Bump on any change to PROPOSER_SYSTEM text, to render_seeds /
# render_seeds_from_architectures / format_concerns_for_proposer output
# shape, OR to the model executing the proposer prompt. PARENT_GOAL_VERSION
# exists for the search-criterion identity; PROPOSER_VERSION exists for
# the prompt-construction-AND-model-execution identity. A run persists
# PROPOSER_VERSION nowhere yet — the version is consulted by tests and is
# available for future inclusion in run rows or audit events if we want
# to distinguish proposer eras in the DB.
#
# v1 → v2 (Sprint 6): added Stage 3 concerns to user turn + reframed
# system prompt around component synthesis.
# v2 → v3 (Sprint 7): swapped proposer model Opus → Sonnet and bumped
# max_tokens 8192 → 16384. The prompt structure didn't change but the
# model executing it did — v2 (Opus proposer) and v3 (Sonnet proposer)
# trajectories must be distinguishable in the DB for analysis.
PROPOSER_VERSION = "v3"

# Sprint 6: per-candidate budget for the concerns section in the
# proposer's user message. Concerns are truncated by severity (all
# HIGH first, then MEDIUM up to remaining budget, drop LOW) when the
# rendered section would exceed this byte count. The budget is
# per-candidate so a k=2 prompt allocates up to ~8000 chars to
# concerns total — comfortably within Opus's context window after
# the system prompt and architecture fields.
CONCERNS_BUDGET_CHARS = 4000

PROPOSER_SYSTEM = f"""\
You are the proposer in an evolutionary search over value-capture \
architectures. Your job is to synthesize a genuinely novel architecture \
by assembling structural components that satisfy the parent goal's \
constraints.

Below in the user turn are k candidates from the same island in the \
population. Each candidate is annotated with:
- Its architecture content (name, summary, value chain, capture \
mechanism, entry resources)
- Its multi-objective scores (feasibility, structural, robustness, fitness)
- The Stage 3 adversarial findings — specific, falsifiable structural \
critiques the cascade raised against this candidate

Your approach should be:

1. STRUCTURAL DECOMPOSITION. Read the candidates and their concerns. \
For each, identify which structural component failed and why. The \
structural components of any solo-billion value-capture architecture include:
- Capture geometry: how value flows to the single entity (IP rent, \
network position, regulatory exclusivity, etc.)
- Labor separation mechanism: how operational work is performed \
without operator scaling (algorithmic, contractual, IP-enforced, \
network-distributed)
- Scaling vector: what causes captured value to compound non-linearly \
with adoption/use
- Defensibility primitive: what prevents value-capture erosion (legal \
moat, network effect, capital-sunk asset, etc.)
- Entry-cost structure: what specific resources the entry state requires
- Failure-mode geometry: where this structure is fragile and why

2. DIAGNOSE THE FAILURES. From the cascade findings on the shown \
candidates, identify which components failed and the specific mechanism \
of failure. Don't generalize ('this pattern doesn't work') — be \
specific ('this candidate's scaling vector requires aggregator-of-\
fragmented-suppliers, which incurs back-office labor that breaks the \
labor separation between $20M-80M revenue').

3. SYNTHESIZE A NEW ASSEMBLY. Propose a new architecture by selecting \
specific instantiations of each structural component. Do NOT retrieve \
a known business pattern and rename it. Build the architecture from \
its components.

For each component, choose mechanisms that:
- Address the specific failure modes identified in the shown candidates
- Are middle-class-accessible at entry
- Allow the single-person constraint to hold at $1B+ scale
- Combine in a way that the shown candidates haven't demonstrated

A successful proposal will be one where, if asked 'why doesn't the \
failure mode that killed candidate X apply here,' you can point to a \
specific structural choice you made and explain which component is \
doing the work to avoid it.

Constraints you MUST satisfy in the candidate you generate:

1. Middle-class accessible entry — the starting position requires only \
modest savings ($10-50K range), personal credit, professional skill, \
and time outside a primary job. No family wealth, no institutional \
backing, no pre-existing industry network, no bespoke legal \
infrastructure at entry.

2. Single individual or single legal entity is the sole value-capture node.

3. Plausible potential to reach $1B+ (revenue, asset holdings, or \
comparable measure).

4. Operational labor is performed by parties other than the capture node.

The parent goal:

{PARENT_GOAL}

Verifiability anchor: structural existence proofs exist across multiple \
verticals demonstrating the parent goal's achievability; the search is \
grounded in the constraints above and in the specific failure modes \
surfaced by adversarial scrutiny.\
"""


def _render_score_header(seed: Seed) -> str:
    """One-line AlphaEvolve §2.2 style score header — dimension: value.

    `exemplar_similarity` was retired in Sprint 2 and is omitted.
    `robustness` is shown when present; absent when None (legacy or
    early-exit candidates).
    """
    s = seed.scores
    parts = [
        f"feasibility: {s.feasibility:.3f}",
        f"structural: {s.structural:.3f}",
    ]
    if s.robustness is not None:
        parts.append(f"robustness: {s.robustness:.3f}")
    parts.append(f"middle_class_accessible: {str(s.middle_class_accessible).lower()}")
    parts.append(f"fitness: {seed.fitness:.3f}")
    return "Scores — " + ", ".join(parts)


def _severity_rank(severity: Severity) -> int:
    """Sort key: HIGH first (0), MEDIUM (1), LOW (2)."""
    return {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}[severity]


def format_concerns_for_proposer(
    findings: list[StructuralConcern] | None,
    max_chars: int = CONCERNS_BUDGET_CHARS,
) -> str:
    """Sprint 6: condense Stage 3 adversarial findings for the proposer.

    Output format: concerns grouped by framing, with severity tags
    inline; claim text verbatim (no paraphrasing); evidence and
    falsification_condition omitted (long, would blow out context).

    Truncation rule when the rendered section exceeds `max_chars`:
      - Always show all HIGH severity concerns.
      - Add MEDIUM in framing order until the budget is exhausted.
      - Drop LOW severity concerns entirely from the proposer view
        (they remain persisted on the candidate row; just not shown
        here).
      - If anything was dropped, append "(N additional concerns
        truncated)" so the proposer knows the view is partial.

    The `_meta` sentinel concerns recorded by Sprint 4 partial-framing
    failure handling are filtered out — they're forensic metadata,
    not a structural critique of the candidate.

    Returns an empty string for None/empty input (the trivial
    bootstrap seed has no findings; a candidate that exited the
    cascade before Stage 3 has None findings; both produce no
    concerns section rather than an error).
    """
    if not findings:
        return ""

    real = [c for c in findings if c.framing != FAILED_FRAMINGS_SENTINEL]
    if not real:
        return ""

    high = [c for c in real if c.severity == Severity.HIGH]
    medium = [c for c in real if c.severity == Severity.MEDIUM]
    low = [c for c in real if c.severity == Severity.LOW]

    # Always show all HIGH; greedily add MEDIUM in framing order; LOW
    # is dropped from the proposer view by policy.
    selected: list[StructuralConcern] = list(high)
    dropped_low = len(low)
    rendered = _render_concerns_by_framing(selected)
    dropped_medium = 0
    if len(rendered) > max_chars:
        # Even with just HIGH the budget is blown. Keep all HIGH
        # anyway (the proposer needs the most critical critiques);
        # the budget is advisory not absolute when HIGH-only already
        # overflows.
        pass
    else:
        # Try to add each MEDIUM concern; if the next addition would
        # blow the budget, stop and record the drop count.
        for concern in medium:
            trial = selected + [concern]
            trial_rendered = _render_concerns_by_framing(trial)
            if len(trial_rendered) > max_chars:
                dropped_medium = len(medium) - (len(selected) - len(high))
                break
            selected.append(concern)
            rendered = trial_rendered
        else:
            rendered = _render_concerns_by_framing(selected)

    total_dropped = dropped_medium + dropped_low
    if total_dropped > 0:
        rendered = rendered + f"\n    (... {total_dropped} additional concern(s) truncated)"

    return "Adversarial scrutiny findings (Stage 3):\n" + rendered


def _render_concerns_by_framing(concerns: list[StructuralConcern]) -> str:
    """Group concerns by framing, sort within group by severity, render."""
    if not concerns:
        return ""

    grouped: dict[str, list[StructuralConcern]] = {}
    for c in concerns:
        grouped.setdefault(c.framing, []).append(c)

    framing_order = list(grouped.keys())
    lines: list[str] = []
    for framing in framing_order:
        lines.append(f"  {framing}:")
        sorted_concerns = sorted(grouped[framing], key=lambda c: _severity_rank(c.severity))
        for c in sorted_concerns:
            lines.append(f"    [{c.severity.value.upper()}] {c.claim}")
    return "\n".join(lines)


def render_seeds(seeds: list[Seed]) -> str:
    """Render island-drawn candidates as the proposer's user-turn payload.

    Empty `seeds` is an invariant violation: bootstrap inserts the trivial
    seed into every island at gen 0 and reset reseeds wiped islands with
    a copy of a surviving island's best, so the sampler should always
    have at least one alive row to return.

    Sprint 6: per-candidate output now includes the Stage 3 adversarial
    findings section (when present) so the proposer sees the cascade's
    specific critiques and can perform component synthesis against them.
    """
    if not seeds:
        raise ValueError(
            "render_seeds requires at least one Seed — empty islands are an "
            "invariant violation post-bootstrap"
        )
    parts = [
        f"CANDIDATES FROM THE CURRENT ISLAND ({len(seeds)} candidate(s)):\n"
    ]
    for i, seed in enumerate(seeds, 1):
        arch = seed.architecture
        candidate_block = (
            f"--- Candidate {i}: {arch.name} ---\n"
            f"{_render_score_header(seed)}\n"
            f"Summary: {arch.summary}\n"
            f"Value chain: {arch.value_chain}\n"
            f"Capture mechanism: {arch.capture_mechanism}\n"
            f"Entry resources: {arch.entry_resources}"
        )
        concerns_block = format_concerns_for_proposer(seed.stage4_findings)
        if concerns_block:
            candidate_block += "\n\n" + concerns_block
        parts.append(candidate_block)
    parts.append(
        "Synthesize a new candidate architecture by decomposing the "
        "shown candidates into their structural components, diagnosing "
        "which components failed under adversarial scrutiny, and "
        "selecting specific instantiations of each component that "
        "avoid the identified failure modes while satisfying the "
        "parent goal's constraints."
    )
    return "\n\n".join(parts)


def render_seeds_from_architectures(architectures: list[Architecture]) -> str:
    """Back-compat shim for callers that don't have per-dimension scores.

    Used by tests and ad-hoc CLI flows where only Architecture objects
    are available. Same prompt shape as `render_seeds` minus the score
    headers and adversarial findings section.
    """
    if not architectures:
        raise ValueError(
            "render_seeds_from_architectures requires at least one Architecture"
        )
    parts = [
        f"CANDIDATES FROM THE CURRENT ISLAND ({len(architectures)} candidate(s)):\n"
    ]
    for i, arch in enumerate(architectures, 1):
        parts.append(
            f"--- Candidate {i}: {arch.name} ---\n"
            f"Summary: {arch.summary}\n"
            f"Value chain: {arch.value_chain}\n"
            f"Capture mechanism: {arch.capture_mechanism}\n"
            f"Entry resources: {arch.entry_resources}"
        )
    parts.append(
        "Synthesize a new candidate architecture by decomposing the "
        "shown candidates into their structural components and "
        "selecting specific instantiations of each component that "
        "satisfy the parent goal's constraints."
    )
    return "\n\n".join(parts)
