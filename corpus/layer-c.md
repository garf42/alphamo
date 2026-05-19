
# Layer C — Substrate Invariants

## What this is

Layer C of the AlphaMo corpus encodes substrate-level structural
constraints that any value-capture architecture must satisfy
regardless of industry, era, or specific composition. These are
the AlphaFold-architectural-priors analog — the equivalent of
triangle inequality, equivariance, and the residue-gas
representation that AlphaFold encoded directly into its neural
network rather than learning from data.

The invariants are not primitives the proposer composes. They are
constraints the proposer reasons within. Just as AlphaFold's
triangle multiplicative update enforces that any 3D structure
must satisfy the triangle inequality on distances between three
points, Layer C constraints enforce that any candidate
value-capture architecture must satisfy a small set of structural
relationships.

The corpus's Layer C is a fixed small set, not a large catalog.
Six candidate invariants are currently identified. The set may
expand if Layer A construction surfaces patterns that require
additional invariants to characterize, but the working assumption
is that the load-bearing invariants are few.


## How Layer C differs from Layer A

- **Time-invariant.** Layer A entries are tied to specific eras
  and force-topology conditions. Layer C invariants hold across
  eras by construction. If an invariant only holds under certain
  conditions, those conditions must be made explicit in the
  bounding-conditions field — but the invariant itself is
  time-invariant given those bounds.
- **General, not entity-specific.** Layer A decomposes specific
  architectures. Layer C makes general claims that apply to all
  architectures.
- **Predictive.** Layer A is descriptive. Layer C is predictive —
  each invariant generates predictions about which architectures
  will fail in which ways. Without testable predictions, an
  invariant is decoration, not substrate.
- **Falsifiable.** Each invariant must specify what would disprove
  it. An invariant that cannot be falsified is closer to a
  tautology than a structural constraint.


## Schema per invariant

```yaml
- id: <slug>
  name: <display>
  type: substrate-invariant

  statement: [E|I|C] <precise statement of the invariant — what it asserts>

  mechanism: [E|I|C] <why the invariant holds — the structural argument,
    grounded in identity, game theory, information theory, or
    resource constraints. Cite the theoretical tradition (Coase,
    Akerlof, Schumpeter, etc.) where applicable.>

  manifestations:                        # how the invariant shows up in observable value-capture
    - [E|I|C] <one manifestation>
    - [E|I|C] <another manifestation>
    - ...

  predicted-failures:                    # what failure modes the invariant predicts
    - [E|I|C] <one predicted failure mode>
    - ...

  violation-examples:                    # real cases where the invariant was apparently violated, with resolution
    - <case-slug>:
        what: <what happened>
        outcome: <how it resolved — usually toward invariant compliance>
    - ...

  edge-cases:                            # boundary conditions where the invariant's application is non-trivial
    - <case>: <explanation>
    - ...

  bounding-conditions: |                 # conditions under which the invariant holds and when it might not
    <prose>

  falsifier: |                           # what would disprove the invariant
    <prose specifying what evidence would force retraction>

  notes: |                               # free-form notes, especially relationships to other invariants
    <prose>
```


## Anti-patterns

- **Tautological invariants.** If the invariant is true by
  definition (e.g., "successful architectures capture value"), it
  is doing no structural work. The constraint must be falsifiable
  in principle.

- **Industry-specific invariants.** If the invariant only holds
  for one industry or era, it is a Layer A or Layer B observation,
  not a substrate constraint. Substrate invariants apply across
  conditions.

- **Manufactured violation examples.** Each invariant requires at
  least one real historical case where an architecture appeared
  to violate it and how that resolved. Manufactured examples
  defeat the falsification discipline.

- **Hidden tautology via fudge factors.** If the invariant has so
  many edge cases and bounding conditions that any apparent
  violation can be explained away, it has degraded into a
  tautology. Edge cases should be principled exceptions, not
  escape hatches that protect the invariant from disconfirmation.

- **Importing post-hoc strategy vocabulary.** Substrate invariants
  must be derivable from identity, game theory, information
  theory, or resource constraints — first principles. If the
  invariant requires post-hoc strategy literature (Porter's five
  forces, 7 Powers, VRIN) to defend, it is not substrate-level.


---

## Invariants

