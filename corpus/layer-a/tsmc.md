
# TSMC

## Research Summary

Verified primary facts as of May 2026: Taiwan Semiconductor Manufacturing Company founded 1987 by Morris Chang as government-backed JV with Philips (Taiwan ITRI initial backing); NYSE listing 1994. Q4 FY2025 revenue NT$1.0T (+20.5% YoY); Q1 FY2026 guidance US$34.6-35.8B; advanced nodes (7nm and below) = 77% of Q4 wafer revenue. Holds ~71% pure-play foundry market share Q2 2025 and produces ~90% of world's most advanced chips. Market cap ~$1.5T (2026); ~85K employees globally.

Critical force-topology updates training data would miss: (1) N2 (2nm) entered high-volume manufacturing Q4 2025 with good yield, fast ramp through 2026; N2P + A16 volume production scheduled H2 2026; A16 features Super Power Rail (SPR) targeting HPC products. (2) N2 already has 70+ customer tape-outs in pipeline, "strongest ever customer adoption." (3) March 2025: Trump + CEO C.C. Wei jointly announced additional $100B US investment (on top of prior $65B) for ~$165B total Arizona commitment; Arizona Fab 21 in N4 volume production since late 2024 with confirmed Apple + Nvidia customers; Arizona Fab 2 equipment install summer 2026, 3nm production 2027; Arizona 2nm volume production not until ~2030; up to 12 Arizona fabs planned long-term. (4) Japan + Germany expansions stalled while Arizona accelerates. (5) PLA air-defense-zone incursions 200+/month 2025 vs <10/month 2020; Bloomberg Economics estimates Taiwan conflict at ~$10T global cost (~10% world GDP). (6) Samsung Foundry (~7% share) struggling with yields; Intel Foundry now testing with NVIDIA + Google for I/O dies and special-purpose silicon but not leading-edge logic; Apple + Qualcomm diversifying lower-end production while keeping flagships at TSMC.

## Canonical Record

