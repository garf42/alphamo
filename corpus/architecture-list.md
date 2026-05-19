
# Layer A Architecture List — AlphaMo Corpus

**Purpose:** Curated set of value-capture architectures for Layer A
decomposition via the RAD skill. Each entry will be processed by
Super-dispatched Claude Code instances to produce one corpus entry.

**Curation principles:**
- Spans industries, eras, and outcome categories
- Includes failed architectures explicitly (not just survivors) —
  primary survivorship-bias countermeasure at the list level
- Eras span ~1880 to present, with deliberate sampling across
  pre-electrification, electrification, computing, internet, mobile,
  and AI regimes
- Includes architectures with structurally distinct profiles to
  test schema coverage (forcibly-restructured, defunct-as-subject,
  two-sided platforms, infrastructure abstractions)

**Status legend:**
- `durable` — operating with apparent long-term stability
- `pressured` — operating but under significant current force-topology pressure
- `transforming` — actively reconfiguring in response to pressure
- `restructured` — forcibly broken up or substantially restructured
  by regulatory or court action
- `defunct` — no longer operating, included as subject not pair
- `emerging` — recent / unproven durability

**Target count:** ~60 entries across the list, of which ~40-50 are
expected to produce viable RAD outputs after QA. Some entries may
decline at Phase 1 (split recommendation for conglomerate scope)
or produce low-evidence entries; QA will filter.

**Sequential vs parallel dispatch:**
- First 5 entries (marked `[SEQ]`) run sequentially with chat-side
  review for schema issues
- Remaining entries can run in parallel (recommended 3-5 concurrent)
- Strategic entries chosen for first 5 stress-test specific schema
  profiles


---

## Section A — Sequential first batch (schema validation)

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| visa-interchange | Visa Interchange | payments | 1958-present | durable | Tests two-sided platform schema handling; pure network-effect substrate | Tests counterparty schema for two-sided dynamics |
| standard-oil | Standard Oil (Trust) | energy/oil | 1870-1911 | restructured | Tests forcibly-restructured profile; canonical bottleneck-control case | Pre-dissolution entity scope; successors are separate entries if added later |
| kodak-film | Kodak (chemical film business) | imaging/consumer-goods | 1888-2012 | defunct | Tests defunct-as-subject; substrate-shift failure mode at scale | Chemical film business specifically, not full Kodak corporate entity |
| tsmc | TSMC | semiconductors | 1987-present | durable | Tests capability-asymmetry-dominant architecture; current AI-era critical infrastructure | Foundry business only |
| coca-cola | Coca-Cola Company | consumer-goods/beverage | 1892-present | durable | Tests identity/trust asymmetry-dominant architecture across longest possible time horizon | Branded-product business |

## Section B — Durable survivors (broad coverage)

### Finance / payments

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| mastercard | Mastercard | payments | 1966-present | durable | Visa-adjacent network architecture; comparison case for two-sided platforms | Network business only |
| swift-network | SWIFT | payments/messaging | 1973-present | durable | International payment messaging standard; standard-setting position | Cooperative governance structure noteworthy |
| stripe | Stripe | payments/infrastructure | 2010-present | durable | Infrastructure abstraction layer for online payments; thin-operator-enabler |  |
| nyse | New York Stock Exchange | finance/exchange | 1817-present | durable | Exchange infrastructure; oldest in list |  |
| cme-group | CME Group | finance/exchange | 1898-present | durable | Derivatives exchange infrastructure |  |
| moodys | Moody's | finance/ratings | 1909-present | durable | Information-asymmetry architecture with regulatory protection | Ratings business only |
| berkshire-hathaway | Berkshire Hathaway | insurance/conglomerate | 1965-present (in current form) | durable | Capital allocation architecture; tests insurance/float model | Insurance + capital allocation; not operating subsidiaries individually |
| goldman-sachs | Goldman Sachs | finance/investment-banking | 1869-present | durable | Investment banking + trading architecture |  |
| jp-morgan | JPMorgan Chase | finance/banking | 1799-present (Chase lineage) | durable | Universal bank architecture |  |
| lloyds-of-london | Lloyd's of London | insurance | 1688-present | durable | Specialty insurance marketplace; very long time horizon |  |

### Information / data / media

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| sp-global | S&P Global Ratings | finance/ratings | 1860-present | durable | Ratings duopoly with Moody's | Ratings business specifically |
| nielsen | Nielsen | media/data | 1923-present | transforming | TV/audience measurement; testing whether durable or transforming category | Audience measurement business |
| ims-health | IQVIA (formerly IMS Health) | healthcare/data | 1954-present | durable | Pharma sales data aggregation |  |
| disney-ip | Disney IP Library | media/entertainment | 1923-present | durable | Identity/IP-asset asymmetry architecture | IP library and franchise business; not theme parks |