### 1. Conservation of Value

```yaml
- id: conservation-of-value
  name: Conservation of Value
  type: substrate-invariant

  statement: [E] An architecture cannot extract more rent than is
    created in the underlying flow it captures, less the minimum
    value counterparties require to keep participating. Total rent
    extracted (X) plus counterparty surplus (Y) is bounded by total
    value created (V): X + Y ≤ V, with Y ≥ Y_min (counterparty
    floor below which participation ceases).

  mechanism: [E] Identity-based, derived from the accounting
    identity that value extracted plus value retained cannot
    exceed value created. The counterparty-floor constraint
    (Y ≥ Y_min) is game-theoretic — rational counterparties exit
    when their participation surplus falls below their next-best
    alternative. The combination bounds extractable rent at
    V - Y_min. Coase (1937) on transaction costs and the bounds
    of firm rent extraction. Standard economic surplus analysis.

  manifestations:
    - [E] High-margin underlying flows allow more rent extraction
      than low-margin flows, regardless of architectural cleverness
    - [E] Commodity flows produce commodity-level rent regardless
      of architectural sophistication on top
    - [E] Counterparty alternatives raise Y_min and compress
      extractable rent — competitive substitutes reduce the
      architecture's rent ceiling
    - [I] Architectures that appear to extract more than V - Y_min
      are typically operating with external subsidies, extracting
      from externalities not visible in the primary flow, or in
      transitional pre-equilibrium states
    - [E] Network effects raise V (by increasing value created
      through coordination) and can also raise Y_min for stayers
      while creating Y_min asymmetries for leavers — a structural
      reason network-effect architectures can extract more rent

  predicted-failures:
    - [E] Architectures attempting extraction above V - Y_min
      experience counterparty disengagement
    - [E] Subsidized flows collapse when subsidy ends if the
      unsubsidized extraction would exceed V - Y_min
    - [E] Architectures with high cost-of-architecture (capital
      intensity, operating overhead) and modest underlying V
      cannot extract enough rent to cover their own cost
      structure, regardless of structural position quality
    - [I] AI-era compression effect: when capability asymmetry
      that previously created V (specialized analysis, expert
      orchestration) becomes accessible to counterparties
      directly, V from architecture-mediation falls and rent
      compresses accordingly

  violation-examples:
    - moviepass-2017-2020:
        what: charged $9.95/month while paying theaters full ticket
          price per movie watched; effectively extracted X negative,
          subsidizing the flow from VC capital
        outcome: collapsed in 2020 when VC subsidy ended;
          unsubsidized unit economics could not satisfy
          conservation
    - webvan-1999-2001:
        what: attempted to extract grocery-retail margins (V
          relatively small) while operating capital-intensive
          delivery infrastructure (cost-of-architecture large);
          extraction needed to cover cost exceeded available V
        outcome: collapsed within 2 years of IPO; subsequent
          attempts (Instacart, AmazonFresh) succeeded only with
          different architectures (asset-light Instacart) or much
          larger V capture (Amazon-scale logistics amortization)
    - many-2010s-dtc-brands:
        what: customer-acquisition-cost via paid social exceeded
          customer-lifetime-value at unsubsidized prices;
          extraction below sustainable level
        outcome: serial collapse as VC funding rounds dried up;
          surviving DTC brands either reduced CAC dramatically or
          increased pricing power through brand identity (raising V)

  edge-cases:
    - externality-extraction: Ad-supported "free" services
      (Google search, Facebook) appear to extract more than the
      visible primary flow allows because they extract from a
      different value stream (advertiser willingness-to-pay for
      attention) layered on top of the apparent primary flow
      (user search results). Conservation holds when both flows
      are accounted for.
    - time-shifted-extraction: Startups operating at apparent
      negative-rent during growth phase rely on the prediction
      that future V will rise to cover present extraction
      deficits. Conservation holds in expectation if the future
      V actually materializes; failures here are usually wrong
      predictions of future V, not invariant violations.
    - third-party-subsidized: Strategic investors, governments,
      or platform sponsors can subsidize flows where unsubsidized
      extraction would violate conservation. The invariant holds
      in the underlying flow; the apparent violation lives in the
      subsidy layer.
    - winner-take-most-dynamics: In some markets the value V
      created depends recursively on the architecture's position
      (network effects, standard-setting). V can rise as the
      architecture's position strengthens, creating apparent
      conservation violations in static snapshots that resolve in
      dynamic analysis.

  bounding-conditions: |
    The invariant holds in equilibrium and over the long run.
    Short-term and transitional periods can show apparent
    violations that resolve toward the bound. Architectures that
    appear to violate the invariant in steady-state operation are
    usually (a) extracting from a different flow than the visible
    one (externality extraction), (b) operating with external
    subsidies, or (c) in genuine transitional states that will
    resolve. The invariant does not specify the rate at which
    apparent violations resolve toward equilibrium; that can be
    slow, especially when subsidies persist.

  falsifier: |
    The invariant would be disproven by a clear case of an
    architecture extracting more rent than the underlying flow's
    value (correctly measured, including all externalities and
    subsidies) for more than ~5 years in steady state without
    counterparty disengagement. To date no such case has been
    identified. Apparent violations under shorter time horizons
    or with hidden subsidies are not disconfirming; they are
    instances the invariant predicts will resolve.

  notes: |
    Most fundamental of the substrate invariants. Conservation of
    value is to Layer C what triangle inequality is to AlphaFold's
    pair representation: a structural constraint derived from
    identity that any valid architecture must satisfy. Other
    invariants partially decompose into this one — competitive
    response (invariant 2) is partly conservation pressure
    transmitted through counterparty alternatives raising Y_min;
    resource constraints (invariant 4) are partly conservation
    pressure on the architecture's own cost side. The
    foundational character means violations of this invariant are
    typically diagnosed by reduction — if an architecture appears
    to violate it, the analysis should locate the missing flow,
    subsidy, or time horizon that resolves the violation.

    Connection to Layer A: Medvi's negative pair drugstore.com
    failed by conservation — extraction needed to cover dot-com-era
    cost-of-architecture exceeded available V in online pharmacy
    retail. The invariant predicted the failure mode that Layer A
    described as "CAC exceeded margin without AI compression."
```

