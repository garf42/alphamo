# hims-hers

**Architecture:** Hims & Hers Health (direct-to-consumer telehealth-+-compounded-pharmacy
+-branded-GLP-1-transition architecture)
**Industry:** healthcare/telehealth
**Era:** 2017-present (current state in active mid-2026 transformation to branded-GLP-1 model)
**Scope:** Hims & Hers Health Inc. (NYSE: HIMS) consumer-facing telehealth platform + affiliated
licensed-provider network + compounded-pharmacy operations + branded-pharmaceutical partnerships

---

## Research summary

Hims & Hers Health, founded 2017 by Andrew Dudum (CEO), built a direct-to-consumer (DTC)
telehealth architecture covering men's wellness (hair loss, ED, mental health), women's
wellness (dermatology, contraception, mental health), weight management, and dermatology.
The architecture combines: brand-led consumer acquisition + asynchronous telehealth visits
with affiliated-licensed-provider-network + subscription-recurring pharmacy fulfillment +
in-house compounded-pharmacy operations for select therapeutic categories [E].

The architecture's value-capture position is the DTC-brand-+-recurring-subscription wrapped
around prescription pharmaceutical access. Margins are driven by: (a) brand-led customer
acquisition cost amortized over subscription LTV, (b) gross-margin on compounded versus
distributed pharmaceutical products, (c) cross-sell ratios into multiple subscription
categories [I].

The defining architectural event of 2024-2026 was the compounded-GLP-1 segment. After FDA
removed semaglutide from the drug-shortage list in early 2025 (compounded-version production
no longer legally permitted at scale), Hims & Hers faced a structural problem: compounded-
GLP-1 weight-management was an oversized share of accelerated 2024 revenue [E]. The
architecture's response, announced April 2024 and operationalized through 2025-2026, was a
brand-partnership with Novo Nordisk to offer brand-name Wegovy/Ozempic directly through the
Hims platform — a transition from compounded-pharmacy-supplier to branded-pharmaceutical-
distributor for the GLP-1 category [E].

This is an architectural-substrate-shift in mid-flight: same flow (DTC consumer +
subscription + telehealth-prescription-+-fulfillment), but the upstream-input changes from
own-compounded to branded-partnered, with very different gross-margin economics and
counterparty-leverage profile [I]. FY2024 revenue ~$1.5B (up from ~$873M FY2023) [E].
FY2025 revenue ~$2.0-2.2B band (projected/reported) with notable margin compression in
Q4 2025 + Q1 2026 as the transition operationalized [I]. Architecture remains operating but
is in active transformation; classification under v1.4 is operating-pressured / executing-
architectural-substrate-transition (not Sub-pattern C — accumulated forces preserved without
external-pressure-driven restructuring). Closer in form to Sub-pattern D candidate
(architecture-voluntarily-transformed-by-operator) but architecturally less dramatic than
Berkshire 1965 — same underlying flow continues, only upstream input changes.

---

## Canonical record (YAML)

