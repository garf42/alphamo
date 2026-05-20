
# ASML

## Research Summary

Verified primary facts as of May 2026: ASML founded April 1, 1984 as ASM Lithography in "leaky shed" in Eindhoven, NL as Philips + ASM International joint venture; moved to Veldhoven 1985; Carl Zeiss partnership established 1986. FY2025 net sales €32.7B (+~50% YoY) at 52.8% gross margin; EUV revenue €11.6B (+39%, 48% of system revenue). FY2026 guidance €36-40B with 51-53% gross margins; Q4 2025 bookings record €13.2B incl €7.4B EUV. Record SK Hynix EUV order $7.9B 2026. Net bookings 2025 surged 48% to €28B. 2030 revenue target €71B. Market cap ~$300B (2026); ~40K employees. Near-monopoly on EUV (100% share) + dominant share of leading-edge DUV.

Critical force-topology updates training data would miss: (1) **China revenue collapsed from 49% (2024) to ~20% (2025)** via Dutch export restrictions on TWINSCAN NXT:1970i/1980i DUV systems expanded late 2024 — successful "harmonization" of Washington-Hague export rules. South Korea now 40% of system sales, largest market. (2) **High-NA EUV** modest revenue recognition FY2026; staged adoption ramping through 2027. (3) ~$71B 2030 revenue target as AI boom drives EUV demand; 3800-series low-NA EUV systems dominating FY2027+. (4) **Carl Zeiss SMT (Germany) optical system supplier** essential — supply chain spans NL (ASML) + Germany (Zeiss) + Japan (precision components) + US (light source via Cymer 2013 acquisition). (5) Nikon $4.8B revenue vs ASML $32.7B — ASML 7x Nikon scale; Nikon competitive in DUV mature nodes only. (6) Pattern from previous entries confirmed: ASML G3 mirror image of TSMC G3 (equipment supplier preferential access) — same architectural relationship from opposite side.

## Canonical Record