---

### 2. Competitive Response

```yaml
- id: competitive-response
  name: Competitive Response
  type: substrate-invariant

  statement: [E] Above-commodity rent extraction creates economic
    incentive for entry. Sustained rents require either active
    barriers to entry or rent magnitude small enough to fall below
    attention thresholds of potential entrants. Rent without
    barriers and above attention thresholds decays through
    competitive entry.

  mechanism: [E] Schumpeter (entrepreneurial profit attracts
    entrants who dissipate it through "perennial gale of creative
    destruction"). Standard IO economics: in markets without
    barriers, Bertrand competition drives rent to zero; with
    imperfect substitution rent is bounded by substitution cost.
    Game theory of entry: rational entrants compare expected rent
    after entry to cost of entry; entry occurs when expected rent
    > entry cost. The Medvi/sub-attention-threshold strategy is
    the architectural exploitation of the rational-entry condition.

  manifestations:
    - [E] Rent magnitude positively correlates with entry pressure
      — larger visible rent attracts more entry attempts
    - [E] Below-attention-threshold architectures can sustain
      modest rent indefinitely without active barriers
    - [E] High-visibility architectures must have active barriers
      (network effects, switching costs, regulatory moats,
      capability gaps that resist arbitrage) or face rent compression
    - [E] Speed of competitive response is increasing in rent
      visibility and decreasing in entry cost — low-capital
      categories see rapid compression
    - [I] Recurring rent extraction is more attention-attracting
      than one-shot — durable rent extraction signals to potential
      entrants that the position is worth contesting

  predicted-failures:
    - [E] High-rent high-visibility architectures without barriers
      experience entry-driven rent compression
    - [E] Barriers that erode (regulatory windows closing,
      capability arbitrage windows compressing) see rent
      compression even without explicit competitor action
    - [I] Architectures that publicly signal extraction magnitude
      (financial filings, press coverage of profits) accelerate
      entry pressure relative to private architectures

  violation-examples:
    - retail-brokerage-commissions:
        what: traditional brokerages extracted $5-30/trade
          commissions for decades; appeared sustained
        outcome: Robinhood's zero-commission entry forced
          industry-wide compression to zero in <5 years (2013-2019)
    - uber-for-x-2014-2018:
        what: many startups attempted "uber for X" categories at
          high visibility; entry pressure exceeded available rent
        outcome: most failed within 3-5 years as competitive
          response compressed unit economics below sustainability

  edge-cases:
    - sub-attention-rent: Architectures extracting rent too small
      to motivate entry can persist indefinitely. This is the
      structural rationale for the Medvi-style sub-visibility
      strategy mentioned across multiple Layer A contexts.
    - active-barriers: Network effects (Visa, Bloomberg chat),
      regulatory moats (banking, telecoms), capability gaps
      (TSMC process leadership), brand identity (luxury goods)
      are barrier types that resist competitive response.
    - latency-in-entry: Markets with high entry capital cost see
      slower competitive response but eventual entry. Latency is
      not absence of the invariant; it is a time-shifted version.

  bounding-conditions: |
    The invariant operates in markets where information about rent
    extraction is observable and entry is permitted. In opaque
    markets (private contracts, dark pools) or regulated markets
    where entry is restricted, the invariant operates with
    extended latency or through different channels (regulatory
    response, Invariant 3).

  falsifier: |
    The invariant would be disproven by a clear case of an
    architecture extracting visibly high rent in a market with
    free entry, no active barriers, and no sub-attention claim,
    sustained for >15 years without competitive compression. To
    date none identified.

  notes: |
    Closely paired with Conservation of Value (Invariant 1):
    competitive response is the dynamic mechanism by which rent
    is bounded below V - Y_min over time. Counterparty alternatives
    raise Y_min (Conservation) when competitive entry expands the
    alternative set (Competitive Response). Sub-attention strategy
    is the architectural response common to both invariants.
    Bloomberg's accumulated barriers (G1-G5 in its Layer A entry)
    illustrate the active-barrier path; Medvi's current position
    illustrates the sub-attention-threshold strategy (though the
    NYT profile suggests it is now exceeding the threshold and
    expected to see compression).
```