### Software / tech

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| microsoft-windows-office | Microsoft Windows + Office | software | 1985-present | durable | File-format network-effect + workflow lock-in | Productivity suite scope; not Azure |
| azure | Microsoft Azure | cloud-infrastructure | 2010-present | durable | Cloud infrastructure abstraction |  |
| aws | Amazon Web Services | cloud-infrastructure | 2006-present | durable | Pioneer of cloud infrastructure abstraction |  |
| oracle-database | Oracle Database | software | 1979-present | durable | Switching-cost-dominant architecture; enterprise lock-in | Database business; not full Oracle |
| salesforce | Salesforce | software/saas | 1999-present | durable | CRM SaaS pioneer; workflow integration architecture |  |
| adobe-creative-cloud | Adobe Creative Cloud | software | 2013-present (subscription era) | durable | Subscription transformation of previously licensed software | Subscription era specifically |
| google-search | Google Search | internet/search | 1998-present | durable | Tests information-aggregation + advertising-extraction model | Search + ads; not Cloud or YouTube |
| meta-facebook | Meta (Facebook product) | social/internet | 2004-present | pressured | Social network with current AI-era pressure | Facebook + Instagram core social; not Reality Labs |
| linkedin | LinkedIn | social/professional | 2003-present | durable | Professional network; specific case of network-effect architecture |  |

### Hardware / semiconductors / industrial

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| nvidia | NVIDIA | semiconductors | 1993-present | durable | Current capability-leader in AI compute |  |
| asml | ASML | semiconductors/equipment | 1984-present | durable | Lithography monopoly; capability bottleneck |  |
| boeing-airbus-duopoly | Boeing | aerospace | 1916-present | pressured | Half of aircraft duopoly; testing duopoly dynamics | Boeing specifically; Airbus could be separate entry if needed |
| ford-motor | Ford Motor Company | automotive | 1903-present | durable | Mass-production automotive; centenarian industrial |  |
| tesla | Tesla | automotive/energy | 2003-present | durable | Recent durable industrial; vertical integration test |  |
| general-electric | General Electric (Edison era) | industrial | 1892-1980s peak | transforming | Tests very-old-architecture profile; conglomerate-era industrial |  |

### Consumer / retail / luxury

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| walmart | Walmart | retail | 1962-present | durable | Logistics-scale + supplier-power retail | US retail business |
| costco | Costco | retail/membership | 1983-present | durable | Membership-fee architecture; subscription on retail |  |
| amazon-retail | Amazon Retail | retail/internet | 1994-present | durable | Internet-era retail flywheel | Retail specifically; AWS is separate |
| apple-iphone | Apple iPhone + iOS | consumer-electronics | 2007-present | durable | Hardware + software + identity integration |  |
| lvmh | LVMH | luxury | 1987-present (in current form) | durable | Luxury conglomerate; identity-architecture exemplar |  |
| hermes | Hermès | luxury | 1837-present | durable | Single-brand luxury durability; very long horizon |  |
| rolex | Rolex | luxury/watches | 1905-present | durable | Identity + scarcity-engineering architecture |  |
| ferrari | Ferrari | automotive/luxury | 1947-present | durable | Scarcity + identity combination |  |
| de-beers | De Beers (cartel era) | jewelry/mining | 1888-2000s | transforming | Tests cartel-era architecture; supply control + manufactured-demand-identity | Cartel-era specifically; current De Beers is different architecture |
| procter-gamble | Procter & Gamble | consumer-goods | 1837-present | durable | CPG portfolio architecture; very long horizon |  |

