"""AlphaMo corpus loader — Sprint 12.

Reads the four-layer corpus (Layer A architecture decompositions,
Layer B current-developments snapshot, Layer C substrate invariants,
Layer D anti-patterns + insights + operational summary) and produces
two routing-targeted subsets for AlphaMo's proposer and Stage 3
evaluator.

Design properties:

  - Pure Python file I/O. No Anthropic SDK or model-provider
    dependencies. A model migration would not touch this file.
  - Compiles once per process (lazy + memoized). The compiled
    subsets are large enough that re-reading the 73 corpus files
    on every call would be wasteful.
  - Routing-target driven. Layer B sections carry YAML
    `routing-target:` tags; the loader reads them mechanically
    rather than hardcoding which sections go where. Layer D
    routing is field-level: `fires-when` predicates → Stage 3
    (evaluation rubric); `comparator-survivor-signature` extracts
    → proposer (compositional substrate).
  - Layer A is compiled to a fingerprint index (~13K tokens) from
    the YAML canonical-record block in each entry. The full Layer
    A (~530K tokens raw) would be unusable in any per-call cached
    prefix.

CORPUS_VERSION bumps when ANY of the following change:
  - Layer A index extraction logic (i.e., the format of what we
    extract from each entry)
  - Layer B/C/D routing logic
  - Number of Layer A entries
  - Field semantics that flow into the cached subsets

Bumping invalidates the prompt cache on both proposer and Stage 3.
The CORPUS_VERSION header is prepended to each cached subset so
audits can identify which corpus rendition was in effect for a
given run. Sprint 8's `llm_usage` audit events surface the cache
read/write counts on the subset block.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

# Bump on any change to compiled-subset format, routing logic, or
# Layer A index extraction. Distinguished from PROPOSER_VERSION
# (which bumps on proposer-PROMPT changes) and PARENT_GOAL_VERSION
# (which bumps on parent-goal text changes). The three versions are
# independent identity axes — code drift on any axis invalidates
# its cache layer, not the others.
CORPUS_VERSION = "v1"

# Repository-relative path to the corpus directory. Resolves from
# this file's location so the loader works regardless of cwd.
_CORPUS_ROOT = Path(__file__).resolve().parent.parent.parent / "corpus"


# --------------------------------------------------------------------- Layer A


# Per-entry fields we extract from each Layer A YAML canonical record.
# The list is intentionally narrow: structural fingerprint, not full
# detail. Each line in the compiled index maps to one of these.
_LAYER_A_EXTRACTED_FIELDS = (
    "era",
    "industry",
    "status",
    "scale",
)
_LAYER_A_NESTED_FIELDS = (
    ("flow", "primary"),
    ("position", "description"),
    ("position", "scarcity-supply"),
    ("economics", "revenue-source"),
    ("economics", "unit"),
    ("dynamics", "retention"),
    ("competitive", "direct"),
    ("competitive", "response-patterns"),
)


def _read_corpus_file(relative_path: str) -> str:
    """Read a file under `corpus/`. Returns empty string on missing
    file (lets the loader degrade gracefully if a corpus update
    removes a file we used to expect)."""
    path = _CORPUS_ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text()


def _list_layer_a_entries() -> list[Path]:
    """Layer A markdown files in lexicographic order. Excludes the
    `_status.md` operational tracker."""
    layer_a_dir = _CORPUS_ROOT / "layer-a"
    if not layer_a_dir.exists():
        return []
    return sorted(
        p for p in layer_a_dir.glob("*.md") if p.name != "_status.md"
    )


def _extract_canonical_yaml_block(entry_text: str) -> str:
    """Pull the YAML canonical-record block out of a Layer A entry.

    The convention across all 72 entries is a `## Canonical Record`
    (or `## Canonical record (YAML)`) section containing a fenced
    ```yaml block. Returns the inner YAML text. Empty string on
    failure — the compiler treats missing/malformed YAML as a
    skipped entry rather than crashing the build.
    """
    # Match either header capitalization or with "(YAML)" suffix.
    header_match = re.search(
        r"^##\s+Canonical\s+[Rr]ecord(?:\s*\([Yy][Aa][Mm][Ll]\))?\s*$",
        entry_text,
        re.MULTILINE,
    )
    if not header_match:
        return ""
    body = entry_text[header_match.end():]
    # Find the next ```yaml fence and capture until the matching close.
    fence_match = re.search(r"```yaml\s*\n(.*?)\n```", body, re.DOTALL)
    if not fence_match:
        return ""
    return fence_match.group(1)


