
# New York Stock Exchange

## Research Summary

Verified primary facts as of May 2026: New York Stock Exchange traces to 1792 Buttonwood Agreement among 24 brokers; formally organized as New York Stock & Exchange Board 1817; became NYSE 1863. Operated as not-for-profit member-owned organization until 2006 demutualization via merger with Archipelago Holdings forming NYSE Group, public-company structure. November 2013 acquired by IntercontinentalExchange (ICE) for $11B; now operates as wholly-owned subsidiary of ICE (NYSE listed under ICE on its own exchange). ICE FY2025 consolidated revenue $9.9B (+7% YoY, 20th consecutive year of record revenues); FY2025 net income $3.3B. Within ICE, NYSE Group includes NYSE + NYSE American + NYSE Arca + NYSE Chicago + NYSE National + American Equity Options + others. ~3,400 listed companies globally on NYSE with ~$30T market cap.

Critical force-topology updates training data would miss: (1) Listing competition lost — Nasdaq won 81% of new IPO listings 2025 (~$25B raised on Nasdaq vs ~$5-7B on NYSE), now in 6th consecutive year leading US exchange listings; 94% of eligible SPAC IPOs in H1 2025 listed on Nasdaq. NYSE's identity-as-American-blue-chip listings position eroded materially over 2010s-2020s. (2) Market fragmentation accelerating — dark pools handled 51.8% of US stock trade volume January 2025 (third consecutive month >50%); 11+ exchanges + ~40 dark pools competing; NYSE share of US equity volume now ~20% from ~80% historically. (3) Reg NMS amendments rolling out November 2025 + May 2026 — tick-size reduction to half-cent for active stocks; odd-lot quote information added to SIP/core data; market structure ongoing reform. (4) Q4 2025 ICE reported record results across all segments including blockchain-settlement push for fixed income. (5) NYSE remains symbolic + brand listing destination for large cap + iconic American companies despite Nasdaq winning IPO share — identity-asset distinct from operating-flow-share.

## Canonical Record