```yaml
slug: hims-hers
name: Hims & Hers Health Inc.
industry: healthcare/telehealth
era: 2017-present
status: operating-pressured / executing-architectural-substrate-transition-2024-2026 / brand-platform-intact
schema_version: v1.4

scope:
  included: [E] Hims (men's brand) + Hers (women's brand) telehealth-+-fulfillment subscription
    platform + affiliated-licensed-provider-network + compounded-pharmacy operations + Novo
    Nordisk brand-GLP-1 partnership 2024-onward
  excluded: [E] employer/B2B health plans (separate segment limited), international expansion
    pre-launch markets, equity-and-financial-instruments commentary, parent-company-only
    legal-entity holdings

evolution:
  - phase: founding-+-Hims-launch (2017-2019)
    summary: [E] Andrew Dudum + co-founders launch Hims (men's wellness — hair loss + ED)
      November 2017. DTC brand-led acquisition + asynchronous telehealth + subscription
      fulfillment for finasteride + minoxidil + sildenafil/tadalafil generics. Hers (women's
      wellness) launches 2018. Asynchronous-visit model relies on affiliated-licensed-
      provider-network across state lines.
  - phase: SPAC-IPO-+-expansion (2020-2022)
    summary: [E] SPAC-merger January 2021 → NYSE listing (HIMS). Category expansion: mental
      health (sertraline + bupropion + therapy referrals), dermatology, primary care.
      Subscription metrics emerge as key reporting + valuation drivers. Compounding pharmacy
      capability built / acquired during this phase to support customization claims +
      manufacturing-margin capture.
  - phase: compounded-GLP-1-acceleration (2023-2024)
    summary: [E] FDA drug-shortage designation for semaglutide enables compounding-pharmacies
      legally to produce compounded-semaglutide at scale. Hims & Hers launches compounded-GLP-
      1 weight-management May 2024 (after $199/month pricing announcement). Revenue
      acceleration: FY2024 ~$1.5B (vs ~$873M FY2023). Stock acceleration during 2024 reflects
      growth-rate-acceleration + compounded-margin economics.
  - phase: FDA-resolution-+-Novo-Nordisk-partnership (2025-2026)
    summary: [E] FDA removes semaglutide from drug-shortage list early-to-mid 2025;
      compounded-semaglutide production at scale no longer legally permitted. Hims & Hers
      pre-announces (April 2024) + operationalizes (2025-2026) partnership with Novo Nordisk
      to distribute brand-Wegovy/Ozempic through platform — pivoting from compounded-supply
      to branded-distribution. Margin compression notable Q4 2025 + Q1 2026. Other categories
      (testosterone, peptides, dermatology, mental health) reach for revenue diversification.

primary_flow:
  description: [E] DTC-consumer-+-subscription healthcare flow: prospect → marketing-funnel →
    telehealth-intake-+-prescription → pharmacy-fulfillment → subscription-renewal-+-cross-
    sell
  inputs: [E] brand-+-marketing-spend, affiliated-licensed-providers (state-by-state),
    pharmaceutical inputs (compounded ingredients pre-2025; branded SKUs increasingly post-
    2025), packaging + fulfillment infrastructure, telehealth-platform technology, regulatory
    compliance (50-state pharmacy + medical licensure)
  transformation: [E] consumer-acquisition + asynchronous-telehealth-intake + prescription-
    issuance + pharmacy-fulfillment + subscription-relationship-management
  outputs: [E] monthly subscription deliveries of prescription medications (compounded-or-
    branded) + adjacent OTC + provider-touchpoints + cross-category upsell
  capture_points: [E] subscription-LTV vs CAC + compounded-margin (decreasing post-2025) +
    branded-partnership-margin (newly capturing post-2025) + cross-category-cross-sell

positions:
  - id: P1
    label: DTC-brand-led-telehealth-platform-for-men's-and-women's-wellness
    description: [E] First-mover or notable-early-mover for men's wellness (hair loss + ED)
      and women's wellness (contraception + mental health) categories in DTC-subscription
      form. Brand recognition (Hims + Hers) is the primary go-to-market differentiator.
    status: [E] held-with-substantial-brand-recognition (consumer-survey-tier-1 in category)
  - id: P2
    label: asynchronous-telehealth-+-prescription-fulfillment-operator
    description: [E] Asynchronous-visit model with licensed-provider-network covers 50 states
      via individual-state licensure. Prescription written + pharmacy-filled + shipped via
      subscription. Architecture is the workflow integrator + customer-relationship-owner.
    status: [E] held-with-regulatory-complexity (50-state licensure + DEA + state-pharmacy
      regulations + telehealth-rule-changes ongoing)
  - id: P3
    label: compounded-pharmacy-operator (2022-2025)
    description: [E] In-house compounded-pharmacy capability built to enable: (a) custom
      dosing claims, (b) manufacturing-margin capture vs distributed generic, (c) supply
      independence. Compounded-GLP-1 capability was central to 2024 revenue acceleration.
    status: [I] active-but-narrowing (specific categories — finasteride blend, peptides,
      testosterone — remain; compounded-GLP-1 phased out by FDA action)
  - id: P4
    label: branded-pharmaceutical-distribution-partner (2025-onward)
    description: [E] Novo Nordisk Wegovy/Ozempic distribution partnership announced April
      2024 + operationalized 2025-2026. Architecture becomes a branded-distribution-channel
      for select major pharmaceuticals where compounding is not legal or appropriate.
    status: [E] emerging (defining-feature of architectural-substrate-transition)

counterparties:
  - id: C1
    label: end-consumer-+-subscriber
    leverage_hims: [E] brand recognition + ease-of-onboarding + asynchronous-vs-clinic
      convenience + bundled-cross-category + Hims/Hers identity
    leverage_counterparty: [E] subscription-cancel-easy + alternative-DTC-providers (Ro,
      Roman, Lemonaid, traditional clinic) + Costco/Amazon-pharmacy + GLP-1-direct-from-Eli-
      Lilly-Direct
  - id: C2
    label: affiliated-licensed-providers (physicians + NPs across 50 states)
    leverage_hims: [E] platform-volume + per-visit-fees + asynchronous-flexibility
    leverage_counterparty: [E] independent-licensure + can serve other DTC platforms +
      regulatory-scrutiny on volume + state-medical-board oversight
  - id: C3
    label: pharmaceutical-manufacturers (Novo Nordisk; Eli Lilly comparative absent)
    leverage_hims: [E] platform reach + DTC marketing capability + curated-prescriber-network
      + branded-distribution channel; sole significant DTC partner for Novo on Wegovy + Ozempic
    leverage_counterparty: [E] supply control + pricing power + alternative-channel (Eli Lilly
      Direct, traditional clinics, hospitals, pharmacy chains) + can renegotiate or terminate
      partnership + reputational sensitivity to compounded-precedent
  - id: C4
    label: FDA + state-medical-and-pharmacy-boards
    leverage_hims: [E] compliance discipline + legal-and-regulatory-staff + lobbying-capacity
    leverage_counterparty: [E] DSHEA-and-compounding rule control + shortage-list designations
      + state-pharmacy-licensing + telehealth-rule changes + ability to make enforcement
      actions
  - id: C5
    label: marketing-channels (Meta, Google, TikTok, podcast, Influencer/Affiliate)
    leverage_hims: [E] sustained ad-spend + creative-content production at scale
    leverage_counterparty: [E] ad-pricing dynamics + Apple-ATT impact + algorithm-shifts +
      brand-safety scrutiny on healthcare advertising
  - id: C6
    label: capital-markets-+-shareholders
    leverage_hims: [E] growth-rate-acceleration + profitability path + brand-platform story
    leverage_counterparty: [E] valuation-sensitivity to growth-deceleration + compounded-GLP-
      1-revenue-overhang in 2025 + insider-selling-scrutiny + short-thesis activity

economics:
  revenue_model: [E] DTC subscription with monthly billing; mix of: compounded products
    (declining), generic-distributed products (steady), branded-partnership products
    (emerging), one-time + ancillary (limited)
  cost_structure: [E] marketing/CAC (largest cost line ~40-50% revenue) + cost of goods
    (compounded vs branded vs generic mix) + provider-fees + pharmacy fulfillment + technology
    + corporate overhead
  margin_pattern: [E] gross margins historically ~80%+ on legacy categories; compressed by
    branded-GLP-1 transition since branded-product COGS substantially higher than compounded;
    contribution-margin per-subscriber positive given high LTV
  cyclicality: [I] subscription-base relatively stable; growth-rate cyclical with marketing-
    spend efficiency + category-launch timing
  recent_financials:
    fy2023_revenue: [E] $872.8M
    fy2024_revenue: [E] ~$1.48B
    fy2025_revenue: [I] ~$2.0-2.2B band (projected; tied to GLP-1 transition timing)
    subscriber_count_2024_year_end: [E] ~2.2M
    gross_margin_2024: [E] ~79%
    gross_margin_q1_2026_projected: [I] mid-60s% range expected as branded GLP-1 mix grows

dynamics:
  current_pressures:
    - [E] FDA semaglutide shortage-list removal early-mid 2025 forcing compounded-GLP-1 phase-
      out
    - [E] Novo Nordisk partnership terms + reliance on single-pharma-partner for category
      continuity
    - [E] Eli Lilly Direct + traditional-clinic alternative routes to GLP-1 access reducing
      Hims differentiation
    - [E] CAC inflation in healthcare marketing categories + ad-platform privacy changes
    - [E] Regulatory scrutiny of DTC-prescription model (state medical boards + DEA)
    - [E] Cross-category diversification execution: testosterone, peptides, dermatology,
      mental health need to absorb GLP-1 revenue mix change
    - [E] Insider selling + short-thesis activity in capital markets through 2024-2025
  recent_strategic_moves:
    - [E] April 2024 Novo Nordisk Wegovy/Ozempic partnership pre-announcement (pre-emptive
      ahead of shortage-list resolution)
    - [E] Peptide category launch + expansion 2024-2025
    - [E] Testosterone + men's-hormone-optimization category launch 2024-2025
    - [E] AI-personalization + intake-flow optimization investments
    - [E] International market entry preparation
    - [E] In-house compounded capability retained for non-GLP-1 categories
  trajectory: [I] architecture in active transformation. Outcome path: (a) successful pivot
    where branded-distribution-margin + category-diversification + LTV-improvements compensate
    for compounded-GLP-1 phase-out → architecture continues with substrate-shifted upstream;
    (b) unsuccessful pivot where GLP-1 revenue replacement insufficient → revenue + profit
    pressure intensifies. Architecture is structurally Sub-pattern-D-adjacent (operator-
    voluntary upstream transition; same flow continues) — distinct from Sub-pattern C
    (external pressure forcing restructuring while preserving accumulated forces). Closer to
    operator-anticipated regulatory-substrate-shift response.

competitive_landscape:
  direct_competitors:
    - ro-roman-and-related-DTC-telehealth
    - lemonaid-health
    - traditional-telehealth-MDLive-+-Teladoc-direct-to-consumer-paths
  adjacent_substitutors:
    - eli-lilly-direct-(LillyDirect)
    - amazon-pharmacy-+-amazon-clinic
    - costco-pharmacy
    - in-person-clinics-+-hospital-systems
    - over-the-counter-+-supplement alternatives where applicable
  comparative_position: [E] strongest brand-recognition in DTC men's-wellness and women's-
    wellness categories + first-to-scale compounded-GLP-1 (now phasing); newer entrants +
    pharma-direct + retail-pharmacy create multi-front competitive pressure
  customer_concentration: [E] consumer-millions, low concentration; partner-concentration
    (Novo Nordisk) is the more relevant concentration variable post-2025

forces-emergence:
  - id: F1
    label: founder-Andrew-Dudum-+-Atomic-incubator-lineage
    description: [E] Dudum + co-founders incubated Hims out of Atomic (venture-builder/
      incubator) 2016-2017. Brand-led-DTC + asynchronous-telehealth + subscription as
      packaged go-to-market strategy from inception, not iterated to.
    contribution: [E] foundational-architectural-template + brand-led-discipline established
      from inception
  - id: F2
    label: men's-wellness-category-positioning-2017-+-women's-wellness-2018
    description: [E] Hims launched men's hair loss + ED as the entry category (large
      undertreated DTC opportunity + clear prescription path). Hers extended to women's
      categories. Brand-tier-positioning vs traditional clinic + drug-store.
    contribution: [E] category-position established + brand-tier asymmetry vs commodity
      pharmacy
  - id: F3
    label: SPAC-IPO-2021-capital-+-valuation-launch
    description: [E] January 2021 SPAC merger gave architecture capital for marketing
      acceleration + acquisition capability + valuation visibility. Stock-currency for talent
      + partnerships.
    contribution: [E] growth capital + public-currency for partnerships
  - id: F4
    label: in-house-pharmacy-+-compounding-capability-built-out
    description: [E] Vertically-integrated compounded-pharmacy capability built/acquired to
      enable customization claims + manufacturing-margin capture + supply independence. This
      capability is what allowed compounded-GLP-1 scaling 2024 + what now anchors retained
      categories (peptides, testosterone blends).
    contribution: [E] manufacturing-margin position + supply-flexibility + regulatory-
      complexity load
  - id: F5
    label: April-2024-Novo-Nordisk-partnership-pre-announcement
    description: [E] Pre-emptive partnership announcement ahead of expected FDA shortage-list
      resolution preserved future-state legitimacy + Novo-channel-partnership before
      competitors could secure equivalent. Strategic anticipation move not reactive.
    contribution: [E] architectural-transition-pre-positioning + counterparty-relationship-
      secured before pressure
  - id: F6
    label: founder-CEO-discipline-+-long-tenure
    description: [E] Andrew Dudum CEO since founding (2017-present). 8+ years founder-led-
      continuity + identifiable architectural-vision + capital-discipline through SPAC + post-
      IPO period.
    contribution: [E] cultural-architectural-consistency + founder-led-discipline as
      execution-coherence-mechanism

forces-accumulated:
  - id: G1
    label: brand-recognition-+-consumer-trust-(Hims-+-Hers)
    description: [E] 8+ years of sustained brand-building + advertising-spend + category-
      leadership produced top-of-mind in target demographics. Brand spans gender + category +
      lifestage with consistent identity. Consumer-survey-tier-1 in men's wellness DTC.
    status_now: [E] active-strengthening (substantial recent brand investment + cultural
      penetration via advertising + social media)
    time_to_accumulate: [E] 8+ years from 2017 launch
  - id: G2
    label: subscription-LTV-+-recurring-customer-base
    description: [E] ~2.2M subscribers FY2024 year-end. Subscription-LTV mechanics improving
      with cross-category cross-sell. Recurring-revenue base provides operating-leverage and
      customer-base-asset.
    status_now: [E] active-growing
    time_to_accumulate: [E] 8+ years; acceleration 2023-2025
  - id: G3
    label: vertically-integrated-pharmacy-+-compounded-manufacturing-capability
    description: [E] In-house pharmacy + compounded-manufacturing capability is rare for DTC
      telehealth + provides supply control + margin capture for select categories +
      flexibility to respond to regulatory + supply shifts.
    status_now: [I] active-but-reconfiguring (GLP-1 segment phased out; peptide + testosterone
      + custom-formulation categories continue)
    time_to_accumulate: [E] 4-5 years buildout via acquisition + organic
  - id: G4
    label: affiliated-licensed-provider-network-(50-state)
    description: [E] 50-state affiliated-provider network covers regulatory licensure for
      asynchronous + synchronous telehealth + prescription issuance. Substantial regulatory-
      complexity-overhead to assemble + maintain.
    status_now: [E] active
    time_to_accumulate: [E] 5-7 years state-by-state buildout
  - id: G5
    label: marketing-+-creative-+-customer-acquisition-machine
    description: [E] Scaled performance-marketing + creative-content + influencer-affiliate
      capability across Meta + Google + TikTok + podcast + offline channels. Brand-led-
      acquisition discipline at marketing-spend ~40-50% of revenue.
    status_now: [E] active (with ongoing CAC-efficiency pressure)
    time_to_accumulate: [E] 7-8 years
  - id: G6
    label: pre-emptive-strategic-architecture-(Novo-Nordisk-pre-announcement-2024)
    description: [I] The April 2024 pre-emptive Novo Nordisk partnership announcement ahead
      of FDA shortage-list resolution exemplifies pre-emptive-strategic-architecture: securing
      future-state structural-position before pressure forces it. Architectural-discipline-
      as-asset in anticipatory form.
    status_now: [E] active-as-pattern (executed once; recurring discipline TBD)
    time_to_accumulate: [E] single-event; underlying discipline may be cumulative
  - id: G7
    label: founder-led-CEO-continuity-+-architectural-vision
    description: [E] Dudum founder-CEO since 2017 (8+ years). Architectural-vision
      consistency + capital-allocation-discipline + brand-protection-discipline traceable to
      founder-tenure-+-incentive-alignment.
    status_now: [E] active
    time_to_accumulate: [E] 8+ years

negative-pairs:
  - slug: ro-(roman)-as-comparator-DTC-telehealth
    description: [E] Roman (Ro) launched parallel DTC men's wellness 2017-2018 with similar
      category + asynchronous-telehealth + subscription mechanics. Differences: less brand-
      tier-positioning, less integrated-pharmacy capability, slower category-expansion. Ro
      pursued PE/private path vs Hims public route. Comparative case for: brand-tier-
      positioning + integrated-pharmacy + public-vs-private capital architecture.
  - slug: medvi-as-DTC-pharmacy-fulfillment-comparator
    description: [E] Medvi is the DTC pharmacy-fulfillment + brand-led-consumer-acquisition
      adjacent comparator. Both architectures rely on brand + asynchronous-prescription +
      subscription mechanics; differences in category-focus + regulatory-segment + capital-
      base. Medvi entry already in corpus (seed) — pairing illustrates architectural-template
      variation across DTC-healthcare-substrate.
  - slug: eli-lilly-direct-(LillyDirect)-as-substitutor
    description: [E] Eli Lilly launched LillyDirect direct-to-consumer GLP-1 + branded
      pharmaceuticals 2024-2025. Pharma-manufacturer-direct DTC-channel that disintermediates
      DTC-telehealth platforms for the manufacturer's own categories. Structurally relevant
      because: (a) demonstrates that pharma-direct can capture some DTC-channel value, (b)
      illustrates that platform-vs-manufacturer leverage shifts when manufacturer adopts
      DTC tools, (c) provides comparative case for branded-pharma-channel architecture.

audit:
  evidence_basis_explicit: [E] 46 fields with publicly-verifiable financials + regulatory
    actions + executive announcements + filings
  inferred: [I] 13 fields strategic-interpretation or projection
  contextual: [C] 7 fields cross-corpus or industry-context anchoring
  unverified: [U] 0 fields
  total: 66 fields
```