def _detect_yaml_format(yaml_text: str) -> str:
    """Two YAML schema variants observed in Layer A:

    Format A (list-item, ~46 entries — kodak/tsmc/visa style):
        - id: kodak-film
          era: 1888-2012
          position:
            description: [E] ...

    Format B (top-level-key, ~26 entries — aig-2008/anthropic-claude style):
        slug: aig-2008
        name: American International Group
        era: 1919-present
        position:
          description: [E] ...

    Both convey the same information; only indentation + id-field-name
    differ. Returns "A" for list-item, "B" for top-level-key, or "B"
    as fallback if neither matches cleanly (B's parser is more
    forgiving)."""
    if re.search(r"^- id:\s*\S", yaml_text, re.MULTILINE):
        return "A"
    return "B"


def _field_indent(fmt: str, depth: int) -> str:
    """Indentation prefix at a given nesting depth for the format.

    Format A (list-item) has fields at depth 1 indented 2 spaces.
    Format B (top-level) has fields at depth 1 indented 0 spaces.
    Nested children are 2 spaces deeper in both."""
    base = 2 if fmt == "A" else 0
    return " " * (base + 2 * depth)


def _yaml_id(yaml_text: str) -> str:
    """Extract the entry id, handling both `- id: X` (Format A) and
    `slug: X` / `id: X` (Format B)."""
    # Format A: list-item with id.
    m = re.search(r"^- id:\s*(\S+)", yaml_text, re.MULTILINE)
    if m:
        return m.group(1)
    # Format B: top-level slug or id.
    for key in ("slug", "id"):
        m = re.search(rf"^{key}:\s*(\S+)", yaml_text, re.MULTILINE)
        if m:
            return m.group(1)
    return ""


def _yaml_top_field(yaml_text: str, field: str, fmt: str) -> str:
    """Extract a depth-1 field's value. Handles single-line + multi-line."""
    indent = _field_indent(fmt, 0)
    # The next-field sentinel matches either depth-1 field or list item.
    pattern = (
        rf"^{indent}{re.escape(field)}:\s*"
        rf"(.*?)(?=\n{indent}[a-z][a-z0-9_-]*:|\n- |\Z)"
    )
    match = re.search(pattern, yaml_text, re.DOTALL | re.MULTILINE)
    if not match:
        return ""
    return _compact_value(match.group(1))


def _yaml_nested_field(yaml_text: str, parent: str, child: str, fmt: str) -> str:
    """Extract a depth-2 nested field (parent.child)."""
    parent_indent = _field_indent(fmt, 0)
    child_indent = _field_indent(fmt, 1)
    parent_match = re.search(
        rf"^{parent_indent}{re.escape(parent)}:\s*\n"
        rf"(.*?)(?=\n{parent_indent}[a-z][a-z0-9_-]*:|\n- |\Z)",
        yaml_text,
        re.DOTALL | re.MULTILINE,
    )
    if not parent_match:
        return ""
    parent_body = parent_match.group(1)
    child_match = re.search(
        rf"^{child_indent}{re.escape(child)}:\s*"
        rf"(.*?)(?=\n{child_indent}[a-z][a-z0-9_-]*:|\Z)",
        parent_body,
        re.DOTALL | re.MULTILINE,
    )
    if not child_match:
        return ""
    return _compact_value(child_match.group(1))