## Section C — Operating but pressured / transforming

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| paypal | PayPal | payments | 1998-present | pressured | Network-effect erosion through multi-homing; current asymmetric pressure | Tests "moat-eroding" architecture |
| netflix | Netflix | media/streaming | 2007-present (streaming era) | pressured | Subscription content; current cost-of-content pressure | Streaming era; not DVD-by-mail |
| spotify | Spotify | media/streaming | 2008-present | pressured | Subscription music; unit economics under label pressure |  |
| ebay | eBay | internet/marketplace | 1995-present | transforming | Two-sided marketplace; long-term erosion case |  |
| intel | Intel | semiconductors | 1968-present | pressured | Capability-asymmetry erosion; ASML/TSMC outflanking |  |
| hims-hers | Hims & Hers Health | healthcare/telehealth | 2017-present | transforming | March 2026 pivot to branded GLP-1; Medvi-adjacent transformation case |  |
| refinitiv-eikon | Refinitiv Eikon (LSE Group) | finance/data | 1973-present (Reuters lineage) | pressured | Bloomberg's main competitor; structurally similar but weaker durability | Tests near-miss case |
| walgreens-boots-alliance | Walgreens Boots Alliance | retail/pharmacy | 1901-present | pressured | Retail pharmacy under multiple pressures | Current state |
| twitter-x | X (formerly Twitter) | social/internet | 2006-present | transforming | Deliberate transformation case; founder-driven restructuring |  |

## Section D — Forcibly restructured (anti-trust / regulatory)

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| att-pre-1984 | AT&T (Bell System pre-1984) | telecom | 1885-1984 | restructured | Canonical regulated-monopoly restructuring | Pre-1984 monopoly specifically |
| microsoft-antitrust-era | Microsoft (1990s antitrust era) | software | 1991-2001 (case-specific) | restructured | Antitrust without dissolution; consent-decree restructuring | Antitrust period specifically — tests narrow-era scoping |
| aig-2008 | AIG | insurance | pre-2008 | restructured | Forced restructuring via government rescue; financial-crisis case | Pre-2008 entity |
| ibm-1980s | IBM (pre-1980s mainframe era) | computing | 1956-1985 | restructured | 1956 consent decree + ongoing antitrust pressure shaped trajectory | Mainframe-era architecture |

## Section E — Failed architectures as subjects

These appear as primary subjects (not just negative pairs in other entries), receiving full RAD decomposition to populate Layer D anti-pattern source material.

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| blockbuster-video | Blockbuster Video | retail/rental | 1985-2014 | defunct | Substrate-shift failure; canonical AI-replaced-by-streaming case |  |
| polaroid | Polaroid | imaging | 1937-2008 | defunct | Capability-asymmetry-aged-out; instant-photography substrate vanished |  |
| sears | Sears | retail | 1893-2018 | defunct | Outcompeted-by-superior-composition (Amazon era) |  |
| yahoo | Yahoo (search/portal era) | internet | 1994-2017 acquisition | defunct | Position-substituted by Google; portal-vs-search era case |  |
| blackberry | BlackBerry | mobile/consumer-electronics | 1999-2016 (phone business) | defunct | Iconic outcompetition case; iPhone substitution | Phone business specifically |
| nokia-phones | Nokia (handset business) | mobile/consumer-electronics | 1992-2014 | defunct | Parallel to BlackBerry; different substrate-shift case | Handset business; not networks |
| pets-com | Pets.com | internet/retail | 1998-2000 | defunct | Conservation-of-value violation case (insufficient V) |  |
| webvan | Webvan | internet/grocery-delivery | 1996-2001 | defunct | Resource-constraints violation case |  |
| moviepass | MoviePass | subscription/media | 2011-2020 | defunct | Conservation-of-value violation; explicit negative-X case |  |
| wework | WeWork | real-estate/workspace | 2010-2023 (collapse) | defunct | Resource-constraints + Conservation violation; long-term-lease-vs-revenue mismatch | Pre-restructuring entity |
| theranos | Theranos | healthcare/diagnostics | 2003-2018 | defunct | Time-consistency defection; canonical visible-defection case |  |
| ftx | FTX | crypto/exchange | 2019-2022 | defunct | Time-consistency defection; rapid collapse case |  |
| enron | Enron | energy/trading | 1985-2001 | defunct | Time-consistency + accounting defection |  |
| lehman-brothers | Lehman Brothers | finance | 1850-2008 | defunct | 2008 collapse; tests financial-crisis-era failure |  |
| ltcm | Long-Term Capital Management | finance/hedge-fund | 1994-2000 | defunct | Information-dynamics failure; model-failure case |  |
| quotron | Quotron Systems | finance/data-terminals | 1957-1991 | defunct | Bloomberg negative-pair, but warrants own entry for Layer D | Tests negative-pair-as-subject pattern |
| telerate | Telerate | finance/data-terminals | 1969-1998 | defunct | Bloomberg negative-pair, but warrants own entry | Tests negative-pair-as-subject pattern |
| drugstore-com | Drugstore.com | internet/retail | 1998-2011 | defunct | Medvi negative-pair; warrants own entry for Layer D | Tests negative-pair-as-subject pattern |
| myspace | Myspace | social/internet | 2003-2008 (peak collapse) | defunct | Social-network failure; pre-Facebook era |  |
| buzzfeed-news | BuzzFeed News | media/digital | 2006-2023 | defunct | Digital-media-business-model failure case | News business specifically |

