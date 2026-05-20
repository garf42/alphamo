# Layer A Build Status

**Started:** 2026-05-19
**Mode:** Direct in-session orchestration (Super dispatch flow modified per chat discussion)
**Total entries planned:** ~63 (per architecture-list.md)
**Completed:** 3 (kodak-film, tsmc, coca-cola) + 4 seed (medvi, bloomberg-terminal, visa-interchange, standard-oil from chat session)
**Failed validation:** 0
**Declined Phase 1:** 0
**Low evidence:** 0
**Schema gaps:** 1 (defunct-as-subject status-vocabulary; see kodak-film notes — chat reviewed, tracked for D+E retests, no v1.4 amendment)
**Cross-architecture patterns surfaced:** 4 (founding-doctrine-as-asset, time-to-accumulation distribution, load-bearing-for-civilization-stack, identity-as-non-zero-sum-position-occupation)
**Section A complete:** 3 new + 2 seed = 5 entries (visa-interchange + standard-oil were seeded; kodak-film + tsmc + coca-cola built in direct-orchestration mode)
**Pending:** ~56 (Sections B-F awaiting Section A authorization)

## Log

- [2026-05-19] kodak-film: success — audit 47E/11I/5C/0U/63 — schema-stress observed (defunct-as-subject), not blocking; details in entry notes and Schema gaps section below
  - First Section A sequential entry built in direct-orchestration mode (skipped seq entries already-seed-built: visa-interchange, standard-oil from chat session)
  - Chat review: validation pass, schema stress tracked across Section D+E retests, no v1.4 amendment needed yet
- [2026-05-19] tsmc: success — audit 56E/9I/7C/0U/72 — no schema stress observed; schema handles capability-asymmetry-dominant architecture cleanly
  - Negative pairs: globalfoundries-2018-exit (capex+execution cliff), intel-IDM-leadership-loss (pure-play discipline as architectural invariant)
  - Notable structural pattern: F5 (pure-play discipline) → G2 (customer trust) promotion is analogous to bloomberg's emergence-era-strategic-moves → accumulated-forces pattern
  - Chat review: validation pass, three cross-architecture patterns surfaced for later synthesis (founding-doctrine-as-asset, time-to-accumulation distribution, load-bearing-for-civilization-stack), no v1.4 amendments
- [2026-05-19] coca-cola: success — audit 52E/12I/9C/0U/73 — no schema stress observed; schema handles identity/trust-asymmetry-dominant architecture cleanly across 134-year horizon
  - Negative pairs: rc-cola (failed parallel architecture missing G1+G3+G6 marketing+identity+cultural-archetype accumulation), pepsi-as-comparator-survivor (different identity position in same architectural pattern, snack diversification hedge)
  - Notable structural pattern: identity asymmetry is non-zero-sum (position-occupation game not position-competition game) — distinct from bloomberg-vs-refinitiv pattern where competitor attempted same position
  - Final Section A entry. Awaiting chat review for Section B-F dispatch authorization.

## Cross-architecture patterns surfaced during Section A

1. **Founding-doctrine-as-asset.** Certain founding doctrines compound into structural assets that decade-shorter competitors cannot replicate. TSMC F5 pure-play → G2 customer trust. Bloomberg 1988-1990 strategic moves → G1+G3. Coca-Cola F3 1899 bottling franchise → G2 + F5 Woodruff 1923 doctrine → G3+G4. Pattern: emergence-era strategic moves can have decades-deferred accumulated-force effects.

2. **Time-to-accumulation distribution.** Accumulated forces build on different timescales depending on the substrate. G7 TSMC AI-workload-dependency: ~3 years. Bloomberg G1 chat network: ~15 years. Coca-Cola G3 cultural archetype: ~25-30 years (1920s-1950s). The schema's `since` field captures this cleanly but pattern suggests substrate-shift events accelerate force-accumulation relative to organic competitive accumulation.

3. **Load-bearing-for-civilization-stack.** TSMC G6 sovereign-strategic significance is simultaneously protective (governments invested in continuity) and target-attracting (critical infrastructure = target). The schema doesn't have explicit vocabulary for forces that are simultaneously protective and adversary-attractive; `[C]` contested tag on G6 status-now captures net-effect uncertainty. Potential v1.4 thought: load-bearing-for-civilization-stack as structural class.

4. **Identity-as-non-zero-sum-position-occupation.** Coca-Cola/Pepsi negative-pair contrast reveals identity asymmetry is a position-occupation game (occupy a specific identity position with cumulative consistency) not a position-competition game (compete for the same position). Distinct from bloomberg-vs-refinitiv or TSMC-vs-Samsung where weaker competitor attempts same position. Worth tracking across other identity-dominant entries (LVMH, Hermès, Disney IP, Rolex, Ferrari in Section B; Apple iPhone identity vs Android etc).

## Schema gaps surfaced

### Gap 1: defunct-as-subject status vocabulary (from kodak-film)

**Observed:** The `status` enum (operating | operating-pressured | declining | defunct | transformed | forcibly-restructured) does not natively distinguish between (a) entity defunct entirely, (b) architecture defunct but entity persistent operating different architecture, (c) architecture partially-persistent at reduced scale via successor entity. Kodak required compound value: "defunct-as-mass-medium-architecture / persists-in-niche-enthusiast-form-via-successor-entity-eastman-kodak". The current entry handles this by extending the value but the controlled-vocabulary slot is stressed.

**Related:** `forces-accumulated.status-now` lacks a "partially-persistent-at-reduced-scale" value analogous to Standard Oil's "redistributed-1911". Kodak's G1 (emulsion IP) and G2 (brand) are not closed but also not architecturally load-bearing at original scale — the entry used compound values like "closed-as-architecturally-load-bearing / partially-persistent" which works but stresses the schema.

**Severity:** Low — both schema slots accommodated the values via compound strings without distortion. Not blocking further dispatch. Should be reviewed alongside Standard Oil's "redistributed" approach as inputs to a possible v1.4 vocabulary refinement covering architecture-persistent-at-reduced-scale and architecture-defunct-entity-persistent cases. AT&T pre-1984 and AIG-2008 in Section D are natural retests (forcibly-restructured cases where successors continue).

**Recommendation:** Continue with current schema; track defunct-as-subject status values across remaining Section E entries (polaroid, blockbuster, sears, yahoo, blackberry, nokia-phones, etc.) to see if a pattern of compound values emerges that would inform a clean v1.4 vocabulary expansion. Do NOT modify schema mid-build — Bloomberg validation discipline says lock vocabulary based on accumulated evidence, not single-case stresses.

## Failed entries needing retry

(none)
