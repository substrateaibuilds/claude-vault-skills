---
name: vault-optimize
description: Audit an existing Obsidian wiki vault against the 10/10 quality standard, report its score, and execute the remediations needed to reach 10/10. Use when the user wants to "optimize", "upgrade", "health-check", or "bring up to standard" an existing vault. Different from /vault-init (which creates new vaults from scratch).
---

# vault-optimize

Audit an existing vault against the 10-point standard, score it, and execute remediations in priority order. The goal is a vault that produces consistent, high-quality RAG retrieval when consumed by a downstream chatbot or RAG application.

## The 10/10 Standard

| Point | Tier | What it requires |
|---|---|---|
| 1 | Structure | CLAUDE.md has: confidence taxonomy for this vault's archetype, view evolution tracking (if corpus spans 20+ years OR single-author with documented position shifts), YAML page template, 10-findings + 3-candidates source page template |
| 2 | Structure | `_ingest-briefing.md` exists at wiki/ root (stub accepted if Phase 2 not yet run) |
| 3 | Structure | `INGESTION-PROMPT.md` exists at vault root with all placeholders rendered, correct source-file paths (NOT defaulting to `raw/` if files live elsewhere), sequential fallback note |
| 4 | Page quality | All concept/framework/entity pages have YAML frontmatter (`confidence:`, `source-date:`, `tags:`) |
| 5 | Page quality | All domain indexes have ≥10-row Diagnostic Quick Reference tables |
| 6 | Page quality | Zero orphaned pages (not in index.md or any domain index); zero stub pages under 600 bytes |
| 7 | Source coverage | ≥80% of meaningful source files have source pages in wiki/sources/ |
| 8 | Source coverage | Source pages follow 10-findings + 3-candidates template |
| 9 | Maintenance | GAPS.md is current, organized by domain, has active entries |
| 10 | Maintenance | corrections.md has an active correction workflow with at least one entry |

## Scoring

Score each point 0, 0.5, or 1.0. Total out of 10.

## Steps

### 1. Identify the vault

Ask for the vault path if not provided. Confirm it has `wiki/` and `CLAUDE.md`.

### 2. Run all 10 audit checks

**Point 1 — CLAUDE.md completeness:**
Read CLAUDE.md in full. Check for: confidence taxonomy section, YAML frontmatter in page template (look for `---\nconfidence:`), 10 numbered findings in source template, "Candidate New Pages" section, view evolution section (only required if corpus is 20+ years OR documented major position shifts).
Score 1.0 if all required elements present; 0.5 if partial; 0.0 if absent.

**Point 2 — _ingest-briefing.md:**
```bash
ls wiki/_ingest-briefing.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

**Point 3 — INGESTION-PROMPT.md:**
```bash
ls INGESTION-PROMPT.md 2>/dev/null && echo "EXISTS" || echo "MISSING"
```
If exists, check for unrendered placeholders: `grep -c "{{" INGESTION-PROMPT.md`
Score 1.0 if exists with 0 unrendered placeholders; 0.5 if exists with placeholders; 0.0 if missing.

**Point 4 — YAML frontmatter on pages:**
Sample 5 pages from concept/framework/entity subfolders (not sources/, not navigation files):
```bash
for f in $(find wiki -name "*.md" -not -path "*/sources/*" -not -name "index.md" \
  -not -name "hot.md" -not -name "log.md" -not -name "GAPS.md" \
  -not -name "corrections.md" | shuf | head -5); do
  head -1 "$f"
done
```
Score 1.0 if all 5 start with `---`; 0.5 if some; 0.0 if none.

**Point 5 — Domain index QR tables:**
For each domain-index-*.md: `grep -c "| Presentation\|| Question\|→ Pages" wiki/domain-index-*.md`
Score 1.0 if all domain indexes have ≥10 data rows; 0.5 if some; 0.0 if none.

**Point 6 — Orphaned/stub pages:**
```bash
# Orphan check — uses full wiki-link path pattern to avoid substring false negatives
find wiki -name "*.md" -not -path "*/sources/*" \
  -not -name "index.md" -not -name "hot.md" -not -name "log.md" \
  -not -name "GAPS.md" -not -name "corrections.md" \
  | while read f; do
    name=$(basename "$f" .md)
    if ! grep -qE "\[\[wiki/[^]]*/${name}(\||\]\])" wiki/index.md; then
      echo "ORPHAN: $f"
    fi
  done
# Stub check
find wiki -name "*.md" -not -path "*/sources/*" \
  -not -name "index.md" | while read f; do
  size=$(wc -c < "$f"); [ "$size" -lt 600 ] && echo "STUB ($size): $f"
