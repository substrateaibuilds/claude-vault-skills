---
name: vault-ingest
description: Autonomously ingest all unprocessed source files from an Obsidian vault in a single run. Handles Phase 1 (scan), Phase 1.5 (briefing), Phase 3 (bulk parallel source pages, 10 at a time), Phase 4 (Pass B synthesis), and Phase 6 (index rebuild). No human re-triggering needed. Use when the user wants to "ingest everything", "run a full ingest", or "process all source files" for a vault. Requires: vault has CLAUDE.md and wiki/ directory. INGESTION-PROMPT.md is recommended; _ingest-briefing.md is created by the skill if missing.
---

# vault-ingest

Run a full autonomous ingestion of all unprocessed source files in an Obsidian vault. One invocation — all phases — no re-triggering.

## When to use

- User says "ingest everything in [vault]" or "run the full ingest"
- User invokes `/vault-ingest [vault-path]`
- After `/vault-optimize` brings a vault to 8/10, user wants to close the source-coverage gap

## When NOT to use

- Single source file ("ingest this one PDF") — just use Claude's Read + Write tools directly
- The vault has no CLAUDE.md or INGESTION-PROMPT.md — run `/vault-optimize` first

## Arguments

`/vault-ingest [vault-path]`

- `vault-path` — absolute path to vault root (e.g. `~/Obsidian/coffee-brewing-research`)
- If omitted, ask the user

## Steps

*Phase numbering follows the INGESTION-PROMPT.md convention. Phases 2 and 5 are manual/human-gated phases not automated here — Phase 2 (foundational ingest) is replaced by the existing wiki pages + Phase 1.5 briefing write; Phase 5 (duplicates) is handled via the skip list.*

### Pre-checks

Before doing anything, verify:

```bash
VAULT=<vault-path>
ls "$VAULT/CLAUDE.md" && echo "OK" || echo "MISSING CLAUDE.md — stop"
ls "$VAULT/wiki/" && echo "OK" || echo "MISSING wiki/ — stop"
ls "$VAULT/INGESTION-PROMPT.md" 2>/dev/null && echo "OK" || echo "INGESTION-PROMPT.md missing (recommended, not required)"
which pdftotext >/dev/null 2>&1 && echo "pdftotext OK" || echo "WARNING: pdftotext missing — PDFs will fail. Install: brew install poppler"
```

Stop if CLAUDE.md or wiki/ is missing. INGESTION-PROMPT.md is recommended (rules are read from CLAUDE.md directly if missing). `_ingest-briefing.md` is created by Phase 1.5 — not a pre-req.

### Phase 0 — Read vault rules

Read `$VAULT/CLAUDE.md` in full. This is the source of truth for:
- Voice rule (preserve verbatim vs. normalize)
- Anonymization rule
- Confidence taxonomy and default
- Wiki subfolder structure
- Page template

If `$VAULT/wiki/_ingest-briefing.md` exists, read it to understand current state. If not, skip — Phase 1.5 will create it from scratch.

Note the confidence default from CLAUDE.md — you'll need it when constructing Phase 3 subagent prompts.

### Phase 1 — Scan and build processing queue

**Step 1: Identify all source files**

First determine where source files live. Check CLAUDE.md for a "Source Files" or "Source file location" note, then:

```bash
VAULT=<vault-path>
# Try vault root first
root_count=$(find "$VAULT" -maxdepth 1 \( -name "*.md" -o -name "*.pdf" -o -name "*.txt" \) \
  | grep -v "CLAUDE.md\|INGESTION-PROMPT.md\|README" | wc -l)

if [ "$root_count" -gt 0 ]; then
  # Source files live at vault root (typical for personal-brain archetype)
  SOURCE_BASE="$VAULT"
  find "$VAULT" -maxdepth 1 \( -name "*.md" -o -name "*.pdf" -o -name "*.txt" \) \
    | grep -v "CLAUDE.md\|INGESTION-PROMPT.md\|README" | sort
else
  # Fall back to raw/ subdirectory (typical for research-wiki and project-kb archetypes)
  SOURCE_BASE="$VAULT/raw"
  find "$VAULT/raw" -type f \( -name "*.md" -o -name "*.pdf" -o -name "*.txt" \) 2>/dev/null | sort
fi
```

