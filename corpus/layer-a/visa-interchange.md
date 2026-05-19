
# Visa Interchange

## Research Summary

Verified primary facts as of May 2026: Visa Inc. is the global payment-network operator descended from BankAmericard, launched by Bank of America in Fresno, California in 1958, licensed to other banks starting 1966, spun off as National BankAmericard Inc. (NBI) in 1970, renamed Visa in 1976, and IPO'd in March 2008. FY2025 net revenue $40.0B (up 11%); FY2026 Q2 net revenue $9.6B (up 9%). Three primary revenue lines: service revenue (~$5.0B/Q, based on payments volume), data processing revenue (~$5.5B/Q, per-transaction fees), international transaction revenue (~$3.6B/Q, cross-border + FX). Client incentives ~$4.2B/Q subtracted. Payments volume growing ~7-8%, cross-border 11-13%.

Critical structural feature: Visa does NOT collect interchange — interchange flows from acquirers (merchant banks) to issuers (cardholder banks), with Visa setting the rates but collecting separate service + data processing fees. Visa is the rails/switch, not the rent collector in the headline interchange flow. November 10, 2025: revised MDL 1720 settlement (20-year antitrust case) announced — 10bps fee cut for 5 years, 1.25% rate cap for standard consumer cards for 8 years, $38B projected merchant savings; merchant groups (NRF, NACS) strongly oppose as "window dressing"; pending preliminary approval early 2026. $992M Q2 2025 and $707M FY26 Q1 litigation provisions. April 16, 2026: Visa/Mastercard settled final claims from ~five-dozen merchants including Circle K parent. October 2025: Commercial Enhanced Data Program (CEDP) launched with AI-driven audits; legacy Level 2 program sunsets April 18, 2026.

## Canonical Record

