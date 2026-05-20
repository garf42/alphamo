
# SWIFT Network

## Research Summary

Verified primary facts as of May 2026: Society for Worldwide Interbank Financial Telecommunication (SWIFT) founded May 1973 in Belgium as cooperative response to US-led First National City Bank's proprietary "MARTI" system; co-owned by ~11,500 member institutions across 200+ countries managed by 25-director board; shareholding reapportioned every 3 years based on messaging volume. Headquartered La Hulpe, Belgium. ~44 million messages/day; ~$5 trillion daily funds-movement value communicated through the network. Cooperative governance — does not transmit money, only messaging — clearing and settlement happens via correspondent banking relationships or local clearing systems.

Critical force-topology updates training data would miss: (1) ISO 20022 cutover complete November 22, 2025 — MT messaging legacy retired for cross-border payments; only ISO 20022 MX format accepted via FINplus Service; 20-year migration promise fulfilled. (2) Russia disconnection precedent (Feb 26, 2022 + June 2022) — 7 major Russian banks plus Sberbank cut off representing ~1-1.5% of SWIFT daily traffic and $700-800B annual cross-border flows; accelerated Russia's SPFS expansion (now 550+ institutions across 24 countries) and integration with China CIPS. (3) Multipolar fragmentation accelerating — CIPS (China) actually clears + settles unlike SWIFT messaging-only, but 80% of CIPS payments still use SWIFT messaging; mBridge CBDC network (China, UAE, Hong Kong, Thailand, Saudi Arabia) now moving ~$55B with 15-second settlement bypassing SWIFT entirely; with Indian BRICS+ presidency 2026 and Russian digital ruble launch, mBridge positioned as parallel-architecture rail. (4) US dollar still ~50% of SWIFT transaction value early 2025, euro ~23%, yuan <4%, but de-dollarization trend accelerating. (5) June 2026 milestone — SWIFT discontinuing legacy Alliance Access Integration Platform (IPLA) and SWIFT Integration Layer (SIL) middleware.

## Canonical Record