```yaml
- id: nyse
  name: New York Stock Exchange
  era: 1817-present (208 years; modern public-company form since 2006)
  industry: finance/exchange/equities
  status: [E] operating-durable / [E] forcibly-restructured-2006-via-demutualization / [E] subsidiary-of-ICE-2013-onward / [C] core-listings-position-eroding-to-nasdaq
  scale: [E] ~3,400-listed-companies / ~$30T-listed-market-cap / part-of-ICE-($9.9B-fy2025-consolidated-rev-+-$3.3B-net-income) / nyse-segment-revenue-not-separately-disclosed-but-meaningful-fraction-of-ICE-cash-equities-+-listings-segment
  scope: [E] nyse-equity-exchange-+-listings-+-related-options-+-exchange-data-products / includes-nyse-american-+-arca-+-chicago-+-national-+-options-business / excludes-ice-futures-+-clearing-+-fixed-income-+-mortgage-+-data-services-not-equity-specific

  flow:
    primary: [E] equity-securities-trade-matching-+-clearing-instructions / buyers->nyse-matching-engine->sellers / [E] listings-flow-issuer-applications-+-listing-fees-+-ongoing-compliance / nyse-at-trade-matching-+-listings-utility-position
    rate: [E] ~$50B+-daily-equity-trade-value-on-nyse-(rough-estimate-given-~20%-of-us-equity-volume) / ~3,400-listed-companies / continuous-realtime-trading-+-listings-cycle
    direction: [E] nyse-at-trade-matching-+-listings-+-data-position / not-at-broker-dealer-OR-clearing-OR-settlement-(separate-DTCC-NSCC-operations)
    recurrence: [E] inherent-recurrence-on-equity-trading-+-issuer-listing-+-ongoing-compliance / engineered-recurrence-via-listings-+-data-+-options-fees / market-volatility-+-IPO-activity-cyclical
    secondary: [E] market-data-products-+-historical-data-licensing / connectivity-+-co-location-services-(hft-+-institutional) / listings-services-+-corporate-services / options-+-ETF-listings-flow / brand-+-bell-ringing-ceremony-services-(symbolic-+-marketing-value-to-issuers)

  position:
    description: [E] equity-exchange-+-listings-utility-+-brand-asset / publicly-traded-via-ICE-parent-since-2006-demutualization / iconic-symbolic-position-as-american-capital-markets-archetype / brand-+-identity-asset-+-trade-matching-utility-+-data-services-composed
    upstream: [E] broker-dealers-+-institutional-trading-firms-+-high-frequency-trading-firms-as-routing-counterparties / listed-companies-as-issuer-clients / data-+-connectivity-vendors / ICE-as-parent-company
    downstream: [E] broker-dealers-routing-orders-+-institutional-investors / market-data-consumers-(bloomberg-refinitiv-quants-+-direct-subscribers) / listed-companies-receiving-listings-services / regulators-using-nyse-data
    scarcity-supply: [E] historically-near-monopolistic-(only-major-us-equity-exchange-pre-1971-nasdaq-launch) / [E] eroded-since-2006-2007-reg-NMS-+-electronic-trading-+-multiple-exchanges-+-dark-pools-fragmenting-the-position / current-share-~20%-of-us-equity-volume-vs-historical-~80%
    substitutability-flow: [E] high-now / 11+-exchanges-+-40-dark-pools / nasdaq-listings-substitute-broadly-+-winning-share / [E] nyse's-symbolic-+-identity-asset-+-bell-ringing-ceremony-+-brand-+-large-cap-association-still-distinguishes-from-pure-trade-matching-substitutes

  counterparty:
    types: [broker-dealers-+-trading-firms-+-hft-(major-trading-counterparties), institutional-investors-+-asset-managers, listed-companies-as-issuer-clients, market-data-consumers-(bloomberg-+-refinitiv-+-direct), parent-ICE-+-related-ICE-businesses, regulators-(SEC-+-FINRA-+-CFTC-overlap-+-state), competitor-exchanges-(nasdaq-+-cboe-+-iex-+-memx-+-misx-+-others), dark-pools-+-ECNs-as-substitute-venues, retail-investors-(via-broker-dealer-routing)]
    concentration: [E] broker-dealers-+-hft-firms-concentrated-(top-tier-handles-most-volume) / listed-companies-very-concentrated-by-market-cap-(top-100-companies-most-cap) / institutional-investors-concentrated / regulators-jurisdictionally-distributed-but-SEC-primary
    relationship: [E] broker-dealers-multi-year-membership-+-routing-+-co-location-+-connectivity-fees / listed-companies-listing-agreements-+-ongoing-compliance-+-listing-fees / market-data-licensing-multi-year-contracts / parent-ICE-strategic-+-operational-integration
    pricing: [E] trade-execution-fees-+-rebates-(maker-taker-model) / listing-fees-by-tier-+-market-cap / market-data-+-connectivity-+-co-location-tier-pricing / options-+-ETF-listings-pricing
    info-asymmetry: [E] nyse-knows-aggregate-trade-flow-+-listings-pipeline-+-market-microstructure-data / institutional-+-hft-+-broker-dealers-know-own-routing-+-strategy / consolidated-tape-public-+-direct-feeds-paid

  economics:
    revenue-source: [E] trade-execution-+-rebate-fees / listing-fees-(annual-+-initial-listings) / market-data-+-connectivity-+-co-location-revenue / options-+-ETF-listings-revenue
    unit: [E] historically-high-fixed-cost-per-trade-+-low-marginal-cost-(software-+-infrastructure-leverage) / [E] maker-taker-rebate-model-creates-volume-incentive-+-narrow-margins-on-pure-execution / data-+-co-location-higher-margin
    cost-structure: [E] technology-+-data-+-regulatory-+-compliance-+-listings-services-cost-base / connectivity-+-co-location-+-data-infrastructure-capital-intensive
    capital: [E] subsidiary-of-ICE-public-company-since-2006-+-2013-acquisition / ICE-market-cap-~$80B-2026 / capital-allocation-+-investment-decisions-via-ICE-parent
    margin-trajectory: [C] core-trade-execution-+-listings-share-eroding / [E] data-+-connectivity-+-listings-still-meaningful-revenue / [I] overall-NYSE-segment-margin-likely-stable-via-mix-shift-from-execution-to-data-+-services

  dynamics:
    acquisition: [E] of-listed-companies-via-listings-sales-+-ipo-pipeline-+-relationship-banking-+-brand-+-identity-marketing / of-broker-dealers-+-hft-via-fee-+-rebate-economics-+-co-location-+-data-services / heavily-driven-by-marketing-+-relationships-+-brand-identity-for-listings-+-by-economic-incentive-for-execution
    retention: [E] listings-retention-via-relationship-+-listed-status-symbolic-value-+-switching-cost-+-regulatory-compliance / execution-retention-via-rebate-+-connectivity-+-co-location-+-routing-relationships / brand-+-bell-ringing-+-archive-+-marketing-services-as-identity-retention-mechanism
    exit: [E] listings-exit-friction-substantial-(delisting-+-relisting-elsewhere-disruptive) / execution-exit-essentially-zero-(broker-dealers-can-route-to-any-venue-+-reg-NMS-requires-best-price)
    info-capture: [E] aggregate-equity-trade-flow-data / listings-pipeline-+-issuer-financial-+-microstructure-data
    info-disclosure: [E] required-public-disclosure-via-ICE-parent / consolidated-tape-public-(SIP) / direct-feeds-paid-subscription / extensive-regulatory-disclosure

  competitive:
    direct: [E] nasdaq-(direct-listings-+-execution-competitor-+-now-winning-81%-of-new-ipos-2025-+-46-consecutive-quarters-leading-listings) / cboe-equity-+-options / iex-(investors-exchange-launched-2014-with-speed-bump-+-anti-hft-position) / memx-+-misx-+-other-newer-exchanges / dark-pools-+-internalizers-as-execution-substitute / london-+-hong-kong-+-singapore-+-shanghai-+-shenzhen-listings-substitutes-for-non-US-listings
    indirect: [E] private-markets-(staying-private-longer-+-tender-offers-as-IPO-substitute-+-stripe-pattern-as-broader-trend) / cryptocurrency-+-token-+-tokenized-securities-platforms-emerging / direct-listings-+-SPAC-alternatives-to-traditional-IPO
    response-patterns: [E] nyse-2006-demutualization-as-response-to-electronic-+-ECN-competition / 2013-ICE-acquisition-providing-scale-+-diversification / [E] data-+-connectivity-+-listings-services-investment-as-margin-defense / brand-+-identity-asset-investment-(bell-ringing-+-listings-marketing-+-american-blue-chip-association) / continued-listings-share-loss-to-nasdaq-suggests-strategic-+-execution-gap-not-architectural-failure
    regulatory: [E] heavily-regulated / sec-primary-regulator-+-finra-self-regulatory / reg-NMS-2007-+-amendments-2025-2026 / sip-+-consolidated-tape-mandate / market-structure-+-fragmentation-policy-ongoing / no-current-antitrust-pressure
    adversarial: [E] direct-listing-+-spac-+-private-market-substitutes-eroding-traditional-IPO-flow / nasdaq's-44-year-+-aggressive-marketing-+-tech-+-fintech-listings-positioning / iex-+-newer-exchanges-positioning-as-anti-hft-or-anti-fragmentation-alternatives / dark-pool-+-internalization-trend-eroding-public-exchange-share

  forces-emergence:
    - id: F1
      description: [E] 1792-buttonwood-agreement-+-1817-formal-organization-+-1863-NYSE-name / first-mover-position-as-organized-US-equity-exchange-of-scale / 100+-year-head-start-over-nasdaq-(1971)
      status-now: closed / now-substrate-only
    - id: F2
      description: [E] 19th-c-railway-+-industrial-capital-formation-+-new-york-as-financial-capital / created-the-issuer-+-trading-flow-substrate
      status-now: closed / now-substrate-not-driver
    - id: F3
      description: [E] member-owned-mutual-organization-1817-2006 / governance-by-broker-+-trading-members / capital-light-utility-+-self-regulatory-structure
      status-now: closed-by-2006-demutualization / restructured-into-investor-owned-form
    - id: F4
      description: [E] floor-trading-+-specialist-system-+-physical-trading-floor / created-identity-+-symbolic-+-information-asymmetry-asset
      status-now: closing-since-2007-electronic-trading / specialist-system-replaced-by-Designated-Market-Makers-+-electronic-trading / physical-floor-now-mostly-symbolic-+-broadcast-platform-not-execution-substrate
    - id: F5
      description: [E] regulatory-+-listing-standards-establishment-late-19th-+-20th-century / blue-chip-listing-standards-created-quality-association-+-identity-asset
      status-now: closed-as-emergence / promoted-into-G3-american-blue-chip-identity-asset

  forces-accumulated:
    - id: G1
      description: [E] american-blue-chip-+-iconic-listings-identity / 208-years-of-listings-including-most-iconic-american-corporations / bell-ringing-+-trading-floor-+-NYSE-symbol-as-cultural-asset / [E] identity-asset-still-meaningful-despite-listings-share-loss-to-nasdaq
      since: 1900s-onward-continuous-accumulation
      status-now: active-but-eroding-as-nasdaq-wins-flagship-tech-listings
    - id: G2
      description: [E] listed-company-base-+-ongoing-listings-relationships / ~3,400-listed-companies-+-multi-decade-issuer-relationships / switching-cost-+-identity-cost-of-delisting / partial-network-effect-via-related-listings-cluster
      since: 1900s-continuous
      status-now: active-but-attrition-via-delistings-+-take-private-+-acquisitions
    - id: G3
      description: [E] market-data-+-historical-data-asset / decades-of-trade-+-listings-+-microstructure-data / consolidated-tape-+-direct-feed-revenue / part-of-broader-ICE-data-services-strategy
      since: 1970s-electronic-onward-strengthening
      status-now: active-strengthening / margin-defense-mechanism-as-execution-margin-compresses
    - id: G4
      description: [E] connectivity-+-co-location-+-tech-infrastructure-scale / millisecond-latency-data-center-+-co-location-services-for-hft-+-institutional / decade-scale-infrastructure-investment
      since: 2007-electronic-trading-+-reg-NMS-buildout-onward
      status-now: active-durable
    - id: G5
      description: [E] regulatory-+-self-regulatory-position-+-relationships / sec-+-finra-+-regulatory-policy-influence / market-structure-+-listings-standards-co-evolution
      since: 1934-securities-exchange-act-onward
      status-now: active-durable
    - id: G6
      description: [E] ICE-parent-strategic-+-financial-backing-+-platform-scale / 2013-acquisition-providing-capital-+-cross-business-leverage-(futures-+-fixed-income-+-data-+-mortgage) / strategic-investment-+-business-diversification
      since: 2013-onward
      status-now: active-durable
    - id: G7
      description: [E] symbolic-+-brand-+-ceremony-+-marketing-asset / nyse-bell-ringing-+-trading-floor-broadcast-+-american-capital-markets-archetype-+-iconic-photography-+-media-association / identity-asset-distinct-from-trade-execution-share
      since: 1900s-onward-continuous-via-media-+-cultural-position
      status-now: active-+-relatively-resilient-+-distinct-from-execution-share-erosion / [C] generational-+-tech-listings-shift-eroding-some-cultural-association

  evolution: [E] 1792-buttonwood-agreement-24-brokers / 1817-formal-organization / 1863-NYSE-name / 1869-NYSE-+-open-board-merger / 1903-current-building-broad-+-wall-street / 1934-securities-exchange-act-creating-SEC-+-regulated-self-regulatory-status / 1971-nasdaq-launch-creating-first-credible-listings-competitor / 1971-2006-progressive-electronic-+-ECN-+-instinet-+-archipelago-competition / 2006-march-demutualization-via-archipelago-merger-+-NYSE-group-public-company-formation / 2007-reg-NMS-+-electronic-trading-acceleration / 2007-2013-NYSE-Euronext-period-with-European-equity-+-derivatives-integration / nov-2013-ICE-acquisition-$11B / 2014-iex-launch-with-speed-bump-anti-hft-position / 2015-onward-progressive-listings-share-loss-to-nasdaq / 2020-onward-spac-+-direct-listing-+-private-market-substitute-pressure / nov-2025-+-may-2026-reg-NMS-amendments-(tick-size-+-odd-lot-+-sip-changes) / 2025-nasdaq-81%-IPO-share-+-NYSE-share-loss-continuing

  closing-conditions: [I] continued-listings-share-loss-to-nasdaq-such-that-G1-+-G2-blue-chip-identity-erodes-materially / [I] private-markets-staying-private-+-tender-offer-IPO-substitute-trend-(stripe-pattern)-shrinking-overall-IPO-pie / [I] dark-pools-+-private-markets-+-internalization-fragmenting-execution-share-below-critical-threshold-for-utility-economics / [I] tokenized-equities-+-blockchain-settlement-substituting-traditional-exchange-architecture / [E] note-architecture-has-already-been-forcibly-restructured-(2006-demutualization)-+-acquired-(2013-ICE)-without-architectural-failure-suggesting-resilience-mechanism / [I] symbolic-+-identity-asset-(G1-+-G7)-likely-resilient-even-as-execution-share-erodes

  trajectory: [C] mature-durable-with-active-erosion / [E] core-listings-share-loss-to-nasdaq-+-execution-share-loss-to-dark-pools-ongoing / [E] data-+-connectivity-+-symbolic-+-identity-asset-margin-defense-effective-in-recent-years / parent-ICE-continues-record-revenue-growth / trajectory-stable-baseline-with-execution-+-listings-erosion-offset-by-data-services

  negative-pairs:
    - id: amex-equity-exchange-1849-2008
      name: American Stock Exchange (AMEX, as equity exchange)
      era: 1849-2008-(NYSE-acquisition-completion)
      similarity: [E] same-architectural-pattern-(equity-+-listings-+-execution-exchange) / same-era-emergence-(amex-1849-curb-market-+-1921-formal-exchange) / same-geographic-+-regulatory-substrate / similar-listings-+-execution-flow-+-market-data-business
      differential: [E] amex-specialized-in-smaller-companies-+-options / never-achieved-NYSE-scale-or-blue-chip-identity / progressive-decline-with-electronic-trading-+-nasdaq-emergence / acquired-by-NYSE-2008-+-folded-into-NYSE-American
      diagnosis: [E] same-architectural-pattern-but-smaller-scale-+-narrower-listings-+-failure-to-build-G1-equivalent-blue-chip-identity-+-G7-symbolic-asset / amex's-curb-market-+-smaller-company-positioning-was-distinct-from-NYSE-blue-chip-association-but-could-not-scale-+-was-substituted-by-nasdaq's-tech-focused-positioning
      reveals: [E] subject's-load-bearing-feature-is-G1-american-blue-chip-identity-+-G7-symbolic-asset-not-trade-matching-utility-per-se / amex-had-trade-matching-+-listings-utility-but-lacked-blue-chip-identity-+-symbolic-asset / parallel-to-rc-cola-vs-coca-cola-pattern-+-globalfoundries-vs-tsmc-pattern / same-architecture-+-failure-to-accumulate-G-forces-at-archetype-scale
    - id: nasdaq-as-comparator-survivor
      name: Nasdaq Stock Market (cross-architecture comparator survivor)
      era: 1971-present
      similarity: [E] same-architectural-pattern-(equity-exchange-+-listings-+-execution-+-data) / same-regulatory-substrate / similar-listings-+-execution-flow / both-public-companies-+-demutualized
      differential: [E] nasdaq-electronic-from-1971-founding-vs-NYSE-1792-floor-trading-tradition / nasdaq-positioned-as-tech-+-growth-+-innovation-listings-vs-NYSE-blue-chip-identity / nasdaq-46-consecutive-quarters-leading-US-listings / nasdaq-81%-IPO-share-2025 / different-identity-position-+-different-customer-mix
      diagnosis: [I] same-architectural-pattern-different-identity-position-occupation-+-different-customer-mix / nasdaq-pursued-tech-+-growth-listings-+-electronic-execution-from-founding / NYSE-pursued-blue-chip-+-floor-trading-+-symbolic-asset / both-architectures-durable-with-different-vulnerability-profiles / [I] nasdaq-tech-mix-currently-benefiting-from-AI-economy-listings-+-growth-share-while-NYSE-blue-chip-mix-faces-private-market-+-take-private-pressure
      reveals: [E] subject's-+-nasdaq's-coexistence-as-co-equal-exchanges-confirms-non-zero-sum-position-occupation-pattern-(cross-corpus-pattern-#4) / parallel-to-coca-cola-pepsi-+-amex-mastercard-+-paypal-stripe-+-visa-mastercard / different-identity-positions-in-same-architectural-space-both-durable / [E] subject's-load-bearing-feature-is-american-blue-chip-+-symbolic-identity-position-not-pure-execution-utility / counterfactually-nyse-pursuing-pure-execution-utility-would-have-faced-direct-substitutability-from-dark-pools-+-newer-exchanges-+-already-lost-share-significantly

  audit: 49E / 12I / 7C / 0U / 68-fields

  notes: |
    NYSE introduces a structurally distinct profile to the corpus:
    forcibly-restructured-architecture-that-persisted-via-
    architectural-transformation-not-asset-redistribution. Unlike
    Standard Oil (forcibly-restructured via dissolution) or Kodak
    (defunct-as-mass-medium architecture), NYSE was restructured
    from member-owned mutual to investor-owned public company
    (2006), then acquired into larger platform (2013 ICE),
    without architecture failure — successor architecture
    continued operations with substantial continuity of G1-G7
    forces.

    This adds a third defunct/restructured profile to the corpus:
    (a) Standard Oil — forcibly dissolved, assets redistributed
        across successor entities, architecture closed
    (b) Kodak — defunct as mass-medium architecture, successor
        entity operates different architecture, accumulated forces
        partially-persistent at reduced scale
    (c) NYSE — forcibly demutualized + acquired, architecture
        substantially continued via successor structure, identity
        + accumulated forces preserved through transformation

    The schema accommodated all three with compound `status` values
    but the controlled vocabulary remains stressed. This is now
    the second instance of the defunct-as-subject status-vocabulary
    schema stress (after kodak-film). Combined with the redistributed
    pattern from Standard Oil and likely AT&T pre-1984 + AIG-2008
    + IBM-1980s in Section D, evidence accumulating for a v1.4
    vocabulary expansion covering architecture-persistent-under-
    restructured-form. Not yet sufficient to recommend v1.4
    amendment, but the convergence is becoming clearer.

    Cross-corpus pattern #4 (identity-as-non-zero-sum-position-
    occupation) confirmed at 5 instances now: coca-cola/pepsi,
    amex/mastercard, paypal/stripe, visa/mastercard, nyse/nasdaq.
    Pattern is robust across multiple architectural domains
    (beverages, payments, fintech, payment networks, exchanges).
    Worth noting: pattern appears to apply specifically to
    identity-asymmetry-dominant or position-defined architectures,
    not capability-asymmetry-dominant ones (where TSMC/Samsung
    Foundry/Intel-Foundry occupy same position with execution
    asymmetry rather than position differentiation).

    Cross-corpus pattern #2 (time-to-accumulation distribution)
    contrast: NYSE's G1 American blue-chip identity took ~100
    years to accumulate (1817 founding through 1900s blue-chip
    standards period). Coca-Cola G3 cultural archetype: ~25-30
    years. Bloomberg G1 chat network: ~15 years. Stripe G6 Bridge:
    ~12 months. TSMC G7 AI-workload-dependency: ~3 years.
    Spread from year-scale (substrate-shift event) to century-
    scale (organic accumulation in low-velocity industry). Worth
    tracking distribution across remaining entries.

    Layer C invariants applied:
    - Competitive Response (Invariant 2): nasdaq-1971-onward-
      cumulative-share-gain demonstrates competitive response
      eroding G2 listings position over decades
    - Information Dynamics (Invariant 5): market data + historical
      data asset (G3) is replenishment-flow-not-stock; analogous
      to bloomberg G3 + visa G3 + stripe G3 patterns
    - Time Consistency (Invariant 6): G1 + G7 (American blue-chip
      identity + symbolic asset) is canonical time-consistency
      play; 208 years of identity-position-occupation; asymmetric
      build-vs-decay risk if NYSE were to defect from blue-chip
      positioning (analogous to Bloomberg G5 trust accumulation)
    - Conservation of Value (Invariant 1): execution-margin
      compression as dark pools + multiple exchanges fragment
      V available; data + connectivity + listings services
      extracting from different V flows compensating

    Layer A status: Section B finance/payments entry 4,
    decomposed May 2026 — tests forcibly-restructured-but-
    persistent + identity/symbolic-asset + acquired-into-larger-
    platform profile.
```