```yaml
- id: tsmc
  name: TSMC (Taiwan Semiconductor Manufacturing Company)
  era: 1987-present
  industry: semiconductors/foundry
  status: [E] operating-durable / strengthening-short-term / contested-long-term-via-geopolitical-and-customer-concentration-risk
  scale: [E] rev-~$90-100B-fy2025-(NT$3.4T-est) / ~$36B-quarterly-run-rate-q1-2026 / ~71%-pure-play-foundry-share / ~90%-of-world's-most-advanced-logic / ~$1.5T-market-cap-2026 / ~85k-employees
  scope: [E] foundry-wafer-fabrication-business / includes-advanced-packaging-(cowos-soic-3dfabric) / excludes-osat-(ase-amkor-still-separate) / excludes-equipment-suppliers-(asml-amat-lam-kla) / excludes-customer-design-services-(value-chain-deliberately-clean)

  flow:
    primary: [E] customer-chip-designs->wafer-fabrication->fabbed-wafers-back-to-customer-for-osat / tsmc-occupies-fab-position-only-in-design->fab->osat->oem->end-user-chain
    rate: [E] ~14-15M-12-inch-equivalent-wafer-starts-per-year-capacity / continuous-24x7-fab-operation / decadal-node-refresh-cycle / 70+-customer-tape-outs-pipeline-for-N2
    direction: [E] tsmc-at-fab-position / fabless-designers-upstream-paying-customers / osat-+-customer-assembly-downstream / not-a-rent-collector-on-end-product-margin
    recurrence: [E] product-cycle-based-with-customer-roadmap-driven-recurrence / engineered-multi-year-capacity-commitments-with-prepayments / inherent-recurrence-from-end-product-refresh-cycles-(iphone-annual-gpu-2yr-etc)
    secondary: [E] advanced-packaging-flow-(cowos-soic)-now-load-bearing-for-ai-accelerators / capacity-allocation-as-non-monetary-flow-(rationing-is-power) / pdk-+-design-library-flow-back-to-customers / yield-+-process-data-internal-asymmetry-flow

  position:
    description: [E] pure-play-foundry / manufacturing-only-no-chip-design / deliberate-non-competition-with-customers-as-founding-doctrine / capability-asymmetry-dominant-architecture-with-customers-locked-via-process-design-kit-investment / now-also-advanced-packaging-leader
    upstream: [E] equipment-suppliers-asml(EUV-monopoly)+applied-materials+kla+lam-research+tokyo-electron / chemical-+-wafer-+-gas-suppliers-shin-etsu+sumco / EUV-+-DUV-photomask-makers / industrial-power-+-water-supply-taiwan-specific
    downstream: [E] fabless-designers-as-paying-customers / apple-~25%-largest / nvidia-~20%+ / amd-qualcomm-broadcom-mediatek-marvell-each-significant / osats-ase-amkor-for-non-tsmc-packaging / customer-direct-products-then-flow-to-oems-and-end-users
    scarcity-supply: [E] extreme-at-leading-edge / only-tsmc-at-N2-volume-production-2026 / samsung-foundry-trailing-with-yield-issues / intel-foundry-not-yet-volume-at-leading-edge-+-customer-trust-gap / no-credible-alternative-for-advanced-AI-compute-volumes / mid-trailing-nodes-(28nm+)-competitive-with-multiple-foundries
    substitutability-flow: [E] very-low-at-leading-edge / no-substrate-substitute-for-silicon-CMOS-for-advanced-logic-at-scale / [C] increasing-substitutability-at-mid-trailing-nodes-via-china-smic-+-globalfoundries-+-umc / advanced-packaging-also-substitutable-only-with-tsmc-or-emerging-intel-foveros-samsung-x-cube

  counterparty:
    types: [fabless-chip-designers(top-10-~70-80%-of-revenue), equipment-suppliers-concentrated(asml-amat-kla-lam-tel), materials-suppliers-(wafers-gases-chemicals-photomasks), osats-downstream(ase-amkor-spil), end-customers-+-oems-(indirect-via-fabless), governments-multiple(taiwan-strategic-asset-+-us-chips-act-+-eu-chips-act-+-jp-meti-+-german-fed-saxony-+-china-export-control-actor), hyperscaler-direct-customers-emerging-(amazon-google-microsoft-meta-custom-silicon), defense-+-national-security-customers-(implicit-via-customer-products), pla-as-adversarial-state-actor-with-blockade-rehearsal-pattern]
    concentration: [E] customers-extremely-concentrated-top-10-~70-80% / apple-~25%-largest-single / nvidia-~20%+-and-rising-with-ai / equipment-suppliers-asml-monopolistic-on-EUV / governments-each-significant-individually
    relationship: [E] multi-year-capacity-commitments-with-prepayments / joint-roadmap-planning-2-3-cycles-out / deep-pdk-+-library-co-investment / pure-play-discipline-as-relationship-contract-(no-design-competition) / governments-strategic-multi-billion-dollar-incentives-+-policy-constraints
    pricing: [E] tiered-per-wafer-by-node-+-volume-+-customer / leading-edge-(N2-N3-N4)-premium-priced / mid-trailing-competitive-with-other-foundries / advanced-packaging-(cowos-soic)-capacity-constrained-and-premium-priced-2024-26 / volume-tier-discounts-+-prepayment-discounts
    info-asymmetry: [E] tsmc-knows-aggregate-customer-roadmap-+-allocation-+-yield-data / customers-know-own-designs-but-not-each-others' / tsmc-publishes-deliberately-less-than-financial-disclosure-minimum-on-customer-specific-allocation / equipment-suppliers-know-process-mix-but-not-product-mix

  economics:
    revenue-source: [E] wafer-fabrication-fees-per-wafer-by-node-mix / advanced-packaging-fees-(cowos-soic)-growing-fast / royalty-+-NRE-engineering-services-modest-fraction / no-product-end-margin-revenue-(deliberate-pure-play)
    unit: [E] very-high-gross-margin-at-leading-edge-(~50%+-corporate-gross-margin-q4-25) / commodity-margins-at-trailing-nodes / advanced-packaging-margin-improving-with-cowos-capacity-constraint / scale-economies-substantial-but-capex-burden-growing
    cost-structure: [E] extreme-fixed-cost-via-fab-capex-($20-30B-per-leading-edge-fab) / EUV-machines-$200M+-each / r&d-spend-~$6-7B/yr / depreciation-large-fraction-of-cogs / variable-materials-+-power-+-labor-modest-fraction-at-leading-edge / capex-FY2025-~$40B-+-FY2026-guide-similar-+-arizona-$165B-multi-year
    capital: [E] public-NYSE-1994-+-TWSE / retained-earnings-+-equity-+-modest-debt / sovereign-strategic-co-investment-via-chips-act-(us-$6.6B-direct-+-eu-+-jp-meti) / capex-largest-financial-question / dividend-payer
    margin-trajectory: [E] improving-structurally-with-advanced-node-mix-shift / [C] arizona-+-japan-+-germany-fab-costs-pressuring-margins-2025-2030 / [I] AI-demand-+-capacity-constraint-supports-pricing-power

  dynamics:
    acquisition: [E] multi-year-customer-development-cycles / PDK-+-design-library-investment-by-customers / capacity-reservation-with-prepayment-+-NRE-fees / joint-roadmap-engagement-for-leading-edge-customers / not-acquisition-marketing-not-channels
    retention: [E] extremely-high / customer-designs-tied-to-tsmc-process-design-kit-(pdk) / port-to-different-foundry-requires-physical-redesign-($100M+-per-chip) / multi-year-migration-typical / advanced-packaging-(cowos-soic)-adds-second-layer-of-lock-in / customer-roadmap-+-tsmc-roadmap-jointly-planned
    exit: [E] very-high-friction-at-leading-edge / lower-at-mid-trailing-nodes-(28nm+-multi-foundry-portability-easier) / customer-multi-sourcing-strategy-(apple-qualcomm)-targets-mid-tier-not-flagship
    info-capture: [E] aggregate-customer-roadmap-data / yield-+-process-optimization-decades-of-cumulative-data / equipment-utilization-+-supplier-performance-data / aggregate-end-product-demand-signal-via-tape-out-mix
    info-disclosure: [E] public-quarterly-filings-+-investor-conferences / tech-symposium-roadmap-disclosure-annually / deliberately-non-disclosure-on-customer-specific-allocation / chips-act-+-government-grants-require-supplementary-disclosure

  competitive:
    direct: [E] samsung-foundry-~7%-share-yield-+-customer-trust-gap / globalfoundries-mature-nodes-only-since-2018-exit-from-leading-edge / smic-china-restricted-by-us-export-controls-to-7nm-and-trailing / umc-mature-nodes / intel-foundry-attempting-to-enter-but-yield-+-customer-trust-gap-+-still-an-idm
    indirect: [E] customer-in-housing-attempts-historically-failed-at-leading-edge / chiplet-+-advanced-packaging-where-tsmc-also-leads / alternative-compute-substrates-(quantum-+-photonic-+-analog)-still-research / RISC-V-+-arm-+-x86-architecture-shifts-do-not-substitute-foundry-position
    response-patterns: [E] tsmc-historically-out-executed-on-process-node-transitions-+-yield-ramp / pure-play-discipline-protected-customer-trust-vs-samsung-IDM-conflict / [E] customer-diversification-pressure-2024-26-met-with-multi-region-fab-expansion-not-architectural-change / [I] capacity-constraint-allows-pricing-power-not-typically-deployed-by-tsmc
    regulatory: [E] heavy-+-strategic / us-chips-act-$6.6B-direct-grants-+-loan-commitments / eu-chips-act-+-german-saxony / japan-meti-kumamoto-fab-support / taiwan-as-strategic-national-asset-+-tsmc-protected-status / china-export-controls-on-leading-edge-tools-+-customers / us-export-controls-on-china-sales-(restricted-customers-since-2022)
    adversarial: [E] pla-blockade-+-invasion-rehearsal-cadence-200+/month-air-incursions / china-cyber-+-industrial-espionage-historical / us-political-pressure-for-onshoring-(both-administrations-2017-2026) / customer-diversification-pressure-creating-multi-foundry-strategy-among-fabless-(apple-qualcomm-amd-google-amazon-microsoft-evaluating-samsung-+-intel-foundry)

  forces-emergence:
    - id: F1
      description: [E] morris-chang-founder-+-itri-government-backing-1987 / taiwan-government-strategic-semiconductor-investment-with-philips-as-jv-partner-funding-+-technology-transfer
      status-now: closed / now-substrate-only-not-driver
    - id: F2
      description: [E] fabless-design-model-emerging-mid-1980s / lsi-logic-+-xilinx-+-altera-+-early-fabless-creating-the-customer-set-foundry-model-requires
      status-now: closed-as-emergence-force-but-its-mature-version-is-G7-now / fabless-set-now-the-dominant-chip-industry-form-+-tsmc's-existence-validated-the-model-recursively
    - id: F3
      description: [E] taiwan-engineering-labor-cost-+-quality-combination-1980s-90s / process-engineer-supply-from-taiwan-universities-+-returnee-engineers-from-us-tsmc-+-intel-+-bell-labs
      status-now: closed-as-emergence-force / labor-cost-no-longer-differentiating-vs-arizona-+-japan / quality-+-cumulative-expertise-promoted-to-G4
    - id: F4
      description: [E] geographic-clustering-in-hsinchu-+-tainan-science-parks / supplier-+-talent-+-customer-+-academia-co-location-creating-network-density-for-rapid-iteration
      status-now: active-durable-but-being-replicated-via-arizona-+-kumamoto-+-dresden-(stalling) / geographic-monopoly-feature-eroding-by-tsmc-itself
    - id: F5
      description: [E] pure-play-discipline-as-founding-doctrine / morris-chang's-explicit-no-competition-with-customers / created-trust-substrate-fabless-designers-could-not-get-from-IDM-foundries-(ibm-intel-samsung-historically)
      status-now: active-strengthening / promoted-effectively-to-architectural-invariant / accumulated-into-G2-customer-trust

  forces-accumulated:
    - id: G1
      description: [E] cumulative-process-technology-lead-+-execution-discipline / decades-of-node-shrink-yield-ramp-+-EUV-deployment-mastery / surpassed-intel-leadership-by-~2017 / now-1-2-nodes-ahead-of-samsung-+-2-3-nodes-ahead-of-intel
      since: 1996-onward-continuous-with-step-function-at-2017
      status-now: active-strengthening / N2-HVM-Q4-2025-+-A16-H2-2026-extending-lead
    - id: G2
      description: [E] customer-trust-+-pdk-+-design-library-co-investment / customers-treat-tsmc-process-as-design-target-with-no-foundry-design-conflict-risk / decade-scale-cumulative-relationship-equity / pure-play-discipline-(F5)-accumulated-into-relational-asset
      since: 1990s-continuous
      status-now: active-durable / [C] under-pressure-from-customer-diversification-strategies-2024-26-but-leading-edge-still-tsmc-only
    - id: G3
      description: [E] equipment-supplier-preferential-access / asml-EUV-first-call-+-amat-+-kla-+-lam-deep-integration / tool-customization-+-process-co-development-+-yield-acceleration-via-supplier-engineering
      since: 2010s-onward-with-EUV-buildout
      status-now: active-strengthening / high-NA-EUV-deployment-2024-2026-extending-tool-asymmetry
    - id: G4
      description: [E] hsinchu-+-tainan-cluster-talent-depth / ~85k-employees-with-deep-process-engineering-+-yield-engineering-+-manufacturing-discipline / multi-decadal-engineering-knowledge-base-not-replicable-without-decade-scale-investment
      since: 1990s-onward
      status-now: active-durable / [C] partial-replication-attempts-arizona-+-kumamoto-+-dresden-with-mixed-progress-+-talent-transfer-required
    - id: G5
      description: [E] advanced-packaging-position-(cowos-soic-3dfabric) / cowos-now-the-bottleneck-for-ai-accelerator-supply-(nvidia-h100-h200-b100-b200-+-amd-mi300-+-google-tpu) / soic-for-apple-+-amd-3d / non-substitutable-for-leading-edge-AI-compute
      since: 2020s-with-step-function-at-AI-demand-surge-2023-onward
      status-now: active-strengthening / capacity-constraint-binding-+-pricing-power-not-yet-fully-deployed
    - id: G6
      description: [E] sovereign-strategic-significance / silicon-shield-+-us-chips-act-+-eu-chips-act-+-jp-meti-+-german-saxony / multiple-governments-co-invested-in-tsmc-continuity / political-coalition-against-disruption / [C] also-makes-tsmc-target-of-state-adversary-action
      since: ~2015-onward-strengthening-rapidly-2022-2026-with-AI-+-china-pressure
      status-now: active-strengthening / [C] double-edged-as-target-also-becomes-more-attractive
    - id: G7
      description: [E] AI-workload-dependency-accumulation / nearly-all-frontier-AI-compute-(nvidia-+-google-tpu-+-anthropic-+-microsoft-+-meta-+-amazon-trainium-+-tesla-dojo)-routes-through-tsmc-leading-edge-+-cowos / AI-buildout-2023-2026-converted-tsmc-from-strategic-to-load-bearing-for-frontier-AI-civilization-stack
      since: 2023-with-AI-buildout-onset / accelerating-2024-2026
      status-now: active-strengthening-most-aggressively / now-the-largest-single-customer-class-driver
    - id: G8
      description: [E] capex-+-execution-scale-barrier / ~$40B/yr-capex-+-multi-year-fab-timelines-+-EUV-machine-supply-constraints-mean-any-credible-leading-edge-competitor-needs-decade-+-$100B+-commitment / globalfoundries-2018-exit-illustrates-the-cliff-magnitude / intel-+-samsung-have-attempted-and-trail
      since: 2010s-onward / step-function-at-EUV-era-2018-2020
      status-now: active-strengthening / capex-cliff-rising-with-each-node

  evolution: [E] 1987-tsmc-founded-as-itri+philips-jv-+-morris-chang-ceo / 1994-NYSE-listing / 1996-2000-0.35um-+-0.25um-process-leadership-emergence-for-foundry-pure-play / 2000s-catch-up-to-intel-at-advanced-nodes / 2010-2017-progressive-execution-lead-over-intel-+-samsung / ~2017-step-function-as-intel-stumbles-on-10nm-(years-of-delay) / 2018-7nm-HVM-with-EUV-pilot / 2020-5nm-volume-(apple-a14-bionic-+-nvidia-data-center) / 2022-3nm-(N3)-volume-(apple-a17-pro) / 2023-AI-demand-step-change-via-cowos-capacity-constraint / 2024-N3E-mature-+-arizona-fab-21-N4-volume-+-japan-kumamoto-fab-online / Q4-2025-N2-HVM-good-yield / nov-2024-trump-+-CC-wei-additional-$100B-arizona-commitment-($165B-total) / Q1-2026-N2-fast-ramp-+-N2P-+-A16-volume-H2-2026 / arizona-fab-2-tool-install-summer-2026 / japan-+-germany-stalled-while-arizona-accelerates

  closing-conditions: [E] PLA-blockade-or-invasion-of-taiwan-(probability-non-trivial-given-2025-2026-incursion-cadence) / [I] severe-multi-year-arizona-ramp-failure-combined-with-china-pressure / [I] customer-coalition-shifts-significant-leading-edge-volume-to-intel-foundry-or-samsung-foundry-via-yield-+-price-+-geographic-pressure / [I] alternative-compute-substrate-(photonic-quantum-analog)-bypasses-silicon-CMOS-(low-probability-current-decade) / [I] export-control-escalation-restricting-customer-base / [I] geopolitical-de-globalization-forcing-multi-region-fab-strategy-+-margin-compression / [E] morris-chang-+-CC-wei-+-founding-discipline-cultural-loss-as-organization-grows-and-geographically-distributes

  trajectory: [E] durable / [E] strengthening-short-term-via-AI-demand-+-N2-ramp / [C] contested-long-term-via-geopolitical-+-customer-concentration-risk / current-financial-trajectory-+25%-revenue-fy2025-with-AI-tailwind-projected-through-fy2026-+-N2-ramp

  negative-pairs:
    - id: globalfoundries-2018-exit
      name: GlobalFoundries (advanced-node ambition era 2009-2018)
      era: 2009-2018-(relevant-comparator-window-for-leading-edge-pursuit-then-exit)
      similarity: [E] pure-play-foundry-business-model / same-decade-pursuing-same-customers-(amd-spinoff-origin-then-broader-fabless-set) / same-equipment-suppliers-+-similar-architectural-position / serious-leading-edge-7nm-program-2015-2018 / multi-billion-dollar-capex-commitments-+-emirati-sovereign-financing
      differential: [E] sub-scale-customer-base-at-leading-edge / smaller-r&d-+-capex-budget / yield-execution-lag-vs-tsmc / sovereign-financing-(mubadala)-with-less-strategic-tolerance-for-long-payback / august-2018-announced-indefinite-suspension-of-7nm-program-+-pivot-to-mature-+-specialty-nodes
      diagnosis: [E] capex-+-execution-scale-cliff-(G8)-was-the-decisive-failure-mode / GF-could-not-match-tsmc's-cumulative-process-lead-(G1)-+-customer-trust-(G2)-+-equipment-access-(G3)-+-talent-depth-(G4)-simultaneously / faced-choice-of-multi-year-multi-$10B-investment-with-uncertain-payback-or-exit / chose-exit
      reveals: [E] subject's-load-bearing-feature-is-the-COMBINED-accumulation-of-G1-G8-not-any-single-one / a-competent-+-well-financed-pure-play-foundry-failed-at-the-leading-edge-not-because-it-lacked-any-single-capability-but-because-the-cumulative-execution-discipline-+-customer-trust-+-equipment-access-+-talent-+-capex-could-not-be-replicated-on-decade-shorter-timeline / explains-why-no-new-leading-edge-foundry-entrant-since-1990s-+-why-intel-foundry-effort-faces-similar-cliff
    - id: intel-IDM-leadership-loss
      name: Intel (IDM advanced-process-leadership era 1990s-2014, leadership-loss era 2014-2024)
      era: 1990s-2024-(relevant-comparator-window-for-process-leadership-loss-+-foundry-attempt)
      similarity: [E] advanced-semiconductor-manufacturing-at-comparable-historical-scale-(intel-larger-revenue-than-tsmc-2010s) / equivalent-r&d-budget-+-equipment-supplier-access-historically / process-technology-leadership-1990s-2010s-then-lost-2014-onward-with-10nm-delays / attempted-foundry-pivot-2021-onward-with-IFS / similar-AI-demand-tailwind-availability-2023-26
      differential: [E] IDM-model-with-internal-design-+-fab-coupling-+-x86-cpu-as-flagship-internal-product / customer-trust-gap-vs-pure-play-(potential-foundry-customers-fear-design-information-leakage-or-priority-conflict-with-intel-cpu-line) / weaker-EUV-deployment-execution-than-tsmc / multiple-CEO-changes-+-strategic-resets-2018-2024 / no-cumulative-equivalent-of-G2-customer-trust-+-G5-advanced-packaging-customer-base
    
      diagnosis: [E] IDM-business-model-(F5-anti-thesis)-prevented-the-customer-trust-accumulation-that-pure-play-discipline-creates / intel-could-not-credibly-promise-non-competition-with-fabless-customers-when-intel-itself-is-a-major-chip-designer / process-leadership-loss-2014-2017-was-execution-failure-but-recovery-as-foundry-faced-structural-obstacle-beyond-execution / 2025-attempt-to-spin-off-IFS-or-partner-acknowledges-the-architectural-constraint
      reveals: [E] subject's-load-bearing-feature-is-the-pure-play-discipline-(F5-promoted-to-G2-trust)-as-much-as-the-process-technology-(G1) / process-leadership-alone-is-insufficient-to-be-the-foundry-(intel-had-it-in-2000s-and-could-not-convert) / pure-play-discipline-is-not-a-business-policy-it-is-an-architectural-invariant-that-took-decades-to-accumulate-into-customer-trust / intel-IDM-trying-to-add-foundry-without-restructuring-the-IDM-conflicts-illustrates-how-architecturally-load-bearing-the-non-competition-with-customers-feature-is

  audit: 56E / 9I / 7C / 0U / 72-fields

  notes: |
    TSMC tests the v1.3 schema's handling of a capability-asymmetry-
    dominant architecture at scale with significant current geopolitical
    overlay. Schema accommodated cleanly with no stress observed,
    in contrast to the kodak-film defunct-as-subject test.

    Two structural observations worth surfacing for cross-corpus
    pattern-finding:

    (1) The F5 → G2 promotion pattern. Morris Chang's founding
    "pure-play discipline" is structurally an emergence-era doctrine
    that compounded into accumulated customer trust (G2) over four
    decades. The Intel negative pair reveals this is not a business
    policy but an architectural invariant: a credible promise of
    non-competition with customers cannot be retrofitted onto an
    IDM. This is analogous to bloomberg's F-G structure where
    1988-1990 strategic moves (still-emergence-era) built G1+G3
    that now do the durability work. The pattern: certain founding
    doctrines accumulate into structural assets that cannot be
    replicated except via decade-scale accumulation by competitors.

    (2) Sovereign-strategic significance (G6) is partially
    self-protective and partially self-targeting. The silicon shield
    is the rent + protection equilibrium that TSMC currently
    operates within. The same feature that protects (multiple
    governments invested in TSMC continuity) also concentrates
    strategic vulnerability (TSMC is a target precisely because
    it is critical). This is a structural feature the schema does
    not have explicit vocabulary for — "load-bearing for civilization
    stack" creates both protective and attractive force-topology
    elements simultaneously. Not a schema gap, just a structural
    observation worth surfacing.

    (3) AI-workload dependency (G7) emerged in just ~3 years
    (2023-2026) and is now the largest single demand driver.
    The schema's `since` field captured this cleanly. This is
    one of the fastest accumulated-force build-outs in the corpus
    so far — instructive contrast vs bloomberg's G1 chat network
    which took ~15 years to build.

    Layer C invariants applied:
    - Competitive Response (Invariant 2): GlobalFoundries 2018
      exit and Intel Foundry struggles illustrate the
      capability-asymmetry barrier; sub-attention-threshold
      strategy not applicable because TSMC operates at maximum
      visibility but capex+execution barrier substitutes
    - Resource Constraints (Invariant 4): ~$40B/yr capex + EUV
      machine supply constraint + decade-scale talent
      accumulation are the resource bound that GlobalFoundries
      hit at the cliff; TSMC clears it by having decades of
      cumulative resource deployment that compounds rather than
      depletes
    - Information Dynamics (Invariant 5): customer roadmap +
      yield + equipment optimization data accumulates faster
      than competitors can replicate because TSMC operates at
      larger leading-edge volume; replenishment-by-operation
      pattern analogous to bloomberg's G3 data archive
    - Time Consistency (Invariant 6): pure-play discipline (F5
      → G2) is the central time-consistency play; 40 years of
      credible non-competition with customers is the asset
      that intel-IDM-becoming-foundry cannot retrofit / a
      single visible defection (TSMC entering chip design)
      would compress G2 rapidly given asymmetric build-vs-decay
      dynamic

    Layer A status: Section A schema-validation entry, decomposed
    May 2026 — tests capability-asymmetry-dominant architecture +
    AI-era critical-infrastructure profile. No schema stress
    observed; schema handles cleanly.
```