---

## Prose synthesis

### Substrate + flow

Hims & Hers operates a DTC-brand-led-+-subscription-+-telehealth-+-fulfillment flow with a
defining 2024-2026 architectural-substrate-transition in the GLP-1 category: from in-house
compounded-pharmacy upstream to Novo-Nordisk-branded-pharmaceutical upstream. The flow itself
(consumer-acquisition → telehealth-intake → prescription → fulfillment → subscription) is
preserved; the upstream input layer is reconfigured. This is the architecture's most visible
recent test of operational + strategic resilience.

### Forces — emergence + accumulated

Emergence forces include Atomic-incubator founding (F1), category-positioning across men's
+ women's wellness (F2), SPAC-IPO capital (F3), in-house pharmacy/compounding capability (F4),
April 2024 pre-emptive Novo Nordisk pre-announcement (F5), and Dudum founder-CEO continuity
(F6). Accumulated forces are brand recognition (G1, primary asset), subscription-LTV-+-base
(G2), pharmacy-+-compounding capability (G3, mid-reconfiguration), 50-state provider network
(G4), marketing-+-creative machinery (G5), pre-emptive-strategic-architecture (G6, single-
instance pattern of anticipatory positioning), and founder-CEO-continuity (G7).

### Counterparties + economics

Consumer-subscribers (C1) are the value-capture endpoint; providers (C2), pharma-partners
(C3), regulators (C4), marketing-channels (C5), and capital-markets (C6) are the leverage-
exchange points. The most consequential 2025-2026 leverage shift is C3: dependence on Novo
Nordisk for GLP-1 category continuity in the absence of legal compounded-GLP-1 production
makes a single pharma partner architecturally load-bearing. Economics: FY2023 ~$873M → FY2024
~$1.48B → FY2025 ~$2.0-2.2B band projected; gross margins compressing from ~79% toward mid-
60s as branded-GLP-1 mix grows.

