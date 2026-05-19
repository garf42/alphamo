
---
name: architecture-decomposition
description: Runs the Architecture Decomposition protocol on a reference value-capture architecture. Begins with a mandatory research pass grounding the architecture and its industry in current reality, then decomposes the architecture into raw structural features across nine standardized dimensions (identification, flow, position, mechanics, dynamics, temporal, force-topology, negative pairs, uncertainty audit) without forcing the decomposition through any pre-existing "moat" or primitive vocabulary. Schema distinguishes emergence forces (F-prefix, the conditions that enabled the architecture initially) from accumulated forces (G-prefix, forces that grew with the architecture after founding and now hold it in place) — critical for architectures over ~10 years old where emergence forces have closed and accumulated forces carry current durability. Produces two artifacts per run: (1) a canonical YAML record (~800-1000 tokens) which is the corpus content for AlphaMo proposer consumption, with bracket-prefix confidence tags [E]/[I]/[C]/[U] enabling machine-parseable audit; (2) a brief prose synthesis (~300-500 tokens) for QA review, not included in the corpus. Triggers ONLY on explicit invocation using "decompose architecture," "run decomposition," "run RAD," "Layer A entry on X," or "architecture decomposition." Do NOT trigger on fuzzy signals like "explain how X works" or "what makes X successful." Explicit invocation only. If the user names an architecture without invocation, you may offer ("Would you like me to run architecture decomposition on this?") but may not invoke without confirmation.
---

# Architecture Decomposition (Layer A entries)

## What this skill does

This skill takes a single reference value-capture architecture
(e.g. Bloomberg Terminal, Standard Oil, Visa interchange, Medvi)
and produces a deep structural decomposition along nine
standardized dimensions, without forcing the decomposition through
any pre-existing primitive vocabulary (moats, 7 Powers, VRIN,
asymmetry × friction × recurrence, or other).

The skill exists because the AlphaFold lineage taught a specific
lesson: high-level domain primitives (alpha helices, beta sheets)
were not the load-bearing substrate. The load-bearing substrate
was raw evolutionary data (MSA), confirmed-valid structures (PDB),
and substrate-level physical constraints encoded in architecture
(triangle inequality, equivariance). High-level patterns emerged
*from* this substrate; they were not pre-installed as vocabulary.

The AlphaMo corpus's Layer A is the templates-plus-MSA analog: a
catalog of confirmed-valid architectures, deeply decomposed into
raw structural features, with enough cross-architecture variation
that pattern-finding can identify regularities that may or may not
match any human vocabulary. The proposer's job downstream is to
find those patterns; the skill's job is to provide substrate that
doesn't pre-empt the search by installing a vocabulary.

Each entry is approximately 1500-2000 tokens, designed to fit in
a corpus of 40-60 architectures within a ~100K-token cache-friendly
prefix.


## When to use this skill

Use it **only** when the user explicitly invokes it with one of
these trigger phrases:
- "decompose architecture"
- "run decomposition"
- "run RAD" / "RAD on [X]"
- "Layer A entry on [X]"
- "architecture decomposition"

The user has chosen explicit invocation deliberately because
decomposition is slow, requires research, and produces a
substantive deliverable.

Do **not** use it when:
- The user asks "explain how [company] works" or "what makes [X]
  successful" without the trigger word — that is a general
  question, not a corpus-building task
- The user names an architecture in passing during another
  discussion
- The user is using "decompose" in an unrelated sense (e.g.,
  decomposing a problem statement)

