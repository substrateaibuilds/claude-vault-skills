# Handoff — claude-vault-skills

## Goal

Make the vault audit measure something real, and bring all 32 Obsidian vaults onto it. The prior scorer could not express a failing vault, so vault quality was unknown across the portfolio.

## Current state

**Done.** Scorer rewritten and shipped; 4 commits pushed to `origin/main` (`98de4ec`). All 32 vaults upgraded: new toolkit, per-vault `_scripts/audit-config.json`, current CLAUDE.md audit + marker sections. `_scripts/` is now version-controlled for the first time — previously each vault held a drifting private copy. Five skills live: `vault-init`, `vault-ingest`, `vault-optimize`, `vault-link`, `vault-interview` (all symlinked from `~/.claude/skills/`).

**Model:** four dimensions × 25 (Coverage, Integrity, Epistemics, Currency), five criteria each scored 0/1/3/5 from measured ratios, evidence-gated (no evidence = 0, never full marks), with hard caps that override the arithmetic. Currency is opt-in via `audit-config.json`; only `qure-cx-brain` is operational.

**Portfolio:** sim-crypto-brain 91 · ai-automation-agency-skool 88 · qure-cx-brain 84 · simone-ferretti 84 · youtube-god 84 · dan-harrison 83 · justin-brand-strategy 83 · compact-keywords-seo 81 · jack-kruse 80 · skool-100k 80 · justin-coaching-brain 79 · AI_CASH_ACCELERATOR 79. Twelve at Dependable or better, up from six. Epistemics (unresolved CONFLICTs, GAP density) is the most common binding constraint.

**Open:** `~/.claude` has uncommitted changes — `commands/vault-audit.md` (rewritten this session) and the `skills/vault-interview` symlink. Separate repo, not covered by the push above.

## Active files

- `vault-init/assets/vault-template/assets/_scripts/vault-audit.py` — the scorer
- `vault-init/assets/vault-template/assets/_scripts/gap-rollup.py` — marker rollup
- `vault-init/assets/vault-template/assets/_scripts/validate-claude-contracts.py` — contract audit
- `vault-init/assets/vault-template/assets/_scripts/concept-frequency-audit.py` — **PER-VAULT TUNED once installed; never bulk-copy over a vault**
- `vault-optimize/SKILL.md`, `vault-ingest/SKILL.md`, `vault-init/SKILL.md`, `vault-interview/SKILL.md`
- `~/.claude/commands/vault-audit.md` — uncommitted, different repo

## Changes made

Rewrote the scorer from start-at-100-and-deduct to earn-from-zero with caps. Fixed six measurement bugs, five of which suppressed scores and one of which inflated them: Coverage V1 counted source pages rather than recorded `File path:` entries; the contract validator parsed its own fenced examples, placeholder paths and generated reports as real contracts, and crashed on non-UTF8 bytes; Epistemics E5 required a literal `sources/` substring so bare-slug wikilinks never matched (every vault scored 0 when the true figure was ~96%); E3 counted template-mandated source-page CONFLICT markers; `gap-rollup` scanned its own output (compounding counts) and hid 246 backtick-styled markers.

Added `vault-interview` (tacit-knowledge capture feeding `vault-ingest`), `connections.md` + `decisions/log.md` templates for operational vaults, and `audit-config.json`. Fixed contract failures in 5 vaults and index reachability in 3.

## Failed attempts

- **Bulk-copied the whole toolkit over 12 vaults.** Destroyed per-vault `concept-frequency-audit.py` SLUG_STOPS tuning (272 lines in justin-coaching-brain, 405 in virra-viral-content). Recovered 3 from git, 8 from a local APFS Time Machine snapshot mounted read-only with `sudo mount_apfs` **from Terminal.app** — Ghostty lacked Full Disk Access, and sudo does not grant it.
- **Tried reconstructing lost SLUG_STOPS from `wiki/log.md` + `wiki/_aliases.md`.** Abandoned: recovered 6 of 104 for one vault and injected two false positives harvested from a line describing a relation-type taxonomy. A false SLUG_STOP permanently hides a real concept — worse than the original loss. Do not retry; re-triage from `CONCEPT-COVERAGE.md` instead.
- **Wrote empty `phases/`/`symptoms/` index sections** for folders containing zero files, and a description extractor that pulled `last-reviewed::` inline fields instead of page content. Restored from backup and redid.

## Next steps

1. Commit the two `~/.claude` loose ends (`commands/vault-audit.md`, `skills/vault-interview` symlink) — separate repo, needs its own commit.
2. Delete empty `wiki/phases/` and `wiki/symptoms/` folders in `justin-coaching-brain` (index-noise anti-pattern).
3. Build `wiki/analysis/doug-wallace-view-evolution.md` — the only genuine remaining contract failure portfolio-wide; its CLAUDE.md promises the page and there is no `analysis/` folder.
4. Orphan cross-linking (Integrity I4), worst first: `naudi-aguilar` 100%, `fitpro-ceo-competitive-intel` 62%, `compact-keywords` 60%, `skool-platinum` 42%. Requires judgment about which page should link to which — do not automate.
5. Optional: genericize vault names in the public repo's SKILL.md war stories, or leave as engineering context.