```yaml
- id: asml
  name: ASML Holding N.V.
  era: 1984-present (modern EUV monopoly era 2018-present post-EUV-launch)
  industry: semiconductors/lithography-equipment
  status: [E] operating-durable / [E] EUV-monopoly-+-capability-asymmetry-dominant-architecture-+-fast-growth-+-strategic-customer-concentration / [C] China-export-restriction-architectural-constraint
  scale: [E] FY2025-rev-€32.7B-+~50% / EUV-€11.6B-+39%-+-48%-of-system-rev / FY2026-guide-€36-40B-+-51-53%-gross-margin / Q4-2025-bookings-€13.2B-record / ~$300B-market-cap-2026 / 2030-target-€71B
  scope: [E] ASML-Holding-NV-full-architecture / lithography-equipment-+-EUV-+-DUV-+-installed-base-services-+-Carl-Zeiss-optical-+-Cymer-light-source / [E] integrated-ASML-architecture-not-decomposed-into-segments

  flow:
    primary: [E] semiconductor-lithography-equipment-design-+-manufacture-+-installation-+-service / ASML-Veldhoven-+-Zeiss-SMT-Germany-+-Cymer-US-light-source-+-Japanese-precision-suppliers->TSMC-+-Samsung-+-Intel-+-SK-Hynix-+-Micron-+-other-fab-customers / ASML-at-lithography-equipment-+-monopolistic-EUV-position
    rate: [E] ~50-100-EUV-+-100-200-DUV-systems-per-year-(supply-constrained-+-cycle-time-12-24-months-per-system) / continuous-multi-year-customer-+-roadmap-+-fab-commitment-cycles
    direction: [E] ASML-at-lithography-equipment-+-EUV-+-DUV-design-+-manufacture-+-installation-+-service-position / [E] monopolistic-supplier-position-vs-handful-of-tier-1-fab-customers-(TSMC-+-Samsung-+-Intel-+-SK-Hynix-+-Micron)
    recurrence: [E] equipment-procurement-+-multi-year-roadmap-+-installed-base-services-+-spare-parts-+-upgrade-+-decade-scale-customer-+-fab-investment / engineered-recurrence-via-installed-base-+-service-+-Holistic-Lithography-+-software-+-upgrade-cycle
    secondary: [E] installed-base-services-+-software-+-Holistic-Lithography-+-metrology-+-yield-+-process-control / Cymer-light-source-+-Carl-Zeiss-SMT-optical-system-strategic-partner-+-supplier-+-integration

  position:
    description: [E] tier-1-lithography-equipment-+-EUV-monopoly-+-DUV-dominant-+-Carl-Zeiss-+-Cymer-+-Japanese-precision-supply-chain-position / 42-year-cumulative-ASML-+-Zeiss-+-Philips-heritage-+-EUV-decade-scale-R&D-+-supply-chain-+-customer-+-roadmap-position
    upstream: [E] Carl-Zeiss-SMT-(Germany)-optical-system-essential-+-Cymer-(US)-light-source-acquired-2013-+-Japanese-precision-+-mechatronics-+-VDL-+-many-Dutch-+-European-+-Japanese-precision-suppliers / R&D-+-engineering-+-Veldhoven-cluster
    downstream: [E] handful-of-tier-1-fab-customers-(TSMC-+-Samsung-+-Intel-Foundry-+-SK-Hynix-+-Micron-+-other-leading-edge-+-trailing-edge) / [E] customer-concentration-+-strategic-customer-position
    scarcity-supply: [E] EXTREMELY-HIGH / EUV-100%-share-+-no-substitute-+-no-credible-competitor-at-leading-edge / Nikon-+-Canon-DUV-+-mature-nodes-only / Canon-nanoimprint-+-Okinawa-Institute-two-mirror-EUV-research-+-not-commercial / decade-scale-EUV-R&D-+-Zeiss-+-Cymer-+-supply-chain-non-replicable
    substitutability-flow: [E] very-low-EUV-(no-substitute-at-leading-edge) / [I] modest-DUV-substitutability-via-Nikon-+-Canon-on-mature-+-trailing-nodes / [C] Canon-nanoimprint-lithography-emerging-+-low-volume-+-narrow-application

  counterparty:
    types: [tier-1-fab-customers-(TSMC-+-Samsung-+-Intel-Foundry-+-SK-Hynix-+-Micron-+-broader-fab-+-leading-edge-+-trailing-edge), Carl-Zeiss-SMT-(Germany-essential-optical-supplier), Cymer-(US-light-source-acquired-2013), Japanese-precision-+-mechatronics-suppliers, regulators-(Dutch-government-export-control-+-US-+-EU-+-China-+-international-+-CHIPS-Act-+-Chips-Act-EU), competitors-(Nikon-+-Canon-+-Tokyo-Electron-+-Applied-Materials-+-Lam-Research-+-KLA-+-emerging-Chinese-+-Okinawa-research), employees-+-Veldhoven-+-Hsinchu-+-Tainan-+-Korea-+-US-+-global-+-cluster]
    concentration: [E] customers-EXTREMELY-CONCENTRATED-(5-major-fabs-+-90%+-leading-edge-+-TSMC-largest) / Zeiss-+-Cymer-single-source-suppliers / regulators-Dutch-+-US-government-decisive / competitors-fragmented-+-DUV-only-+-research-emerging
    relationship: [E] multi-year-+-multi-decade-strategic-customer-+-roadmap-co-development-+-EUV-+-Holistic-Lithography-+-decade-scale-fab-+-cluster-investment / Zeiss-1986-partnership-+-Cymer-2013-acquisition-+-Japanese-precision-+-supply-chain-decade-scale-relationships
    pricing: [E] EUV-NXE-+-EXE-system-pricing-€150-380M-per-system-+-High-NA-€350M+ / DUV-NXT-+-other-system-pricing-€20-80M / installed-base-+-service-+-Holistic-Lithography-+-software-+-upgrade-cycle-pricing / [E] supply-constrained-+-pricing-power-extreme-via-monopoly-position
    info-asymmetry: [E] ASML-knows-aggregate-leading-edge-fab-+-roadmap-+-EUV-+-DUV-+-AI-substrate-customer-+-process-control-data / 42-year-cumulative-ASML-+-Zeiss-+-EUV-+-DUV-+-fab-+-customer-roadmap-asymmetry / [E] uniquely-positioned-as-only-leading-edge-fab-process-control-+-roadmap-co-developer

  economics:
    revenue-source: [E] EUV-systems-(48%-+-€11.6B-+39%-FY2025-+-fastest-growing) / DUV-systems / installed-base-services-+-spare-parts-+-upgrade-+-Holistic-Lithography-+-software / metrology-+-process-control
    unit: [E] 52.8%-gross-margin-FY2025-+-51-53%-FY2026-guide-+-extreme-margin / EUV-system-+-installed-base-+-service-+-software-+-Holistic-Lithography-high-margin / [E] supply-constrained-+-pricing-power-via-EUV-monopoly-+-DUV-+-installed-base-position
    cost-structure: [E] R&D-+-engineering-+-Veldhoven-+-Carl-Zeiss-+-Cymer-+-Japanese-precision-supply-chain-+-cleanroom-+-installation / capex-+-R&D-+-strategic-investment-heavy-+-supply-chain-+-system-cycle-time-12-24-months
    capital: [E] public-Euronext-Amsterdam-+-NASDAQ-since-1995-IPO / market-cap-~$300B-2026 / strong-balance-sheet-+-buyback-+-dividend / strategic-customer-+-government-+-EU-+-Dutch-+-CHIPS-Act-financial-relationships
    margin-trajectory: [E] extreme-+-stable-+-improving-via-EUV-mix-+-Holistic-Lithography-+-installed-base-services / [C] China-export-restrictions-+-Chinese-DUV-+-customer-mix-+-mid-term-volatility

  dynamics:
    acquisition: [E] of-fab-customers-via-multi-year-roadmap-co-development-+-EUV-+-DUV-+-strategic-+-supply-allocation / [E] strategic-customer-+-decade-scale-fab-+-EUV-+-DUV-+-Holistic-Lithography-+-Cymer-+-Zeiss-supply-chain-+-roadmap-co-development
    retention: [E] very-high-via-EUV-+-DUV-+-fab-installed-base-+-Holistic-Lithography-+-software-+-service-+-multi-year-spare-+-upgrade-+-decade-scale-fab-+-customer-investment / [E] decade-scale-switching-cost-+-EUV-+-DUV-+-Carl-Zeiss-+-Cymer-+-supply-chain-+-process-control-+-customer-roadmap
    exit: [E] near-impossible-for-leading-edge-fab-customers-(no-EUV-substitute) / [I] modest-DUV-substitutability-via-Nikon-+-Canon-on-mature-+-trailing-nodes-+-Chinese-Domestic-DUV-emerging
    info-capture: [E] 42-year-cumulative-ASML-+-Zeiss-+-EUV-+-DUV-+-fab-+-customer-+-roadmap-+-Holistic-Lithography-data / unique-aggregate-leading-edge-fab-process-control-asymmetry
    info-disclosure: [E] required-public-disclosure-via-Euronext-+-NASDAQ / EUV-+-DUV-+-Holistic-Lithography-roadmap-+-customer-+-supply-chain-deliberately-public / [E] strategic-supply-chain-+-Carl-Zeiss-+-Cymer-+-Japanese-precision-relationship-detail-non-disclosed

  competitive:
    direct: [E] Nikon-(DUV-+-ArF-+-KrF-+-mature-+-specialty-nodes-+-~$4.8B-revenue-+-7x-smaller-than-ASML) / Canon-(DUV-+-nanoimprint-lithography-NIL-emerging-narrow-low-volume) / emerging-Chinese-domestic-DUV-+-research / Okinawa-Institute-of-Science-+-Technology-two-mirror-EUV-research-(early-+-non-commercial)
    indirect: [E] Tokyo-Electron-+-Applied-Materials-+-Lam-Research-+-KLA-(etch-+-deposition-+-inspection-adjacent-equipment-not-substitutable) / Canon-nanoimprint-lithography-+-narrow-+-low-volume-+-research-substitute / [I] alternative-compute-substrate-(photonic-+-quantum-+-on-device-+-edge)-substitution-of-CMOS-+-EUV-+-DUV-+-leading-edge-fab-position
    response-patterns: [E] decade-scale-EUV-R&D-+-Cymer-2013-acquisition-+-Carl-Zeiss-partnership-+-supply-chain-+-customer-roadmap-co-development / 2018-EUV-volume-launch-+-2019-onward-aggressive-EUV-+-DUV-+-Holistic-Lithography-+-installed-base-+-services-buildout / 2024-2025-High-NA-EUV-+-3800-series-+-Rubin-roadmap-+-fab-+-customer-co-development
    regulatory: [E] Dutch-government-export-control-+-2024-DUV-restrictions-(NXT:1970i-+-NXT:1980i) / US-+-EU-+-CHIPS-Act-+-Chips-Act-EU-+-international-+-export-control-coordination / [E] G7-+-EU-+-NATO-+-Washington-Hague-harmonization-+-architectural-constraint-via-government-export-control
    adversarial: [E] China-export-control-architectural-constraint-+-Chinese-stockpiling-2024-+-2025-revenue-collapse-from-49%-to-20% / Chinese-domestic-DUV-+-research-+-emerging-+-Canon-nanoimprint-research / [C] geopolitical-+-trade-+-export-control-+-architectural-constraint-via-government-export-control-pressure

  forces-emergence:
    - id: F1
      description: [E] 1984-April-1-ASML-founding-Eindhoven-leaky-shed-as-Philips-+-ASM-International-JV / 1985-Veldhoven-move-+-PAS-2000-+-early-wafer-stepper-substrate / 1986-Carl-Zeiss-partnership-establishment
      status-now: closed / now-substrate-only-+-promoted-into-G1-ASML-+-Zeiss-+-Cymer-supply-chain-position
    - id: F2
      description: [E] 1990s-2000s-DUV-lithography-+-immersion-DUV-+-Holistic-Lithography-+-leading-edge-fab-+-TSMC-+-Samsung-+-Intel-roadmap-co-development / progressive-lithography-+-EUV-R&D-investment-+-Cymer-+-Zeiss-+-Japanese-precision-supply-chain-buildout
      status-now: closed-as-emergence-+-promoted-into-G2-DUV-+-EUV-+-Holistic-Lithography-position
    - id: F3
      description: [E] 2010s-EUV-decade-scale-R&D-+-Cymer-2013-$1.95B-acquisition-+-Zeiss-2016-strategic-investment-(€1B)-+-EUV-NXE-3300B-volume-2014-2018 / decisive-strategic-investment-+-decade-scale-EUV-+-supply-chain-+-customer-roadmap-co-development
      status-now: closed-as-emergence / promoted-into-G3-EUV-monopoly-position
    - id: F4
      description: [E] 2018-2020-EUV-volume-+-7nm-+-5nm-+-TSMC-+-Samsung-+-Intel-+-SK-Hynix-+-EUV-buildout-+-decade-scale-fab-+-customer-roadmap-co-development / EUV-substrate-shift-+-leading-edge-fab-+-AI-+-compute-substrate-positioning
      status-now: closed-as-emergence / promoted-into-G4-EUV-+-AI-substrate-+-strategic-customer-position
    - id: F5
      description: [E] 2024-2026-High-NA-EUV-+-3800-series-+-Rubin-roadmap-+-customer-+-AI-substrate-extension / extending-EUV-monopoly-into-next-generation-architecture
      status-now: active-strengthening / fast-build-out-similar-to-tsmc-G7-+-stripe-G6-+-IQVIA-G7-+-Disney-G8-+-Microsoft-G7-+-Azure-G4-+-AWS-G4-+-Oracle-G5-+-Salesforce-G7-+-Adobe-G6-+-NVIDIA-G8-patterns

  forces-accumulated:
    - id: G1
      description: [E] 42-year-cumulative-ASML-+-Zeiss-+-Cymer-+-Japanese-precision-supply-chain-+-decade-scale-EUV-+-DUV-+-Holistic-Lithography-+-fab-+-customer-+-roadmap-position / non-replicable-without-equivalent-decade-+-multi-decade-EUV-+-DUV-+-Zeiss-+-Cymer-+-supply-chain-+-customer-+-roadmap-accumulation
      since: 1984-onward-continuous-+-acceleration-2010s-onward-EUV
      status-now: active-durable
    - id: G2
      description: [E] EUV-monopoly-position-+-100%-share-+-no-substitute-at-leading-edge / [E] structurally-distinct-from-TSMC-capability-asymmetry-via-EQUIPMENT-monopoly-position-+-decade-scale-EUV-R&D-+-Zeiss-+-Cymer-supply-chain
      since: 2014-EUV-NXE-3300B-onward-+-acceleration-2018-volume
      status-now: active-strengthening / High-NA-EUV-+-3800-series-+-Rubin-roadmap
    - id: G3
      description: [E] Carl-Zeiss-SMT-Germany-essential-optical-supplier-+-Cymer-US-light-source-acquired-2013-+-Japanese-precision-mechatronics-+-decade-scale-supply-chain-relationship-+-+-cluster-position / [E] symmetrical-strategic-customer-supplier-pattern-mirror-of-TSMC-G3-equipment-supplier-preferential-access
      since: 1986-Zeiss-+-2013-Cymer-+-decade-scale
      status-now: active-durable
    - id: G4
      description: [E] tier-1-fab-customer-+-decade-scale-strategic-customer-+-roadmap-co-development-position / 5-major-fab-customers-(TSMC-+-Samsung-+-Intel-+-SK-Hynix-+-Micron)-+-decade-scale-EUV-+-DUV-+-Holistic-Lithography-+-roadmap-co-development / [E] strategic-customer-concentration-+-tier-1-fab-co-development-position
      since: 1990s-onward-continuous-+-EUV-acceleration-2014-onward
      status-now: active-strengthening / [C] strategic-customer-concentration-similar-to-NVIDIA-G3-hyperscaler-+-Oracle-G8-Stargate-pattern
    - id: G5
      description: [E] Holistic-Lithography-+-Brion-+-Hermes-Microvision-+-installed-base-services-+-process-control-+-yield-+-metrology-+-software-+-decade-scale-customer-+-fab-+-process-+-data-asymmetry-position
      since: 2007-Brion-acquisition-+-2016-Hermes-Microvision-+-progressive
      status-now: active-strengthening
    - id: G6
      description: [E] Dutch-+-EU-+-government-+-export-control-+-CHIPS-Act-+-Chips-Act-EU-+-international-relationship-+-G7-+-Washington-Hague-harmonization-architectural-+-protective-position / [E] sovereign-strategic-significance-+-load-bearing-for-civilization-stack-pattern-(cross-corpus-pattern-#3-instance-via-different-mechanism)
      since: 2022-onward-formalization
      status-now: active-+-protective-+-export-control-architectural-constraint-double-edged
    - id: G7
      description: [E] Veldhoven-cluster-+-Dutch-+-European-+-Japanese-precision-+-engineering-+-talent-+-decade-scale-cluster-+-supply-chain-+-cultural-+-execution-discipline / Eindhoven-region-+-Veldhoven-+-Dutch-engineering-+-precision-mechatronics-cluster-position
      since: 1985-Veldhoven-onward
      status-now: active-durable
    - id: G8
      description: [E] €28B-record-2025-net-bookings-+-€7.4B-EUV-Q4-2025-+-multi-year-strategic-customer-+-roadmap-+-commitment-asset / forward-revenue-+-strategic-customer-+-multi-year-commitment-+-roadmap-economic-asset
      since: 2024-2025-onward
      status-now: active-strengthening / similar-to-NVIDIA-G8-Blackwell-backlog-+-Oracle-G8-RPO-+-strategic-customer-+-multi-year-commitment-pattern

  evolution: [E] 1984-April-1-ASML-founding-Eindhoven-leaky-shed-as-Philips-+-ASM-International-JV / 1985-Veldhoven-move / 1986-Carl-Zeiss-partnership / 1995-NASDAQ-IPO / 2007-Brion-acquisition-+-Holistic-Lithography / 2013-Cymer-$1.95B-light-source-acquisition / 2014-EUV-NXE-3300B-+-progressive-volume / 2016-Hermes-Microvision-+-Zeiss-€1B-strategic-investment / 2018-EUV-volume-+-7nm-+-leading-edge / 2020-5nm-+-EUV-+-TSMC-+-Samsung / 2022-onward-China-export-control-+-Dutch-+-US-coordination / 2024-DUV-export-restrictions-(NXT:1970i-+-NXT:1980i)-+-China-revenue-collapse / Q4-2025-record-€13.2B-bookings-+-EUV-+39% / 2025-2026-High-NA-EUV-+-3800-series-+-Rubin-roadmap / 2030-target-€71B

  closing-conditions: [I] Canon-nanoimprint-lithography-+-Okinawa-Institute-two-mirror-EUV-research-+-alternative-EUV-substitution-+-modest-near-term-probability / [I] Chinese-domestic-DUV-+-research-+-emerging-+-bypassing-export-control-+-substituting-DUV-+-EUV / [I] AI-substrate-shift-+-alternative-compute-(photonic-+-quantum-+-on-device-+-edge)-substituting-CMOS-+-EUV-+-leading-edge-fab-position / [I] strategic-customer-concentration-+-TSMC-+-Samsung-+-Intel-+-SK-Hynix-capex-pullback-+-mid-term-volatility / [I] regulatory-+-export-control-+-Dutch-+-US-+-EU-+-international-architectural-restructuring-pressure / [I] Zeiss-+-Cymer-+-supply-chain-disruption-+-Japanese-precision-supply-chain-disruption / [I] succession-+-cultural-+-execution-discipline-erosion

  trajectory: [E] strengthening / FY2025-+~50%-+-EUV-+39%-+-Q4-bookings-€13.2B-+-2030-target-€71B / [E] High-NA-EUV-+-3800-series-+-Rubin-roadmap-+-AI-substrate-+-leading-edge-fab-+-strategic-customer-extension / [C] China-export-restriction-+-strategic-customer-concentration-+-substrate-shift-+-mid-term-uncertainty

  negative-pairs:
    - id: nikon-lithography
      name: Nikon Precision (lithography equipment as ASML competitor)
      era: 1980s-present (Nikon lithography era continuous)
      similarity: [E] same-architectural-class-(lithography-equipment-+-semiconductor-+-fab-customer) / similar-era-emergence-+-DUV-+-immersion-+-leading-edge-historical-position / similar-target-tier-1-fab-customer-set
      differential: [E] Nikon-DUV-+-ArF-+-KrF-+-mature-+-specialty-nodes-only / no-EUV-+-no-Carl-Zeiss-optical-+-no-Cymer-light-source-+-no-decade-scale-EUV-R&D-investment / Nikon-~$4.8B-revenue-+-7x-smaller-than-ASML / failed-to-pivot-+-invest-in-EUV-+-co-develop-with-Zeiss-+-Cymer-+-leading-edge-fab-+-progressive-decline-+-DUV-+-mature-+-specialty-only
      diagnosis: [E] same-architectural-class-+-different-strategic-+-R&D-+-EUV-+-Zeiss-+-Cymer-+-supply-chain-+-customer-co-development-execution / Nikon's-DUV-+-failed-to-invest-EUV-decade-scale-+-Zeiss-+-Cymer-supply-chain-+-customer-co-development / ASML-+-decade-scale-EUV-R&D-+-Zeiss-+-Cymer-+-customer-co-development-prevailed
      reveals: [E] subject's-load-bearing-feature-is-the-CUMULATIVE-G1-+-G2-+-G3-+-G4-(decade-scale-EUV-R&D-+-Zeiss-+-Cymer-+-customer-co-development)-NOT-lithography-equipment-design-+-DUV-position-alone / Nikon-shows-equivalent-architectural-class-+-different-+-DUV-only-+-no-EUV-+-no-Zeiss-+-Cymer-+-no-decade-scale-investment-fails-at-leading-edge / parallel-to-OS/2-vs-Windows-+-IBM-Cloud-vs-Azure-+-globalfoundries-vs-tsmc-+-3dfx-vs-NVIDIA-architectural-discipline-patterns
    - id: tsmc-as-comparator-supplier-side-symmetry
      name: TSMC (cross-architecture comparator, symmetrical-supplier-customer relationship)
      era: 1987-present
      similarity: [E] same-architectural-class-(tier-1-semiconductor-+-capability-asymmetry-dominant-+-decade-scale-strategic-customer-+-supplier-relationship-+-AI-substrate-+-fast-growth-+-cumulative-G-force) / similar-era-emergence-+-decade-scale-+-Chang-+-Veldhoven-+-Hsinchu-cluster-+-cultural-+-execution-discipline
      differential: [E] TSMC-foundry-+-customer-position / ASML-equipment-supplier-+-customer-position / [E] symmetrical-strategic-customer-supplier-relationship-+-TSMC-G3-(equipment-supplier-preferential-access)-mirror-of-ASML-G3-+-G4-(customer-+-co-development) / different-architectural-position-+-roles-reversed
      diagnosis: [I] same-architectural-class-+-different-position-+-symmetrical-customer-supplier-roles / both-coexist-+-mutually-architectural-+-non-zero-sum-position-occupation-pattern / [E] strategic-supply-chain-+-decade-scale-customer-+-supplier-+-roadmap-co-development-+-mutual-architectural-asset
      reveals: [E] subject's-+-TSMC's-relationship-is-SYMMETRICAL-strategic-customer-supplier-+-mutually-architectural-+-mirror-G3-position / [E] cross-corpus-pattern-symmetrical-strategic-customer-supplier-relationship-confirmed-(candidate-from-NVIDIA-notes)-+-2nd-instance / [E] cross-corpus-pattern-#4-(non-zero-sum-position-occupation)-confirmed-at-15th-instance-via-DIFFERENT-architectural-positions-not-overlap / TSMC-+-ASML-occupy-mutually-architectural-positions-+-roles-reversed

  audit: 51E / 11I / 6C / 0U / 68-fields

  notes: |
    ASML introduces tier-1 lithography-equipment-+-EUV-monopoly-+-
    capability-asymmetry-dominant-+-strategic-customer-concentration
    architecture to the corpus. Schema v1.4 accommodated cleanly;
    no schema stress observed. Several observations:

    (1) **Symmetrical-strategic-customer-supplier-relationship**
    pattern candidate from NVIDIA notes CONFIRMED at 2nd instance
    via ASML/TSMC relationship. ASML G3 (Carl Zeiss + Cymer
    supplier preferential access) is mirror of TSMC G3 (equipment
    supplier preferential access). ASML G4 (tier-1 fab customer
    co-development) is mirror of TSMC G5 (advanced packaging
    customer position). Cross-corpus pattern: strategic customer-
    supplier-relationships in semiconductor architecture create
    mutually-architectural positions. Pattern candidate now
    reaches 2 instances; saturation threshold ~4-5 with potential
    NVIDIA, Cymer, Zeiss separate decompositions if pursued.

    (2) **Strategic-customer-concentration-risk** pattern from
    Oracle + NVIDIA confirmed at 3rd instance via ASML 5 tier-1
    fab customers (~90%+ leading edge concentration). Pattern
    saturation threshold reached for AI-substrate-extended +
    capability-asymmetry-dominant architectures. Worth final
    confirmation in Section F (Anthropic, OpenAI).

    (3) **Load-bearing-for-civilization-stack** pattern (cross-
    corpus pattern #3) gains 6th instance via ASML G6 (Dutch +
    EU + Washington-Hague harmonization + sovereign strategic
    significance via different mechanism than TSMC silicon shield
    or SWIFT G7). ASML protective coalition is via Dutch + EU +
    US export control coordination + CHIPS Acts + sovereign
    significance — different mechanism, same structural feature.
    Pattern now at 6 instances; well-confirmed.

    (4) **Antitrust-as-architectural-extension-barrier** count
    remains at 2 instances (Adobe-Figma + NVIDIA-Arm). ASML did
    not undergo major M&A blocked; Cymer 2013 + Hermes-Microvision
    2016 acquisitions completed without major regulatory pushback.

    (5) Cross-corpus pattern #6 (architectural-discipline-as-asset)
    NOT explicitly gained an instance via ASML — Peter Wennink CEO
    2013-2024 (11 years), Christophe Fouquet CEO 2024-present
    (transition), Veldhoven cluster + Dutch engineering cultural
    discipline is more institutional than individual CEO-led.
    Worth noting as cultural-cluster-discipline variant.

    (6) Sub-pattern D count remains at 1 (Berkshire only). ASML
    has continuous architectural evolution since 1984 with
    strategic extensions (Zeiss 1986, Cymer 2013, EUV 2014, High-NA
    2024) — not operator-voluntary-transformation pattern.

    (7) G8 (€28B record bookings) similar to NVIDIA G8 Blackwell
    backlog + Oracle G8 RPO — strategic-customer-+-multi-year-
    commitment as accumulated force confirming at 3rd instance.
    Cross-corpus pattern emerging.

    Layer C invariants applied:
    - Resource Constraints (Invariant 4): EUV R&D + Zeiss + Cymer
      + Japanese precision supply chain at decade-scale capex +
      execution capability + cluster + talent; only handful
      globally can sustain; parallels TSMC G8 + Azure G6 + AWS G7
      + Oracle G7 + NVIDIA G7 capex/resource barriers
    - Information Dynamics (Invariant 5): G1 + G5 cumulative
      ASML + Zeiss + EUV + DUV + Holistic Lithography + customer
      + fab + roadmap data asymmetry replenishment-flow
    - Competitive Response (Invariant 2): EUV monopoly active
      barrier prevents competitive response despite high
      visibility; Canon nanoimprint + Okinawa research emerging
      + low-volume + not credible substitute
    - Regulatory Response (Invariant 3): Dutch + EU + US export
      control + CHIPS Acts active regulatory + protective
      coalition; architecture preserved + extended via
      cooperation

    Layer A status: Section B hardware/semiconductors -> second
    entry (entry 22 of direct-orchestration build), decomposed
    May 2026 with v1.4 schema natively — tests tier-1-lithography-
    equipment-+-EUV-monopoly-+-capability-asymmetry-+-symmetrical-
    strategic-customer-supplier-relationship profile.
```

