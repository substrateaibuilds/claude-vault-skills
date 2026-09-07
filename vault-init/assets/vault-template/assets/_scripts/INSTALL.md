# Vault Audit Toolkit — Install

A portable coverage-axis audit toolkit for Obsidian knowledge vaults built on the [Justin Brain](../CLAUDE.md) template. Drop the `_scripts/` folder into any compatible vault and run.

## What it does

Measures the second axis of vault quality: **what should be here that isn't.**

Most vault audits are forward-looking (does the thing in front of me check out). This toolkit is coverage-looking — it scans source material to identify concepts that are taught but undocumented, references that promise pages that don't exist, and metadata that's missing.

## What's inside

| Script | Purpose | Output |
|--------|---------|--------|
| `concept-frequency-audit.py` | Find concepts mentioned in ≥N source pages but missing as wiki pages | `wiki/CONCEPT-COVERAGE.md` |
| `validate-claude-contracts.py` | Validate every `[[wikilink]]` and backticked path in CLAUDE.md resolves to a real, non-stub page | `wiki/CLAUDE-CONTRACTS-AUDIT.md` |
| `gap-rollup.py` | Roll up every `GAP:` / `CONFLICT:` / `ASSUMPTION:` marker across the wiki into one report | `wiki/GAPS-AUDIT.md` |
| `vault-audit.py` | Master orchestrator. Runs all three above, plus metadata scan, plus scorecard | `wiki/VAULT-AUDIT.md` |

## Vault assumptions

The toolkit assumes the standard Justin Brain layout:

```
vault-root/
├── CLAUDE.md                  ← architectural contract
├── _scripts/                  ← this folder
│   ├── concept-frequency-audit.py
│   ├── validate-claude-contracts.py
│   ├── gap-rollup.py
│   ├── vault-audit.py
│   └── INSTALL.md
└── wiki/
    ├── index.md
    ├── log.md, hot.md, GAPS.md, STATUS.md, corrections.md
    ├── ASSESSMENT-ENGINE-EXPORT.md
    ├── domain-index-*.md
    ├── sources/               ← source-summary pages
    └── <concept folders>/     ← conditions/, science/, nutrition/, etc.
```

If your vault diverges (different folder names, no sources/ folder, etc.), adapt the path constants at the top of each script.

## Install

```
cp -R _scripts /path/to/your-vault/
```

That's it. The scripts use `Path(__file__).resolve().parent.parent` to find the vault root, so they work wherever you drop them.

## Run

From the vault root:

```
python3 _scripts/vault-audit.py
```

This runs all four audits and writes four report files into `wiki/`. Open `wiki/VAULT-AUDIT.md` in Obsidian for the scorecard.

Individual audits can run standalone:

```
python3 _scripts/concept-frequency-audit.py
python3 _scripts/validate-claude-contracts.py
python3 _scripts/gap-rollup.py
```

## Cadence

- **After every ingest pass** — coverage shifts with new sources. Rerun.
- **Quarterly otherwise** — confidence labels and last-reviewed stamps drift.
- **Pre-handoff for client vaults** — if a Brain is being delivered to a client, the master report should hit ≥85 before handover. Under the rewritten scorer this is a real bar: it requires every scored dimension at 20+/25 and no CLAUDE.md contract failures. Vaults that scored 100 under the old deduction model typically land in the 70s–80s now; that is the measurement improving, not the vault degrading.

## Tuning

Each script has tunable constants at the top. The two you'll touch most often:

**`concept-frequency-audit.py`:**
- `MIN_PAGES` — threshold for surfacing candidates (default: 5)
- `SLUG_STOPS` — false-positive slugs you've already triaged
- `WORD_STOPS` — vault-specific boundary words (anonymized placeholders, vault organizing terms, etc.)

**`vault-audit.py`** — tuned through `_scripts/audit-config.json`, not by editing the script:

```json
{
  "operational": false,
  "operational_reason": "Static knowledge corpus...",
  "high_freq_threshold": 15,
  "freshness_days": 90,
  "stub_bytes": 600
}
```

- `operational` — set `true` only for a vault that reaches live systems (a `connections.md` with wired rows). That enables the Currency dimension. Static expert corpora leave it `false` and are scored over the other three dimensions, scaled to 100.
- `operational_reason` — required prose when `operational` is `false`. It prints in the report, so the exclusion is stated rather than silent.
- `high_freq_threshold` — source-mention count above which a missing concept page counts as a coverage gap.
- `freshness_days` — the staleness window for Currency criteria.

