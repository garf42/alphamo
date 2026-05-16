"""The parent goal — immutable, load-bearing context for every evaluator call.

Sharpened from IDD pre-run + middle-class entry constraint. This text is the
verifiability anchor — change it only when the parent goal itself is
re-framed by the meta-curator, not for prompt tuning. PARENT_GOAL_VERSION
must be bumped any time the text below changes so historical runs in the DB
can be distinguished from runs under the new framing.

Version history:
  v1 — original framing; closing "verifiability anchor" line cited named
       historical existence proofs (Satoshi, Rowling, Levels).
  v2 — named citations removed. The proposer's system prompt no longer
       sees historical-pattern names. Structural grounding remains via
       the constraints themselves and the cascade's verification work.
       Aligns with Sprint 3's intent that PARENT_GOAL ground the search
       through criteria, not through named patterns.
"""

PARENT_GOAL_VERSION = "v2"

PARENT_GOAL = """\
Identify legal, structural, or protocol-level configurations in which a \
SINGLE INDIVIDUAL or SINGLE LEGAL ENTITY captures $1B+ in value (annual \
revenue, asset holdings, or comparable measure) from a value chain whose \
operational labor is performed by parties other than that individual, and \
characterize the structural features (contract architecture, IP design, \
network position, regulatory geometry) that enable the value-capture \
asymmetry — where the configuration MUST be enterable from MIDDLE-CLASS \
PERSONAL RESOURCES (modest savings $10-50K range, personal credit access, \
professional skill, time outside a primary job, and only standard business \
infrastructure) with NO PRIVILEGED STARTING CONDITIONS (no family wealth, no \
institutional backing, no pre-existing industry network, no access to \
bespoke multi-jurisdictional legal structuring). Networking, loans, \
partnerships, and capital may be acquired along the way; the constraint \
binds only on starting position.

Load-bearing constraints:
1. ONE-PERSON THRESHOLD — a single individual or single legal entity is the value-capture node.
2. BILLION-DOLLAR QUANTUM — captured value reaches $1B+ in revenue, assets, or comparable measure.
3. MIDDLE-CLASS ACCESSIBLE ENTRY — the configuration is enterable from modest savings, personal credit, skill, and time, with no privileged starting conditions. This is a STRUCTURAL FILTER, not a soft preference.

Verifiability anchor: structural existence proofs exist across multiple verticals demonstrating the parent goal's achievability; the search is grounded in the constraints above, not in any named historical pattern.
"""