## Prose Synthesis

**Identification:** TSMC is the pure-play semiconductor foundry founded 1987 by Morris Chang as Taiwan ITRI + Philips joint venture, listed NYSE 1994, with ~$90-100B FY2025 revenue, ~71% pure-play foundry market share, ~90% of world's most advanced chips, and ~$1.5T market cap (2026). Entry scope is the foundry wafer-fabrication business including TSMC's advanced packaging (CoWoS, SoIC, 3DFabric); excludes OSATs (ASE, Amkor), equipment suppliers (ASML et al.), and customer design services (deliberately not occupied per founding doctrine).

**Structural position:** TSMC occupies the wafer-fabrication position in the design→fab→OSAT→OEM→end-user chain, with a capability-asymmetry-dominant architecture characterized by extreme supply-side scarcity at leading-edge (only TSMC at N2 volume production 2026, Samsung trailing with yield issues, Intel Foundry not yet volume at leading edge with customer trust gap) and very low flow-side substitutability for advanced AI compute. The position is reinforced by pure-play discipline (no competition with customer designs) and by advanced packaging dominance (CoWoS) which is now the structural bottleneck for AI accelerator supply (NVIDIA H/B-series, AMD MI300, Google TPU, hyperscaler custom silicon).

**Force-topology dependence:** All five emergence forces (F1-F5: Morris Chang + ITRI government backing, fabless-model emergence, Taiwan labor cost + quality, Hsinchu clustering, pure-play discipline) are closed as emergence drivers but F4 and F5 promoted to accumulated forces. Eight accumulated forces (G1-G8: cumulative process-tech lead, customer trust + PDK lock-in, equipment-supplier preferential access, Hsinchu talent depth, advanced packaging position, sovereign-strategic significance, AI-workload dependency, capex+execution scale barrier) are all active. G7 (AI workload dependency) accumulated in just ~3 years 2023-2026 and is now the largest single demand driver. Closing conditions are primarily geopolitical: PLA blockade or invasion (probability non-trivial given 2025-26 incursion cadence of 200+/month), severe Arizona ramp failure combined with China pressure, customer coalition shift to alternative foundries, and alternative compute substrate emergence (low probability current decade). Trajectory: durable / strengthening short-term / contested long-term via geopolitics.