def _compact_value(raw: str) -> str:
    """Normalize a YAML value to a single line and trim aggressively.

    Layer A YAML values are bracket-tag-prefixed strings like
    `[E] foo-bar / baz / quux` that often span multiple lines. The
    compiled index needs one-line summaries. We collapse whitespace
    and truncate to ~160 chars per field — enough to preserve the
    structural signal without bloating per-entry size.
    """
    # Collapse all whitespace runs to single spaces.
    flat = re.sub(r"\s+", " ", raw).strip()
    # Strip trailing junk from regex captures.
    flat = flat.rstrip("|>").strip()
    # ~95 chars per field × ~12 fields × 72 entries ≈ 82K chars total
    # raw; this keeps per-entry size close to the ~175-token target.
    if len(flat) > 95:
        flat = flat[:92] + "..."
    return flat


def _failure_mode_summary(yaml_text: str, fmt: str) -> str:
    """Build a one-line failure-mode summary from forces-decreasing
    entries (if present) or competitive.response-patterns (fallback).

    Layer A schema for declined architectures uses
    `forces-decreasing:` with bullet entries; live architectures use
    `forces-emergence:` and `forces-accumulated:` without a decline
    block. For the compiled index we want the architectural fragility
    signal — what failed or could fail — so we synthesize from
    whatever the entry exposes.
    """
    parent_indent = _field_indent(fmt, 0)
    forces_match = re.search(
        rf"^{parent_indent}forces-decreasing:\s*\n"
        rf"(.*?)(?=\n{parent_indent}[a-z][a-z0-9_-]*:|\n- |\Z)",
        yaml_text,
        re.DOTALL | re.MULTILINE,
    )
    if forces_match:
        body = forces_match.group(1)
        desc_match = re.search(
            r"^\s*-\s+id:.*?\n\s+description:\s*(.*?)(?=\n\s+status-now:|\n\s+-\s+id:|\Z)",
            body,
            re.DOTALL | re.MULTILINE,
        )
        if desc_match:
            return _compact_value(desc_match.group(1))
    response = _yaml_nested_field(yaml_text, "competitive", "response-patterns", fmt)
    if response:
        return response
    return ""


def _compile_layer_a_entry(entry_path: Path) -> str | None:
    """Produce one compiled-index block for a single Layer A entry.

    Returns None on parse failure (the entry is then silently skipped
    from the index — preferable to a corrupt index entry).
    """
    text = entry_path.read_text()
    yaml_text = _extract_canonical_yaml_block(text)
    if not yaml_text:
        return None

    entry_id = _yaml_id(yaml_text)
    if not entry_id:
        return None
    fmt = _detect_yaml_format(yaml_text)

    fields: list[tuple[str, str]] = []
    fields.append(("id", entry_id))
    for field in _LAYER_A_EXTRACTED_FIELDS:
        value = _yaml_top_field(yaml_text, field, fmt)
        if value:
            fields.append((field, value))
    for parent, child in _LAYER_A_NESTED_FIELDS:
        value = _yaml_nested_field(yaml_text, parent, child, fmt)
        if value:
            fields.append((f"{parent}.{child}", value))
    failure = _failure_mode_summary(yaml_text, fmt)
    if failure:
        fields.append(("failure-mode", failure))

    lines = [f"  {key}: {value}" for key, value in fields]
    return "- " + "\n".join(lines)[2:]  # strip the leading "  " from first line