## Prose Synthesis

**Identification:** The New York Stock Exchange traces to 1792 Buttonwood Agreement, formally organized 1817, became NYSE 1863, operated as member-owned mutual until 2006 demutualization via Archipelago merger forming NYSE Group public company, then acquired by IntercontinentalExchange (ICE) November 2013 for $11B. Now wholly-owned ICE subsidiary; ICE FY2025 consolidated revenue $9.9B (+7%), net income $3.3B. ~3,400 listed companies with ~$30T listed market cap. Entry scope is the NYSE equity exchange, listings, and related options + data businesses; excludes ICE futures, fixed income, mortgage, and non-equity-specific data services operated by ICE parent.

**Structural position:** NYSE occupies the equity-exchange-plus-listings-plus-symbolic-identity position, with three distinct functional layers: trade matching utility, listings utility, and brand/identity/symbolic asset (bell ringing, floor broadcast, American capital markets archetype association). Position supply scarcity was near-monopolistic pre-1971 (Nasdaq launch) but has eroded materially — current ~20% of US equity volume vs historical ~80%; Nasdaq winning 81% of new IPO listings 2025 in 6th consecutive year leading US listings. Substitutability is now high for trade matching (11+ exchanges + 40 dark pools handling 51.8% of volume) but the symbolic + identity asset remains distinct from pure execution substitutes.

