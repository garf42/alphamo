
# Layer A Bulk Build — Super Dispatch Protocol

**Purpose:** Instructions for Super to manage bulk Layer A
construction by dispatching Claude Code instances against the
curated architecture list, each instance running RAD on one
architecture and producing one corpus entry file.

**Audience:** Super (AI orchestrator, Claude Opus backend) running
on the Raspberry Pi systemd daemon. This document is the prompt
Super reads to understand the bulk-build task.


---

## Inputs

Super needs access to:

1. **RAD skill file:** `{SKILL_PATH}/architecture-decomposition/SKILL.md`
2. **Architecture list:** `{LIST_PATH}/layer-a-architecture-list.md`
3. **Output directory:** `{CORPUS_PATH}/layer-a/`
4. **Status log:** `{CORPUS_PATH}/layer-a/_status.md` (created/updated by Super)
5. **Per-architecture prompt template:** embedded below (see "Prompt Template")

Replace bracketed paths with actual filesystem paths in your environment.


## Goal

Process every entry in the architecture list. For each architecture:

1. Generate a per-architecture prompt by filling the template (below) with the entry's fields
2. Dispatch a fresh Claude Code instance with the prompt
3. Validate the Claude Code output produces a well-formed corpus entry file
4. Update the status log
5. Move to the next entry (or batch if parallelizing)

Continue until every entry in the list is either processed or
explicitly flagged for chat-side review.


## Processing order

Follow the "Suggested processing order" section of the architecture list:

1. Section A (sequential): 5 entries, one at a time, pause for chat-side review between each
2. Section E (parallel, 3-5 concurrent)
3. Section D (parallel, 3-5 concurrent)
4. Section C (parallel, 3-5 concurrent)
5. Section B (parallel, 3-5 concurrent — largest batch)
6. Section F (parallel, 3-5 concurrent)

Section A's sequential dispatch is the schema-validation gate. If any of those 5 surfaces a schema issue, halt dispatch and surface for chat-side resolution before continuing.


## Per-entry processing

For each architecture entry in the list:

### Step 1 — Check if already processed

Check if `{CORPUS_PATH}/layer-a/{slug}.md` exists. If yes, skip
this entry and log "already-processed" in the status log.

### Step 2 — Fill the prompt template

Substitute the entry's fields into the template below:
- `{SLUG}` → slug field
- `{NAME}` → name field
- `{INDUSTRY}` → industry field
- `{ERA}` → era field
- `{STATUS}` → status field
- `{RATIONALE}` → rationale field
- `{SCOPE_NOTES}` → scope/notes field (may be empty)

Write the filled prompt to a temporary file or use directly.

### Step 3 — Dispatch Claude Code

Launch a fresh Claude Code instance with the filled prompt. The
instance should have:
- Read access to the RAD skill file
- Write access to `{CORPUS_PATH}/layer-a/{slug}.md`
- Web search capability (RAD requires Phase 0 research pass)

Wait for the instance to complete.

### Step 4 — Validate output

Check that the output file exists at the expected path and
contains:
- A "Research Summary" section (3-5 sentences)
- A "Canonical Record" section with a YAML code block
- The YAML block has the required top-level structure (id, name, era, industry, status, scale, scope, plus nested sections)
- Bracket-prefix confidence tags `[E]`/`[I]`/`[C]`/`[U]` present in field values
- A "negative-pairs" list with at least one entry that includes a "reveals" field
- An "audit" line with counts in format "Ne / Ni / Nc / Nu / Ntotal"
- A "Prose Synthesis" section with the five required subsections

If any required element is missing, mark the entry as "failed-validation" and queue for retry or chat-side review. Do NOT mark as completed.

### Step 5 — Update status log

Append to `{CORPUS_PATH}/layer-a/_status.md`:
```
- [TIMESTAMP] {slug}: [success | failed-validation | declined-phase-1 | low-evidence | schema-gap]
  [optional: one-line note]
```


## Failure handling

Three failure modes Super should handle distinctly:

**(a) RAD decline at Phase 1 (scope conflation).** Claude Code returns a Phase 1 decline saying the architecture conflates multiple distinct value-capture mechanisms. This is legitimate output. Log as `declined-phase-1` and surface for chat-side decision — typically means the entry should be split into multiple entries (e.g., "Amazon" → "Amazon Retail" + "AWS" + "Amazon Advertising") and re-queued.

**(b) Low-evidence entry.** Claude Code produces a complete entry but audit shows mostly `[I]`/`[U]` tags (less than ~40% `[E]`). This is legitimate but flagged. Log as `low-evidence` and continue. QA pass will decide whether to keep or rerun with better research.

**(c) Schema gap.** Claude Code produces a valid entry but the `notes` field flags a structural feature the current schema cannot capture. This is the most important failure mode — surface immediately for chat-side schema review BEFORE continuing bulk dispatch. The Bloomberg run identified one such gap (forces-accumulated); future gaps will guide v1.4+ refinement.

**(d) Hard failure.** Claude Code instance errors out, exceeds budget, or produces malformed output. Log as `hard-failure` with diagnostic info. Retry once after 1 hour; if second attempt also fails, surface for chat-side review.


## Parallelism guidance