---

### 3. Regulatory Response

```yaml
- id: regulatory-response
  name: Regulatory Response
  type: substrate-invariant

  statement: [E] Concentrated rent extraction with diffuse costs
    invites regulatory action. The probability of regulatory
    intervention is increasing in extraction concentration, total
    social cost imposed, and political salience of affected
    parties. Architectures imposing diffuse costs on politically
    salient groups face faster regulatory response than those
    with diffuse benefits or politically marginal affected groups.

  mechanism: [E] Olson (Logic of Collective Action — concentrated
    benefits and diffuse costs produce asymmetric political
    organization). Stigler (regulatory capture — once regulation
    is established, incumbents shape it). Political economy: the
    cost of political action is sufficient that it requires
    concentrated affected parties or high enough salience to
    organize diffuse ones. Public choice theory: regulators
    respond to organized interests, not aggregate welfare.

  manifestations:
    - [E] Standard Oil 1911 anti-trust dissolution — extreme
      concentration produced political response
    - [E] AT&T 1984 break-up — analogous concentration response
    - [E] Tech platform antitrust pressure 2020+ — concentration
      and political salience producing slow regulatory response
    - [E] GLP-1 compounding closure 2025-2026 — Medvi context —
      regulatory response activated when category reached
      visibility threshold and branded-manufacturer interests
      (Novo, Lilly) became organized counterparties
    - [E] Architectures operating below regulatory attention
      threshold (most small businesses, niche categories) can
      persist for decades without regulatory contact

  predicted-failures:
    - [E] High-visibility high-extraction architectures with
      diffuse counterparty harm face regulatory pressure on
      timescales of years to decades
    - [E] Architectures depending on regulatory loopholes face
      closure when the loophole closes (the loophole is itself a
      window-dependent force-topology element)
    - [I] Architectures harming politically organized groups
      (workers, small businesses, manufacturers with lobbying
      capacity) face faster regulatory response than those
      harming diffuse consumers

  violation-examples:
    - standard-oil-1870-1911:
        what: extreme oil-refining concentration sustained for
          decades; appeared invulnerable
        outcome: 1911 Supreme Court dissolution; successor
          entities (Exxon, Mobil, Chevron) still highly profitable
          but in modified structure
    - medvi-2024-2026:
        what: compounded GLP-1 telehealth category exploited
          shortage-list legal pathway; visible architectural
          success
        outcome: FDA closed shortage pathway Feb 2025, expanded
          enforcement 2025-2026, proposed 503B bulks-list closure
          April 2026; regulatory response activated within ~24
          months of category emergence

  edge-cases:
    - regulatory-capture: Once regulation is established,
      architectures can shape it to protect their position
      (banking, defense, healthcare incumbents). Capture is the
      mature form of this invariant, not an exception to it.
    - politically-favored-sectors: Architectures aligned with
      government priorities (defense contractors, certain
      healthcare research) operate in regulatory environments
      designed to support rather than constrain them.
    - pre-emptive-cooperation: Architectures that anticipate
      regulatory response can negotiate cooperative arrangements
      that prevent harsher intervention. Hims & Hers's March 2026
      Novo Nordisk partnership exemplifies — pre-emptively
      shifting to branded products to avoid prolonged enforcement
      exposure.
    - regulatory-lag: Response operates on political timescales,
      often years to decades behind the underlying concentration.
      Slow response is not absence of the invariant.

  bounding-conditions: |
    The invariant operates in jurisdictions with functional
    regulatory institutions and political processes responsive to
    organized interests. In jurisdictions with weak institutions
    or where the architecture controls the institutions, response
    is suppressed or distorted. Even in functional jurisdictions,
    response operates on decade-scale timeframes; short-term
    apparent absence of response is not disconfirming.

  falsifier: |
    The invariant would be disproven by a clear case of an
    architecture with extreme rent concentration, visible diffuse
    harm to politically organized counterparties, operating in a
    functional regulatory jurisdiction for >30 years without
    regulatory contact, partnership, or restructuring. The 20th
    century anti-trust record makes this hard to find.

  notes: |
    Political analog of Competitive Response (Invariant 2). The
    two invariants together bound durability of any high-extraction
    architecture: economic entry (Invariant 2) or political entry
    (Invariant 3) eventually responds to visible concentrated
    rent. Sub-attention strategy is the architectural response
    common to both. Bloomberg's relative immunity reflects
    regulatory-light classification (data vendor rather than
    critical infrastructure); Medvi's exposure reflects healthcare
    being heavily regulated with strong incumbent organization
    (Novo, Lilly).
```