```yaml
- id: swift-network
  name: SWIFT (Society for Worldwide Interbank Financial Telecommunication)
  era: 1973-present
  industry: payments/messaging/financial-infrastructure
  status: [E] operating-durable / [C] under-multipolar-fragmentation-pressure-2022-onward / [E] cooperative-governance-distinguishes-from-investor-owned-payment-networks
  scale: [E] ~11,500-member-institutions / ~200+-countries / ~44M-messages/day / ~$5T-daily-funds-movement-value-communicated / cooperative-co-owned-not-profit-maximizing
  scope: [E] financial-messaging-cooperative-infrastructure / cross-border-+-domestic-bank-to-bank-+-securities-+-treasury-messaging / explicitly-excludes-clearing-+-settlement-(messaging-only-distinction)

  flow:
    primary: [E] standardized-financial-messages-between-member-institutions / bank-to-bank-payment-instructions-+-treasury-+-securities-+-trade-finance-+-confirmations / SWIFT-as-messaging-rail-not-money-rail
    rate: [E] ~44M-messages/day / ~16B-messages/year / ~$5T-equivalent-funds-flow-instruction-value-daily / continuous-realtime
    direction: [E] swift-at-messaging-layer-position / clearing-+-settlement-happens-via-correspondent-banking-or-domestic-clearing-systems-(chips-target2-etc) / swift-orchestrates-information-flow-not-value-flow
    recurrence: [E] inherent-recurrence-on-bank-cross-border-+-treasury-+-securities-activity / messaging-volume-grows-with-global-trade-+-finance-activity
    secondary: [E] messaging-standards-(ISO-15022-+-ISO-20022-MX) / gpi-tracking-+-transparency-services / sanctions-screening-+-KYC-+-compliance-services / API-services-(emerging) / cross-border-payment-tracker-data

  position:
    description: [E] cooperative-standard-setter-+-messaging-utility / member-owned-not-investor-owned / utility-pricing-model-not-profit-maximizing / occupies-de-facto-standard-position-via-half-century-network-effect-+-iso-standards-process
    upstream: [E] member-banks-as-co-owners-+-message-senders / iso-standards-bodies / national-+-supranational-regulators-(eu-+-us-+-belgium-host)
    downstream: [E] member-banks-as-message-recipients / [E] same-entities-as-both-sender-+-recipient-+-owner-(cooperative-structure)
    scarcity-supply: [E] historically-very-high / 1-global-cooperative-messaging-standard / [E] 2014-2026-erosion-via-SPFS-(russia)-+-CIPS-(china)-+-mBridge-(BRICS+)-+-domestic-real-time-payment-systems-fragmenting-the-monolithic-position
    substitutability-flow: [E] very-low-historically / [C] increasing-2022-onward / SPFS-+-CIPS-now-substitute-for-russia-+-allied-flows / mBridge-+-CBDC-rails-substituting-for-non-aligned-flows / [E] geopolitical-fragmentation-is-the-active-substrate-shift-pressure

  counterparty:
    types: [member-banks-as-co-owners-(unusual-structure-customer-+-owner-+-counterparty-same), national-central-banks, supranational-regulators-(eu-+-us-treasury-via-ofac-+-uk-fcato), governments-as-sanctioning-actors-(g7-coalitions-+-bilateral), competitor-networks-(SPFS-+-CIPS-+-mBridge-+-domestic-rtps), ISO-standards-bodies, payment-system-operators-(target2-chips-fednow-domestic), technology-providers-(message-platform-vendors), security-+-resilience-counterparties-(after-2016-bangladesh-bank-heist)]
    concentration: [E] member-banks-concentrated-(top-100-handle-most-volume-but-cooperative-structure-distributes-control) / regulators-jurisdictionally-distributed-but-EU-+-belgium-host-+-US-treasury-most-significant / competitor-networks-emerging-+-fragmenting
    relationship: [E] cooperative-membership-with-volume-based-share-reapportioning-every-3-years / member-banks-pay-fees-+-receive-voting-+-economic-rights / regulator-relationships-quasi-utility-status / NOT-a-typical-vendor-customer-relationship-(membership-+-co-ownership-structure)
    pricing: [E] utility-pricing-not-profit-maximizing / per-message-fees-+-membership-fees / pricing-deliberately-low-relative-to-extractable-value / cooperative-structure-constrains-rent-extraction
    info-asymmetry: [E] swift-knows-aggregate-cross-border-flow-data / [E] this-data-asset-was-the-foundation-for-sanctions-enforcement-(post-9/11-terrorist-finance-tracking-program-via-swift-data-sharing-with-US) / [C] revealed-data-sharing-2006-controversy

  economics:
    revenue-source: [E] member-banks-pay-per-message-fees-+-annual-membership / utility-pricing-model-with-volume-tiers
    unit: [E] cooperative-structure-explicitly-NOT-profit-maximizing / surplus-rebated-or-reinvested-in-infrastructure / unit-economics-not-architecturally-relevant-the-way-they-are-for-investor-owned-payment-networks
    cost-structure: [E] heavy-fixed-cost-(messaging-infrastructure-+-security-+-resilience-+-compliance) / ~3,500-employees / capital-+-resilience-investment-largest-cost-categories
    capital: [E] cooperative-not-public-company / co-owned-by-member-banks / shareholding-reapportioned-every-3-years / governance-via-25-director-board / financing-via-member-fees-+-retained-surplus
    margin-trajectory: [E] not-applicable-cooperative-structure / utility-pricing-stable-historically / current-pressure-from-multipolar-fragmentation-+-cooperative-investment-needed-for-modernization-(ISO-20022-+-gpi-+-stablecoin-+-cbdc-integration)

  dynamics:
    acquisition: [E] cooperative-membership-via-bank-licensing-+-iso-9362-BIC-code-allocation / acquisition-is-essentially-default-for-any-bank-doing-cross-border-+-international-treasury-activity
    retention: [E] near-universal-bank-retention-historically / [E] retention-via-network-effect-(must-be-on-rail-other-banks-use)-+-messaging-standard-lock-in-+-cooperative-economic-alignment
    exit: [E] exits-typically-imposed-not-chosen-(2012-iran-+-2022-russia-disconnections-via-EU-political-decision) / voluntary-exit-essentially-zero-because-no-substitute-existed-pre-2014-+-limited-substitute-2022-onward
    info-capture: [E] half-century-of-cross-border-financial-flow-metadata / aggregate-bank-relationship-mapping / [C] used-for-sanctions-enforcement-since-2001-creating-tension-with-cooperative-neutrality
    info-disclosure: [E] cooperative-not-public-company-+-limited-financial-disclosure / regulatory-disclosure-required / [E] sanctions-cooperation-with-US-treasury-+-EU-via-terrorist-finance-tracking-program-since-2001-+-2006-controversy-when-disclosed

  competitive:
    direct: [E] SPFS-(russia-2014-onward-500+-institutions-24-countries) / CIPS-(china-2015-onward-but-80%-of-CIPS-still-uses-SWIFT-messaging-as-of-2025) / mBridge-(BRICS+-CBDC-network-china-uae-hong-kong-thailand-saudi-arabia-~$55B-volume-15-second-settlement) / SPFS-CIPS-integration-creating-russia-china-axis-rail
    indirect: [E] domestic-real-time-payment-systems-(fednow-rtp-sepa-instant-pix-upi)-substituting-for-cross-border-where-corridors-supported / stablecoin-+-bitcoin-+-crypto-rails-(emerging-but-still-marginal-at-bank-to-bank-scale) / CBDC-rails-emerging
    response-patterns: [E] swift-modernization-via-ISO-20022-cutover-nov-2025-+-gpi-tracking-services-+-cross-border-payment-improvement-program / [E] strategic-cooperation-with-CBDC-projects-+-stablecoin-issuers-rather-than-opposition / [I] cooperative-structure-+-utility-pricing-makes-rent-extraction-counter-attack-harder-than-investor-owned-network-competitors-face
    regulatory: [E] heavily-regulated-as-systemically-important-financial-market-infrastructure / belgian-regulatory-oversight-+-eu-+-G10-central-banks-cooperative-oversight-arrangement / us-treasury-+-eu-sanctions-leverage-via-host-jurisdiction-control / occasional-data-privacy-+-fundamental-rights-tension-(2006-controversy)
    adversarial: [E] state-actor-cyber-+-fraud-targeting-(2016-bangladesh-bank-$81M-heist-via-swift-credentials-+-multiple-subsequent-incidents) / sanctioned-+-non-aligned-countries-actively-building-alternatives / geopolitical-pressure-from-both-sides-(west-uses-as-sanctions-tool-east-builds-around)

  forces-emergence:
    - id: F1
      description: [E] 1973-cooperative-formation-as-defensive-response-to-first-national-city-bank's-proprietary-MARTI-system-attempt / coalition-of-non-US-banks-created-cooperative-to-prevent-private-network-capture-of-cross-border-messaging-substrate
      status-now: closed / cooperative-structure-now-architectural-feature-not-emergence-force
    - id: F2
      description: [E] mid-1970s-pre-electronic-cross-border-banking-relied-on-telex-+-postal-mail-+-bilateral-correspondent-relationships / emergence-of-need-for-standardized-electronic-messaging-substrate-for-rapidly-globalizing-banking
      status-now: closed / electronic-messaging-now-baseline-not-emerging
    - id: F3
      description: [E] cooperative-governance-+-utility-pricing-as-explicit-architectural-decision / made-network-attractive-to-rival-banks-who-would-not-cooperate-on-a-profit-maximizing-network-controlled-by-one-of-them
      status-now: closed-as-emergence / promoted-into-G3-cooperative-trust-asset
    - id: F4
      description: [E] iso-7775-+-15022-message-standards-process-1970s-1980s / created-shared-syntactic-substrate-no-bank-could-economically-deviate-from
      status-now: closed / standards-now-mature-+-evolving-via-ISO-20022
    - id: F5
      description: [E] 1980s-1990s-globalization-+-bretton-woods-2-era-cross-border-finance-explosion / created-network-effect-substrate-where-each-additional-member-bank-increased-value-to-all-others
      status-now: closed-as-emergence-+-promoted-into-G1-network-effect

  forces-accumulated:
    - id: G1
      description: [E] universal-bank-network-effect / ~11,500-members-+-near-universal-coverage-makes-non-membership-prohibitively-costly-for-any-bank-doing-cross-border / network-effect-+-standard-position-mutually-reinforcing
      since: 1980s-1990s-continuous
      status-now: active-durable / [C] under-multipolar-fragmentation-pressure-2022-onward-+-russia-disconnection-precedent
    - id: G2
      description: [E] de-facto-messaging-standard-position / ISO-15022-+-now-ISO-20022-mature-+-deeply-integrated-into-global-bank-payment-+-treasury-+-securities-systems / migration-cost-for-any-replacement-network-decade-+-billions
      since: 1980s-onward-with-step-function-at-ISO-20022-cutover-nov-2025
      status-now: active-strengthening / ISO-20022-mandatory-cutover-nov-22-2025-+-legacy-MT-retirement-deepens-lock-in
    - id: G3
      description: [E] cooperative-trust-asset / cooperative-structure-+-utility-pricing-+-neutrality-doctrine-historically-distinguished-from-investor-owned-rails / member-banks-trust-cooperative-not-to-extract-or-compete / [C] 2006-+-2022-controversies-(US-data-sharing-+-russia-disconnection-via-EU-political-pressure)-revealed-cooperative-neutrality-is-conditional-on-host-jurisdiction-+-G7-political-consensus
      since: 1973-continuous
      status-now: active-but-eroding / [C] cooperative-neutrality-no-longer-credible-to-non-aligned-+-sanctioned-states
    - id: G4
      description: [E] half-century-of-messaging-+-compliance-+-resilience-+-security-investment / continuous-replenishment-via-cooperative-investment / sanctions-screening-+-KYC-+-gpi-tracking-+-fraud-detection-services-accumulating
      since: 1973-continuous
      status-now: active-strengthening
    - id: G5
      description: [E] data-asset-cumulative-cross-border-flow-metadata / half-century-of-aggregate-bank-relationship-+-flow-data / [C] used-for-sanctions-+-AML-+-terrorist-finance-tracking-since-2001 / dual-use-asset-protective-+-targeting
      since: 1973-continuous
      status-now: active-but-politically-charged
    - id: G6
      description: [E] regulatory-+-central-bank-cooperative-oversight-arrangement / G10-central-banks-cooperative-oversight-+-belgian-financial-regulator-+-EU-+-US-treasury-relationships / formal-systemically-important-financial-market-infrastructure-status
      since: 1990s-onward-formalization
      status-now: active-durable
    - id: G7
      description: [E] G7-+-EU-political-coalition-using-SWIFT-as-sanctions-tool / 2012-iran-+-2022-russia-disconnections-demonstrated-+-formalized-this-power / cooperative-+-belgian-host-jurisdiction-constrained-to-comply-with-EU-political-decisions
      since: 2012-iran-precedent-onward-strengthening-2022-russia
      status-now: active-strengthening / [C] this-is-simultaneously-protective-(G7-political-coalition-supports-swift-continuity)-and-fragmenting-(non-aligned-states-actively-build-alternatives)

  evolution: [E] 1973-cooperative-formation-as-defensive-response-to-private-network-attempt / 1977-first-message-transmitted-between-belgium-+-amsterdam / 1980s-progressive-membership-expansion-+-iso-7775-+-15022-standards-+-globalization-tailwind / 1990s-near-universal-bank-coverage-+-securities-+-treasury-messaging-extension / 2001-9/11-terrorist-finance-tracking-program-cooperation-with-US-treasury / 2006-disclosure-controversy-+-cooperative-neutrality-tension-+-belgian-+-EU-data-privacy-pressure / 2012-iran-disconnection-as-sanctions-tool / 2014-russia-creates-SPFS-as-defensive-backup / 2015-china-creates-CIPS / 2016-bangladesh-bank-heist-+-subsequent-security-+-resilience-investment-cycle / 2017-gpi-tracking-services-launch / feb-2022-russia-disconnection-(7-banks-+-sberbank-later) / 2022-onward-multipolar-fragmentation-acceleration / 2023-2025-ISO-20022-progressive-migration / 2024-mBridge-CBDC-network-launch / nov-22-2025-ISO-20022-mandatory-cutover-complete / 2026-india-BRICS+-presidency-+-russian-digital-ruble-+-mBridge-positioning-as-parallel-rail / june-2026-IPLA-+-SIL-middleware-discontinuation

  closing-conditions: [I] multipolar-fragmentation-progresses-such-that-non-aligned-flows-route-via-mBridge-+-CIPS-+-SPFS-rather-than-SWIFT-eroding-G1-+-G2-+-G3 / [I] mBridge-+-CBDC-rails-mature-enough-to-substitute-not-just-supplement / [I] additional-major-sanctions-disconnection-event-(china-+-saudi-+-india-?)-confirming-non-neutrality-+-accelerating-defection / [I] technological-substrate-shift-blockchain-+-stablecoin-rails-making-cooperative-messaging-substrate-obsolete / [E] short-term-G1-+-G2-still-decisively-load-bearing-but-long-term-decade+-trajectory-uncertain

  trajectory: [E] mature-durable-in-short-term / [C] long-term-multipolar-fragmentation-+-substrate-shift-pressure-2022-onward / current-financial-trajectory-stable-but-strategic-trajectory-actively-contested

  negative-pairs:
    - id: marti-1973-attempt
      name: MARTI (First National City Bank's proprietary cross-border messaging attempt)
      era: ~1970-1973-(pre-SWIFT-emergence-window)
      similarity: [E] same-substrate-(cross-border-bank-messaging-substitute-for-telex) / same-era-emergence / same-target-counterparty-set-(international-banks) / first-national-city-bank-(now-citigroup)-pursuing-proprietary-network-position
      differential: [E] proprietary-private-network-controlled-by-one-bank-vs-cooperative-multi-bank-ownership / would-have-required-rival-banks-to-cooperate-on-network-controlled-by-one-of-them
      diagnosis: [E] proprietary-control-architecture-was-architecturally-incompatible-with-multi-bank-cooperation-need / rival-banks-would-not-cede-cross-border-messaging-substrate-to-one-of-them / collective-action-via-cooperative-formation-was-defensive-architectural-response-that-prevailed
      reveals: [E] subject's-load-bearing-feature-is-the-cooperative-governance-structure-(F3-+-G3)-not-the-messaging-technology / multi-bank-coalition-architecture-was-the-architecturally-defining-decision-+-the-only-architecture-rival-banks-would-adopt / parallel-to-visa-F4-multi-bank-licensing-emergence-decision / [E] cross-corpus-pattern-cooperative-+-coalition-architectures-emerge-defensively-when-rival-participants-need-shared-infrastructure-but-cannot-trust-any-one-of-them-to-own-it
    - id: cips-as-comparator
      name: CIPS (China's Cross-Border Interbank Payment System, as comparator)
      era: 2015-present
      similarity: [E] cross-border-bank-payment-infrastructure / state-backed-or-sponsored / international-bank-counterparties / messaging-+-clearing-+-settlement-functions
      differential: [E] CIPS-handles-clearing-+-settlement-(swift-only-messages) / chinese-state-sponsored-not-cooperative / explicit-sanctions-resistant-positioning-(not-bound-by-Western-unilateral-sanctions) / much-smaller-scale-historically-but-growing-+-80%-of-CIPS-payments-still-use-SWIFT-messaging-(2025-data)
      diagnosis: [I] same-substrate-different-strategic-architecture / CIPS-explicitly-positioned-as-sanctions-resistant-+-clearing-+-settlement-+-messaging-bundled / SWIFT-messaging-only-+-cooperative-utility-explicitly-G7-+-EU-political-tolerated-but-conditional / both-architectures-currently-coexist-with-CIPS-piggy-backing-on-SWIFT-messaging-while-building-independent-rails
      reveals: [E] subject's-G7-political-coalition-protective-force-(G7)-creates-symmetric-vulnerability-+-G6-+-G7-jointly-define-the-architecture's-strategic-position-rather-than-just-protect-it / CIPS-+-mBridge-architectures-emerge-defensively-against-SWIFT's-non-neutrality / structurally-similar-to-MARTI-1973-emergence-dynamic-but-with-roles-reversed-(now-non-G7-banks-build-cooperative-alternative-to-G7-controlled-network) / [E] cross-corpus-pattern-defensive-coalition-formation-recurs-when-rival-actors-cannot-trust-incumbent-infrastructure / cooperative-architectures-can-be-substituted-by-newer-cooperative-or-state-architectures-if-incumbent-becomes-politically-weaponized

  audit: 47E / 9I / 11C / 0U / 67-fields

  notes: |
    SWIFT introduces a structurally distinct architecture profile
    to the corpus: cooperative-governance + utility-pricing +
    explicitly-non-profit-maximizing. Schema accommodated cleanly
    with one observation worth surfacing.

    (1) The economics block fields are not load-bearing for
    cooperative architectures the way they are for investor-
    owned ones. Unit economics, margin trajectory, etc. are
    less informative than for visa/mastercard/coca-cola because
    the cooperative-structure constrains rent extraction
    architecturally. This is not a schema gap — the fields are
    populated with the relevant cooperative-structural facts —
    but the relative weight of economics vs forces-accumulated
    in characterizing the architecture is structurally different.
    Worth tracking: do other cooperative-governance entries
    (NYSE pre-demutualization, Lloyd's of London) show the
    same pattern?

    (2) G7 (G7+EU political coalition using SWIFT as sanctions
    tool) is structurally similar to TSMC G6 (sovereign-strategic
    significance) — simultaneously protective and target-
    attracting. This is the second instance of the
    load-bearing-for-civilization-stack pattern (cross-corpus
    pattern candidate #3) appearing in the corpus. The protective
    coalition that sustains the architecture is also the source
    of the architecture's strategic vulnerability — non-aligned
    actors actively build alternatives because incumbent is
    politically weaponized. Worth tracking as a recurring
    structural feature for systemically-important architectures.

    (3) Negative pairs surface a new cross-architecture pattern
    candidate: defensive coalition formation recurs when rival
    actors cannot trust incumbent infrastructure. MARTI 1973 →
    SWIFT cooperative formation; SWIFT G7 weaponization →
    CIPS + mBridge formation. The same dynamic operates in
    both cases with roles reversed. Visa 1966 multi-bank
    licensing program (visa F4) and mastercard 1966 Interbank
    Card Association (mastercard F1) are both instances of the
    same coalition-formation-as-defensive-architecture pattern.
    Candidate cross-architecture pattern #5:
    coalition-architecture-emerges-as-defensive-response-to-
    proprietary-network-threat-or-incumbent-politicization.

    Layer C invariants applied:
    - Conservation of Value (Invariant 1): cooperative
      structure deliberately operates at utility pricing
      below extractable rent / surplus rebated or reinvested
      / V available to extractive incumbent (eg visa) does
      NOT operate here by design / structurally distinct
      conservation profile
    - Competitive Response (Invariant 2): CIPS + mBridge +
      SPFS represent active competitive response after 2012
      iran + 2022 russia disconnection eroded sub-attention-
      threshold by making SWIFT politically weaponized
    - Regulatory Response (Invariant 3): SWIFT is itself the
      regulatory tool (G7 sanctions enforcement) rather than
      the target — inversion of the typical regulatory-
      response invariant operation
    - Time Consistency (Invariant 6): 2006 + 2022 controversies
      revealed SWIFT cooperative-neutrality time-consistency
      defection (relative to non-aligned member promise) /
      reputation as neutral cooperative compressed rapidly
      among non-aligned states / G3 actively eroding in
      asymmetric build-vs-decay pattern

    Layer A status: Section B finance/payments entry 2,
    decomposed May 2026 — tests cooperative-governance +
    utility-pricing + multipolar-fragmentation profile.
```