```yaml
- id: visa-interchange
  name: Visa
  era: 1958-present
  industry: payments/network-infrastructure
  status: [E] durable / contested-litigation-active
  scale: [E] rev-$40B-FY2025 / ~$14T+-payments-volume / ~$3.3T-cross-border / ~280B-transactions-est-annually
  scope: [E] visa-network-rails-and-data-processing / excludes-issuer-card-issuance / excludes-acquirer-merchant-processing / excludes-stablecoin-and-rtgs-experiments

  flow:
    primary: [E] payment-authorization+clearing+settlement-messages / cardholder->merchant-value-flow-via-issuer->acquirer / visa-as-switch
    rate: [E] ~280B-transactions-annually / ~$14T+-payments-volume / continuous-realtime-365-day / nominal-volume-growth-7-8%-fy25
    direction: [E] visa-at-switch-position / not-at-rent-collection-position-of-headline-interchange-flow
    recurrence: [E] inherent-transactional-recurrence / driven-by-consumer-spending-frequency / no-subscription-layer
    secondary: [E] fraud-detection-data / global-flow-data / cross-border-fx-data / issuer-program-management-services / visa-advanced-auth / visa-token-service

  position:
    description: [E] four-sided-network-rails / sits-between-issuing-banks-and-acquiring-banks-as-switch / sets-interchange-rates-flowing-acquirer-to-issuer-but-does-not-collect-them / collects-own-fees-from-both-sides-on-volume-and-per-transaction
    upstream: [E] issuing-banks-as-paying-customers / thousands-of-issuers-globally / ~10-major-issuers-dominate-volume(chase-citi-cap-one-amex-discover-direct-issuers-distinct)
    downstream: [E] acquiring-banks-and-processors-as-paying-customers / merchant-end-users-who-do-not-pay-visa-directly-but-pay-acquirers / cardholder-end-users-who-do-not-pay-visa-directly-but-pay-issuers
    scarcity-supply: [E] very-low / 1-visa-globally / mastercard-the-only-direct-substitute-at-equivalent-scale / amex-discover-smaller-3-party-or-4-party-variants
    substitutability-flow: [E] very-low-historically / [C] increasing-2026 / real-time-payment-rails-fednow-rtp-sepa-instant-gaining-merchant-acceptance / stablecoin-rails-emerging / crypto-not-yet-credible-at-pos

  counterparty:
    types: [issuing-banks-(paying-customers), acquiring-banks-and-processors-(paying-customers), merchants-(price-takers-but-organized-litigants-nrf-nacs), cardholders-(end-users-non-paying), regulators-(usdoj-cfpb-fed-state-banking-eu-india-mdr-etc), governments-as-policy-actors, direct-competitors-(mastercard-amex-discover-unionpay), substitute-rails-(fednow-rtp-stablecoin-bnpl), litigation-class-(20+-yr-mdl-1720)]
    concentration: [E] issuers-thousands-but-top-10-dominate-volume / acquirers-concentrated-(fiserv-fis-globalpayments-chase-mp-stripe-adyen) / merchants-very-fragmented-with-concentrated-litigation-orgs / cardholders-totally-fragmented / regulators-jurisdictionally-concentrated-but-distributed-globally
    relationship: [E] issuers-long-term-multi-year-contracts-with-volume-incentive-clawbacks / acquirers-similar / merchants-must-accept-or-honor-all-cards-rule(modified-by-mdl) / cardholders-no-direct-relationship / regulators-adversarial-active-20yr-mdl
    pricing: [E] complex-interchange-rate-cards-with-mcc-category-differentiation / service-fees-to-issuers-on-volume / data-processing-fees-per-transaction / international-transaction-premium-fee-+-fx-spread / cedp-introduces-ai-driven-audit-pricing-tier-oct-2025
    info-asymmetry: [E] visa-knows-aggregate-global-flow-data / issuers-know-cardholder-spend / acquirers-know-merchant-spend / merchants-and-cardholders-cannot-observe-rate-setting-mechanics / fraud-pattern-asymmetry-favors-visa-via-visanet

  economics:
    revenue-source: [E] service-revenue-from-issuers-on-payment-volume-~$20B / data-processing-revenue-per-transaction-~$22B / international-transaction-revenue-on-cross-border-+-fx-~$14B-highest-margin / value-added-services-~$5B / client-incentives-~$16B-subtracted-from-gross
    unit: [E] very-high-margin-per-transaction / marginal-cost-of-incremental-transaction-near-zero / software-like-economics / typical-net-margin-~50%-historically
    cost-structure: [E] heavy-fixed-cost / visanet-infrastructure / 30k+-employees / data-center-and-fraud-detection-systems / client-incentive-program-largest-revenue-deduction
    capital: [E] public-since-march-2008-ipo-($17.9B-at-time) / prior-bank-cooperative-structure-1970-2007 / current-mkt-cap-~$650B-may-2026
    margin-trajectory: [I] historically-stable / [C] mdl-1720-settlement-+-cedp-changes-+-rtps-competition-creating-forward-pressure

  dynamics:
    acquisition: [E] institutional-sales-to-issuers-and-acquirers / merchant-acceptance-driven-by-consumer-demand / no-direct-consumer-marketing-substantial / brand-presence-via-issuer-co-branded-cards
    retention: [E] very-high / multi-year-contracts-with-issuer-and-acquirer-clients / honor-all-cards-rule-modified-by-mdl / cardholder-habits-deeply-formed / merchant-pos-systems-fully-integrated-with-visa-rails
    exit: [E] extremely-high-friction-for-issuers-(year-or-more-migration) / impossible-for-merchants-during-honor-all-cards-era-(modified-2024-25) / trivial-for-cardholders-but-they-still-need-some-card
    info-capture: [E] aggregate-global-transaction-data-decades / fraud-pattern-database-visanet / cardholder-segment-data / cross-border-flow-data / merchant-category-spending-patterns
    info-disclosure: [E] required-public-financial-disclosure-since-2008-ipo / regulatory-disclosure-to-multiple-jurisdictions / aggregate-data-products-sold-back-to-clients / interchange-rate-schedules-public-since-mid-2000s-pressure

  competitive:
    direct: [E] mastercard-(duopoly-partner-similar-structure-similar-revenue-$30B-fy25) / amex-(3-party-issuer+network+acquirer-smaller-~$70B-revenue-but-most-non-network) / discover-(4-party-smaller-acquired-by-capital-one-2025) / china-unionpay-(regional-dominant-not-substitutable-outside-china)
    indirect: [E] real-time-payment-systems-fednow-rtp-sepa-instant-pix-india-upi-(gaining-merchant-acceptance) / stablecoin-rails-(emerging-but-not-yet-pos-credible) / buy-now-pay-later-affirm-klarna-(competing-for-incremental-credit-flow) / paypal-venmo-zelle-(p2p-substitution-low-overlap-with-card-flow) / stripe-and-similar-fintechs-attempting-to-build-direct-bank-connections
    response-patterns: [E] visa-historically-navigated-antitrust-without-dissolution / multiple-mdl-settlements-2012-2024-2025-each-reducing-merchant-restrictions-while-preserving-core-economics / acquired-or-partnered-with-emerging-rails-(visa-direct-for-p2p) / 2025-26-acquisitions-+-acceptance-rule-modifications-via-mdl
    regulatory: [E] heavily-regulated-and-actively-litigated / 20-year-mdl-1720-antitrust-litigation-revised-settlement-nov-2025 / durbin-amendment-2010-caps-debit-interchange / eu-ifr-2015-caps-interchange-eu-wide / india-2017-mdr-caps / cfpb-active-2010s-onward / state-banking-regulators
    adversarial: [E] merchant-lobbying-groups-actively-litigating-and-supporting-legislation-nrf-nacs / durbin-marshall-credit-card-competition-act-legislative-effort-ongoing / individual-large-merchants-opting-out-of-class-and-pursuing-direct-claims / merchants-strongly-condemned-nov-2025-revised-settlement

  forces-emergence:
    - id: F1
      description: [E] bank-of-america-pre-existing-scale-in-1958-(800-ca-branches-+-2m-customers-+-mainframe-and-telephony-infrastructure) / no-other-bank-had-this-combination
      status-now: closed / structural-prerequisite-only
    - id: F2
      description: [E] post-war-consumer-revolving-credit-demand-emerging / first-time-mass-market-needed-non-merchant-specific-charge-mechanism
      status-now: closed / consumer-credit-now-mature
    - id: F3
      description: [E] diners-club-1950-demonstration-that-multipurpose-cards-could-work-but-without-bank-issuing-network-stayed-niche
      status-now: closed / observational-substrate-only
    - id: F4
      description: [E] multi-bank-cooperation-framework-1966-licensing-program / move-from-single-bank-product-to-network
      status-now: closed-by-1976-rename-and-NBI-spinoff
    - id: F5
      description: [E] 1970s-computerization-of-transaction-authorization / made-realtime-multi-bank-clearing-feasible
      status-now: closed / now-substrate-not-driver

  forces-accumulated:
    - id: G1
      description: [E] two-sided-network-effect / issuer-acceptance-and-merchant-acceptance-reinforcing / cardholder-utility-rises-with-merchant-acceptance-merchant-utility-rises-with-cardholder-base
      since: 1970s-1980s
      status-now: active-durable / [C] under-pressure-from-rtps-and-honor-all-cards-modifications
    - id: G2
      description: [E] de-facto-payment-standard / visa-rails-and-message-formats-the-base-layer-of-global-payment-processing / pos-systems-and-ecommerce-checkouts-built-against-visa-protocols
      since: 1980s-1990s
      status-now: active-durable
    - id: G3
      description: [E] visanet-fraud-detection-infrastructure / decades-of-pattern-data / visa-advanced-authorization-and-visa-token-service-built-on-this
      since: 1970s-continuous
      status-now: active-strengthening / ai-fraud-detection-extending
    - id: G4
      description: [E] cross-border-+-fx-infrastructure / visa-handles-global-currency-conversion-at-scale / highest-margin-revenue-segment / hard-to-replicate-without-bank-relationships-in-every-jurisdiction
      since: 1990s
      status-now: active-strengthening / cross-border-growing-11-13%-fy25
    - id: G5
      description: [E] card-not-present-+-ecommerce-rails / visa-checkout-+-click-to-pay-+-direct-api-integrations / digital-commerce-grew-faster-than-face-to-face-fy25
      since: 1995-onward
      status-now: active-strengthening
    - id: G6
      description: [E] regulatory-accumulation / visa-has-navigated-20-years-of-antitrust-mdl-1720-without-dissolution / 2025-revised-settlement-preserves-core-economic-model-while-conceding-tactical-rules / each-settlement-becomes-precedent-narrowing-future-merchant-challenges
      since: 2008-onward-(post-ipo-litigation-era)
      status-now: active / but-contested-via-credit-card-competition-act-legislative-effort
    - id: G7
      description: [E] issuer-revenue-dependence / issuers-earn-substantial-revenue-from-interchange / their-economic-interest-aligns-with-visa-rate-preservation / political-and-lobbying-coalition-of-banks-supports-visa-position
      since: 1970s-continuous
      status-now: active-durable

  evolution: [E] 1958-bankamericard-launch-fresno-by-bofa / 1966-licensing-program-to-other-banks / 1970-NBI-spinoff / 1973-visanet-electronic-authorization / 1976-visa-rename / 1979-magnetic-stripe-standardization / 1990s-card-not-present-and-ecommerce-emergence / 2008-march-ipo-$17.9B / 2010-durbin-amendment-debit-cap / 2012-first-class-mdl-settlement-$5.7B / 2015-eu-ifr-caps / 2023-2024-novbr-2024-settlement-rejected-by-judge-brodie / oct-2025-cedp-launch-+-level-2-sunset-april-18-26 / nov-2025-revised-mdl-1720-settlement-$38B-projected-merchant-savings / april-2026-final-merchant-claims-settled-(circle-k-parent-resolution)

  closing-conditions: [I] real-time-payment-rails-achieving-merchant-acceptance-at-pos-scale-(currently-mostly-p2p-and-b2b) / [I] regulatory-mandate-of-interchange-caps-similar-to-durbin-debit-extended-to-credit-(durbin-marshall-act-pending) / [I] cbdc-or-stablecoin-credible-at-retail-pos / [C] revised-mdl-1720-preliminary-approval-and-final-approval-(early-late-2026) / [I] honor-all-cards-rule-further-erosion-allowing-merchants-to-surcharge-or-reject-premium-cards / [I] generational-shift-to-non-card-payment-defaults-(walletization-or-rtps)

  trajectory: [C] mature-durable-with-active-pressure / stable-revenue-growth-7-11%-fy25 / first-credible-substrate-pressure-from-rtps-and-from-mdl-settlement-rule-modifications / outcome-stable-baseline-with-margin-compression-pressure

  negative-pairs:
    - id: diners-club
      name: Diners Club
      era: 1950-1980s-relevance-declining
      similarity: [E] general-purpose-charge-card-attempt / two-sided-network-attempt-merchants-+-cardholders / pre-bankamericard-by-8-years / first-mover-in-multipurpose-card-category
      differential: [E] proprietary-charge-not-bank-issued-revolving / no-multi-bank-licensing-program / no-merchant-acquirer-network-built-on-top / required-full-payment-monthly-not-revolving / smaller-acquirer-and-issuer-base-by-design-(single-entity)
      diagnosis: [E] failed-to-build-multi-bank-issuer-network-(no-analog-to-bofa-licensing-1966) / failed-to-build-merchant-acquirer-tier / stayed-at-luxury-restaurant-+-travel-niche / 200-members-1950-grew-to-42k-but-stuck-at-elite-segment / acquired-by-citicorp-1981-then-discover-2008-now-marginal
      reveals: [E] subject's-load-bearing-feature-is-not-card-concept-itself-(diners-had-that-first) / load-bearing-feature-is-multi-bank-licensing-program-1966-(F4-emergence-force)-which-built-the-issuer-network-then-the-merchant-acceptance-network / single-entity-card-cannot-scale-to-universal-acceptance / bank-coalition-was-the-structural-move-that-built-G1-and-G2
    - id: discover-card
      name: Discover Card
      era: 1985-present
      similarity: [E] 4-party-network-model / general-purpose-credit-card / direct-competitor-attempting-same-structural-position
      differential: [E] 27-years-late-to-visa-launch / sears-as-corporate-parent-not-bank-coalition / no-international-acceptance-network-at-launch / never-achieved-bank-coalition-issuer-base
      diagnosis: [E] entered-after-network-effects-G1-and-standardization-G2-had-cemented-visa-mc-duopoly / cardholder-acquisition-required-overcoming-deep-acceptance-asymmetry / acquired-by-capital-one-2025-completing-issuer-consolidation-trajectory
      reveals: [E] subject's-load-bearing-feature-is-not-just-the-network-architecture-but-the-1958-1970-time-window / once-G1-and-G2-cemented-by-the-1980s-new-entry-at-the-same-position-was-not-feasible / first-mover-advantage-in-multi-bank-licensing-was-decisive / explains-why-no-credible-new-4-party-network-has-emerged-in-40-years

  audit: 48E / 8I / 6C / 0U / 62-fields

  notes: |
    Visa illustrates the v1.3 schema's handling of a multi-sided
    network architecture where the headline-rent flow (interchange)
    is not collected by the architecture itself. Visa sets
    interchange rates but the rates flow acquirer-to-issuer; Visa's
    own revenue comes from service fees, data processing fees,
    and international transaction fees charged separately. This
    distinction matters structurally: Visa is not a rent-collector
    on interchange — it is a rails operator whose revenue depends
    on volume that interchange rates incentivize issuers to drive.
    The MDL 1720 litigation pressure is therefore indirect:
    interchange caps don't reduce Visa's revenue directly, but
    they could reduce issuer participation incentives and merchant
    acceptance flexibility.

    All five emergence forces are closed; durability rests on
    seven accumulated forces. The 1966 multi-bank licensing
    program (F4) is the move that built G1 and G2; the negative-
    pair contrast with Diners Club reveals this as the decisive
    structural move, not the 1958 card launch. This is a temporal
    asymmetry the static schema cannot capture without forces-
    accumulated: the entry window (1958-1970) was structurally
    distinct from the durability period (1970-present).

    Layer C invariants applied:
    - Competitive Response (Invariant 2): Discover's failure
      illustrates the closing of the entry window once G1-G2
      cemented; sub-attention-threshold strategy not applicable
      because Visa operates at maximum visibility
    - Regulatory Response (Invariant 3): 20-year MDL is the
      regulatory response invariant manifesting at scale;
      revised 2025 settlement is the pre-emptive-cooperation
      edge case
    - Time Consistency (Invariant 6): G6 (regulatory accumulation)
      is partly time-consistency in the regulatory domain — Visa's
      track record of settling within bounds rather than defecting
      preserves its negotiating position with regulators

    Layer A status: Section A schema-validation entry, decomposed
    May 2026 — tests multi-sided platform schema profile.
```

