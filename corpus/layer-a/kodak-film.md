
# Kodak (chemical film business)

## Research Summary

Verified primary facts as of May 2026: Eastman Kodak Company founded 1888 by George Eastman with flexible roll-film innovation that displaced glass-plate photography. Bankruptcy filing January 19, 2012; emergence from Chapter 11 September 3, 2013 after shedding personalized imaging business to UK pension plan ($325M for Kodak Alaris formation) and selling 1,100-patent digital imaging portfolio to consortium led by Apple, Google, Microsoft for ~$525M. Peak architecture (1990s) generated ~$13-15B annual revenue and employed ~140K at peak; reduced to ~$1.04B revenue 2024 and ~3,800 employees. Steven Sasson built first digital camera prototype at Kodak in 1975 (0.01 MP, 23-second per image); Kodak patented but did not commercialize; digital camera patent portfolio later monetized in bankruptcy.

Critical force-topology updates training data would miss: film photography revival is material and accelerating — Kodak 2024 film sales +20% YoY, wholesale film orders +127% since 2020, 312 new film labs opened globally 2025. September 2025 Eastman Kodak resumed direct consumer film distribution in US/Canada (first time in >10 years) coinciding with revived Kodacolor 100/200 launch; professional films followed January 2026. Consumer photography film now represents ~1/3 of Kodak's chemical/materials division revenue (which is ~30% of total sales, 63% of total profits). Kodak Alaris sold by UK Pension Protection Fund to private equity (Kingswood Capital) April 2024. Eastman Kodak continues issuing going-concern warnings re debt obligations through 2026 despite the film revival; pension reversion increased from $500M to $600M as available debt paydown source.

## Canonical Record