- Sequential for Section A (5 entries, ~5 hours estimated)
- Parallel 3-5 concurrent for Sections B-F (~40-50 entries total)
- Per-entry budget: ~50K tokens estimated (research + decomposition + audit + prose synthesis), so ~$0.50-1.00 per entry at current API rates
- Total estimated cost: ~$30-60 for full Layer A build, well within $75/month Super budget
- Estimated wall-clock: 1-2 weeks at 3-5 entries/day with parallel dispatch


## Recommended status log format

`{CORPUS_PATH}/layer-a/_status.md`:

```markdown
# Layer A Build Status

**Started:** {timestamp}
**Total entries:** {N from list}
**Completed:** {count}
**Failed validation:** {count}
**Declined Phase 1:** {count}
**Low evidence:** {count}
**Schema gaps:** {count}
**Pending:** {count}

## Log

- [2026-05-19T10:00Z] visa-interchange: success (audit 35E/8I/4C/2U/49)
- [2026-05-19T10:45Z] standard-oil: success (audit 40E/6I/3C/1U/50)
- [2026-05-19T11:30Z] kodak-film: schema-gap — defunct-as-subject required adapting trajectory field; see entry notes
- [2026-05-19T12:15Z] tsmc: success (audit 38E/9I/3C/2U/52)
- ...

## Schema gaps surfaced

(empty if none)

## Failed entries needing retry

(empty if none)
```


---

## Prompt Template (per-architecture)

The following template is filled per entry and given to each Claude Code instance.

```markdown
# RAD Run: {NAME}

## Task

You are running the Architecture Decomposition (RAD) skill on the
architecture named below. Read the full skill file at
`{SKILL_PATH}/architecture-decomposition/SKILL.md` and follow the
ten-phase protocol exactly. Produce the canonical YAML record
plus the prose synthesis. Write the combined output to the
specified output file.

## Architecture details (from curated list)

- **Name:** {NAME}
- **Slug:** {SLUG}
- **Industry:** {INDUSTRY}
- **Era of analysis:** {ERA}
- **Status hint:** {STATUS}
- **Curation rationale:** {RATIONALE}
- **Scope/notes:** {SCOPE_NOTES}

These hints come from the architecture list. Treat them as
starting context only — verify and override based on Phase 0
research if the hints prove inaccurate.

## Output

Write the complete result to:
`{CORPUS_PATH}/layer-a/{SLUG}.md`

Format (per RAD skill output-format section):

1. Research Summary (3-5 sentences from Phase 0)
2. Canonical Record (YAML, ~800-1000 tokens, the load-bearing
   corpus content)
3. Prose Synthesis (~300-500 tokens, QA ergonomics)

## Discipline reminders

Follow the RAD skill exactly. In particular:

- **Phase 0 mandatory.** Do not skip the research pass. Cap at 4-6
  targeted searches.
- **Bracket-prefix tags.** Every field value starts with `[E]`,
  `[I]`, `[C]`, or `[U]`.
- **No primitive vocabulary.** Do not write "two-sided network
  effects" or similar; write the raw structural mechanics.
- **No pattern-name labels.** Do not write "rented-infrastructure
  pattern" or similar shorthand; write the mechanics out.
- **Required negative pairs.** Phase 9 requires at least one. If
  none locatable, decline the field with the standard decline
  statement; do not manufacture.
- **Required "reveals" field.** Each negative pair must include
  what the contrast reveals about the subject.
- **Required uncertainty audit.** Phase 10 produces summary counts.
- **Forces-emergence vs forces-accumulated.** For architectures
  older than ~10 years, populate both sections distinctly. Do not
  compress accumulated forces into the evolution prose field.
- **Token budget.** Target ~800-1000 tokens for canonical YAML.
  Use the `notes` free-form field for structural nuance that
  doesn't fit the schema.
- **Empty outputs preferred over manufactured.** If a field is
  genuinely unknown or contested, tag it `[U]` or `[C]` with a
  one-line explanation. Do not fabricate confident-sounding
  content.

## Special-case handling

- **If Phase 1 surfaces a scope conflation:** decline at Phase 1
  with split recommendation. Do not proceed.
- **If research surfaces a structural feature the schema cannot
  capture:** complete the entry using best-fit fields, then flag
  the schema gap in the `notes` field. The dispatcher will
  surface for chat-side schema review.
- **If the entry is defunct or restructured:** the trajectory
  field uses `contested`, `eroding`, or `transforming` rather
  than the live-architecture options.

## When complete

When you have written the output file, end your run. The
dispatcher will validate the output and update the status log.
Do not summarize the work in chat; the file is the deliverable.
```


---

## Notes for Super

- Each Claude Code instance is independent. Do not pass state
  between instances; the prompt and the skill file are sufficient.
- Some entries may take multiple research searches and produce
  longer outputs than others. Do not impose a hard token cap on
  Claude Code; the discipline is in the skill, not in the
  dispatcher.
- Periodically (every ~10 completed entries) surface the status
  log to chat for review. If a schema gap is flagged, surface
  immediately.
- When all entries are processed, surface the full status log
  plus a list of entries flagged `low-evidence`, `failed-
  validation`, or `schema-gap` for batched QA review.