## Prose Synthesis

**Identification:** Visa is the global payment-network operator descended from BankAmericard (1958, Bank of America, Fresno), licensed multi-bank starting 1966, spun off as NBI in 1970, renamed Visa in 1976, public since March 2008. FY2025 net revenue $40.0B with ~50% net margin; ~$14T+ annual payments volume across ~280B transactions. Entry scope is Visa's network rails and data processing operations specifically; issuer card programs and acquirer merchant processing are operated by third parties not Visa itself.

**Structural position:** Visa occupies the switch position in a four-sided network — issuers, acquirers, merchants, cardholders — with revenue coming from service fees on issuers and data processing fees on transactions, not from the headline interchange flow which is rent collected by issuers from acquirers. The position is one of two globally (Mastercard the structural twin) and substitution has been historically near-zero, with current 2026 pressure from real-time payment systems (FedNow, RTP, SEPA Instant, UPI, Pix) starting to attack merchant acceptance at points-of-sale traditionally locked to card rails.

**Force-topology dependence:** All five emergence forces (F1-F5: BoA's pre-existing scale, post-war revolving credit demand, Diners Club's prior demonstration, the 1966 multi-bank licensing program, 1970s computerization) have closed; current durability rests on seven accumulated forces (G1-G7: two-sided network effect, de-facto standard-setting, VisaNet fraud infrastructure, cross-border + FX infrastructure, card-not-present rails, regulatory accumulation, issuer revenue dependence). Closing conditions visible: RTP rails achieving POS scale, Durbin-Marshall credit caps legislation, CBDC/stablecoin credibility at retail, and MDL settlement rule modifications eroding the honor-all-cards rule. Trajectory contested but stable baseline with margin compression pressure.

**Negative-pair insights:** Diners Club (1950-1980s, came first by 8 years but failed to build multi-bank issuer network) and Discover (1985-2025, entered too late after network effects cemented) together reveal the load-bearing structural feature is not the card concept itself but the 1966 multi-bank licensing program — the move that built G1 and G2. Diners Club had the card-concept first and failed; Discover had the four-party network architecture and failed because the entry window had closed by the 1980s. This isolates the 1958-1970 entry window as structurally distinct from the 1970-present durability period — a temporal asymmetry that a static schema would obscure without the emergence/accumulated forces split.

**Epistemic profile:** Strong evidence base (48 [E] / 8 [I] / 6 [C] / 0 [U] across 62 fields). Contested fields are forward-looking: RTP substitution timing, MDL settlement approval and effects, regulatory caps prospects, generational payment defaults — all genuinely uncertain in current force topology. Entry is high-confidence for descriptive structural mechanics and historical evolution; lower-confidence for forward trajectory specifics. Zero [U] fields — Visa is one of the best-documented architectures in the corpus due to public-company disclosure since 2008.
