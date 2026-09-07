---
name: vault-init
description: Create a new structured Obsidian knowledge vault for any topic — scaffolds raw/ and wiki/ directories, renders CLAUDE.md, master index, domain indexes, GAPS.md, hot.md, log.md, corrections.md, and a paste-ready ingestion prompt from the shared template assets. Use when the user wants to "build a vault for X", "create an Obsidian wiki for X", "set up a second brain for X", or "spin up a knowledge base for X".
---

# vault-init

Scaffold a new Obsidian vault at `~/Obsidian/<VAULT_NAME>/` using the reusable template at `~/.claude/skills/vault-init/assets/vault-template/`. All template content lives in that visible folder — this skill is the glue that interviews the user, renders placeholders, and writes the vault.

## Steps

### 1. Interview

Use AskUserQuestion to collect parameters. Ask in small batches (AskUserQuestion allows ≤4 at a time); free-text fields can be gathered via a single plain question if needed.

Required parameters:
- `VAULT_NAME` — free text, kebab-case (e.g., `coffee-brewing-research`)
- `VAULT_TITLE` — human-readable title
- `OWNER_NAME` — whose brain / what entity this serves
- `VAULT_PURPOSE` — 1–3 sentences
- `ARCHETYPE` — select one: `personal-brain`, `research-wiki`, `expert-wiki`, `project-kb`, `custom`
- `DOMAINS` — comma-separated list, 1–6 entries (each becomes a `domain-index-<slug>.md`)
- `RAW_SOURCE_TYPES` — comma-separated (e.g., "PDFs, call transcripts, interviews")
- `DOWNSTREAM_CONSUMERS` — comma-separated, or "None"
- `VOICE_PRESERVATION` — `yes` or `no`
- `ANONYMIZATION_RULE` — free text, or "None"
- `CONFIDENCE_DEFAULT` — select one:
  - `settled-unless-noted` — source is generally reliable/mainstream; assume claims are settled unless flagged otherwise (use for factual research, financial reference material, business playbooks)
  - `contested-by-default` — source works against mainstream consensus; assume claims are contested unless proven across 3+ independent sources (use for heterodox scientists, unconventional thinkers)
  - `practical-by-default` — source is operational/coaching; claims are evaluated on utility not truth-value (use for coaching methodology, psychological frameworks, personal brain)
- `MULTI_DECADE_CORPUS` — `yes` or `no`. Does this vault cover a single author's work spanning 20+ years? (yes = triggers view-evolution tracking)
- `OPERATIONAL` — `yes` or `no`. Will this vault reach **live systems** (CRM, calendar, Slack, a database, an analytics API) in addition to ingested source material?
  - `no` (default, and correct for most vaults) — a static knowledge corpus. Expert wikis, research vaults, course rips, coaching corpora. The audit's Currency dimension is not scored and the vault is graded over the other three, scaled to 100.
  - `yes` — an operational brain whose value depends on current data. Business brains, client-ops brains. Scaffolds `connections.md` and `decisions/log.md`, and enables Currency scoring.
  - If `no`, also collect `OPERATIONAL_REASON` — one sentence on why live data doesn't apply. It prints in every audit report, so the exclusion is stated rather than silent. Default: *"Static knowledge corpus. Content comes from ingested source material, not live systems."*

### 2. Confirm

Summarize all collected answers. Ask for confirmation before writing any files.

### 3. Resolve archetype to folder list