```yaml
- id: kodak-film
  name: Kodak (chemical film business)
  era: 1888-2012
  industry: imaging/consumer-goods/chemical-film
  status: [E] defunct-as-mass-medium-architecture / persists-in-niche-enthusiast-form-via-successor-entity-eastman-kodak
  scale: [E] peak-rev-~$13-15B-1990s / peak-emp-~140k-1988 / bankruptcy-filing-jan-19-2012 / post-bankruptcy-rev-~$1B-2024 / post-bankruptcy-emp-~3.8k / film-business-~85%-of-peak-revenue
  scope: [E] chemical-film-business-1888-2012(consumer-film+motion-picture-film+photographic-paper+processing-chemicals) / excludes-pre-bankruptcy-digital-camera-business / excludes-post-2013-eastman-kodak-AM&C-pivot / excludes-kodak-alaris-distribution-entity-separate

  flow:
    primary: [E] silver-halide-chemical-emulsion-film-stock+paper+chemicals / kodak-manufacturing->independent-processors->consumers / motion-picture-film-direct-to-studios
    rate: [I] peak-~1B+-rolls-of-consumer-film-annually-1990s / continuous-batch-chemical-manufacturing / replenishment-driven-by-per-photograph-consumption
    direction: [E] kodak-as-manufacturer-hub / fragmented-retail-and-processor-channel-downstream / motion-picture-film-direct-channel-to-concentrated-studio-buyers
    recurrence: [E] inherent-consumable-per-photograph / no-engineered-recurrence-needed / consumer-photo-frequency-drove-replenishment
    secondary: [E] processing-chemicals-flow / photographic-paper-flow / X-ray-medical-film-flow / motion-picture-print-film-flow / cinema-projection-stock

  position:
    description: [E] vertically-integrated-chemical-emulsion-manufacturer / patent+trade-secret-protected-color-chemistry / brand+distribution-scale-at-mass-consumer-retail / "you-press-the-button-we-do-the-rest"-end-to-end-system-1888-onward
    upstream: [E] silver-commodity-supply / chemical-input-suppliers-relatively-fragmented / R&D-internal
    downstream: [E] fragmented-independent-photo-processors-(fotomat-drugstores-1-hour-labs) / consumer-retail-chains / motion-picture-studios-direct / professional-photographer-channel / industrial+medical-imaging-customers
    scarcity-supply: [E] very-high-at-peak / ~3-global-competitors(fujifilm-agfa-polaroid-in-adjacent-niche) / chemical-formulation-trade-secrets-+-patents-+-~100yr-cumulative-R&D-barrier / new-entry-required-decade-scale-chemistry-investment
    substitutability-flow: [E] very-low-pre-1995 / [E] increasing-1995-2005 / [E] catastrophic-post-2005 / substrate-substitution-by-digital-capture-not-position-substitution-by-another-film-maker

  counterparty:
    types: [consumers-mass-fragmented, professional-photographers, motion-picture-studios-concentrated, independent-photo-processors-fragmented, retail-chains-moderate-concentration, competitors(fujifilm-agfa-polaroid-ilford), digital-camera-makers-emerging-substitutes-1990s-onward(canon-nikon-sony-then-apple), silver-commodity-suppliers, regulators-FTC+antitrust-historically-light, employees-as-major-stakeholder-given-rochester-concentration]
    concentration: [E] consumers-totally-fragmented / processors-fragmented / retailers-moderate / motion-picture-studios-concentrated-8-major-then-6 / competitors-concentrated-3-major
    relationship: [E] consumer-transactional-no-relationship / processors-wholesale-distribution / studios-multi-year-contracts / retailers-volume-discount-tiers / competitors-implicit-price-umbrella-1900s-1980s-broken-by-fuji-1980s
    pricing: [E] uniform-retail / volume-tiers-wholesale / professional-film-premium / motion-picture-film-negotiated / kodak-as-historical-price-leader-with-umbrella-broken-by-fujifilm-1984-onward
    info-asymmetry: [E] kodak-knew-aggregate-consumption-and-format-mix-data / consumers-knew-own-usage / [C] kodak-knew-digital-substitution-trajectory-via-internal-1975-sasson-prototype-+-1990s-internal-roadmaps-but-acted-on-information-with-strategic-rather-than-existential-frame

  economics:
    revenue-source: [E] consumer-film-largest-line(~60%-at-peak) / motion-picture-film(~10%) / photographic-paper-and-chemicals(~15%) / professional-and-industrial(~10%) / other(~5%) / film-and-photographic-products-~85%-of-kodak-total-at-peak
    unit: [E] very-high-gross-margin-per-roll-(~60-70%-historically) / marginal-cost-of-incremental-roll-low-once-manufacturing-built / [I] declining-gross-margin-2000-2012-as-volume-collapsed-and-fixed-costs-absorbed-by-falling-volume
    cost-structure: [E] heavy-fixed-(rochester+global-manufacturing+R&D-~$1B/yr-at-peak) / variable-silver+chemical-input-cost-modest-fraction / scale-economies-substantial-pre-volume-collapse / fixed-cost-absorption-failure-was-2000s-collapse-mechanism
    capital: [E] public-NYSE-since-1880s / retained-earnings-historical / debt-financing-2000s-as-pivot-investment / pension-obligations-major-bankruptcy-driver / [E] bankruptcy-jan-19-2012-+-emergence-sept-3-2013
    margin-trajectory: [E] high-and-stable-1900s-1990s / declining-1995-2002 / collapsing-2002-2012 / [E] post-bankruptcy-architecture-different-business-not-comparable

  dynamics:
    acquisition: [E] universal-household-brand-recognition-since-1900-brownie-launch / "kodak-moment"-cultural-archetype / drug-store-+-photo-shop-retail-presence-essentially-default-channel / no-direct-marketing-substantial-pre-1980s
    retention: [I] habit-+-default-behavior-not-structural-lock-in / consumer-switching-cost-near-zero / professional-photographers-had-modest-workflow-preference-for-kodak-color-science(kodachrome+portra) / motion-picture-studio-relationships-deeper-via-format-standards
    exit: [E] near-frictionless-for-consumers / professional-film-format-preference-modest-friction / motion-picture-studio-format-friction-substantial-but-digital-cinema-replaced-rather-than-substituted-by-2010s
    info-capture: [E] aggregate-consumption-data / film-format-demand-mix / processor-wholesale-flows / [E] technology-roadmap-internal-knowledge-of-digital-substitution-since-1975-not-leveraged-for-defensive-pivot
    info-disclosure: [E] required-public-disclosure-as-NYSE-listed / chemical-formulations-patented-or-trade-secret / 1990s-2000s-public-warnings-about-digital-shift-in-shareholder-communications-but-pivot-execution-failed

  competitive:
    direct: [E] fujifilm-from-1934-aggressive-US-entry-1984-LA-olympics-sponsorship-broke-kodak-price-umbrella / agfa-german-largely-european / polaroid-instant-niche-only / ilford-black-and-white-niche / 3-4-global-competitors-throughout
    indirect: [E] digital-cameras-1990s-onward-(canon-nikon-sony) / camera-phones-from-2000-onward / smartphone-cameras-from-iphone-2007-onward / cloud-photo-storage-as-secondary-displacement-of-photographic-paper / digital-cinema-projection-displacing-motion-picture-film
    response-patterns: [E] kodak-1980s-90s-defended-price-umbrella-against-fujifilm-rather-than-restructuring-cost-base / [E] kodak-2003-announced-"transformation"-to-digital-multi-year-restructuring / [E] kodak-1990s-2000s-attempted-entry-into-digital-cameras-(easyshare)+printers+kiosks-where-it-had-no-structural-advantage / [E] kodak-monetized-digital-patent-portfolio-2010-2013-via-litigation-then-sale / [E] fujifilm-pivoted-emulsion-expertise-into-cosmetics(astalift)+pharmaceuticals(fujifilm-pharma)+document-imaging-while-kodak-pivoted-into-hardware-it-could-not-defend
    regulatory: [E] historically-light / FTC-consent-decrees-1921-1954-on-photographic-paper-bundling / no-active-antitrust-in-decline-era / patent-IP-disputes-with-polaroid-1976-1990-($925M-judgment) / no-regulatory-event-load-bearing-in-architecture-failure
    adversarial: [E] fujifilm-strategic-attack-on-US-price-umbrella-1984-onward / digital-camera-makers-pursued-substitution-not-direct-attack / [I] no-political-or-activist-adversarial-pressure-load-bearing

  forces-emergence:
    - id: F1
      description: [E] george-eastman-1888-flexible-roll-film-innovation / replaced-glass-plates-as-photography-substrate / enabled-mass-consumer-photography-as-category
      status-now: closed-by-1900s / now-substrate-only-not-driver
    - id: F2
      description: [E] mass-consumer-photography-as-emerging-category-late-19th-c / no-prior-consumer-photography-existed-pre-eastman / created-the-flow-itself
      status-now: closed / category-now-displaced-by-digital-+-smartphone-capture
    - id: F3
      description: [E] vertical-integration-of-complete-imaging-chemistry-stack-(emulsion+film-stock+paper+chemicals+processing) / no-competitor-occupied-full-stack-pre-1930s
      status-now: closed / stack-redistributed-or-dismantled-post-2012
    - id: F4
      description: [E] patent-+-trade-secret-protection-on-color-emulsion-chemistry / kodachrome-1935-+-cumulative-R&D-investment-decade-scale / barrier-to-entry-for-color-film
      status-now: closed / digital-substrate-bypassed-color-chemistry-entirely
    - id: F5
      description: [E] first-mover-global-retail-+-processor-distribution-network-(drugstore-channel+fotomat+1-hour-labs+motion-picture-studio-relationships)
      status-now: closed / retail-channel-collapsed-with-film-demand-2000s-2010s

  forces-accumulated:
    - id: G1
      description: [E] cumulative-emulsion-chemistry-trade-secret-knowledge / ~100yr-R&D-investment-in-color-+-grain-+-stability-properties / kodachrome-portra-tri-x-formulations-as-IP-stock
      since: 1900s-continuous-through-1990s
      status-now: closed-as-architecturally-load-bearing / partially-persistent-in-eastman-kodak-2024-26-niche-revival-but-no-longer-mass-medium-substrate
    - id: G2
      description: [E] "kodak-moment"-cultural-+-brand-identity-accumulation / universal-household-recognition / cultural-archetype-status
      since: 1900-brownie-onward-continuous
      status-now: partially-persistent / brand-survives-but-commercial-leverage-diminished-as-photographic-substrate-shifted / 2025-revival-marketing-trades-on-residual-identity
    - id: G3
      description: [E] global-manufacturing-scale-rochester-+-worldwide-plants / chemical-batch-manufacturing-with-decades-of-process-optimization
      since: 1920s-1990s-build-out
      status-now: closed / most-plants-shuttered-2002-2015 / rochester-footprint-dramatically-reduced
    - id: G4
      description: [E] motion-picture-film-standard-setting-position / kodak-formats+stocks-the-industry-default-for-shooting-film-for-decades / [E] digital-cinema-displacement-2010s
      since: 1920s-2000s
      status-now: closed-by-digital-cinema / motion-picture-film-now-deliberate-aesthetic-choice-not-default
    - id: G5
      description: [E] digital-imaging-patent-portfolio-accumulated-1975-2010 / 1,100-patents-sold-2012-2013-for-~$525M-during-bankruptcy / sasson-1975-prototype-as-foundational
      since: 1975-continuous-through-2010
      status-now: monetized-then-closed / sold-to-apple-google-microsoft-consortium-2013 / no-longer-belongs-to-kodak

  evolution: [E] 1888-eastman-roll-film-patent-+-launch / 1900-brownie-camera-mass-consumer-photography-launch / 1935-kodachrome-color-film-launch / 1963-instamatic-launch / 1975-sasson-builds-first-digital-camera-prototype-internally-not-commercialized / 1981-fujifilm-aggressive-us-entry-via-1984-LA-olympics-sponsorship-after-kodak-declined / 1986-polavision-instant-failure / 1991-photo-CD-attempted-bridge-failed / 1995-2002-modest-digital-camera-entry-(easyshare)-but-without-cost-structure-pivot / 2002-2010-revenue-collapse-from-~$13B-to-~$6B / 2003-publicly-announced-"transformation"-to-digital-multi-year-restructuring / 2010-2012-digital-patent-litigation-+-sale-attempts / jan-19-2012-chapter-11-filing / sept-3-2013-emergence-with-film-business-spun-to-uk-pension-as-kodak-alaris-+-digital-patents-sold-for-~$525M / 2013-onward-eastman-kodak-becomes-different-architecture-(printing+packaging+advanced-materials+chemicals) / 2024-26-film-photography-revival-(20%/yr-growth)-allows-modest-niche-resumption / sept-2025-direct-consumer-film-sales-resumed-+-kodacolor-revival / april-2024-kodak-alaris-sold-to-kingswood-capital-private-equity

  closing-conditions: [E] not-applicable-architecture-closed-2012-chapter-11 / closed-by-substrate-substitution-(digital-capture)-not-by-regulatory-or-competitive-position-pressure-alone

  trajectory: [E] terminated-2012 / partial-niche-revival-2020-2026-in-enthusiast-segment-via-successor-entities(eastman-kodak-film-unit+kodak-alaris-now-kingswood) / revival-at-~5-8%-of-peak-scale / [I] revival-may-stabilize-as-deliberate-aesthetic-medium-analogous-to-vinyl-records-rather-than-mass-consumer-substrate-restoration

  negative-pairs:
    - id: polaroid
      name: Polaroid Corporation
      era: 1937-2008-(two-bankruptcies-2001-and-2008)
      similarity: [E] chemical-imaging-mass-consumer-architecture / vertically-integrated-chemistry-+-hardware-+-brand / faced-digital-substrate-shift-1990s-2000s / internal-CCD-and-digital-imaging-R&D-1980s-1990s-not-translated-to-commercial-pivot / iconic-cultural-brand-with-strong-identity-component
      differential: [E] instant-photography-niche-not-general-purpose / land-tighter-founder-control-1937-1980 / smaller-scale-(~$3B-peak-vs-kodak-$15B) / earlier-bankruptcy-(2001-vs-kodak-2012) / instant-niche-meant-substrate-shift-was-existential-not-just-major
      diagnosis: [E] same-substrate-substitution-failure-mode / chemical-imaging-expertise-could-not-be-leveraged-into-digital-substrate-where-the-relevant-capability-was-CCD-engineering-+-software-not-emulsion-chemistry / both-architectures-died-from-substrate-displacement-not-positional-competition
      reveals: [E] kodak's-failure-was-not-idiosyncratic-or-managerial-but-systemic-to-chemical-imaging-architectures-facing-digital-substrate-shift / polaroid-with-tighter-controls+earlier-warning-also-failed / suggests-substrate-shift-was-the-load-bearing-failure-cause / counterfactual-good-management-could-not-have-preserved-the-chemical-film-architecture-as-mass-medium / could-only-have-pivoted-to-different-architecture(fujifilm-path)-or-managed-decline-better
    - id: fujifilm-survived-pivot
      name: Fujifilm (chemical-imaging architecture, surviving comparator)
      era: 1934-present (comparator window 1990-2015 pivot period)
      similarity: [E] chemical-emulsion-imaging-architecture / similar-scale-(~$10-15B-peak-revenue) / same-substrate-shift-pressure-1990s-2000s / similar-cumulative-R&D-in-emulsion-chemistry-+-brand-recognition / faced-same-digital-substrate-displacement-of-core-business
      differential: [E] fujifilm-CEO-komori-2003-onward-executed-pivot-of-emulsion-+-coating-+-imaging-IP-into-adjacent-chemistry-applications-(astalift-cosmetics-2007 / fujifilm-pharmaceuticals-acquisitions-2008-onward / healthcare-imaging-equipment / document-imaging) / kodak-attempted-pivot-into-digital-cameras-+-printers-+-kiosks-where-it-had-no-cost-or-structural-advantage / fujifilm-deployed-existing-chemical-IP-laterally / kodak-deployed-capital-into-categories-it-did-not-understand
      diagnosis: [I] same-substrate-substitution-pressure-different-strategic-response / fujifilm-redeployed-architectural-capability(chemical-+-coating-+-color-science-expertise)-into-categories-where-that-capability-was-load-bearing / kodak-redeployed-capital-into-categories-where-its-architectural-capabilities-were-irrelevant / fujifilm-preserved-the-architecture-by-changing-the-flow-it-served / kodak-preserved-the-flow-(consumer-imaging)-and-changed-the-architecture-(to-hardware)-and-failed
      reveals: [E] subject's-load-bearing-feature-was-cumulative-chemical-emulsion-+-coating-expertise-not-the-photographic-consumer-flow / preserving-the-flow-while-shifting-to-different-architecture-(hardware)-discards-the-load-bearing-asset / preserving-the-architectural-capability-while-shifting-flow-(fujifilm-cosmetics-pharma)-retains-it / standard-strategy-literature-frames-kodak's-failure-as-failure-to-embrace-digital-but-the-fujifilm-contrast-suggests-the-actual-failure-was-failure-to-recognize-which-capability-was-the-architecture / 1975-internal-digital-camera-prototype-was-availability-of-information-not-availability-of-architectural-capability-to-execute-on-it

  audit: 47E / 11I / 5C / 0U / 63-fields

  notes: |
    Kodak is the first defunct-as-subject entry decomposed and
    stresses the v1.3 schema in two specific ways:

    (1) Status field stress. The architecture-list status is
    "defunct" but the entity Eastman Kodak still operates as a
    different architecture (printing + advanced materials +
    chemicals + recently-revived niche film), and Kodak Alaris
    operates as a separate film-distribution entity. The status
    field accommodates this with a compound value
    ("defunct-as-mass-medium-architecture / persists-in-niche-
    enthusiast-form-via-successor-entity") but the controlled-
    vocabulary slot does not natively support "architecture
    defunct, entity persistent with different architecture."
    Schema gap candidate: status enum could add
    "architecture-defunct-entity-persistent" to capture the
    distinction Standard Oil's "redistributed-1911" approached
    from the assets-side.

    (2) Forces-accumulated status-now stress. G1 (emulsion
    chemistry IP) and G2 (brand) are partially-persistent in
    the niche revival but no longer architecturally load-bearing
    at the mass-medium scale where they originally operated.
    The status-now field accommodates with "closed-as-
    architecturally-load-bearing / partially-persistent" but
    a cleaner schema would distinguish "structurally closed
    at original scale" from "persistent at reduced scale."
    Standard Oil used "redistributed-1911" for forcibly-divided
    persistence; Kodak needs analogous vocabulary for
    substrate-shift partial persistence.

    The two negative pairs deliberately bracket the failure
    case: Polaroid (similar architecture + similar failure)
    confirms the substrate-shift was systemic to chemical-
    imaging architectures, while Fujifilm (similar architecture
    + survived via strategic pivot) reveals what specifically
    Kodak failed at — strategic redeployment of architectural
    capability into adjacent categories rather than capital
    redeployment into unrelated hardware categories. The
    contrast isolates the load-bearing failure: not the
    substrate shift itself (which was unavoidable) but the
    misidentification of which capability constituted the
    architecture (chemistry-and-coatings vs photographic-
    consumer-flow).

    The 1975 Sasson digital camera prototype is a structurally
    interesting feature: Kodak possessed the disrupting
    substrate INTERNALLY before competitors did, but did not
    deploy it because deployment would cannibalize the
    architecture in place. This is a known organizational
    pattern (Christensen's innovator's dilemma) but the
    architectural decomposition does not require importing
    that framing — the raw structural fact is that information-
    availability (G5 patent portfolio) accumulated decades
    ahead of competitive-pressure-availability, allowing the
    architecture to delay action longer than typical, which
    ultimately compressed the recovery window when the
    pressure did arrive in force.

    Layer C invariants applied:
    - Information Dynamics (Invariant 5): the substrate shift
      from chemical to digital was an information-substrate
      shift that decayed Kodak's accumulated emulsion-chemistry
      asymmetry (G1); the asymmetry was real but the substrate
      it operated on became irrelevant — invariant predicts
      this failure mode for asymmetries dependent on a substrate
      that may itself shift
    - Conservation of Value (Invariant 1): post-2002 the V from
      chemical-film-mediated photography compressed faster than
      Kodak's cost-of-architecture could be reduced; X + Y > V
      structural condition predicted bankruptcy mechanism
    - Competitive Response (Invariant 2): Fujifilm's 1984
      attack on Kodak's price umbrella was a classic
      competitive-response event; Kodak's defensive posture
      preserved short-term rent at the cost of cost-structure
      restructuring that would have been needed for the
      substrate-shift response

    Layer A status: first defunct-as-subject schema-validation
    entry, decomposed May 2026 — tests substrate-shift failure
    mode at scale + persistent-successor-entity profile.
```