## Prose Synthesis

**Identification:** ASML Holding N.V. is the tier-1 lithography equipment + EUV monopoly + DUV-dominant architecture founded April 1, 1984 in Eindhoven as Philips + ASM International joint venture; Carl Zeiss partnership since 1986; Cymer 2013 acquisition; Veldhoven HQ since 1985. FY2025 net sales €32.7B (+~50%); EUV €11.6B (+39%, 48% of system revenue); FY2026 guidance €36-40B; record Q4 2025 bookings €13.2B; 2030 revenue target €71B; ~$300B market cap. Entry scope is full ASML Holding architecture including EUV + DUV + Holistic Lithography + Carl Zeiss optical + Cymer light source supply chain.

**Structural position:** ASML occupies tier-1 lithography equipment + EUV monopoly + capability-asymmetry-dominant + strategic-customer-concentration position. 100% EUV share; no substitute at leading edge; Canon + Nikon competitive in DUV mature nodes only. 5 tier-1 fab customers (TSMC + Samsung + Intel Foundry + SK Hynix + Micron) representing ~90%+ leading-edge concentration. Symmetrical strategic-customer-supplier-relationship with TSMC (G3 mirror of TSMC's equipment supplier preferential access).

**Force-topology dependence:** All five emergence forces (F1-F5) closed; F5 (High-NA EUV + 3800-series + Rubin roadmap) actively strengthening. Eight accumulated forces operate: G1 42-year cumulative ASML + Zeiss + supply chain position, G2 EUV monopoly 100% share, G3 Carl Zeiss + Cymer + Japanese precision supply chain (mirror of TSMC G3), G4 tier-1 fab customer + roadmap co-development (strategic concentration risk), G5 Holistic Lithography + installed base services + process control, G6 Dutch + EU + Washington-Hague export control + sovereign strategic significance (load-bearing-for-civilization-stack), G7 Veldhoven cluster + engineering discipline, G8 €28B record bookings + multi-year commitment asset. Trajectory strengthening with FY2025 ~50% growth + 2030 €71B target; mid-term China export restriction + strategic customer concentration + alternative compute substrate uncertainty.

**Negative-pair insights:** Nikon Precision (DUV mature nodes only, ~$4.8B revenue, 7x smaller than ASML) and TSMC (cross-architecture comparator with symmetrical supplier-customer relationship) bracket the comparison space. Nikon reveals subject's load-bearing feature is cumulative G1+G2+G3+G4 (decade-scale EUV R&D + Zeiss + Cymer + customer co-development) — NOT lithography equipment design alone. TSMC confirms symmetrical-strategic-customer-supplier-relationship pattern (candidate from NVIDIA notes) at 2nd instance — ASML G3 mirror of TSMC G3; cross-corpus pattern #4 confirmed at 15th instance via different architectural positions not overlap. Strategic-customer-concentration-risk pattern confirmed at 3rd instance (Oracle + NVIDIA + ASML).

**Epistemic profile:** Strong evidence base (51 [E] / 11 [I] / 6 [C] / 0 [U] across 68 fields). Contested fields cover China export restriction trajectory, alternative compute substrate substitution timing, strategic customer concentration risk, Canon nanoimprint emerging substitution. Zero [U] fields. No schema stress observed. New cross-corpus pattern candidate confirmed: symmetrical-strategic-customer-supplier-relationship (2 instances now).