**Negative-pair insights:** GlobalFoundries (2009-2018 leading-edge pursuit then 2018 exit) illustrates the capex + execution scale cliff — a well-financed pure-play foundry with sovereign backing could not match TSMC's cumulative G1+G2+G3+G4 simultaneously and chose exit. Intel (1990s-2024 process leadership loss + foundry pivot attempt) illustrates that the pure-play discipline (F5 → G2 customer trust) is not a business policy but an architectural invariant: process leadership alone is insufficient to be the foundry, because IDM-conflict-with-customers cannot credibly promise non-competition. Together they reveal that TSMC's load-bearing feature is the COMBINED accumulation across G1-G8, not any single capability — a decade-scale architectural lock that competitors cannot replicate on shorter timelines, structurally analogous to Bloomberg's G1+G2+G3+G4 layered composition that Telerate and Quotron each occupied subsets of and failed.

**Epistemic profile:** Strong evidence base (56 [E] / 9 [I] / 7 [C] / 0 [U] across 72 fields). Contested fields are forward-looking: Arizona/Japan/Germany ramp execution, customer diversification trajectory under AI-era capacity constraint, geopolitical outcome distributions, and sovereign-strategic G6 net effect as protective vs targeting. Zero [U] fields — TSMC is extensively documented via public-company quarterly filings, annual tech symposiums, and ~$10T-scale strategic analyst coverage. Entry is high-confidence for descriptive structural mechanics and current force topology; lower-confidence for ten-year forward trajectory specifics given the unusual combination of strong short-term tailwinds and meaningful long-term geopolitical tail risk.