## Prose Synthesis

**Identification:** Kodak's chemical film business operated from 1888 (Eastman roll-film innovation) through January 19, 2012 (Chapter 11 filing), at peak generating ~$13-15B revenue and employing ~140K with film constituting ~85% of company revenue. Entry scope is the 1888-2012 chemical-film business specifically; the post-2013 emerged Eastman Kodak Company operates a different architecture (advanced materials + printing + chemicals with niche film revival) and is not part of this entry; Kodak Alaris (UK pension plan vehicle, 2013 onward, sold to private equity 2024) is also separately structured.

**Structural position:** Kodak occupied a vertically integrated position spanning emulsion chemistry through retail brand at mass-consumer scale, with three layers of structural advantage compounding over a century: (1) cumulative trade-secret chemistry expertise that no competitor could replicate without decade-scale R&D investment, (2) universal household brand identity ("Kodak moment") supporting price-umbrella positioning, and (3) first-mover retail and processor distribution networks. Substitutability was very low pre-1995 (no chemical-film alternatives at consumer scale), increasing 1995-2005 as digital cameras matured, catastrophic post-2005 as smartphone cameras began the second-wave displacement. The displacement was substrate-substitution — a different flow (digital capture + cloud storage + screen viewing) replacing the chemical-film flow entirely — not positional competition by another film manufacturer.