If you think decomposition would help but the user has not
invoked it, you may **offer** ("Would you like me to run RAD on
this?") but may not run it without explicit confirmation.


## Inputs

The skill requires:
1. **An architecture name.** A specific value-capture architecture
   to decompose. Must be specific enough that the research pass
   can locate concrete information (e.g., "Bloomberg Terminal" not
   "financial data businesses").
2. **Era of analysis.** Defaults to current state if the
   architecture is still operating, or peak-capture era if defunct.
   The user can specify a different era.

Optional:
3. **Particular dimensions of interest.** The user can request
   deeper analysis on specific dimensions (e.g., "focus on
   regulatory dynamics for this one"). The protocol still runs
   all nine dimensions but allocates more depth to the requested
   ones.


## Empty outputs are preferred over manufactured outputs

Per the discipline shared across this user's skill set: declining
to produce output is a first-class result. The decomposition
protocol has specific decline patterns by dimension, and the most
dangerous failure mode is producing confident-sounding structural
claims for an architecture where the actual structural mechanics
are not well documented or are genuinely contested.

Each dimension has legitimate decline patterns:

- **Phase 0 (research).** "Research yielded insufficient
  information to ground the architecture in current reality;
  proceeding will produce a Layer A entry built largely on
  inference rather than evidence. Flagging the entry as
  'low-evidence' for downstream weighting."
- **Phase 1 (identification).** "Architecture cannot be cleanly
  identified — the candidate conflates multiple distinct
  architectures (e.g., 'Amazon' contains retail, AWS, advertising,
  and logistics, each with different structural mechanics). Test
  cannot proceed; user should pick a specific architecture and
  re-invoke."
- **Phases 2-7 (substantive dimensions).** Individual fields may
  decline with confidence tag `unknown` and a one-line explanation
  of why the information is not available. Declining a field is
  not failure; manufacturing a confident-sounding field where the
  evidence is absent is the actual failure.
- **Phase 8 (temporal evolution and force-topology).** Two-part
  decline pattern. For `forces-emergence`: "Emergence-era
  information is insufficient to identify the specific force
  conditions that enabled this architecture; recording what can be
  established and flagging the rest as `[U]`." For
  `forces-accumulated`: "No accumulated forces identified — either
  the architecture is too young for accumulated forces to have
  developed, or the search did not surface them." Empty
  `forces-accumulated` is legitimate for young architectures
  (under ~5 years). Do not manufacture accumulated forces to fill
  the section.
- **Phase 9 (negative pairs).** "No clear negative pair locatable
  — the architecture is genuinely sui generis at this resolution
  of analysis, or the pattern is too recent to have produced
  observable failures." Flagging required; do not manufacture a
  negative pair to fill the slot.
- **Phase 10 (uncertainty audit).** A clean audit with many
  fields tagged `[E]` is a sign of a well-documented architecture.
  A clean audit with many fields tagged `[I]` is a sign that the
  entry should be weighted lower downstream. Both are legitimate;
  the audit is the place this gets recorded honestly.

Treating these declines as first-class outputs is the primary
defense against the survivorship-tautology trap. An entry full of
confident-sounding structural claims that are actually post-hoc
rationalizations is exactly the failure mode the AlphaFold-faithful
corpus design is meant to avoid.


## The protocol

Ten phases. Run in order. Do not skip.

### Phase 0 — Grounding (research)

Before decomposing the architecture, ground it in current reality.

**What to research:**
- Current state of the architecture (still operating? what's the
  current scale, revenue, market position?). If defunct, when and
  why did it cease.
- Current state of the industry the architecture operates in.
- Recent (last 12 months) developments that affect the architecture
  — competitor actions, regulatory changes, technology shifts.
- Anything that would update training-data assumptions about the
  architecture's mechanics.

**Cap:** 4-6 targeted searches by default. More if the architecture
is unfamiliar or in fast-moving territory.

**What not to research:**
- The architecture's founding history (stable in training data)
- Generic industry background
- Theoretical strategy literature analyzing this architecture
  (often post-hoc rationalization; the skill is meant to bypass
  that layer of interpretation)

**Output:** Research Summary, 3-5 sentences with explicit notes on
anything that updates training-data assumptions. List any
significant unverified assumptions.

### Phase 1 — Identification

Establish the scope of decomposition.

**Fields:**
- **Name.** Specific architecture name.
- **Era of analysis.** Year or year-range being decomposed (current
  state by default).
- **Industry.** Coarse industry classification (energy, finance,
  software, retail, transport, healthcare, consumer goods, payments,
  media, etc.).
- **Current status.** Operating, declining, defunct, or
  transformed.
- **Scale signature.** Approximate revenue or value-flow magnitude
  at era of analysis, with year. (This is for cross-architecture
  comparison; precision is less important than order of magnitude.)
- **Scope clause.** What this entry covers and excludes. Important
  for conglomerates — e.g., "this entry covers Amazon's retail
  operations only; AWS and advertising are separate entries."

**Decline condition:** If the architecture conflates multiple
distinct value-capture mechanisms that should be separate entries,
decline with a split recommendation.

### Phase 2 — Flow mechanics

What's flowing through the architecture and at what rate.

**Fields:**
- **Primary flow.** What is the dominant flow the architecture
  participates in? (Money, goods, information, attention, labor,
  data, etc.) Be specific about what's flowing in what form.
- **Flow rate.** Order of magnitude — transactions per period,
  volume per period, users per period.
- **Flow direction.** Where does the flow originate, where does it
  terminate, where does the architecture sit relative to those
  endpoints?
- **Flow recurrence pattern.** One-shot, episodic, continuous,
  subscription-based, lifecycle-based. What drives the recurrence
  — inherent necessity, contractual engineering, habit, network
  reinforcement?
- **Secondary flows.** Any non-primary flows the architecture
  participates in or generates (data exhaust, attention,
  reputational signal, etc.).

### Phase 3 — Structural position

Where the architecture sits in its flow and what about that
position is non-trivial.

**Fields:**
- **Position description.** Upstream, downstream, intermediary,
  branch, hub, alternative path. Concrete description of where
  in the flow the architecture operates.
- **Adjacent positions.** Who/what is immediately upstream and
  downstream of the architecture in the flow.
- **Position scarcity (supply side).** How many other actors
  could occupy the same structural position the architecture
  occupies? What prevents them from doing so — capital
  requirements, regulatory barriers, network effects,
  scarce-input control, learning curves, or other? This is
  where things that strategy literature would call "moats"
  tend to manifest, but the skill records the structural
  fact, not the moat-category label.
- **Position substitutability (flow side).** Could counterparties
  accomplish the same end without passing through this
  structural position at all — by using a different flow that
  bypasses the architecture's category entirely? At what cost?
  (Note: this is distinct from scarcity. Many positions can have
  high scarcity — few actors occupy them — while being highly
  substitutable because counterparties can route around the
  whole flow. PayPal in 2026 illustrates this: scarce position
  with rapidly increasing substitutability via Apple Pay /
  Google Pay multi-homing.)

### Phase 4 — Counterparty structure

Who interacts with the architecture and on what terms.

**Fields:**
- **Counterparty types.** Categories of counterparty
  (consumers, enterprise buyers, suppliers, regulators,
  partners, competitors). Distinguish; do not aggregate.
  **Include operational suppliers explicitly** — AI
  infrastructure providers, advertising platforms, payment
  processors, cloud providers, and other operational
  inputs that the architecture depends on but does not
  control. These are often load-bearing for thin-operator
  architectures and are easy to overlook because they sit
  in the background of customer-facing analysis.
- **Counterparty count and concentration.** Order of magnitude of
  each counterparty type, and concentration (highly fragmented,
  moderately fragmented, concentrated).
- **Counterparty relationship structure.** Transactional, contractual,
  relational, network-mediated, platform-mediated. Term length and
  termination conditions where applicable.
- **Pricing and discrimination.** Uniform pricing or price
  discrimination? On what dimensions does the architecture
  discriminate?
- **Counterparty information asymmetry.** What does the architecture
  know about counterparties that they don't know about themselves
  or each other? What do counterparties know that the architecture
  doesn't?

### Phase 5 — Economic mechanics

The architecture's unit economics and capital structure.

**Fields:**
- **Revenue source.** Where revenue comes from — which counterparty
  type pays, for what specifically, on what schedule.
- **Unit economics.** Marginal revenue and marginal cost per unit of
  flow, in approximate terms. Where margin lives.
- **Cost structure.** Fixed vs variable cost balance, scale effects
  on cost, capital intensity.
- **Capital structure.** How financed at era of analysis — debt,
  equity, retained earnings, customer prepayments, government
  funding. Capital efficiency (revenue per dollar of capital
  deployed).
- **Margin trajectory.** Margin profile over the architecture's
  history — improving, stable, compressing.

### Phase 6 — Switching and information dynamics

How counterparties enter, stay, and exit; what information flows
do and don't cross the boundary.

**Fields:**
- **Acquisition mechanics.** How counterparties come to use the
  architecture initially. What attracts them; what costs they bear
  in joining.
- **Retention mechanics.** What keeps counterparties using the
  architecture after acquisition. Contractual, technical,
  relational, network-based, identity-based, habit-based.
- **Exit mechanics.** What it costs counterparties to leave. Both
  the cost of leaving and the cost of replacing what the
  architecture provided.
- **Information capture.** What information does the architecture
  accumulate through its operation that is not available to
  outsiders? How does this accumulation compound or decay?
- **Information disclosure.** What does the architecture reveal
  about its operation (voluntarily or by regulation) that
  counterparties or competitors can act on?

### Phase 7 — Competitive and regulatory environment

The adversarial layer.

**Fields:**
- **Direct competitors.** Who attempts to occupy similar structural
  positions. How they compete.
- **Indirect competitors.** Who provides alternative flows that
  could substitute for the architecture's value to counterparties.
- **Competitive response patterns.** Historically, how have
  competitors responded to the architecture? What has worked,
  what has failed?
- **Regulatory environment.** What regulatory regime applies. How
  stable is it. What regulatory actions has the architecture
  faced or escaped.
- **Adversarial pressure beyond competition.** Anyone actively
  working to undermine the architecture for non-competitive
  reasons (activist groups, hostile states, organized fraud,
  cultural shifts). How they attempt it.

### Phase 8 — Temporal evolution and force-topology

How the architecture got here and what currently holds it in place.

For architectures older than approximately 10 years, the forces
that hold the architecture in place now are often different from
the forces that enabled emergence. The schema separates these
deliberately. Young architectures (under ~5 years) typically have
populated `forces-emergence` and empty or minimal
`forces-accumulated`. Old architectures (decades) typically have
mostly-closed `forces-emergence` and substantial
`forces-accumulated`. The Bloomberg validation run produced this
finding: all five of Bloomberg's emergence forces had closed by
1995, and the architecture's current durability rests entirely on
five accumulated forces (chat network, training-cost lock-in, data
archive accumulation, standard-setting, trust/identity) that
emerged after founding.

**Fields:**

- **Emergence conditions (forces-emergence).** Force-topology
  conditions that enabled the architecture to emerge initially.
  Numbered list F1, F2, ... — each one-sentence description of the
  force plus its `status-now` (active / active-strengthening /
  active-durable / closing / closed / transformed / unknown).
  Explicit decomposition is required so the proposer can identify
  which forces appear across many architectures and which are
  idiosyncratic. Avoid blending forces into narrative prose.

- **Accumulated forces (forces-accumulated).** Forces that emerged
  AFTER founding and now hold the architecture in place. Numbered
  list G1, G2, ... — each entry includes description, approximate
  `since` vintage, and `status-now`. These are typically
  network-effect accumulations, data archives, training/integration
  costs, standard-setting positions, identity/trust accretions, or
  political relationships that grew with the architecture rather
  than enabling its emergence. For young architectures this field
  may be empty; do not manufacture accumulated forces to fill it.

- **Evolution.** Narrative of how the architecture changed since
  emergence — acquisitions, pivots, regulatory events, technology
  shifts, leadership changes. This is the story field, not the
  force-list field. If you find yourself listing forces here,
  promote them to `forces-accumulated` instead. The evolution field
  is for the context that explains *why* forces shifted, not the
  forces themselves.

- **Closing conditions.** What conditions would close the
  currently-active forces from either emergence or accumulated
  sets? Reference forces by their F-prefix or G-prefix ID. What
  signals would precede such closure?

- **Trajectory.** Current direction — growing capture, stable
  capture, eroding capture, transforming into something else,
  contested.

### Phase 9 — Negative pairs

Required: at least one architecture that attempted a similar
configuration and failed, with structural diagnosis.

**For each negative pair:**
- **Name and era.** The failed architecture.
- **Similarity to subject.** What structural features were shared.
- **Differential.** What was structurally different.
- **Failure diagnosis.** Specific structural reason the failure
  occurred, distinguished from execution errors and bad luck where
  possible.
- **What the contrast reveals about the subject.** What does the
  negative pair surface about the *subject* architecture that the
  positive decomposition did not? This is where the most
  load-bearing insights from RAD tend to live: the contrast
  between a failed and a successful instance of a similar pattern
  isolates which features are necessary versus which are
  incidental. Do not skip this field; it is where the negative
  pair's analytical value is realized.

**Discipline:** Negative pairs counter survivorship bias. An entry
without negative pairs is incomplete — but a manufactured negative
pair is worse than declining the slot. If genuine negative pairs
cannot be located, decline the field with: "No clear negative pair
locatable at this resolution; entry should be weighted lower
downstream due to absence of failure-case grounding."

### Phase 10 — Uncertainty audit

Pass through every field from Phases 1-9 and tag each with a
confidence bracket prefix at the start of the field's value:

- **`[E]`** — established — documented fact verifiable from
  primary sources or strong consensus
- **`[I]`** — inferred — reasoned conclusion from established
  facts, but not directly documented
- **`[C]`** — contested — multiple credible accounts disagree
- **`[U]`** — unknown — genuinely insufficient information
  available

Bracket-prefix the value of each field as you write it in the
output. Example: "Position description: [E] Pure customer-
acquisition layer sitting upstream of a fully rented regulated
medical operational stack."

At the end of the entry, produce a summary count: X established
/ Y inferred / Z contested / W unknown across N total fields.
This summary is the entry's epistemic profile and governs how
the downstream proposer should weight the entry's features.

An entry where most structural-position and economic-mechanics
fields are tagged `[E]` is high-confidence. An entry where those
fields are mostly `[I]` is suggestive but not load-bearing. Both
are useful; mistaking the latter for the former is the failure
mode.

Bracket-prefix tags are required because the audit is then a
straightforward count operation rather than a narrative
interpretation. Inline parenthetical tags like "(inferred)"
inside prose are not acceptable — they make the count
impossible to perform consistently across entries.

## Output schema

The canonical corpus content is a YAML record per architecture.
The format is designed for LLM consumption by the AlphaMo proposer,
not human readability. Each field value carries a bracket-prefix
confidence tag (`[E]`/`[I]`/`[C]`/`[U]`) embedded directly in the
string, enabling machine-parseable audit.

Values use compact controlled-vocabulary where possible (operators
joined by `/` or `+` to indicate or/and-style relations) and short
prose where structural mechanics genuinely require it. Aim for
~800-1000 tokens per record at the canonical-content level (the
structured YAML), with the prose synthesis below it as ~300-500
tokens of QA ergonomics.

### Schema fields

```yaml
- id: <slug>                  # lowercase-hyphenated identifier, used for cross-entry refs
  name: <display name>
  era: <year-range>           # e.g. "2024-2026", "1981-present", "1870-1911"
  industry: <slash-path>      # e.g. "healthcare/telehealth/dtc-rx"
  status: <controlled>        # operating | operating-pressured | declining | defunct | transformed | forcibly-restructured
  scale: <[E|I|C|U] value>    # order-of-magnitude with vintage
  scope: <[E|I|C|U] value>    # what this entry covers and excludes

  flow:
    primary: <[E|I|C|U] value>           # what flows, direction, parties
    rate: <[E|I|C|U] value>              # order-of-magnitude
    direction: <[E|I|C|U] value>         # where in the flow the architecture sits
    recurrence: <[E|I|C|U] value>        # tags: engineered | inherent | path-dependent | lifecycle | subscription | transactional (combine with +)
    secondary: <[E|I|C|U] value>         # non-primary flows

  position:
    description: <[E|I|C|U] value>
    upstream: <[E|I|C|U] value>          # what sits immediately upstream
    downstream: <[E|I|C|U] value>        # what sits immediately downstream
    scarcity-supply: <[E|I|C|U] value>   # supply-side: who else could occupy this position
    substitutability-flow: <[E|I|C|U] value>  # flow-side: can counterparties route around entirely

  counterparty:
    types: [<list of types>]             # include operational suppliers (AI, ad platforms, payment, cloud)
    concentration: <[E|I|C|U] value>     # by type: fragmented | moderate | concentrated | monopolistic
    relationship: <[E|I|C|U] value>      # transactional | contractual | relational | network-mediated | platform-mediated
    pricing: <[E|I|C|U] value>           # uniform vs discriminated; tier structure
    info-asymmetry: <[E|I|C|U] value>    # who knows what

  economics:
    revenue-source: <[E|I|C|U] value>
    unit: <[E|I|C|U] value>              # marginal revenue, marginal cost, where margin lives
    cost-structure: <[E|I|C|U] value>    # fixed/variable balance, capital intensity
    capital: <[E|I|C|U] value>           # how financed
    margin-trajectory: <[E|I|C|U] value> # improving | stable | compressing | contested

  dynamics:
    acquisition: <[E|I|C|U] value>       # how counterparties enter
    retention: <[E|I|C|U] value>         # what keeps them
    exit: <[E|I|C|U] value>              # cost of leaving
    info-capture: <[E|I|C|U] value>      # what the architecture accumulates
    info-disclosure: <[E|I|C|U] value>   # what it reveals voluntarily or by mandate

  competitive:
    direct: <[E|I|C|U] value>
    indirect: <[E|I|C|U] value>
    response-patterns: <[E|I|C|U] value> # historical competitive responses
    regulatory: <[E|I|C|U] value>        # current regulatory environment
    adversarial: <[E|I|C|U] value>       # beyond competition: activists, hostile manufacturers, etc

  forces-emergence:                       # explicit numbered force-topology elements at emergence
    - id: F1
      description: <[E|I|C|U] value>     # one-sentence describing the force
      status-now: <controlled>            # active | active-strengthening | active-durable | closing | closed | transformed | unknown
    - id: F2
      ...

  forces-accumulated:                     # forces that emerged AFTER founding and now hold the architecture
    - id: G1                              # G-prefix distinguishes from F (emergence) forces
      description: <[E|I|C|U] value>
      since: <year-or-range>              # approximate vintage when this force became load-bearing
      status-now: <controlled>            # same controlled vocabulary as forces-emergence
    - id: G2
      ...

  evolution: <[E|I|C|U] value>           # narrative of how the architecture changed — acquisitions, pivots, regulatory events, technology shifts. NOT the place for force-list content (use forces-accumulated for that).
  closing-conditions: <[E|I|C|U] value>  # what would close currently-active forces (from either emergence or accumulated)
  trajectory: <[E|I|C|U] value>          # growing | stable | eroding | transforming | contested

  negative-pairs:
    - id: <slug>                          # for cross-corpus lookup if the negative pair is also a corpus entry
      name: <display>
      era: <year-range>
      similarity: <value>
      differential: <value>
      diagnosis: <value>
      reveals: <value>                    # what the contrast reveals about the subject — required field
    - ...

  audit: <Ne / Ni / Nc / Nu / Ntotal>    # e.g. "30E / 12I / 3C / 3U / 48-fields"

  notes: |                                # free-form escape hatch for structural nuance that doesn't fit schema
    <prose>
```

**Controlled-vocabulary status note.** The enumerated value sets in
the schema above (status, recurrence tags, concentration,
relationship, force status-now, trajectory) are v1.2 working
defaults. They will be locked after the Bloomberg validation run,
when we have two structurally-different entries to validate the
vocabulary against. If a value doesn't fit an existing enumerated
slot, write what fits and flag in `notes` — the vocabulary will
expand to accommodate genuine variation rather than the entry
being distorted to fit existing slots.

### Cross-entry references

Negative pairs and force-topology elements can reference other
corpus entries by `id`. When the corpus is consumed by the
proposer, these references enable cross-entry pattern-finding
without each entry having to repeat shared structural mechanics.

## Output format

Each RAD run produces two artifacts:

**1. The canonical YAML record** (this is what gets concatenated
into the corpus). Format per the schema above. Target ~800-1000
tokens. This is the load-bearing output.

**2. A brief prose synthesis** (this is for QA ergonomics — Chris
or downstream reviewer reads this to assess entry quality without
parsing the YAML by hand). Format below. Target ~300-500 tokens.
This is NOT included in the corpus that ships to AlphaMo.

Structure the output as follows:

```
## Research Summary
[3-5 sentences from Phase 0]

## Canonical Record

```yaml
- id: <slug>
  ... full structured record per schema ...
```

## Prose Synthesis

**Identification:** [1-2 sentences naming and scoping the entry]

**Structural position:** [2-3 sentences capturing the load-bearing
structural mechanics — what's actually doing the work in this
architecture, in plain language]

**Force-topology dependence:** [2-3 sentences on which forces
hold the architecture in place now. For architectures over ~10
years, explicitly distinguish emergence forces (F-prefix) from
accumulated forces (G-prefix) and identify which set is doing the
load-bearing work currently. Note closing conditions if visible.]

**Negative-pair insights:** [1-2 sentences on what the contrast
with failed similar architectures reveals about the subject —
the load-bearing analytical content from Phase 9]

**Epistemic profile:** [1-2 sentences on the audit result —
where the entry is firm, where it's inferred, what's contested
or unknown]
```

The prose synthesis is review material, not corpus material. It
exists so that QA can be done at a glance without parsing the
YAML, and so that the running model (you, executing this skill)
has to articulate the structural insight in human language at
least once before the entry ships — which surfaces failures of
understanding that the structured form can hide.

## Anti-patterns

Things this skill should never do:

- **Trigger without explicit invocation.** Explicit triggers only.

- **Force decomposition through a primitive vocabulary.** The
  skill is designed precisely to bypass moat-vocabulary and let
  raw structural features stand on their own. If a field would
  read more naturally with a primitive name attached (e.g.,
  "two-sided network effects" instead of "the architecture
  intermediates between consumers and merchants, with each side's
  participation increasing value to the other"), use the raw
  description, not the primitive name. The proposer downstream
  can rediscover primitives from raw descriptions; it cannot
  rediscover raw descriptions from primitive labels.

- **Use pattern-name labels.** This is a specific failure mode
  related to the previous one but distinct. Labels like
  "rented-infrastructure pattern," "thin-operator architecture,"
  "AI-orchestration layer," "consumer-acquisition wrapper," and
  similar shorthand pre-empt the downstream pattern-finding the
  corpus is designed to enable. Even when the label feels apt,
  write out the structural mechanics: "Medvi rents its physician
  network from CareValidate, its pharmacy fulfillment from
  OpenLoop, and operates only the customer-acquisition layer
  itself" is acceptable; "Medvi exemplifies the rented-
  infrastructure pattern" is not. Patterns are what the proposer
  will find; the skill's job is to make them findable, not to
  name them in advance.

- **Produce prose-only output.** The canonical corpus content is
  the structured YAML record. Producing only a prose decomposition
  (the v1.0 / v1.1 format) means the entry cannot be ingested into
  the corpus without a re-compression step that loses information.
  Always produce the structured record first and the prose
  synthesis second; the prose synthesis is review ergonomics, not
  corpus content.

- **Bloat the canonical record with prose.** The structured YAML
  record targets ~800-1000 tokens. If field values are growing
  into paragraph-length descriptions, the entry is failing the
  compression discipline that lets the corpus fit 40-60 entries
  in the proposer's context. Move long-form structural nuance to
  the `notes` free-form field rather than expanding individual
  field values past 1-3 short clauses.

- **Skip the prose synthesis section.** Even though the prose
  synthesis is not in the canonical corpus, it is required output.
  Producing the synthesis forces articulation of the structural
  insight in plain language, which catches failures of
  understanding that the structured form can hide. A run that
  produces a clean-looking YAML record but cannot produce a
  coherent prose synthesis is a run where the model produced
  schema-conforming output without actually understanding the
  architecture — the exact failure mode the synthesis is meant
  to catch.

- **Compress accumulated forces into the evolution prose field.**
  For architectures older than approximately 10 years, the forces
  that hold the architecture in place now are typically different
  from the emergence forces and have to be captured explicitly in
  `forces-accumulated`. If you find yourself listing forces inside
  the `evolution` prose field (e.g., "G1 is X, G2 is Y, G3 is Z"),
  stop and move them to `forces-accumulated` with proper structure.
  The evolution field is for the *narrative* of how the architecture
  changed — acquisitions, pivots, leadership changes, regulatory
  events. The accumulated forces are first-class structural objects
  with their own vintage and status, not narrative elements.
  Conflating them defeats the cross-architecture pattern-finding
  the corpus is designed to enable. This anti-pattern was the
  primary v1.3 schema gap identified by the Bloomberg validation
  run.

- **Skip the research pass.** Phase 0 is mandatory. The 2026
  force-topology may have shifted the architecture's mechanics
  since training-data cutoff.

- **Skip negative pairs.** Phase 9 is the survivorship-bias
  countermeasure. Skipping it produces a corpus full of
  retrospectively-confident success stories, which is exactly the
  failure mode the AlphaFold-faithful redesign is meant to avoid.
  Declining the slot honestly when no negative pair exists is
  acceptable; omitting it is not.

- **Skip the uncertainty audit.** Phase 10 is what makes the
  entry honest. Without it, the proposer cannot distinguish
  high-evidence entries from inferred ones, and treats them all
  as equally load-bearing. This silently degrades the corpus.

- **Manufacture confident-sounding fields where evidence is
  absent.** Tagging a field `unknown` with a one-line explanation
  is more useful than a confident-sounding sentence with no
  grounding. The survivorship-tautology failure mode is exactly
  the production of confident-sounding post-hoc rationalizations;
  the skill exists to resist it.

- **Treat success as evidence of intentional design.** Architectures
  that succeeded didn't necessarily emerge through deliberate
  composition of structural features. Many succeeded through
  accident, lucky timing, or path-dependent advantages that the
  founders did not foresee. Where evolution-by-accident is
  visible, the entry should record it, not retrospectively
  rationalize it as strategy.

- **Conflate initial conditions with current state.** Many
  architectures look stable now but emerged under very different
  force-topology conditions. Phase 8 keeps these distinct
  deliberately; do not collapse them into a unified narrative.

- **Quote heavily from strategy literature.** The skill is meant
  to bypass the post-hoc interpretation layer that strategy
  literature provides. Use primary sources (financial filings,
  primary historical accounts, the architecture's own
  documentation, regulatory records, contemporaneous reporting)
  where possible. Strategy literature can be referenced for
  context but should not be the primary source of structural
  claims.

- **Exceed the token budget.** Aim for ~1500-2000 tokens per
  entry. If decomposition genuinely requires more (very large or
  multi-faceted architectures), split into multiple entries
  rather than producing one bloated entry.

- **Add sycophantic framing.** Open with the Research Summary
  and proceed directly into the decomposition. The protocol is
  doing serious work; the framing should match.