---

### 4. Resource Constraints

```yaml
- id: resource-constraints
  name: Resource Constraints
  type: substrate-invariant

  statement: [E] Architectures operate within finite resource
    bounds — capital, attention, expertise, time. Unit economics
    must close within available resources at every operational
    scale the architecture passes through. Architectures cannot
    sustainably scale beyond the resources their unit economics
    generate (plus external subsidy, which is bounded). Scale
    transitions reveal new resource constraints that may not have
    bound at smaller scale.

  mechanism: [E] Identity-based for capital (cannot spend more than
    available). Operational for capacity (physical, computational,
    human limits). Game-theoretic for attention (finite operator
    and consumer attention competed by alternatives). Standard
    managerial economics: cost structure must be supportable from
    revenue at any sustainable scale. The cost of the architecture
    itself constrains the rent the architecture can capture
    (extends Conservation of Value to the architecture's own
    resource consumption).

  manifestations:
    - [E] Capital-intensive architectures require either deep
      pockets, strong unit economics, or external subsidy —
      middle paths fail
    - [E] Attention-intensive architectures face crowding from
      attention-competing alternatives as alternatives multiply
    - [E] Solo-operator and small-team architectures succeed by
      minimizing resource requirements; this is the structural
      reason AI cost compression matters at the architecture
      level (Medvi context)
    - [E] Scale transitions can break previously-closed unit
      economics — what fits at 1K users may not at 1M because
      different resources bind at different scales
    - [I] Resource arbitrage (renting infrastructure vs building,
      AI tools replacing labor) is the architectural response
      to this invariant

  predicted-failures:
    - [E] Architectures scaling faster than resources allow either
      fail outright or take on debt/equity that compromises
      structural position
    - [E] WeWork-style cases where fixed-resource commitments
      (long-term leases) grow faster than revenue capacity
    - [I] Capital-intensive AI infrastructure plays that cannot
      reach scale before incumbents' deeper capital pools enable
      them to absorb losses longer

  violation-examples:
    - wework-2010-2023:
        what: long-term lease obligations grew faster than
          revenue capacity; resource commitment exceeded sustainable
          extraction
        outcome: failed IPO 2019, near-bankruptcy 2023; resource
          structure was the structural flaw, not the demand side
    - webvan-1999-2001:
        what: capital-intensive delivery infrastructure required
          extraction exceeding available unit economics in
          grocery retail
        outcome: collapsed within 2 years; later successful
          architectures in same space (Instacart, AmazonFresh)
          used resource arbitrage (asset-light Instacart) or
          much larger amortization base (Amazon scale)
    - many-AI-startup-burn-rates-2023-2025:
        what: compute-resource costs growing faster than revenue
          for many AI-native startups
        outcome: consolidation pressure; many that survive are
          subsidized by strategic investors or capable of pricing
          tokens at well above marginal compute cost

  edge-cases:
    - VC-subsidy: Venture capital can temporarily relax resource
      constraints, allowing architectures to operate at unsustainable
      unit economics during growth phase. The constraint reasserts
      when subsidy ends.
    - strategic-patience: Architectures with deep-pocket backers
      (Amazon's 20-year low-margin retail era) can extend the
      horizon over which resource constraints bind, but cannot
      eliminate the constraint.
    - resource-arbitrage: Renting infrastructure rather than
      building (Medvi's rented operational stack), or using AI to
      replace labor (Medvi's AI orchestration), is the
      architectural response to resource constraint pressure.
      Successful arbitrage shifts where the constraint binds rather
      than eliminating it.

  bounding-conditions: |
    The invariant operates over sustainable operating timeframes.
    Short-term subsidies, strategic loss-making, and bootstrap
    phases can show apparent violations. The invariant resolves
    over the operating horizon (typically 5-10 years) — sustained
    architectures must close unit economics within available
    resources.

  falsifier: |
    The invariant would be disproven by an architecture that
    sustains operations for >10 years with unit economics that
    cannot close from available resources and no external
    subsidy. Government entities and some non-profits are
    excluded; among value-capture architectures specifically,
    none identified.

  notes: |
    Connects directly to Conservation of Value (Invariant 1):
    resource consumption by the architecture must be less than
    rent extracted (V - Y_min), bounding the architecture's own
    cost structure. Also connects to Competitive Response
    (Invariant 2): resource-intensive entry creates a barrier
    that suppresses competition, providing a structural
    explanation for why capital-intensive industries see less
    rapid competitive response. Medvi's AI cost compression is a
    direct architectural response to this invariant: by reducing
    resource consumption, the architecture can extract rent at
    scales that would not close for resource-heavier competitors
    (Hims & Hers with 2,442 employees vs Medvi with 2).
```