**Force-topology dependence:** All five emergence forces (F1-F5: roll-film innovation, mass consumer photography emergence, vertical chemistry integration, color-emulsion patent/trade-secret stack, retail distribution scale) have closed. Five accumulated forces (G1-G5: cumulative emulsion IP, "Kodak moment" brand, global manufacturing scale, motion-picture standard-setting, digital patent portfolio 1975-2010) all closed or were monetized through bankruptcy. Closing-conditions field is "not-applicable" — architecture terminated 2012 by substrate substitution, not by ongoing pressure on currently-active forces. Trajectory is "terminated-2012" with partial niche revival 2020-2026 at ~5-8% of peak scale; the revival is structurally a different architecture (deliberate aesthetic medium, analogous to vinyl) operating on the same chemistry IP but a different flow than mass-consumer imaging.

**Negative-pair insights:** Polaroid (1937-2008, same substrate shift, also failed) and Fujifilm (1934-present, same substrate shift, survived through strategic pivot) together bracket the failure case. Polaroid's failure confirms the substrate shift was systemic to chemical-imaging architectures, not idiosyncratic to Kodak management. Fujifilm's survival reveals what Kodak specifically failed at: strategic redeployment of architectural capability (chemistry, coatings, color science) into adjacent categories (cosmetics, pharmaceuticals, document imaging) where that capability remained load-bearing. Kodak instead redeployed capital into hardware (cameras, printers, kiosks) where it had no structural advantage. The contrast isolates the load-bearing failure as misidentification of which capability constituted the architecture — Kodak preserved the photographic-consumer flow and changed the architecture (to hardware) and failed; Fujifilm preserved the architectural capability and changed the flow (to adjacent categories) and survived.

**Epistemic profile:** Strong evidence base (47 [E] / 11 [I] / 5 [C] / 0 [U] across 63 fields). Contested fields cover the internal strategic decision-making at Kodak 1975-2005 (specifically what executives knew when about substitution trajectory) and forward-looking trajectory of the post-bankruptcy revival. Inferred fields cover peak-scale operational details and some unit-economics decomposition where private financial breakdown is not directly available. Zero [U] fields — Kodak is one of the best-documented architectural failures in business history due to public-company filings, bankruptcy proceedings, and ~15 years of post-mortem scholarship.