## Scoring model (rewritten 2026-09-06)

The previous scorer started at 100 and subtracted small deductions (0.03–0.05 per gap). Four production vaults reported **100/100 while printing real deductions on the same screen** — the arithmetic could not express a failing vault. `youtube-god` had 9 genuine high-frequency coverage gaps and scored 100.

The current scorer earns from zero:

- **Four dimensions**, 25 points each: Coverage, Integrity, Epistemics, Currency.
- **Five criteria per dimension**, each scored **0, 1, 3, or 5** — the highest anchor the measurement fully supports. Never interpolated, never "start full and deduct."
- **Evidence gating.** A criterion with no evidence base scores 0, not full marks. An empty vault does not earn points for having zero unresolved conflicts.
- **Hard caps** override the arithmetic, lowest wins:

| Cap | Trigger |
|---|---|
| 24 | No source pages — nothing ingested |
| 49 | Any scored dimension below 10/25 |
| 69 | Any scored dimension below 15/25 |
| 84 | Any scored dimension below 20/25 |
| 84 | Any unresolved CLAUDE.md contract failure |

| Score | Band |
|---|---|
| 0–24 | Unproven |
| 25–49 | Foundation |
| 50–69 | Working, with gaps |
| 70–84 | Dependable in the verified scope |
| 85–100 | Maintained and evidenced |

Calibration checks the scorer must keep passing:

- A freshly scaffolded vault scores **0**, not 20 and not 70.
- A large, well-formatted vault with a weak dimension is capped — page count and tidy frontmatter cannot buy past it.
- `--json` emits the score, per-dimension subtotals, and applied caps for programmatic gates (used by `vault-ingest` Phase 7).

## How this prevents what happened with metabolic-damage / metabolic-adaptation

The 2026-06-05 discovery: two concepts foundational to Justin's methodology — and explicitly named as the canonical example in CLAUDE.md — were missing from the vault for months. The 2026-05-24 full ingest hit 10/10 on /vault-optimize without catching them.

Five structural reasons (see `wiki/log.md` 2026-06-06 entry for the full forensic):

1. The ingest's promotion logic measured *explicit nominations* in source pages, not *mentions*. Foundational concepts don't get nominated because they don't feel novel.
2. Page-internal `GAP:` markers were invisible to GAPS.md rebuilds.
3. CLAUDE.md examples (`"metabolic damage" and "metabolic adaptation"`) were prose-only — nothing checked them as contracts.
4. /vault-optimize measured *what is here*, not *what should be here*.
5. Concept salience inverted by familiarity — the most-used terms generated the least documentation effort.

The four scripts in this toolkit each close one of those gaps:

| Failure mode | Closed by |
|--------------|-----------|
| Mentions vs nominations | `concept-frequency-audit.py` measures mentions |
| Invisible page-internal GAPs | `gap-rollup.py` greps wiki-wide for the literal marker |
| Prose-only CLAUDE.md examples | `validate-claude-contracts.py` (with CLAUDE.md migrated to wikilinks/explicit contracts) |
| Forward-only audit posture | `vault-audit.py` scores the coverage axis explicitly, separate from forward-looking |
| Salience bias by familiarity | All four — they don't rely on human judgment of what's "interesting" |

## Optional: global slash command

To make `python3 _scripts/vault-audit.py` available as `/vault-audit` across Claude Code sessions in any vault, add:

```
# ~/.claude/commands/vault-audit.md
---
description: Run the coverage-axis vault audit (concept frequency, CLAUDE.md contracts, GAP rollup, scorecard).
---

Run `python3 _scripts/vault-audit.py` from the current vault root. Read the resulting `wiki/VAULT-AUDIT.md` aloud — score, deductions, top action items. Offer to act on the top action item.
```

## License / portability notes

- Pure Python 3.7+, stdlib only. No pip install required.
- Tested on macOS (Python 3.14). Should run unchanged on Linux. Windows untested.
- All paths via `pathlib` — no shell-specific assumptions.
- Reports are vanilla CommonMark — render in Obsidian, GitHub, and every other markdown reader.
