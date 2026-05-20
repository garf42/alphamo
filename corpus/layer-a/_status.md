# Layer A Build Status

**Started:** 2026-05-19
**Mode:** Direct in-session orchestration (Super dispatch flow modified per chat discussion)
**Total entries planned:** ~63 (per architecture-list.md)
**Completed:** 2 (kodak-film, tsmc) + 4 seed (medvi, bloomberg-terminal, visa-interchange, standard-oil from chat session)
**Failed validation:** 0
**Declined Phase 1:** 0
**Low evidence:** 0
**Schema gaps:** 1 (defunct-as-subject status-vocabulary; see kodak-film notes — chat reviewed, tracked for D+E retests, no v1.4 amendment)
**Pending:** ~57

## Log

- [2026-05-19] kodak-film: success — audit 47E/11I/5C/0U/63 — schema-stress observed (defunct-as-subject), not blocking; details in entry notes and Schema gaps section below
  - First Section A sequential entry built in direct-orchestration mode (skipped seq entries already-seed-built: visa-interchange, standard-oil from chat session)
  - Chat review: validation pass, schema stress tracked across Section D+E retests, no v1.4 amendment needed yet
- [2026-05-19] tsmc: success — audit 56E/9I/7C/0U/72 — no schema stress observed; schema handles capability-asymmetry-dominant architecture cleanly
  - Negative pairs: globalfoundries-2018-exit (capex+execution cliff), intel-IDM-leadership-loss (pure-play discipline as architectural invariant)
  - Notable structural pattern: F5 (pure-play discipline) → G2 (customer trust) promotion is analogous to bloomberg's emergence-era-strategic-moves → accumulated-forces pattern
  - Next Section A entry: coca-cola (awaiting chat review of tsmc before dispatch)

## Schema gaps surfaced

### Gap 1: defunct-as-subject status vocabulary (from kodak-film)

**Observed:** The `status` enum (operating | operating-pressured | declining | defunct | transformed | forcibly-restructured) does not natively distinguish between (a) entity defunct entirely, (b) architecture defunct but entity persistent operating different architecture, (c) architecture partially-persistent at reduced scale via successor entity. Kodak required compound value: "defunct-as-mass-medium-architecture / persists-in-niche-enthusiast-form-via-successor-entity-eastman-kodak". The current entry handles this by extending the value but the controlled-vocabulary slot is stressed.

**Related:** `forces-accumulated.status-now` lacks a "partially-persistent-at-reduced-scale" value analogous to Standard Oil's "redistributed-1911". Kodak's G1 (emulsion IP) and G2 (brand) are not closed but also not architecturally load-bearing at original scale — the entry used compound values like "closed-as-architecturally-load-bearing / partially-persistent" which works but stresses the schema.

**Severity:** Low — both schema slots accommodated the values via compound strings without distortion. Not blocking further dispatch. Should be reviewed alongside Standard Oil's "redistributed" approach as inputs to a possible v1.4 vocabulary refinement covering architecture-persistent-at-reduced-scale and architecture-defunct-entity-persistent cases. AT&T pre-1984 and AIG-2008 in Section D are natural retests (forcibly-restructured cases where successors continue).

**Recommendation:** Continue with current schema; track defunct-as-subject status values across remaining Section E entries (polaroid, blockbuster, sears, yahoo, blackberry, nokia-phones, etc.) to see if a pattern of compound values emerges that would inform a clean v1.4 vocabulary expansion. Do NOT modify schema mid-build — Bloomberg validation discipline says lock vocabulary based on accumulated evidence, not single-case stresses.

## Failed entries needing retry

(none)