---

### 5. Information Dynamics

```yaml
- id: information-dynamics
  name: Information Dynamics
  type: substrate-invariant

  statement: [E] Information differentials decay through
    observation. Private information that creates rent becomes
    increasingly public as the architecture operates at scale
    because operating at scale reveals what the architecture
    knows. Sustained information-asymmetry rents require either
    active replenishment (continuous research, continuously
    accumulating proprietary data) or structural barriers to
    observation (private transactions, regulatory protection of
    data, encryption).

  mechanism: [E] Akerlof on information asymmetry — the market for
    lemons formalizes how informed parties can extract rent up
    to the value of the informational differential, but also how
    repeated transactions reveal information. Stiglitz on screening
    and signaling: counterparties develop instruments to extract
    private information from informed parties. Information theory:
    observation reduces uncertainty; sustained asymmetry requires
    sustained new information generation, since the existing
    differential is consumed in each rent-extracting transaction.

  manifestations:
    - [E] Quantitative trading strategies decay in alpha over time
      as more participants observe similar signals
    - [E] Bloomberg's information advantage for any specific data
      point decays as the data becomes public; durability comes
      from continuous accumulation (its G3 accumulated force is
      a flow, not a stock)
    - [E] AI-era compression of B2B procurement information
      asymmetry (2026) — buyers now access aggregated intelligence
      directly, eroding seller-side information rent
    - [I] Pure information-arbitrage businesses without active
      replenishment have short lifespans (typically <5 years)
    - [E] Privacy-protected information (medical records, financial
      account data) can sustain longer because observation is
      restricted by law; the regulatory protection is what
      preserves the asymmetry

  predicted-failures:
    - [E] Architectures relying on static information asymmetry
      see rent erosion over time as the asymmetry becomes public
    - [E] AI-era acceleration of consumer-side information
      symmetry — many B2C information-asymmetry architectures
      compressing rapidly
    - [I] Architectures dependent on a single information source
      that becomes publicly accessible (regulatory disclosure,
      API publication, AI training) face step-function rent loss

  violation-examples:
    - pre-internet-stockbrokers:
        what: relied on information asymmetry about pricing and
          market access; profitable for decades
        outcome: internet eliminated most pricing asymmetry by
          mid-2000s; sales-driven brokerages forced into advisory
          or RIA business models or commoditized
    - pre-2020-B2B-sales:
        what: relied on buyer asymmetry about vendor pricing,
          performance, alternatives
        outcome: AI-aggregated procurement intelligence (2024-2026)
          compressing margins; PYMNTS coverage of B2B procurement
          AI tools documents the compression
    - hedge-fund-quant-strategies:
        what: specific quantitative edges (factor strategies,
          arbitrage opportunities) generate rent when private
        outcome: edges decay over time as more participants find
          similar signals; sustained funds replenish through
          continuous research

  edge-cases:
    - regulatory-information-protection: Insider trading laws,
      HIPAA, financial-data regulations create artificial barriers
      to observation. The protection is what sustains the
      asymmetry; remove the protection and asymmetry erodes.
    - architecture-generated-data: Bloomberg's chat-network graph,
      Visa's transaction database, Google's search query data —
      data the architecture generates through its own operation
      and that competitors cannot replicate without similar
      operational scale. This is replenishment, not stock.
    - continuous-research: Drug discovery, scientific research,
      proprietary expertise development — domains where new
      information is generated rather than just consumed.
      Replenishment-by-research is the most sustainable form.

  bounding-conditions: |
    The invariant operates in domains where observation is
    permitted and signal-receiving infrastructure is available.
    Information that cannot be observed (truly private contracts,
    encrypted data, suppressed disclosure) does not decay through
    observation. The invariant bounds decay rate by observation
    rate, not by absolute time.

  falsifier: |
    The invariant would be disproven by an architecture sustaining
    pure-information-asymmetry rent for >20 years with no active
    replenishment mechanism, no regulatory observation barrier,
    and operating at substantial scale (where observation should
    have eroded the asymmetry). No such case identified; apparent
    long-lived information-asymmetry architectures all show
    replenishment on inspection.

  notes: |
    Especially active in 2026 force topology — AI capability shifts
    compressing many information asymmetries simultaneously
    (Finastra/Fintech-Times "death of information asymmetry"
    framing in banking; PYMNTS analog in B2B procurement).
    Connects to Time Consistency (Invariant 6): observable past
    actions are public information by definition, so reputation
    accumulation is the time-extended form of information
    accumulation. Connects to Competitive Response (Invariant 2):
    observation enables entry, so the speed of competitive response
    in an industry tracks the speed of information dynamics in
    that industry.
```