## Section F — Emerging / recent (unproven durability)

| Slug | Name | Industry | Era | Status | Rationale | Scope/Notes |
|------|------|----------|-----|--------|-----------|-------------|
| medvi | Medvi | healthcare/telehealth | 2024-present | emerging | Already decomposed; included for completeness | (Skip in bulk dispatch; entry exists from chat-side validation) |
| openai-chatgpt | OpenAI (consumer ChatGPT) | ai/consumer | 2022-present | emerging | Current-era AI consumer architecture | ChatGPT/consumer; not API or enterprise |
| anthropic-claude | Anthropic (Claude product) | ai/foundation-models | 2021-present | emerging | Self-referential entry; tests AI-vendor architecture | Foundation model business |
| stripe-atlas | Stripe Atlas | fintech/infrastructure | 2016-present | emerging | Adjacent to Stripe; testing thin-wrapper-on-regulatory case |  |
| substack | Substack | media/creator | 2017-present | emerging | Creator-economy infrastructure; commission-on-recurrence model |  |

---

## Coverage check

**By outcome:**
- Durable: ~25 entries (Sections A + B)
- Pressured/transforming: ~9 entries (Section C)
- Restructured: 4 entries (Section D)
- Defunct as subjects: ~20 entries (Section E)
- Emerging: ~5 entries (Section F)
- **Total: ~63 entries**

**By era (approximate):**
- Pre-1900: ~6 entries (Hermès, Lloyd's, S&P, Moody's, Standard Oil, NYSE, JP Morgan, P&G, Hermès)
- 1900-1945: ~10 entries (Ford, GE, Coca-Cola, Rolex, IBM-era, Boeing, Disney, AT&T-era, Lehman-era, Polaroid)
- 1945-1980: ~10 entries (Walmart, Berkshire, McDonald's-era candidates, Costco, etc.)
- 1980-2000: ~15 entries (Bloomberg, Microsoft, Oracle, TSMC, ASML, Adobe, Amazon, eBay, NVIDIA, etc.)
- 2000-2015: ~12 entries (Google, Facebook, Apple-iPhone, AWS, LinkedIn, Tesla, Salesforce, Stripe, etc.)
- 2015-present: ~10 entries (Medvi, Anthropic, OpenAI, Hims, Twitter-X transformation, Substack, etc.)

**By industry (approximate count):**
- Finance/payments/data: ~12
- Software/cloud/internet: ~12
- Healthcare/pharma: ~3 (light — may want to add a major pharma like Pfizer/Roche if coverage matters)
- Consumer goods/retail/luxury: ~10
- Industrial/auto/aerospace: ~5
- Semiconductors/hardware: ~4
- Media/entertainment: ~4
- Telecom: ~2 (light — may want to add Verizon or another)
- Insurance: ~3
- Energy: ~1 (light — Standard Oil only; may want to add Saudi Aramco or ExxonMobil)
- Other (real-estate, crypto, etc.): ~3

**Gaps surfaced:**
- Energy is light (1 entry); consider adding Saudi Aramco or post-1911 ExxonMobil
- Healthcare/pharma is light (3 entries); consider adding Pfizer, Roche, or Novo Nordisk
- Telecom is light (2 entries); consider adding modern Verizon or T-Mobile
- Pre-1900 era is light; could add more very-old architectures (e.g., the British East India Company as historical reference, or older specific companies)

**Note on coverage:** This list is a starting point. Add or remove
based on judgment. Pruning aggressively to ~40-50 entries is fine
if some entries seem redundant; expanding to ~70+ is also fine if
specific categories need more depth.


---

## Suggested processing order

1. Section A (sequential, chat-side review): 5 entries
2. Section E failures (parallel batch 1): processes survivorship-
   bias countermeasure entries early, generating Layer D source
   material before further survivor entries
3. Section D restructured (parallel batch 2): tests
   forcibly-restructured schema profile
4. Section C pressured (parallel batch 3): tests current-pressure
   schema profile
5. Section B durables (parallel batch 4, largest): bulk survivor
   entries with schema already validated
6. Section F emerging (parallel batch 5): tests young-architecture
   schema profile

This ordering ensures the structural-profile-stress-test entries
run early. If a schema gap surfaces, it surfaces before bulk
durable entries are dispatched (which would be the largest waste
to rerun).

