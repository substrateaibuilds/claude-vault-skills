# Obsidian Vault Template — Reusable Walkthrough

*Create a new structured knowledge vault for any topic. Karpathy-style `raw/` → `wiki/` split, domain-indexed `CLAUDE.md`, phased LLM ingestion, gap analysis, bidirectional linking.*

*Prefer automation? Invoke `/vault-init` in Claude Code — it runs this walkthrough for you. This doc is the source of truth; the skill calls the same assets.*

---

## Step 0 — Fill In Parameters

Answer these before starting. These thread through every file the template writes.

| Key | Example | Notes |
|---|---|---|
| `VAULT_NAME` | `coffee-brewing-research` | Directory under `~/Obsidian/`; kebab-case |
| `VAULT_TITLE` | Coffee Brewing Research Wiki | Human-readable title |
| `OWNER_NAME` | Jane Doe | Whose brain / what entity this serves; shown in CLAUDE.md + ingestion prompt |
| `VAULT_PURPOSE` | 1–3 sentences explaining what this vault is and why it exists | Goes into CLAUDE.md verbatim |
| `ARCHETYPE` | `personal-brain` / `research-wiki` / `project-kb` / `custom` | Determines default `wiki/` folder set (see Step 1) |
| `DOMAINS` | `["origin", "method", "equipment"]` | One `domain-index-<slug>.md` per entry |
| `RAW_SOURCE_TYPES` | `["PDFs", "barista interviews", "supplier spec sheets"]` | Shown in CLAUDE.md; tailors extraction rules |
| `DOWNSTREAM_CONSUMERS` | `["brew-recommender-app"]` or `"None"` | AI systems or projects that will query the vault |
| `VOICE_PRESERVATION` | `yes` / `no` | `yes` when the source's exact terminology matters (personal brains); `no` for neutral research wikis |
| `ANONYMIZATION_RULE` | `"Replace client names with Client A/B/C"` or `"None"` | Extraction rule for PII |

## Step 1 — Pick Archetype

