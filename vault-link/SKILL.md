---
name: vault-link
description: Wire an existing project to consume an existing Obsidian vault in real time. Appends a "Knowledge Vault" section to the project's CLAUDE.md so Claude Code sessions read from the vault's domain-index and wiki pages on-demand. Use when the user wants to "connect this project to my vault", "wire up the vault for this project", "add vault context to this repo", or "let Claude read from the X vault when working on Y".
---

# vault-link

Append a `## Knowledge Vault` section to a project's CLAUDE.md so Claude Code sessions running in that project pull from the vault via the normal Read tool. No MCP, no sync — Claude just reads fresh on each session.

## Steps

### 1. List available vaults

```bash
ls -d ~/Documents/Obsidian/*/ 2>/dev/null
```

If none found, tell the user to run `/vault-init` first. Otherwise show the list.

### 2. Interview

Use AskUserQuestion:

- `VAULT` — select one from the available vaults
- `PROJECT_PATH` — default the current working directory; let the user override with a different absolute path
- `DOMAIN` — list the `domain-index-*.md` files under `$VAULT/wiki/` (glob `~/Documents/Obsidian/<vault>/wiki/domain-index-*.md` and extract the slug from each filename); let the user pick one. If only one exists, pick it automatically and confirm.
- `TOPIC` — free text, short phrase describing what the vault covers (e.g., "fertility protocols", "ecommerce product catalog"). This goes in the usage sentence.

### 3. Verify

Check that all of these exist:
- `$VAULT/wiki/index.md`
- `$VAULT/wiki/domain-index-<DOMAIN>.md`
- `$VAULT/wiki/hot.md` (optional — note if missing)

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
- **Primary domain index:** `<VAULT>/wiki/domain-index-<DOMAIN>.md`
- **Recent changes cache:** `<VAULT>/wiki/hot.md`

**Usage:** for questions about <TOPIC>, read the domain index first, then follow wiki-links to specific pages. Read `hot.md` for recent changes before re-reading the full index. Do not scan `raw/` — that's unprocessed source material.
```

Substitute `<VAULT>`, `<DOMAIN>`, and `<TOPIC>` literally (use absolute paths, not `~`, so Claude can resolve them unambiguously).

### 5. Report

Print:
- Full path of the modified CLAUDE.md
- The exact block that was appended
- A one-line confirmation: the next Claude Code session in this project will read the vault via the domain index automatically

## Safety

- Never overwrite existing CLAUDE.md content — always append (unless the user explicitly approved replacement in step 3).
- Don't modify the vault itself. This skill only touches the project's CLAUDE.md.
- Don't touch any other file in the project.