---

### 6. Time Consistency

```yaml
- id: time-consistency
  name: Time Consistency
  type: substrate-invariant

  statement: [E] An architecture's past commitments to
    counterparties and its observable track record constrain its
    future actions. Promises made cannot be unmade without
    reputational cost. Reputation accumulation is asymmetric —
    slow to build, fast to lose. Sustainable rent extraction
    requires consistency between current promises, current
    actions, and observable past actions; defection from
    promised behavior accelerates rent compression beyond what
    competitive or regulatory response alone would produce.

  mechanism: [E] Kydland and Prescott (1977) on rules vs
    discretion: credible commitment requires giving up
    flexibility, and the value of credibility is the rent the
    architecture can extract from being trusted to behave
    consistently. Reputation game theory: repeated games support
    cooperation through reputation; one-shot defection destroys
    cumulative reputation because counterparties update
    expectations rapidly on negative evidence. Information
    dynamics (Invariant 5): past actions are public information,
    so defection is observable.

  manifestations:
    - [E] Bloomberg's 40-year trust accumulation (G5 in its Layer
      A entry) is durable precisely because it is asymmetric —
      decades to build, but a single major defection (analogous
      to 2015 reporter-data scandal escalating) could compress
      rapidly
    - [E] Brand-identity architectures (Coca-Cola, LVMH, Apple)
      depend critically on time-consistency between brand promise
      and product experience
    - [E] Architectures that defect from promises collapse
      rapidly when defection becomes visible
    - [I] Long-term commitment to constraint can itself be rent-
      generating — Vanguard's 50-year low-fee commitment created
      trust premium that more flexible competitors cannot match
    - [E] Reputation premia transfer poorly to adjacent categories
      where the original promise does not directly apply (brand
      extension failures)

  predicted-failures:
    - [E] Architectures whose promised position becomes
      unsustainable face choice between visible defection (loses
      reputation rapidly) and continued promise-keeping at
      uneconomic terms (compresses rent via Resource Constraints
      or Conservation)
    - [E] Architectures attempting reinvention face friction from
      existing reputation that may not transfer to the new
      position
    - [E] Visible defection compresses rent at a rate exceeding
      what Competitive or Regulatory Response alone would
      produce

  violation-examples:
    - theranos-2003-2018:
        what: claimed to have transformative diagnostic technology;
          promise was inconsistent with actual capability
        outcome: when defection became visible (2015 WSJ reporting),
          collapse was rapid — within 3 years company dissolved
          and founder faced criminal conviction
    - ftx-2019-2022:
        what: promised exchange-grade custody and safety;
          defected on customer-asset segregation
        outcome: collapse within weeks of defection becoming
          visible (November 2022)
    - bud-light-2023:
        what: brand promise to traditional customer base
          inconsistent with marketing campaign actions
        outcome: rapid sales decline; reputation damage that
          persisted years and required substantial repositioning

  edge-cases:
    - generational-turnover: New generations of counterparties
      have less complete information about past actions; some
      reputation reset is possible over multi-decade horizons.
      Hewlett-Packard's reputation evolution across decades
      illustrates partial reset.
    - crisis-response-asymmetry: How an architecture handles a
      visible failure shapes whether the failure damages or
      enhances reputation. Tylenol's 1982 product-tampering
      response enhanced rather than damaged J&J's reputation;
      contrast Boeing 737-MAX response damaging Boeing's.
    - architectures-without-promises: Pure transactional
      architectures (commodity trading, anonymous markets) have
      minimal reputation exposure because they made no promises
      beyond completing the transaction.

  bounding-conditions: |
    The invariant operates where counterparties have memory and
    observation. In markets with high counterparty turnover
    (consumer products, tourism) reputation decays faster through
    forgetting; in markets with stable institutional counterparties
    (B2B, professional services) reputation persists longer. The
    asymmetric build-vs-decay dynamic holds across both, but the
    decay rate varies.

  falsifier: |
    The invariant would be disproven by an architecture that
    visibly defected on counterparty promises and continued to
    extract rent at the same level for >5 years without
    counterparty disengagement, regulatory action, or visible
    erosion. Apparent cases on inspection show either pre-emptive
    counterparty disengagement (rent already compressed) or
    extraction in a different counterparty population than the
    one that observed the defection.

  notes: |
    Closest to overlapping with Information Dynamics (Invariant 5)
    among the six invariants. The distinguishing feature: Time
    Consistency adds the asymmetric build-vs-decay dynamic that
    Information Dynamics alone does not capture. Information
    Dynamics says private information becomes public through
    observation; Time Consistency adds that the *implications*
    of that information for future trust are not symmetric. Good
    track records take many transactions to establish; defection
    is updated on in one. Whether this is a separate substrate
    invariant or a manifestation of Information Dynamics + an
    asymmetric updating rule is a judgment call; it is treated
    here as separate because the asymmetry is structurally
    distinct from the observation-decay mechanism. Cross-references
    to Layer A: Bloomberg's G5 trust accumulation force is a
    direct manifestation; the Hims & Hers 2026 pre-emptive
    Novo Nordisk partnership is partly time-consistency
    management (avoiding visible defection from compliance posture).
```