| Archetype | Default `wiki/` subfolders | When to use |
|---|---|---|
| `personal-brain` | `frameworks/`, `concepts/`, `stories/`, `protocols/`, `assessments/`, `sources/` + your domain folders | Coaching brains, second-brains, expert methodology vaults |
| `research-wiki` | `concepts/`, `entities/`, `analysis/`, `sources/`, `tools/`, `techniques/` | Reading digests, research collections, topic studies (Karpathy's YouTube wiki uses this) |
| `project-kb` | `requirements/`, `decisions/`, `components/`, `stakeholders/`, `sources/` | Project/company knowledge bases |
| `custom` | You define the list | Everything else |

## Step 2 — Scaffold Folders

```bash
VAULT=~/Obsidian/{{VAULT_NAME}}
mkdir -p "$VAULT"/{raw,wiki,.obsidian}

# Archetype subfolders (example for research-wiki):
mkdir -p "$VAULT"/wiki/{concepts,entities,analysis,sources,tools,techniques}

# Plus one folder per domain you want surfaced independently
# (often the same slugs you use for domain indexes):
# mkdir -p "$VAULT"/wiki/{origin,method,equipment}
```

## Step 3 — Copy Obsidian Config

From this template directory:
```bash
cp ~/.claude/skills/vault-init/assets/vault-template/assets/obsidian-config/*.json "$VAULT"/.obsidian/
```

This gives you a minimal, battle-tested Obsidian config — core plugins only, graph view pre-configured.

## Step 4 — Write Scaffold Files

Render each `assets/*.template` by replacing `{{PLACEHOLDERS}}` with your values. Write to:

| Source template | Destination in vault |
|---|---|
| `assets/claude-md.template` | `CLAUDE.md` (vault root) |
| `assets/index-md.template` | `wiki/index.md` |
| `assets/hot-md.template` | `wiki/hot.md` |
| `assets/log-md.template` | `wiki/log.md` |
| `assets/gaps-md.template` | `wiki/GAPS.md` |
| `assets/domain-index.template` | `wiki/domain-index-<slug>.md` (× N, one per domain) |
| `assets/ingestion-prompt.template` | `INGESTION-PROMPT.md` (vault root) |

### Placeholder reference

Simple substitutions:
- `{{VAULT_NAME}}`, `{{VAULT_TITLE}}`, `{{OWNER_NAME}}`, `{{VAULT_PURPOSE}}`, `{{RAW_SOURCE_TYPES}}`, `{{DATE}}` (today, `YYYY-MM-DD`), `{{DOMAIN_COUNT}}`

Constructed (the skill builds these from your answers — if running manually, paste the hand-built version):
- `{{DOMAIN_INDEX_LIST}}` (CLAUDE.md) — one line per domain in tree-style
- `{{DOMAIN_INDEX_TABLE}}` (CLAUDE.md) — markdown table: domain → purpose
- `{{WIKI_SUBFOLDER_LIST}}` (CLAUDE.md) — tree of wiki/ subfolders, one-line description each
- `{{DOMAIN_INDEX_BULLET_LIST}}` (log.md) — bulleted list of domain index filenames
- `{{FOLDER_SECTIONS}}` (index.md) — empty `## folder/` heading per wiki subfolder
- `{{DOMAIN_GAP_SECTIONS}}` (GAPS.md) — `## <domain> Gaps` placeholder per domain
- `{{SUBFOLDER_LIST}}` (log.md) — comma-separated list of wiki subfolders

Toggled sections (controlled by `VOICE_PRESERVATION` and `ANONYMIZATION_RULE`):
- `{{VOICE_RULE_SECTION}}` (CLAUDE.md) — if `yes`: "Preserve source voice verbatim — exact phrases, analogies, and terminology ARE the methodology." If `no`: "Normalize terminology and tone; prioritize clarity over voice."
- `{{VOICE_RULE}}` (ingestion-prompt) — short one-liner, same toggle
- `{{VOICE_SECTION_HEADER}}` (CLAUDE.md page template) — "Source Language" (if yes) / "Key Terms" (if no)
- `{{VOICE_EXTRACTION_NOTE}}` (ingestion-prompt Phase 4) — if yes: "Exact language, phrases, analogies — capture verbatim for voice-cloning downstream use." If no: omit or "Normalize phrasing."
- `{{ANONYMIZATION_RULE_SECTION}}` (CLAUDE.md) — header + rule text, or "No anonymization required for this vault."
- `{{ANONYMIZATION_RULE}}` (ingestion-prompt) — one-liner, same
- `{{CONVERSATIONAL_ANONYMIZATION_NOTE}}` (ingestion-prompt Phase 4) — restates the rule for transcript handling
- `{{DOWNSTREAM_CONSUMERS_SECTION}}` (CLAUDE.md + ingestion-prompt) — paragraph listing consumers, or "No downstream consumers; vault is for direct human reference only."

## Step 5 — Drop Raw Files in `raw/`

Whatever you're ingesting: PDFs, transcripts, articles, meeting notes, scripts, exports. No preprocessing needed.

**Tip:** use the [Obsidian Web Clipper](https://obsidian.md/clipper) browser extension to deposit web articles straight into `raw/` — set the Web Clipper default folder to `raw/` for this vault.

## Step 6 — Run Ingestion

Open Claude Code in the vault root:
```bash
cd "$VAULT" && claude
```

Paste the contents of `INGESTION-PROMPT.md` as your first message. The prompt runs a 6-pass ingestion:

1. **Scan & categorize** — inventory of raw files, batching plan
2. **Foundational material** — courses, protocols, reference PDFs
3. **Assessments & forms** — intake questions, scoring logic
4. **Conversational material** — transcripts, interviews (typically biggest)
5. **Remaining material** — marketing copy, scripts, misc
6. **Build indexes + gap analysis** — master index, domain indexes, lint, GAPS.md, hot.md

The session logs progress to `wiki/log.md` continuously — if interrupted, resume by pointing Claude at the log.

## Step 7 — Maintenance (Weekly or Per-Ingest)

Paste this lint prompt periodically:

```
Lint this wiki. Scan for:
- Orphaned pages (not in any index)
- Missing backlinks (A references B but B doesn't link A)
- Broken wikilinks (pointing at nonexistent pages)
- GAP: markers — list all
- CONFLICT: markers — list all
- Stub pages (headers only, no content)
Report findings. Do not invent content — if a page is under-filled, log it as a GAP.
```

## Step 8 — Connect Vault to a Project

Two options:

**Automated.** Invoke `/vault-link` in Claude Code — it lists your vaults, asks which one and which domain, and appends the block to the target project's `CLAUDE.md`.

**Manual.** Append to the target project's `CLAUDE.md`:

```markdown

---

## Knowledge Vault

- **Vault:** `~/Obsidian/{{VAULT_NAME}}`
- **Master index:** `~/Obsidian/{{VAULT_NAME}}/wiki/index.md`
- **Primary domain index:** `~/Obsidian/{{VAULT_NAME}}/wiki/domain-index-{{DOMAIN}}.md`
- **Recent changes cache:** `~/Obsidian/{{VAULT_NAME}}/wiki/hot.md`

**Usage:** for questions about {{TOPIC}}, read the domain-index first, then follow wiki-links to specific pages. Read `hot.md` for recent changes before full index re-reads. Do not scan `raw/` — that's unprocessed source material.
```

Claude Code reads the project `CLAUDE.md` at session start, sees the Knowledge Vault block, and pulls vault pages on-demand via normal Read calls. No MCP, no sync, no daemon. Edits in Obsidian are immediately visible on the next session.

## Universal Non-Negotiables (carried into every vault)

- **Never invent.** Flag with `GAP:`, `CONFLICT:`, or `Assumption:`.
- **Preserve source voice verbatim** when `VOICE_PRESERVATION = yes`; normalize when `= no`.
- **Bidirectional wikilinks** — if A references B, B must link A.
- **Cross-domain callouts** — `> **Cross-domain:** [...]` blocks mark bridges.
- **Anonymize** per the `ANONYMIZATION_RULE` you chose.
- **Log every operation** in `log.md` so an interrupted session can resume.
- **Never merge distinct concepts** — if the source treats things as separate, they stay separate.

## When This Template Stops Working

The Karpathy-style raw/→wiki/ pattern scales well up to a few hundred wiki pages with good indexes. Beyond that:
- Consider sharding into multiple vaults (one per major domain) linked via project CLAUDE.mds.
- Or move to a vector database / semantic search RAG setup. This template is explicitly a simple, token-cheap alternative — it isn't meant to replace RAG at million-document scale.