def compile_layer_a_index() -> str:
    """Produce the compiled Layer A index — structural fingerprints
    for all parseable entries. ~13K tokens when fully populated.

    This is shared between the proposer and Stage 3 subsets. Same
    bytes go to both call sites; one cache entry, two read sites.
    """
    blocks: list[str] = []
    for entry_path in _list_layer_a_entries():
        block = _compile_layer_a_entry(entry_path)
        if block is not None:
            blocks.append(block)
    if not blocks:
        return "(layer-a index: no entries compiled)"
    header = (
        "## Layer A — Architecture Fingerprint Index\n\n"
        f"Compiled from {len(blocks)} architecture decompositions in "
        "corpus/layer-a/. Each entry below captures the structural "
        "fingerprint (era / industry / flow / position / capture / "
        "scaling vector / defensibility / failure mode) drawn from "
        "the full Layer A canonical record. Reference these as "
        "compositional substrate; the full entry for any architecture "
        "is available in corpus/layer-a/<id>.md.\n"
    )
    return header + "\n" + "\n\n".join(blocks)


# --------------------------------------------------------------------- Layer B


def _layer_b_sections() -> list[tuple[str, str, str]]:
    """Parse Layer B into (section_heading, routing_target, body) tuples.

    The convention is `## Section N — <title>` followed by a fenced
    ```yaml block whose first field is `id:` and second is
    `routing-target:`. We capture from each section header to the
    next one (or EOF).
    """
    text = _read_corpus_file("layer-b.md")
    if not text:
        return []

    sections: list[tuple[str, str, str]] = []
    # Split on section markers; first split is the preamble (skipped).
    parts = re.split(r"(?=^## Section \d+ — )", text, flags=re.MULTILINE)
    for part in parts[1:]:
        # Section heading is the first line.
        first_newline = part.find("\n")
        if first_newline == -1:
            continue
        heading = part[:first_newline].strip()
        body = part[first_newline + 1:]
        # Extract routing-target from the section's YAML block.
        routing_match = re.search(r"^  routing-target:\s*(.+)$", body, re.MULTILINE)
        if not routing_match:
            continue
        routing_value = routing_match.group(1).strip().lower()
        sections.append((heading, routing_value, body))
    return sections


def _section_targets_audience(routing_value: str, audience: str) -> bool:
    """A Layer B section is included for `audience` if its routing-target
    string contains the audience name or `both`."""
    rv = routing_value.lower()
    if "both" in rv:
        return True
    if audience == "proposer":
        return "proposer" in rv
    if audience == "stage-3":
        return "stage-3" in rv or "stage3" in rv
    return False


def _compile_layer_b_for(audience: str) -> str:
    """Compile the Layer B subset for the given audience by selecting
    sections whose routing-target tag matches.

    `audience` is "proposer" or "stage-3"."""
    sections = _layer_b_sections()
    selected: list[str] = []
    for heading, routing, body in sections:
        if _section_targets_audience(routing, audience):
            selected.append(f"{heading}\n\n{body}".rstrip())
    if not selected:
        return ""
    header = (
        f"## Layer B — Current-Developments Snapshot ({audience} subset)\n"
    )
    return header + "\n".join(selected)


# --------------------------------------------------------------------- Layer C


def _compile_layer_c() -> str:
    """Full Layer C — substrate invariants. Universal to both audiences.

    Layer C is ~10K tokens of structural invariants the proposer and
    Stage 3 must both reason within. No routing — the file is
    included verbatim.
    """
    text = _read_corpus_file("layer-c.md")
    if not text:
        return ""
    return text


# --------------------------------------------------------------------- Layer D