**Force-topology dependence:** All five emergence forces (F1-F5: 1792 founding + 100-year head start, 19th-c capital formation tailwind, member-owned mutual structure, floor + specialist trading, listing standards establishment) are closed — F3 closed forcibly by 2006 demutualization, F4 closing since 2007 electronic trading. Seven accumulated forces (G1-G7: American blue-chip identity, listed company relationships, market data asset, connectivity + co-location infrastructure, regulatory position, ICE parent backing, symbolic + brand + ceremony asset) operate. G1 + G2 (blue-chip identity + listings base) eroding as Nasdaq wins flagship tech listings; G3 (data) strengthening as margin defense; G7 (symbolic asset) relatively resilient. Closing conditions: continued listings share loss eroding G1/G2 materially, private-market substitute pressure (Stripe pattern) shrinking overall IPO pie, tokenized equities + blockchain settlement substitution. Architecture has already been forcibly restructured twice (2006 demutualization, 2013 ICE acquisition) without architectural failure — suggests resilience mechanism.

**Negative-pair insights:** AMEX (1849-2008, smaller-scale equity exchange folded into NYSE) and Nasdaq (1971-present, comparator survivor with different identity position) bracket the failure space. AMEX reveals the same architectural pattern + failure to accumulate G1-equivalent blue-chip identity + G7 symbolic asset cannot sustain at archetype scale — parallel to RC Cola/Coca-Cola and GlobalFoundries/TSMC patterns. Nasdaq reveals non-zero-sum position-occupation pattern (cross-corpus pattern #4) at 5 instances now: different identity positions in same architectural space, both durable. The contrast isolates NYSE's load-bearing feature as American blue-chip + symbolic identity position rather than pure execution utility — counterfactually pure-execution NYSE would have lost catastrophically to dark pools + newer exchanges.

**Epistemic profile:** Strong evidence base (49 [E] / 12 [I] / 7 [C] / 0 [U] across 68 fields). Higher inferred-field count reflects NYSE-specific segment disclosure being limited within ICE parent consolidated reporting. Contested fields cover forward-looking listings share trajectory, private-market substitution pace, tokenized-equity emergence timing. Zero [U] fields. Entry is high-confidence for descriptive structural mechanics and 208-year force-topology evolution; lower-confidence for forward trajectory under simultaneous private-market + tokenization + Nasdaq-share-loss pressures.
