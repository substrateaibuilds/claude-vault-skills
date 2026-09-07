# claude-vault-skills

Four Claude Code skills for turning unstructured source material (PDFs, transcripts, CSVs, notes) into a structured Obsidian wiki vault that downstream RAG applications can consume.

## What's in here

| Skill | Purpose |
|---|---|
| `/vault-init` | Scaffold a new Obsidian vault from a 12-question interview. Writes folder structure, `CLAUDE.md`, master index, domain indexes, `INGESTION-PROMPT.md`, and all template files. |
| `/vault-ingest` | Autonomously process every source file in `raw/` through Phase 1 (scan + PDF extract), Phase 1.5 (briefing write), Phase 3 (parallel source-page generation, 10 subagents per turn), Phase 4 (cross-source synthesis with ≥3-vote promotion threshold), and Phase 6 (index rebuild). |
| `/vault-optimize` | Audit a vault against the evidence-gated four-dimension scorecard (Coverage, Integrity, Epistemics, Currency) and remediate the binding cap. Target every dimension above 20/25; ≥85 is the client-handoff bar. |
| `/vault-link` | Wire an existing vault into a Claude Code project so the project reads the wiki on demand. |

## Install (macOS)

```bash
git clone https://github.com/substrateaibuilds/claude-vault-skills.git ~/claude-vault-skills
```

```bash
for s in vault-init vault-ingest vault-optimize vault-link; do ln -sfn ~/claude-vault-skills/$s ~/.claude/skills/$s; done
```

Then verify the skills load by running `claude` in any directory and typing `/vault-init`.

To update later:

```bash
cd ~/claude-vault-skills && git pull
```

## Requirements

- macOS with Homebrew (the skills are designed for macOS; Linux probably works but is untested)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/quickstart)
- [Obsidian](https://obsidian.md) — optional, only needed if you want to browse the finished vault visually
- `pdftotext` (`brew install poppler`) — required if any of your source material is PDF
- `ffmpeg` (`brew install ffmpeg`) — required only if you'll transcribe video before ingest
- `whisper-cpp` (`brew install whisper-cpp`) — same, for video transcription
- `ocrmypdf` (`brew install ocrmypdf`) — required only if you'll OCR image-only PDFs

## Configuring the tag map (optional)

`/vault-optimize`'s R2 remediation auto-adds YAML frontmatter to wiki pages. The tag it applies to each page is driven by `vault-optimize/scripts/tag-map.json` — copy `tag-map.example.json` to `tag-map.json` and edit it to match your vault's taxonomy.

If `tag-map.json` is absent, pages get tagged with an empty `tags: []` field and the script prints a note explaining how to set it up.

## Typical workflow

1. `/vault-init` — scaffolds the vault at `~/Obsidian/<vault-name>/`
2. Drop your source files into `~/Obsidian/<vault-name>/raw/`
3. `/vault-ingest ~/Obsidian/<vault-name>` — autonomous full ingest
4. `/vault-optimize ~/Obsidian/<vault-name>` — audit and remediate the binding cap
5. `/vault-link ~/Obsidian/<vault-name>` — wire the vault into a chatbot/RAG project

## License

MIT
