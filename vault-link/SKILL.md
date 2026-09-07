---
name: vault-link
description: Wire an existing project to consume an existing Obsidian vault in real time. Appends a "Knowledge Vault" section to the project's CLAUDE.md so Claude Code sessions read from the vault's domain-index and wiki pages on-demand. Use when the user wants to "connect this project to my vault", "wire up the vault for this project", "add vault context to this repo", or "let Claude read from the X vault when working on Y".
---

# vault-link

Append a `## Knowledge Vault` section to a project's CLAUDE.md so Claude Code sessions running in that project pull from the vault via the normal Read tool. No MCP, no sync — Claude just reads fresh on each session.

## Steps

### 1. List available vaults

```bash
ls -d ~/Obsidian/*/ 2>/dev/null
```

If none found, tell the user to run `/vault-init` first. Otherwise show the list.

### 2. Interview

Use AskUserQuestion:

- `VAULT` — select one from the available vaults
- `PROJECT_PATH` — default the current working directory; let the user override with a different absolute path
- `TOPIC` — free text, short phrase describing what the vault covers (e.g., "fertility protocols", "ecommerce product catalog"). This goes in the usage sentence.

Detect all domain indexes automatically:

```bash
ls "$VAULT/wiki/domain-index-"*.md 2>/dev/null
```

All found domain indexes will be included in the block. No user selection needed — include all of them.

### 3. Verify vault structure + score

Check that all of these exist:
- `$VAULT/wiki/index.md`
- At least one `$VAULT/wiki/domain-index-*.md`
- `$VAULT/wiki/hot.md` (optional — note if missing)
- Aliases file (optional — check for both names, use whichever exists):
  ```bash
  ls "$VAULT/wiki/aliases.md" "$VAULT/wiki/_aliases.md" 2>/dev/null | head -1
  ```
  Store the result as `ALIASES_PATH`. If neither exists, note it but continue.
- `$VAULT/_scripts/vault-audit.py` (optional — note if missing; vault doesn't have the audit toolkit)

### 3a. Check the vault's audit score

If the audit toolkit is installed, read the score from `$VAULT/wiki/VAULT-AUDIT.md`:

```bash
grep "^## Score:" "$VAULT/wiki/VAULT-AUDIT.md" 2>/dev/null
```

**Decision tree:**
- **Score ≥ 85** — proceed. The vault is in good shape for downstream consumption.
- **Score 70-84** — warn the user. The vault has known coverage gaps; downstream queries may surface incomplete content. Recommend running `/vault-optimize` before linking.
- **Score < 70 or no audit toolkit installed** — strongly recommend running `/vault-optimize` first. Linking a low-quality vault to a project ships its gaps downstream. Ask the user whether to proceed anyway or stop.

If no `VAULT-AUDIT.md` exists, the vault hasn't been audited under the new methodology — strongly recommend running `/vault-optimize` first.

Check whether `$PROJECT_PATH/CLAUDE.md` exists. If missing, ask the user whether to create a fresh one (with just the Knowledge Vault section) or stop.

Check whether the existing CLAUDE.md already contains a `## Knowledge Vault` heading. If yes, ask the user whether to:
- Append a second vault block (for multi-vault projects)
- Replace the existing block
- Cancel

### 4. Append the block

Append this markdown to `$PROJECT_PATH/CLAUDE.md`:

```markdown

---

## Knowledge Vault

- **Vault:** `<VAULT>`
- **Master index:** `<VAULT>/wiki/index.md`
- **Domain indexes (all active):**
<LIST ALL FOUND domain-index-*.md FILES, ONE PER LINE, AS:>
  - `<VAULT>/wiki/domain-index-<slug>.md`
- **Recent changes cache:** `<VAULT>/wiki/hot.md`
- **Alias mappings:** `<ALIASES_PATH>` (resolves alternate names to canonical pages)
- **Audit scorecard:** `<VAULT>/wiki/VAULT-AUDIT.md` (last known score: <SCORE>/100)

**Usage:** for questions about <TOPIC>, read the relevant domain index first, then follow wiki-links to specific pages. Read `hot.md` for recent changes before re-reading the full index. Do not scan `raw/` — that's unprocessed source material.

**Marker conventions in this vault:**
- `GAP:` — open action item. Knowledge that should exist but doesn't yet.
- `ACKNOWLEDGED:` — documented limitation. Information that source material doesn't contain. Not an action item.
- `CONFLICT:` — two sources disagree, unresolved. Treat as uncertainty; cite both positions.
- `ASSUMPTION:` — synthesis decision awaiting owner ratification. Treat as the page's stated position with a caveat that it's pending review.

**Alias resolution:** When a query mentions a term that isn't a wiki page slug, check the aliases file before assuming the concept is missing. Many alternate names map to canonical pages.
```

Substitute `<VAULT>`, `<TOPIC>`, and `<SCORE>` literally (use absolute paths, not `~`, so Claude can resolve them unambiguously). Replace `<ALIASES_PATH>` with the actual path detected in step 3. List every domain index found — do not truncate to one.

### 5. Report

Print:
- Full path of the modified CLAUDE.md
- The exact block that was appended
- A one-line confirmation: the next Claude Code session in this project will read the vault via the domain index automatically

## Safety

- Never overwrite existing CLAUDE.md content — always append (unless the user explicitly approved replacement in step 3).
- Don't modify the vault itself. This skill only touches the project's CLAUDE.md.
- Don't touch any other file in the project.