def _layer_d_anti_pattern_entries() -> list[dict[str, str]]:
    """Parse Layer D anti-pattern entries into structured dicts with
    `id`, `fires-when`, `comparator-survivor-signature`, and other
    field text.

    Layer D anti-pattern entries are YAML list items in a single
    fenced block under `## Anti-patterns`. Each entry begins with
    `- id:` and contains multi-line fields including `fires-when:`
    (a bulleted predicate list) and
    `comparator-survivor-signature: |` (a multi-line block-scalar).
    """
    text = _read_corpus_file("layer-d.md")
    if not text:
        return []

    # Locate the anti-patterns section.
    section_match = re.search(
        r"## Anti-patterns\n.*?```yaml\n(.*?)\n```",
        text,
        re.DOTALL,
    )
    if not section_match:
        return []
    yaml_body = section_match.group(1)

    # Split into entries on `- id:` boundaries.
    entries: list[dict[str, str]] = []
    parts = re.split(r"(?=^- id:)", yaml_body, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part.startswith("- id:"):
            continue
        entry: dict[str, str] = {}
        id_match = re.search(r"^- id:\s*(\S+)", part, re.MULTILINE)
        if id_match:
            entry["id"] = id_match.group(1)
        # Extract fires-when (bulleted list under `  fires-when:`).
        fires_match = re.search(
            r"^  fires-when:\s*\n(.*?)(?=\n  [a-z][a-z0-9_-]*:|\Z)",
            part,
            re.DOTALL | re.MULTILINE,
        )
        if fires_match:
            entry["fires-when"] = fires_match.group(1).rstrip()
        # firing-threshold sits with fires-when as evaluation context.
        threshold_match = re.search(
            r"^  firing-threshold:\s*(.+)$",
            part,
            re.MULTILINE,
        )
        if threshold_match:
            entry["firing-threshold"] = threshold_match.group(1).strip()
        # comparator-survivor-signature (block scalar).
        survivor_match = re.search(
            r"^  comparator-survivor-signature:\s*\|\s*\n(.*?)(?=\n  [a-z][a-z0-9_-]*:|\Z)",
            part,
            re.DOTALL | re.MULTILINE,
        )
        if survivor_match:
            entry["comparator-survivor-signature"] = survivor_match.group(1).rstrip()
        # definition for context.
        def_match = re.search(
            r"^  definition:\s*\|\s*\n(.*?)(?=\n  [a-z][a-z0-9_-]*:|\Z)",
            part,
            re.DOTALL | re.MULTILINE,
        )
        if def_match:
            entry["definition"] = def_match.group(1).rstrip()
        entries.append(entry)
    return entries


def _layer_d_positive_insights() -> str:
    """Layer D positive-insights section, verbatim. Routed to proposer
    only — they're cross-architecture structural principles for
    compositional reasoning."""
    text = _read_corpus_file("layer-d.md")
    if not text:
        return ""
    match = re.search(
        r"^## Positive insights\s*\n(.*?)(?=^## (?:Operational summary|Audit|Revision log)|\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if not match:
        return ""
    return "## Layer D — Positive Insights\n\n" + match.group(1).rstrip()


def _layer_d_operational_summary() -> str:
    """Layer D operational-summary section, verbatim. Routed to Stage 3
    — it summarizes how anti-patterns interact with each other,
    useful evaluation context."""
    text = _read_corpus_file("layer-d.md")
    if not text:
        return ""
    match = re.search(
        r"^## Operational summary\s*\n(.*?)(?=^## (?:Audit|Revision log)|\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if not match:
        return ""
    return "## Layer D — Operational Summary\n\n" + match.group(1).rstrip()


def _compile_layer_d_for(audience: str) -> str:
    """Compile the Layer D subset for the given audience.

    Field-level routing per Sprint 12 directive:
      - proposer gets `comparator-survivor-signature` extracts (which
        mechanism distinguishes survivors — compositional substrate)
        plus the full positive-insights section.
      - stage-3 gets `fires-when` predicates (evaluation rubric for
        anti-pattern detection) plus the operational summary.
    """
    entries = _layer_d_anti_pattern_entries()
    if not entries:
        return ""

    parts: list[str] = []
    if audience == "proposer":
        # Survivor signatures + positive insights.
        survivor_blocks: list[str] = []
        for entry in entries:
            sig = entry.get("comparator-survivor-signature", "").strip()
            if not sig:
                continue
            definition = entry.get("definition", "").strip()
            block_parts = [f"- id: {entry.get('id', '?')}"]
            if definition:
                block_parts.append(f"  definition: |\n{_indent(definition, 4)}")
            block_parts.append(
                f"  comparator-survivor-signature: |\n{_indent(sig, 4)}"
            )
            survivor_blocks.append("\n".join(block_parts))
        if survivor_blocks:
            parts.append(
                "## Layer D — Comparator Survivor Signatures (proposer subset)\n\n"
                "What mechanism distinguishes the survivor of each "
                "anti-pattern from the canonical failure case. Use these "
                "as compositional substrate: if your candidate "
                "instantiates the anti-pattern, identify which survivor "
                "mechanism it relies on and ensure that mechanism is "
                "structurally present.\n\n"
                + "\n\n".join(survivor_blocks)
            )
        insights = _layer_d_positive_insights()
        if insights:
            parts.append(insights)
    elif audience == "stage-3":
        # fires-when predicates + operational summary.
        firing_blocks: list[str] = []
        for entry in entries:
            fires = entry.get("fires-when", "").strip()
            if not fires:
                continue
            definition = entry.get("definition", "").strip()
            threshold = entry.get("firing-threshold", "").strip()
            block_parts = [f"- id: {entry.get('id', '?')}"]
            if definition:
                block_parts.append(f"  definition: |\n{_indent(definition, 4)}")
            block_parts.append(f"  fires-when:\n{fires}")
            if threshold:
                block_parts.append(f"  firing-threshold: {threshold}")
            firing_blocks.append("\n".join(block_parts))
        if firing_blocks:
            parts.append(
                "## Layer D — Anti-pattern Firing Predicates (stage-3 subset)\n\n"
                "Each anti-pattern below has an ordered list of "
                "testable `fires-when` predicates plus a firing "
                "threshold. Apply during evaluation: if the candidate "
                "satisfies threshold-many predicates, flag the "
                "anti-pattern as instantiated.\n\n"
                + "\n\n".join(firing_blocks)
            )
        op_summary = _layer_d_operational_summary()
        if op_summary:
            parts.append(op_summary)

    return "\n\n".join(parts)


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.split("\n"))


# --------------------------------------------------------------------- subsets


def _version_header(audience: str) -> str:
    return (
        f"# AlphaMo Corpus — {audience} subset (CORPUS_VERSION={CORPUS_VERSION})\n\n"
        "The text below is stable substrate the proposer/evaluator "
        "reasons WITHIN, not text the model is asked to read fresh "
        "each call. It is prepended as a cached prefix to the system "
        "prompt; cache reads after the first call drop the input cost "
        "to ~10% of base.\n"
    )


@lru_cache(maxsize=1)
def load_proposer_subset() -> str:
    """Return the proposer's corpus subset (compositional substrate).

    Composition:
      - Layer A compiled index (all 72 architectures fingerprinted)
      - Layer B sections tagged routing-target ∈ {proposer, both}
      - Layer C invariants (universal)
      - Layer D comparator-survivor-signature extracts (proposer routed)
      - Layer D positive-insights section (proposer routed)
    """
    blocks = [
        _version_header("proposer"),
        compile_layer_a_index(),
        _compile_layer_b_for("proposer"),
        _compile_layer_c(),
        _compile_layer_d_for("proposer"),
    ]
    return "\n\n".join(b for b in blocks if b)


@lru_cache(maxsize=1)
def load_stage3_subset() -> str:
    """Return the Stage 3 evaluator's corpus subset (evaluative substrate).

    Composition:
      - Layer A compiled index (shared with proposer; same bytes)
      - Layer B sections tagged routing-target ∈ {stage-3, both}
      - Layer C invariants (universal)
      - Layer D fires-when predicate extracts (stage-3 routed)
      - Layer D operational-summary section (stage-3 routed)
    """
    blocks = [
        _version_header("stage-3"),
        compile_layer_a_index(),
        _compile_layer_b_for("stage-3"),
        _compile_layer_c(),
        _compile_layer_d_for("stage-3"),
    ]
    return "\n\n".join(b for b in blocks if b)


__all__ = [
    "CORPUS_VERSION",
    "compile_layer_a_index",
    "load_proposer_subset",
    "load_stage3_subset",
]