### Competitive position + dynamics

Architecture holds tier-1 brand-recognition in DTC men's + women's wellness and is mid-pivot
in GLP-1 weight management. Competitive pressure from: peer DTC telehealth (Ro, Lemonaid),
pharma-direct DTC (LillyDirect — structural new entrant 2024-2025), retail-pharmacy expansion
(Amazon, Costco), and in-person/clinical alternatives. Architecture's path forward: (a)
successful Novo-Nordisk branded-GLP-1 distribution + category-diversification (testosterone,
peptides, dermatology, mental health) → architecture continues with substrate-shifted GLP-1
upstream; (b) failure to absorb compounded-GLP-1 revenue change → revenue + profit pressure.

### Cross-architecture patterns + Sub-pattern classification

Hims & Hers contributes structurally to the architectural-discipline-as-asset cross-corpus
pattern (#6) via G6 (pre-emptive-strategic-architecture — April 2024 partnership
pre-announcement). This is a new flavor: anticipatory-strategic-positioning-as-discipline
distinct from corporate-structure-discipline (Stripe), founding-doctrine-discipline (TSMC),
permanent-capital-discipline (Berkshire), long-tenure-CEO-discipline (JPM Dimon). Pattern #6
now at 13 instances with substantially diversified mechanism set.

Architecture is also a candidate for Sub-pattern D-adjacent classification (operator-voluntary
architectural-substrate-transition), but architecturally less dramatic than Berkshire 1965 —
the flow continues unchanged, only one input layer shifts. Closer to operator-anticipated-
regulatory-substrate-response than to architectural-abandonment. Documented but not promoted
to Sub-pattern D status. Sub-pattern D remains v1.5 candidate at single Berkshire instance.

Architecture-survival-via-radical-restructuring pattern (#9) at candidate-position via
voluntary-pre-emptive transition rather than crisis-driven restructuring; doesn't yet qualify
as full instance.

**Audit:** 46E / 13I / 7C / 0U / 66 fields total.