done
```
Score 1.0 if no orphans and no stubs; 0.5 if minor issues; 0.0 if significant orphaned content.

Note: domain-index-*.md files at the wiki root are NOT orphans even if the pattern doesn't match them — they are navigational root files. Only count subfolder pages as orphaned.

**Point 7 — Source coverage:**
```bash
# Count raw source files (adjust find command for vault-specific raw file location)
raw_count=$(find . -maxdepth 1 \( -name "*.md" -o -name "*.pdf" -o -name "*.txt" \) \
  | grep -v "CLAUDE\|README\|INGESTION" | wc -l)
source_count=$(ls wiki/sources/ | wc -l)
echo "Coverage: $source_count / $raw_count"
```
Score 1.0 if ≥80%; 0.5 if 40-79%; 0.0 if <40%.

**Point 8 — Source page template quality:**
Sample 3 source pages. Check for: "## Key Findings" with numbered items AND "## Candidate New Pages" section.
Score 1.0 if all 3 have both; 0.5 if some; 0.0 if neither.

**Point 9 — GAPS.md:**
```bash
ls wiki/GAPS.md 2>/dev/null && grep -c "^- \*\*GAP\|^- GAP:" wiki/GAPS.md || echo "0"
```
Score 1.0 if exists with ≥5 domain-organized entries; 0.5 if sparse; 0.0 if absent.

**Point 10 — corrections.md:**
```bash
ls wiki/corrections.md 2>/dev/null && grep -c "##" wiki/corrections.md || echo "0"
```
Score 1.0 if present with ≥1 correction entry; 0.5 if present but empty; 0.0 if absent.

### 3. Report audit findings

Present a table with per-point scores and one-line evidence. State the total.

### 4. Confirm before remediating

Ask: "Ready to execute remediations? I'll work through them in priority order."

### 5. Execute remediations in this fixed order

**R1: CLAUDE.md upgrade** (if Point 1 < 1.0)
- Determine vault archetype from existing CLAUDE.md content
- Add missing sections (confidence taxonomy, view evolution if applicable, YAML page template, updated source template)
- **Replace** the existing page template code block with the YAML version — do not add a second template alongside the old one
- Preserve all other existing content

**R2: YAML frontmatter migration** (if Point 4 < 1.0)
- If `~/.claude/skills/vault-optimize/scripts/migrate_vault_frontmatter.py` exists: run it
- If not: write the script (see vault-init skill assets for reference implementation)
- Dry-run first, then execute
- Spot-check 3 pages after execution

**R3: Generate INGESTION-PROMPT.md** (if Point 3 < 1.0)
- Read `~/.claude/skills/vault-init/assets/vault-template/assets/ingestion-prompt.template`
- Render ALL placeholders using vault parameters from CLAUDE.md
- Check vault structure for raw file location — if files are NOT in `raw/`, replace ALL occurrences (≥6) of `raw/` with the correct path
- Verify: `grep -c "{{" INGESTION-PROMPT.md` must return 0

**R4: Create _ingest-briefing.md stub** (if Point 2 < 1.0)
- Write the standard stub content (pre-Phase-2 stub with vault parameters and known conflicts)

**R5: Domain index QR table repair** (if Point 5 < 1.0)
- For each domain index missing a ≥10-row QR table, synthesize rows from domain's existing pages
- Format: `| [Presentation / Question] | → [[page-slug]] |`

**R6: Orphaned page cleanup** (if Point 6 < 1.0)
- Add orphaned pages to index.md and relevant domain indexes
- Delete stub pages under 600 bytes that are not high-traffic (referenced <3 times)
- Note: domain-index-*.md files at wiki root are not orphans even if the grep pattern flags them

**R7–R8: Source coverage scoping** (if Points 7-8 < 1.0)
- Do NOT run ingestion inline — create `wiki/_ingestion-manifest.md` with source files grouped by priority and estimated sessions
- The actual ingestion is a separate multi-session effort using INGESTION-PROMPT.md

**R9–R10: GAPS.md / corrections.md** (if Points 9-10 < 1.0)
- Create GAPS.md from scratch if missing; seed from `GAP:` tags across wiki pages: `grep -rn "GAP:" wiki/ > wiki/GAPS.md`
- Create corrections.md template if missing

### 6. Re-score and report final state

Re-run checks for all remediated points. Report new score and what remains.

### 7. State next steps

Always include:
- New score (X/10)
- Points still below 1.0 and specific action to fix each
- Whether the vault is ready for platform ingestion (score ≥ 7.0 = ingest-ready)
- Reference to INGESTION-PROMPT.md for source coverage expansion sessions

## What vault-optimize does NOT do

- Run the actual ingestion sessions (Points 7-8) — those require separate Claude sessions using INGESTION-PROMPT.md
- Build platform code or new bots — separate task
- Physically merge vaults — never; serve from same platform via domain retrieval
- Overwrite existing page content — only adds infrastructure (frontmatter, files)

## Related skills

- `/vault-init` — creates new vaults from scratch with correct structure
- `superpowers:subagent-driven-development` — for executing optimization in parallel when multiple remediations apply