Default wiki/ subfolders per archetype:
- `personal-brain` → `frameworks`, `concepts`, `stories`, `protocols`, `assessments`, `sources` + one folder per domain slug
- `research-wiki` → `concepts`, `entities`, `analysis`, `sources`, `tools`, `techniques`
- `expert-wiki` → `concepts`, `entities`, `analysis`, `sources`, `techniques` + one folder per domain slug (domain names should match the expert's own framework, not generic categories)
- `project-kb` → `requirements`, `decisions`, `components`, `stakeholders`, `sources`
- `custom` → ask the user for a comma-separated folder list

### 4. Safety check

Before creating anything, test if `~/Obsidian/<VAULT_NAME>/` already exists. If yes, stop and ask the user whether to abort, pick a new name, or overwrite. Never silently overwrite.

### 5. Scaffold directories

```bash
VAULT=~/Obsidian/<VAULT_NAME>
mkdir -p "$VAULT"/{raw,wiki,.obsidian,_scripts}
mkdir -p "$VAULT"/wiki/<each-archetype-folder>
```

### 6. Copy Obsidian config

```bash
cp ~/.claude/skills/vault-init/assets/vault-template/assets/obsidian-config/*.json "$VAULT"/.obsidian/
```

### 6a. Install the vault audit toolkit

This is non-negotiable. Every vault ships with the four-script audit toolkit so the coverage-axis failure mode (concepts mentioned across many sources but missing as canonical pages) is structurally impossible.

```bash
cp ~/.claude/skills/vault-init/assets/vault-template/assets/_scripts/*.py "$VAULT/_scripts/"
cp ~/.claude/skills/vault-init/assets/vault-template/assets/_scripts/INSTALL.md "$VAULT/_scripts/"
cp ~/.claude/skills/vault-init/assets/vault-template/assets/_scripts/audit-config.json "$VAULT/_scripts/"
```

Then write `$VAULT/_scripts/audit-config.json` with this vault's answers:

```json
{
  "operational": <true if OPERATIONAL = yes, else false>,
  "operational_reason": "<OPERATIONAL_REASON — required when operational is false>",
  "high_freq_threshold": 15,
  "freshness_days": 90,
  "stub_bytes": 600
}
```

After scaffolding, the vault should be able to run `python3 _scripts/vault-audit.py` and produce a baseline scorecard. **Expect a score near 0 — that is correct.** The scorer earns points from measured evidence and gates criteria with no evidence base to 0, so a vault with no content is `Unproven`. A fresh scaffold that scored well would mean the scorer was broken. Verify this in step 9.

### 7. Render and write template files

For each `.template` file in `~/.claude/skills/vault-init/assets/vault-template/assets/`, Read it, substitute every `{{PLACEHOLDER}}`, and Write the result to the vault. Mapping:

| Template | Destination |
|---|---|
| `claude-md.template` | `$VAULT/CLAUDE.md` |
| `index-md.template` | `$VAULT/wiki/index.md` |
| `hot-md.template` | `$VAULT/wiki/hot.md` |
| `log-md.template` | `$VAULT/wiki/log.md` |
| `gaps-md.template` | `$VAULT/wiki/GAPS.md` |
| `corrections-md.template` | `$VAULT/wiki/corrections.md` |
| `aliases-md.template` | `$VAULT/wiki/_aliases.md` |
| `domain-index.template` | `$VAULT/wiki/domain-index-<slug>.md` (one per domain) |
| `ingestion-prompt.template` | `$VAULT/INGESTION-PROMPT.md` |

**Only when `OPERATIONAL = yes`** — skip both otherwise. An unused `connections.md` full of permanent placeholder rows is noise that every future audit has to explain away, and an empty `decisions/` folder is exactly the kind of pre-created structure that rots:

| Template | Destination |
|---|---|
| `connections-md.template` | `$VAULT/connections.md` |
| `decisions-log-md.template` | `$VAULT/decisions/log.md` (`mkdir -p "$VAULT/decisions"` first) |

Also create this stub file directly (no template needed — its content is generated dynamically during Phase 2):

```bash
cat > "$VAULT/wiki/_ingest-briefing.md" << 'EOF'
# Ingest Briefing — (Generated During Phase 2)

This file does not exist yet. It is written by the Phase 2 orchestrator at the end of
the foundational ingest pass. It contains: project context, critical rules, full slug
inventory, page template, filename conventions, and return-value discipline.

Every Phase 3 subagent reads this file before processing its source file.
EOF
```

### 8. Placeholder substitution rules

Direct substitutions (straight replacement):
- `{{VAULT_NAME}}`, `{{VAULT_TITLE}}`, `{{OWNER_NAME}}`, `{{VAULT_PURPOSE}}`, `{{RAW_SOURCE_TYPES}}` (render as comma-joined list)
- `{{ARCHETYPE}}` — the selected archetype slug (used by `decisions-log-md.template`)
- `{{DATE}}` — today's date in `YYYY-MM-DD` format
- `{{DOMAIN_COUNT}}` — integer count of domains

Constructed substitutions (build from the interview answers):

- `{{DOMAIN_INDEX_LIST}}` — for CLAUDE.md tree. Format each as `  domain-index-<slug>.md    — Pages relevant to <domain name> only` (indented 2 spaces, line per domain, joined with newlines).

- `{{DOMAIN_NAME}}` — for `domain-index.template`. The human-readable domain name (e.g., "Investing", "Client Acquisition"). Rendered once per domain when creating that domain's index file.

- `{{DOMAIN_DESCRIPTION}}` — for `domain-index.template`. A short phrase describing the domain's scope (e.g., "stock selection, portfolio construction, and capital allocation principles"). Rendered once per domain.

- `{{DOMAIN_INDEX_TABLE}}` — markdown table in CLAUDE.md:
  ```
  | File | Purpose |
  |------|---------|
  | `domain-index-<slug>.md` | All pages relevant to <domain name> |
  ```

- `{{WIKI_SUBFOLDER_LIST}}` — for CLAUDE.md. Tree-style block listing each wiki subfolder with a one-line description. Use reasonable defaults per archetype. For domain-named folders added on top, use the domain's own description.

- `{{DOMAIN_INDEX_BULLET_LIST}}` — for log.md. One bullet per domain: `- wiki/domain-index-<slug>.md (stub)`.

- `{{SUBFOLDER_LIST}}` — for log.md. Comma-joined list of the archetype + domain folder names.

- `{{FOLDER_SECTIONS}}` — for index.md. One section per wiki subfolder:
  ```
  ## <folder>/
  _(Empty — populated during ingestion)_
  ```

- `{{DOMAIN_GAP_SECTIONS}}` — for GAPS.md. One section per domain:
  ```
  ## <Domain Name> Gaps

  _(populated during ingestion)_
  ```

Toggled substitutions:

- `{{VOICE_RULE_SECTION}}` (CLAUDE.md) — a full subsection block.
  - If `VOICE_PRESERVATION = yes`:
    ```
    Preserve Source Voice
    Exact terminology, phrases, and analogies from the source ARE the methodology. An AI trained on this wiki must sound like the source, not a textbook. Capture specific terms, analogies, storytelling patterns, and rhetorical moves. Every `## Source Language` section is non-negotiable — these quotes are what downstream bots cite.
    ```
  - If `no`:
    ```
    Normalize Language
    Use clear, neutral terminology. Prioritize clarity and consistency over preserving source-specific phrasing. Normalize tone across pages.
    ```

- `{{VOICE_RULE}}` (ingestion-prompt) — one-liner version.
  - yes: `Preserve source voice verbatim — exact phrases, analogies, and terminology.`
  - no: `Normalize terminology and tone across pages.`

- `{{VOICE_SECTION_HEADER}}` (CLAUDE.md page template) — `Source Language` (yes) or `Key Terms` (no).

- `{{VOICE_EXTRACTION_NOTE}}` (ingestion-prompt Phase 4) — yes: `**Exact language** — phrases, analogies, rhetorical moves. Capture verbatim for downstream voice-cloning use.` no: `**Key terminology** — normalize phrasing; capture terms of art only.`

- `{{ANONYMIZATION_RULE_SECTION}}` (CLAUDE.md) — a subsection block.
  - If rule ≠ "None": `Anonymize Per Rule\n<rule text>\nNo real names, identifying employers, locations, or family details from transcripts.`
  - If "None": `No Anonymization Required\nSource material does not contain PII requiring redaction.`

- `{{ANONYMIZATION_RULE}}` (ingestion-prompt) — one-liner of the rule, or `No anonymization required.`

- `{{CONVERSATIONAL_ANONYMIZATION_NOTE}}` (ingestion-prompt Phase 4) — restates the rule scoped to transcripts, or `No anonymization required for conversational material.`

- `{{DOWNSTREAM_CONSUMERS_SECTION}}` (CLAUDE.md + ingestion-prompt) —
  - If list non-empty: `## Downstream Consumers\n\nThis wiki is queried by: <comma-joined list>. Ingestion should prioritize what these systems need.`
  - If "None": omit the section (render empty string).

- `{{CONFIDENCE_TAXONOMY_SECTION}}` (CLAUDE.md) — based on `CONFIDENCE_DEFAULT`:

  If `settled-unless-noted`:
  ```markdown
  ## Confidence Taxonomy

  Every concept/framework/entity page must include a `confidence:` frontmatter field using these values:

  | Value | When to use |
  |-------|-------------|
  | `settled` | Consistent across 3+ independent sources spanning different periods |
  | `contested` | Internally consistent and well-defended, but contradicted by other sources |
  | `single-source` | Only one source covers this; may not generalize |
  | `needs-research` | Referenced but insufficient detail to classify; flag for future ingest |

  **Default:** `single-source` unless explicitly cross-corroborated.
  ```

  If `contested-by-default`:
  ```markdown
  ## Confidence Taxonomy

  Every concept/framework/entity page must include a `confidence:` frontmatter field. This vault covers a source working against mainstream consensus — the default must reflect that.

  | Value | When to use |
  |-------|-------------|
  | `settled` | Consistent across 3+ independent sources from DIFFERENT epistemic traditions; empirically corroborated |
  | `contested` | Expert's view diverges from mainstream but has substantial defense in their corpus |
  | `fringe` | Expert's view is rejected by mainstream AND may carry clinical/social cost if presented as settled |
  | `needs-research` | Mentioned but insufficient detail to classify |

  **Default:** `contested`. Only promote to `settled` if 3+ independent non-partisan sources agree. Never default to `settled`.

  **Format:** YAML frontmatter fenced with `---`. Do NOT use Obsidian Dataview `::` syntax — the consuming app's parser expects YAML.
  ```

  If `practical-by-default`:
  ```markdown
  ## Confidence Taxonomy

  Every concept/framework/entity page must include a `confidence:` frontmatter field. In this vault, confidence reflects operational reliability, not epistemic certainty.

  | Value | When to use |
  |-------|-------------|
  | `practical` | Operationally defined and tested; mechanism may be disputed but utility is established |
  | `doctrinal` | Internal to a tradition; valid within its premise-set; doesn't transfer without accepting those premises |
  | `speculative` | AI-synthesized inference or theoretical extrapolation; not directly verified |
  | `needs-research` | Referenced but insufficient detail to classify |

  **Default:** `doctrinal` for tradition-sourced content, `speculative` for synthesized claims. Never default to `practical` without operational evidence.

  **Format:** YAML frontmatter fenced with `---`. Do NOT use Obsidian Dataview `::` syntax.
  ```

- `{{VIEW_EVOLUTION_SECTION}}` (CLAUDE.md + ingestion-prompt) —
  - If `MULTI_DECADE_CORPUS = yes`:
    ```markdown
    ## View Evolution Tracking

    This vault covers source material spanning 20+ years from a single author. The author's views may have evolved over time. Apply these rules:

    1. When a concept page draws from sources spanning ≥20 years, add `view-evolution:: candidate` to the page's frontmatter.
    2. After Phase 4 synthesis, create `wiki/analysis/[author-slug]-view-evolution.md` cataloguing the thematic drift areas identified (pages where early and late-career positions differ).
    3. Conflict sections on evolved pages must note the era: "**Early-career view (pre-[year]):** [...] **Later view ([year]+):** [...]"
    4. Do not silently merge old and new positions — the temporal dimension IS the content.
    ```
  - If `no`: omit (render empty string).

- `{{SEQUENTIAL_FALLBACK_NOTE}}` (ingestion-prompt Architecture section) — always include this block:
  ```markdown
  **Claude Max / no background subagents:** If you are running under Claude Max or a tier that does not support `run_in_background: true`, fall back to the sequential pattern: Read 3-4 source files in main context → write 3-4 source pages → continue until complete. This is ~5× slower but produces identical quality. Never mix parallel and sequential mid-batch.
  ```

### 9. Verify the audit toolkit + report

Run the audit on the freshly-scaffolded vault to verify the toolkit is installed correctly:

```bash
cd "$VAULT" && python3 _scripts/vault-audit.py 2>&1 | tail -12
```

Expected output for a freshly-scaffolded vault: **0 / 100 — Unproven**, with no script errors. That is a passing installation check, not a problem. If the score comes back high, the scorer's evidence gating is broken — investigate rather than celebrating.

If `vault-audit.py` fails with import or path errors, the toolkit installation is broken — investigate before reporting success.

Print a summary to the user:
- Vault path
- Files written (count + list, including `_scripts/`)
- Baseline audit score — say plainly that 0/Unproven is expected for an empty vault
- Whether the vault is operational (Currency scored) or a static corpus (Currency `n/a`)
- Next steps:
  1. Add source material — drop files into `$VAULT/raw/` (or the vault root), **or** run `/vault-interview` if the knowledge is still in someone's head
  2. `cd $VAULT && claude`
  3. Run `/vault-ingest`, or paste `INGESTION-PROMPT.md` as the first message
  4. After ingest, run `/vault-audit`. A first ingest typically lands in **Working, with gaps (50–69)** or **Dependable (70–84)**. Every dimension above 20/25 is the goal; 100/100 is not, and chasing it produces busywork.
  5. Later, invoke `/vault-link` to connect a project to this vault

## Safety

- Never overwrite an existing vault silently. Always check first and ask.
- All operations are local; no network calls, no secrets.
- Don't `git init` the vault — let the user decide whether to version-control it.