## Prose Synthesis

**Identification:** SWIFT is the cooperative bank-messaging utility founded May 1973 in Belgium as defensive response to private cross-border messaging attempts (First National City Bank's MARTI), co-owned by ~11,500 member institutions across 200+ countries, with ~44M messages/day and ~$5T daily funds-movement value communicated. Entry scope is the cooperative messaging infrastructure specifically; SWIFT explicitly does not transmit money — clearing and settlement happens via correspondent banking or local clearing systems.

**Structural position:** SWIFT occupies the standard-setting messaging-utility position in cross-border banking flow, with cooperative governance and utility pricing distinguishing it architecturally from investor-owned payment networks (Visa, Mastercard). Position supply scarcity was historically very high (1 global cooperative messaging standard) but is eroding 2014-2026 via SPFS (Russia), CIPS (China), mBridge (BRICS+ CBDC network), and domestic real-time payment systems creating multipolar fragmentation. Substitutability has been very low historically but is increasing meaningfully 2022 onward, with non-aligned flows actively routing alternatives.

**Force-topology dependence:** All five emergence forces (F1-F5: 1973 cooperative formation as MARTI defense, pre-electronic globalizing banking need, cooperative governance + utility pricing decision, ISO message standards, 1980s-90s globalization tailwind) closed; F3 and F5 promoted into G3 (cooperative trust) and G1 (network effect). Seven accumulated forces (G1-G7: universal bank network effect, ISO 20022 standard position, cooperative trust asset, half-century compliance + resilience investment, cross-border flow metadata, central-bank cooperative oversight, G7+EU political coalition as sanctions tool) operate. G3 (cooperative neutrality) is actively eroding — the 2006 US data-sharing controversy and 2022 Russia disconnection revealed cooperative neutrality is conditional on host jurisdiction + G7 political consensus. G7 (G7+EU sanctions tool) is double-edged: protective coalition that also creates active substitution incentive for non-aligned actors. Closing conditions: multipolar fragmentation progress, mBridge/CBDC rail maturation, additional major sanctions disconnection events confirming non-neutrality. Trajectory contested: mature durable short-term, long-term uncertain.

**Negative-pair insights:** MARTI (1970-1973 First National City Bank proprietary attempt that failed) and CIPS (2015-present Chinese state-backed comparator that is actively building) together bracket a recurring cross-architecture pattern: defensive coalition formation recurs when rival actors cannot trust incumbent infrastructure. MARTI failed because rival banks would not cede cross-border substrate to one of them → SWIFT cooperative formed defensively. SWIFT G7 weaponization → CIPS + mBridge formed defensively by non-aligned actors. The same dynamic operates in both cases with roles reversed. Reveals cooperative architectures emerge and can be substituted by newer cooperative/state architectures when incumbent becomes politically weaponized.

**Epistemic profile:** Strong evidence base (47 [E] / 9 [I] / 11 [C] / 0 [U] across 67 fields). Higher contested-field count than prior entries (11 vs typical 5-9) reflects forward-looking uncertainty about multipolar fragmentation trajectory, mBridge + CBDC adoption rates, and net effect of G7 political coalition (protective vs target-attracting). Zero [U] fields. Entry is high-confidence for descriptive structural mechanics; lower-confidence for 5-10 year forward trajectory given the unusual stack of geopolitical + technological + cooperative-neutrality pressures operating simultaneously.