**Step 2: Build skip list from already-ingested files**

Check by the `**File path:**` field in existing source pages — NOT by slug-name matching (existing hand-crafted source pages use human-assigned slugs that don't match the filename→slug formula).

```bash
# Extract the File field from all existing source pages.
# Handles both "**File:**" (hand-crafted) and "- **File path:**" (template-generated with leading bullet).
# The \*\*File[^:]*:\*\* pattern catches both variants mid-line.
grep -rh '\*\*File[^:]*:\*\*' "$VAULT/wiki/sources/"*.md 2>/dev/null \
  | sed 's/.*\*\*File[^:]*:\*\* //' | tr -d '`' | sed 's/^[[:space:]]*//' \
  | sort > /tmp/vault-ingest-done.txt
```

Then for each source file in Step 1: check if its basename (e.g. `client-a-2024-01-15.md`) appears in `/tmp/vault-ingest-done.txt`. If yes, skip it.

**Step 3: Build processing queue and compute slugs**

Standardized slug formula — handles apostrophes, parentheses, commas, and any other special chars in source filenames like `2022-12-30 Private Coaching (Client A).md`:

```bash
normalize_slug() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/--*/-/g; s/^-//; s/-$//'
}
# Example: "Client A - Session 1 (Jan 2024).md" → "client-a-session-1-jan-2024"
```

Use this function consistently everywhere slugs are computed. For each source file from Step 1:
- `slug=$(normalize_slug "$(basename "$file" "${file##*.}")")`
- Intended output: `$VAULT/wiki/sources/${slug}.md`
- Check if file's basename appears in done list; if not, add to queue

Report the queue:
```
Processing queue: N files to process, N already done, N skipped (meta-files)
PDF count: N (will pre-extract)
```

**Step 4: Pre-extract PDFs**

If any PDFs are in the queue:
```bash
mkdir -p /tmp/vault-ingest-pdfs/
for pdf in <pdf-files>; do
  slug=$(normalize_slug "$(basename "$pdf" .pdf)")
  pdftotext -layout "$pdf" "/tmp/vault-ingest-pdfs/${slug}.txt" 2>/dev/null || \
    echo "IMAGE-ONLY: $pdf" >> /tmp/vault-ingest-failures.txt
done
```

For any PDF that produced near-empty output (<500 chars), mark as IMAGE-ONLY and skip.
For successfully extracted PDFs: use the extracted .txt file as the source for Phase 3 (not the PDF).

### Phase 1.5 — Write proper _ingest-briefing.md

This is the shared context for all Phase 3 subagents. Write it ONCE before launching any Phase 3 subagents.

**Step 1: Build slug inventory via shell**

Use `-mindepth 2` to exclude flat wiki root files (domain-index-*.md, STATUS.md, ASSESSMENT-ENGINE-EXPORT.md, etc.) — only include pages in subdirectories:

```bash
find "$VAULT/wiki" -mindepth 2 -name "*.md" \
  -not -path "*/sources/*" \
  | sort | while read f; do
    slug=$(basename "$f" .md)
    title=$(head -1 "$f" 2>/dev/null | sed 's/^# //' | cut -c1-80)
    echo "- $slug — $title"
  done > /tmp/vault-ingest-slugs.txt
wc -l /tmp/vault-ingest-slugs.txt
```

**Step 2: Check before overwriting the briefing**

```bash
if grep -q "Pre-Phase-2 stub" "$VAULT/wiki/_ingest-briefing.md" 2>/dev/null || \
   [ ! -f "$VAULT/wiki/_ingest-briefing.md" ]; then
  echo "Writing fresh briefing (stub or missing)"
else
  echo "WARNING: briefing appears fully-written. Overwriting with updated slug inventory."
fi
```

Always overwrite in autonomous mode — the slug inventory must reflect the current wiki state. Log the overwrite to wiki/log.md.

**Step 3: Write the briefing file**

Write `$VAULT/wiki/_ingest-briefing.md` with ALL of the following sections (substituting values from CLAUDE.md):

```markdown
# Ingest Briefing — [VAULT_TITLE]

*Written [DATE] by vault-ingest orchestrator. All Phase 3 subagents must read this before processing any source file.*

---

## Project Context

[1 paragraph: vault owner, purpose, downstream consumers — taken from CLAUDE.md]

## Critical Rules (enforce throughout)

- **Never invent.** If a fact isn't in the source file, use `GAP:` not a plausible guess.
- **[VOICE_RULE from CLAUDE.md]**
- **Bidirectional links mandatory.** If page A references B, page B must link back to A.
- **[ANONYMIZATION_RULE from CLAUDE.md]**
- **Never merge distinct concepts.** Two separate things in the source → two separate pages.
- **One source file → one source page.** Do NOT create concept/framework/entity pages in Phase 3. Only wiki/sources/ pages. Concept pages are created in Phase 4.
- **Return discipline:** After writing your source page, return ONLY the string: `CREATED: wiki/sources/<slug>.md`. No summary, no commentary, no extra text.

## Confidence Taxonomy

[Copy verbatim from CLAUDE.md's ## Confidence Taxonomy section]

**Default confidence for this vault:** [CONFIDENCE_DEFAULT from CLAUDE.md]

## Slug Inventory (existing wiki pages — do NOT duplicate these)

[paste contents of /tmp/vault-ingest-slugs.txt]

## Source Page Template

Every wiki/sources/<slug>.md must follow this exact structure:

```
# Source: [Full Title]

> **Historical context:** [Why recorded/written, what situation it responded to]

- **Type:** [coaching call | group call | course module | interview | protocol doc | etc.]
- **Content Date:** [original date — NOT today's date]
- **Domain(s):** [list all that apply]
- **File path:** [filename]

## Abstract / Key Question
[3 sentences: what this file is + what question it answers + why it matters]

## Key Findings
1. **[Bold header]** [substantive paragraph with verbatim quotes embedded]
2. **[Bold header]** [...]
...
10. **[Bold header]** [...]

## [VOICE_SECTION_HEADER from CLAUDE.md]
[10–15 verbatim quotes, each ending with: — [Source anchor]]

## Cross-Domain Connections
> **Cross-domain:** [vault owner's actual numbers/programs/clients — not generic principles]

## Related Pages
- [[slug]] — [why related, one sentence]

## Pages Created/Updated: (pending Pass B)

## Candidate New Pages (Pass B)
- `wiki/<folder>/<slug>.md` — [description] — Supporting quote: "[verbatim]"
- `wiki/<folder>/<slug>.md` — [description] — Supporting quote: "[verbatim]"
- `wiki/<folder>/<slug>.md` — [description] — Supporting quote: "[verbatim]"

## Gaps
- GAP: [specific gaps — unread sections, missing data, unverified claims]
```

## Filename Convention

`wiki/sources/<kebab-case-slug>.md`
- Derived from source filename: lowercase, spaces→hyphens, remove special chars via `tr -cs 'a-z0-9' '-'`
- For near-duplicate titles: append last 4 chars of source filename to disambiguate

## Source Files Location

Source files live at: `[SOURCE_BASE]/` (computed by the orchestrator in Phase 1 — either the vault root or `raw/` subdirectory depending on vault structure). Full paths: `[SOURCE_BASE]/<filename>`
```

### Phase 3 — Bulk parallel processing

**Gate:** Do not start Phase 3 until _ingest-briefing.md has been written in Phase 1.5.

Fire 10 subagents per turn, all with `run_in_background: true`. Each subagent handles one source file.

**Subagent prompt template (construct one per file):**

```
Read this briefing in full: [VAULT_PATH]/wiki/_ingest-briefing.md

Then read this source file in full:
[SOURCE_FILE_FULL_PATH]

For files over 2000 lines: read in 1000-line chunks (offset=0, limit=1000; then offset=1000, limit=1000; continue until end of file). Mark each unread portion as: GAP: lines N–M not read — large file, chunk limit reached.

Write ONE source page to: [VAULT_PATH]/wiki/sources/[SLUG].md

Follow the Source Page Template from the briefing exactly.

Return ONLY: CREATED: wiki/sources/[SLUG].md
If you cannot complete the task: FAILED: [filename] - [one-line reason]
```

**Batch loop:**

```
remaining_queue = [list of all files to process]
failed = []

while remaining_queue is not empty:
    batch = remaining_queue[:10]
    remaining_queue = remaining_queue[10:]

    Fire all 10 as parallel background subagents in ONE message
    Wait for all 10 to return

    for result in batch_results:
        if result starts with "CREATED:":
            log to wiki/log.md
        else:
            failed.append(result)
            log failure to wiki/log.md

    print progress: "Batch N complete: X/Y total done, Z failed so far"
```

After all batches: report the failed list. Do NOT retry non-rate-limit failures — report and let user decide.

**Logging format for wiki/log.md:**

Append after each batch:
```markdown
## Phase 3 Batch [N] — [timestamp]
- Processed: [file1], [file2], ... [file10]
- Results: [N] CREATED, [N] FAILED
```

### Phase 4 — Pass B Synthesis (Nomination-based + Frequency-based)

**Gate:** Start only after ALL Phase 3 batches have completed.

**Critical:** Phase 4 uses TWO promotion signals, not one. The original ingest skill used only nomination-based promotion (counts entries in the "Candidate New Pages" sections of source pages). That logic misses *foundational* concepts that get mentioned heavily across source pages but rarely nominated — because the most-used concepts in a corpus don't feel like discoveries to the source-summary writers. The frequency-based check catches them.

Fire ONE `general-purpose` subagent:

```
Read this briefing first (it contains the Page Template and confidence taxonomy you need):
[VAULT_PATH]/wiki/_ingest-briefing.md

You are running Pass B Synthesis for [VAULT_TITLE]. Promotion uses TWO signals.

=== SIGNAL 1: Nomination-based (Candidate New Pages sections) ===

1. Run: grep -A 5 "^## Candidate New Pages" [VAULT_PATH]/wiki/sources/*.md
   Collect every proposed new page slug.

2. Tally votes per slug — extract ONLY the slug before counting:
   grep -roh '`wiki/[^`]*\.md`' [VAULT_PATH]/wiki/sources/*.md \
     | sed 's/[^:]*://' | sed 's/`//g' \
     | sort | uniq -c | sort -rn

3. Promote any slug proposed by ≥3 different source pages.

=== SIGNAL 2: Frequency-based (concept-frequency audit) ===

4. Run the concept-frequency audit to find concepts mentioned in many source pages but missing as wiki pages:
   python3 [VAULT_PATH]/_scripts/concept-frequency-audit.py

5. Read [VAULT_PATH]/wiki/CONCEPT-COVERAGE.md. Take the top 10 candidates by mention count. Each is a real coverage gap that nomination-based promotion missed.

6. For each candidate in the top 10:
   - Read 2-3 of the highest-density source pages that mention it
   - Decide: BUILD (real concept, no existing page covers it), ALIAS (existing page covers it under different name; add to wiki/_aliases.md and SLUG_STOPS), or REJECT (too generic or template artifact; add to SLUG_STOPS only)
   - If BUILD: create the page per the Page Template from the briefing

=== APPLY ===

7. For each promoted page (from either signal):
   - Confirm it doesn't already exist
   - Create it per the Page Template; use the vault default confidence from the briefing
   - Mark ASSUMPTION markers on any synthesis decisions for owner review

8. For each promoted page: update the source pages that proposed it — fill their
   "## Pages Created/Updated" section with [[slug]] links.

9. Append to [VAULT_PATH]/wiki/log.md:
   ## Phase 4 Synthesis — [date]
   - Source pages scanned: N
   - Nomination-based candidates: N proposed, N promoted (≥3 sources)
   - Frequency-based candidates: N surfaced (≥5 mentions), N built, N aliased, N rejected
   - Total new pages: N
   - Open ASSUMPTION markers: N (flagged for owner review)

Return: a terse summary — "Phase 4 complete: N pages promoted (nomination), N pages built (frequency), N deferred"
```

### Phase 6 — Index rebuild and cleanup

**Gate:** Start only after Phase 4 synthesis subagent returns.

**Step 1: Domain indexes (parallel)**

Fire one subagent per domain index in the vault. Each subagent reads all pages in its domain, then rewrites its `domain-index-<slug>.md` with:
- 4-sentence Overview paragraph
- ≥10-row Diagnostic Quick Reference table mapping questions → page slugs
- Page listings by folder with one-line descriptions drawn from Overview paragraphs
- Cross-domain callout for pages spanning multiple domains

**Step 2: Sequential cleanup (after domain indexes return)**

Run sequentially in main context:

```bash
# Master index rebuild — rebuild index.md alphabetically by folder
find "$VAULT/wiki" -name "*.md" -not -path "*/sources/*" | sort > /tmp/all-pages.txt
# Claude rebuilds index.md from this list directly

# GAPS.md rebuild via shell — exclude sources/ (prevents thousands of noise entries)
cd "$VAULT/wiki"
{ echo "# Knowledge Gaps — $(date +%Y-%m-%d)"; echo;
  for d in $(ls -d */ | grep -v '^sources/$'); do
    echo "## ${d%/}/"; echo;
    grep -rn "GAP:" "$d" 2>/dev/null | while IFS=: read file line rest; do
      echo "- $file line $line: $rest"
    done | cut -c1-250
    echo
  done; } > GAPS.md

# Lint pass — find non-source pages under 600 bytes
find "$VAULT/wiki" -name "*.md" -not -path "*/sources/*" | while read f; do
  size=$(wc -c < "$f")
  [ "$size" -lt 600 ] && echo "STUB: $f ($size bytes)"
done
```

**Step 3: hot.md refresh**

Write a 400-500 word summary to `wiki/hot.md`:
- What was ingested in this session
- Key new concepts promoted in Phase 4
- Domains with most new source coverage
- Top 3 gaps surfaced

### Phase 7 — Mandatory audit gate

**This phase is non-negotiable.** Ingest is not "complete" until the vault audit passes. This catches the failure mode where Phase 4 promotion logic missed concepts that should have become pages, and surfaces them before they ship.

Run the full audit and capture the machine-readable summary:

```bash
cd "$VAULT" && python3 _scripts/vault-audit.py --json 2>&1 | tail -40
```

**Thresholds retuned 2026-09-06** for the rewritten scorer (`_scripts/vault-audit.py`). It earns from zero across four dimensions with hard caps, replacing the old start-at-100 deduction model whose weights were so small that four production vaults reported 100/100 while printing real deductions. Old and new scores are not comparable — a vault that scored 100 before typically lands in the 70s–80s now. **Do not read a lower number as regression.** If the vault still has the old scorer, install the current one from `~/.claude/skills/vault-init/assets/vault-template/assets/_scripts/` before gating.

**Read the binding cap first, not just the score.** The JSON `caps` array names what is actually holding the score down. Remediate *that*, not whatever is easiest.

**Decision tree:**

- **Score ≥ 85 (Maintained and evidenced)** — proceed to completion report. Note remaining sub-5 criteria for owner triage.

- **Score 70–84 (Dependable)** — the expected landing zone for a fresh ingest. Run the safe remediations below, re-run the audit, then proceed and report the final number plus what remains:
  - Stamp pages missing `last-reviewed::` (lifts Epistemics E2)
  - Convert documented CONFLICTs (those already in `corrections.md`) to ACKNOWLEDGED (E3)
  - Convert source-limitation GAPs (text matches "not documented", "not captured", "not in source", "no source captures", "Whether X is unknown") to ACKNOWLEDGED (E4)
  - Add newly built pages to `index.md` and the relevant `domain-index-*.md` (Coverage V4). **An unindexed new page lowers the score** — it fails V4 and, with no inbound links, Integrity I4 too. Three good pages added without wiring dropped a real vault from 83 to 80. Index and cross-link in the same batch you create, and re-run the audit per batch so you can tell which change moved the number.
  - Add inbound links to orphaned pages from their topic neighbours (Integrity I4) — orphans are the single most common reason Integrity stalls at 21

- **Score 50–69 (Working, with gaps)** — run the same remediations, then re-run. If still below 70, **surface to owner**. Name the binding cap and the dimension that triggered it, plus the top 10 candidates from `CONCEPT-COVERAGE.md` for build/alias/reject triage. Do not claim "ingest complete."

- **Score < 50** — stop. Something structural is wrong: the toolkit isn't installed, CLAUDE.md contracts are broken, `sources/` is empty, or Phase 3 didn't write pages. Report the failure honestly; do not remediate around it.

**Never** raise a score by loosening `_scripts/audit-config.json` (widening `freshness_days`, dropping `high_freq_threshold`, or flipping `operational` to `false` to dodge Currency). Config changes are scope declarations, not score levers. If one is genuinely warranted, make it in a separate step, state the reason, and re-baseline.

### Completion Report

After Phase 7 audit passes, report:

```
## Vault Ingest Complete — [VAULT_TITLE]

**Source pages created:** N / N queued
**Phase 4 promotions:** N (nomination-based) + N (frequency-based) = N new concept pages
**Failed files:** N (list below if any)
**Estimated source coverage:** N% (new source pages / total source files)

**Vault audit score (Phase 7):** N / 100
**Open ASSUMPTION markers:** N (owner review needed)
**Top 5 high-freq concept candidates above threshold:** (from CONCEPT-COVERAGE.md, for next triage pass)

**Failed files (retry manually or re-run /vault-ingest):**
- [filename] — [reason]

Next: review ASSUMPTION markers and triage the CONCEPT-COVERAGE candidates. Run /vault-optimize to work the binding cap — target every dimension above 20/25, not a perfect score.
```

## Failure handling

- **Rate limit (HTTP 429/529):** Auto-retry is acceptable — re-queue into the next batch. If the same file rate-limits 3× consecutively, mark PERMANENT_FAIL and skip.
- **All other failures:** Log as FAILED, report to user at end. Do NOT auto-retry — these need human inspection.
- **Image-only PDF:** Logged in Phase 1 Step 4. Skip in Phase 3.
- **Large file (>2000 lines):** 1000-line chunk instruction is in the subagent prompt. Subagent marks each unread portion as `GAP: lines N–M not read — large file, chunk limit reached`.
- **Subagent returns verbose output instead of CREATED/FAILED:** Log as FAILED. Never re-parse verbose output.
- **Session interrupted mid-Phase-3:** Re-run /vault-ingest. Skip list rebuilds from `**File path:**` fields. Only files without a matching source page get queued.

## What this skill does NOT do

- Process files already in wiki/sources/ — always skips those
- Create concept/framework/entity pages during Phase 3 — only source pages
- Handle encrypted or password-protected PDFs

## Related skills

- `/vault-init` — creates a new vault from scratch
- `/vault-optimize` — audits and fixes vault structure before ingesting
- `/vault-link` — wires a vault into a Claude Code project so the project can read the wiki on demand
