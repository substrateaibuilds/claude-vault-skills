---
name: vault-optimize
description: Audit and remediate an existing Obsidian wiki vault against the evidence-gated four-dimension scorecard. Installs the audit toolkit if missing, brings CLAUDE.md to the contract-enforceable standard, runs the four-script audit, and remediates the binding cap until the vault reaches its target band. Use when the user wants to "optimize", "upgrade", "bring up to standard", "score", or "audit" an existing vault. Replaces the old 10/10 forward-only audit — that methodology gave false confidence because it didn't measure the coverage axis (concepts taught in source material but missing as canonical pages).
---

# vault-optimize

Raise an existing vault's band on the four-dimension scorecard: Coverage, Integrity, Epistemics, Currency.

**Target the band, not a perfect number.** The scorer was rewritten 2026-09-06 to earn from zero with hard caps, replacing a deduction model whose weights were so small that four production vaults reported 100/100 while printing real deductions on the same screen. Under the current scorer:

| Band | Score | What it means |
|---|---|---|
| Maintained and evidenced | 85–100 | Every dimension 20+/25, no contract failures. The bar for client handoff. |
| Dependable in the verified scope | 70–84 | Sound, with named gaps. Normal resting state for an active vault. |
| Working, with gaps | 50–69 | A dimension is below 15/25 and is capping the total. |
| Foundation | 25–49 | A dimension is below 10/25. |
| Unproven | 0–24 | Nothing ingested, or nothing measurable. |

100/100 is not the goal and chasing it produces busywork. Getting every dimension above 20 is the goal.

## Why this skill replaced the old 10/10 audit

The original `/vault-optimize` measured a vault on 10 forward-looking quality points (CLAUDE.md completeness, YAML frontmatter, source coverage %, etc.). It could score 10/10 while missing canonical concepts entirely — because forward-looking audits ask "is what's here in good shape?" not "is what should be here actually here?"

The coverage-axis failure was discovered in the Justin Brain vault on 2026-06-05: two foundational concepts ([[metabolic-damage]] and [[metabolic-adaptation]], explicitly named as the canonical example pair in CLAUDE.md) were missing from the vault for months while the vault scored 10/10. The forensic root causes were:

1. **Promotion logic measured nominations, not mentions** — foundational concepts don't get nominated because they don't feel novel
2. **Page-internal GAP markers were invisible to GAPS.md rebuilds**
3. **CLAUDE.md examples were prose-only, never validated as contracts**
4. **Audit posture was forward-only — never measured "what's missing"**
5. **Concept salience inverted by familiarity — most-used terms got least attention**

The new methodology — implemented as `_scripts/vault-audit.py` and three sub-audits — measures all four axes. The 100-point score requires hitting all of them.

## Steps

### 1. Identify the vault

Ask for the vault path if not provided. Confirm it has `wiki/` and `CLAUDE.md`.

### 2. Install the audit toolkit if missing

```bash
VAULT=<vault-path>
if [ ! -f "$VAULT/_scripts/vault-audit.py" ]; then
  mkdir -p "$VAULT/_scripts"
  cp ~/.claude/skills/vault-init/assets/vault-template/assets/_scripts/*.py "$VAULT/_scripts/"
  cp ~/.claude/skills/vault-init/assets/vault-template/assets/_scripts/INSTALL.md "$VAULT/_scripts/"
  echo "Audit toolkit installed at $VAULT/_scripts/"
fi
```

### 3. Bring CLAUDE.md to the contract-enforceable standard

Read CLAUDE.md. Check for the three structural elements the audit depends on:

1. **Marker Conventions section** — documents the four marker types (GAP / ACKNOWLEDGED / CONFLICT / ASSUMPTION) and what each one means
2. **Canonical Example Pairs section** — uses wikilinks, not prose, for any "don't merge X and Y" rules
3. **Vault Audit reference** — points to `python3 _scripts/vault-audit.py` as the maintenance command

If any are missing, surface them to the user and offer to add them. Use the template at `~/.claude/skills/vault-init/assets/vault-template/assets/claude-md.template` as the source for the new sections.

Convert any prose-only canonical example pairs in the existing CLAUDE.md to wikilink form:

```
Before: Do not combine "metabolic damage" and "metabolic adaptation"
After:  Do not combine [[wiki/conditions/metabolic-damage]] and [[wiki/conditions/metabolic-adaptation]]
```

This makes them enforceable by `validate-claude-contracts.py`.

### 4. Run baseline audit

```bash
cd "$VAULT" && python3 _scripts/vault-audit.py --json 2>&1 | tail -40
```

Read `wiki/VAULT-AUDIT.md` for the full scorecard.

Report:
- Score and band: N / 100 — <band>
- Per-dimension subtotals (Coverage / Integrity / Epistemics / Currency)
- **The binding cap and what triggered it** — this is the diagnosis. The lowest dimension is what's holding the score down; everything else is secondary.
- The sub-5 criteria, worst first (the report's "Top action items" is already sorted this way)

### 5. Confirm before remediating

Ask: "Baseline is N/100 (<band>). The binding constraint is <dimension> at X/25 because <criterion evidence>. Ready to remediate? I'll target that dimension first, then the cheap wins."

Do not promise 100/100. Promise the next band up.

### 6. Execute remediations in priority order

**R1: Stamp missing `last-reviewed::` metadata** (free points)

```bash
find "$VAULT/wiki" -name "*.md" ! -path "*/sources/*" \
  -exec grep -L "last-reviewed:" {} + 2>/dev/null \
  | grep -v "domain-index-\|index.md\|GAPS\|log.md\|hot.md\|STATUS\|corrections\|VAULT-AUDIT\|CONCEPT-COVERAGE\|CLAUDE-CONTRACTS\|GAPS-AUDIT\|_aliases\|_ingest\|ASSESSMENT-ENGINE" \
  | while read f; do
    grep -q "^\*\*Sources:\*\*" "$f" 2>/dev/null \
      && perl -i -pe 's/^(\*\*Sources:\*\*.*)$/$1\nlast-reviewed:: '"$(date +%Y-%m-%d)"'/' "$f"
  done
```

**R2: Convert *documented* CONFLICTs to ACKNOWLEDGED** (only those already resolved in corrections.md)

A CONFLICT marker means two sources disagree and a downstream bot will produce a wrong answer. ACKNOWLEDGED means someone read it and decided the disagreement is understood and preserved deliberately. Converting one to the other **per file, after reading it** is remediation. Converting them in bulk is score-gaming, and under the rewritten scorer it is gaming the Epistemics dimension specifically.

```bash
# List every CONFLICT with its file and line — this is a review queue, not a batch job:
grep -rn "CONFLICT:" "$VAULT/wiki" 2>/dev/null
```

Read `wiki/corrections.md`. For each CONFLICT, check whether corrections.md already records a resolution. Convert **only those**, one file at a time, with the user's confirmation:

```bash
# Single file, after reading it and confirming corrections.md covers it:
perl -i -pe 's/\bCONFLICT: /ACKNOWLEDGED: /g; s/\*\*CONFLICT:\*\*/\*\*ACKNOWLEDGED:\*\*/g' "$VAULT/wiki/<folder>/<page>.md"
```

Any CONFLICT with no entry in corrections.md stays a CONFLICT. It is a real finding, and the score is supposed to reflect it.

**R3: Bulk-convert source-limitation GAPs to ACKNOWLEDGED**

GAP markers that describe what the source material couldn't provide aren't action items — they're documented limitations. Common patterns:

```bash
find "$VAULT/wiki" -name "*.md" ! -path "*/sources/*" -exec perl -i -pe '
  s/^(\s*-?\s*)GAP: (.*?(not documented|not in source|not captured|no source captures|not specified|not formalized|not yet documented|not yet quantified|not personally tested|in passing|never elaborated|cited by title|referenced but not|cannot be verified|is unknown|whether \w+ is|whether \w+ are|whether \w+ was).*)$/$1ACKNOWLEDGED: $2/i
' {} +
```

**R4: Triage high-frequency concept-coverage candidates** (the big lever)

```bash
cd "$VAULT" && python3 _scripts/concept-frequency-audit.py
```

Read `wiki/CONCEPT-COVERAGE.md`. The top candidates above the threshold are real action items. For each (in batches of 10-15):

- **REJECT** if too generic (template artifact, descriptor prose, anonymization residue, marketing term) — add slug to `_scripts/concept-frequency-audit.py` `SLUG_STOPS` with an inline `# REJECT:` rationale comment
- **ALIAS** if covered by an existing page under a different name — add to `wiki/_aliases.md` and `SLUG_STOPS` with `# ALIAS: <canonical>` rationale
- **BUILD** if it's a real distinct concept with no existing canonical home — create the page following CLAUDE.md page template; flag ASSUMPTION markers for owner review

Confirm each BUILD with the user before writing.

**R5: Fix orphans and index reachability** (usually the binding constraint on Integrity)

> **Writing a new page LOWERS the score until you index it.** A page that isn't listed in `index.md` or a domain index fails Coverage V4, and one with no inbound links fails Integrity I4 — so three well-researched pages added without wiring dropped `justin-brand-strategy` from 83 to 80 in a real session. This is the scorer working correctly: a page nothing links to is a page a downstream bot will never retrieve, so its knowledge may as well not exist. **Index and cross-link every page in the same batch you create it, and re-run the audit after each batch** — otherwise good work registers as damage and you won't know which change caused it.

Two criteria stall most mature vaults: `I4` (pages with no inbound links) and `V4` (pages not listed in the master or any domain index). Both are cheap to close and both are real retrieval problems — an orphaned page is one a downstream bot will never reach.

```bash
# Pages absent from every index:
cd "$VAULT/wiki" && comm -23 \
  <(find . -name '*.md' ! -path './sources/*' ! -name '_*' ! -name 'domain-index-*' \
      ! -name 'index.md' ! -name 'log.md' ! -name 'hot.md' ! -name 'GAPS*' \
      ! -name 'STATUS.md' ! -name 'corrections.md' ! -name '*-AUDIT.md' \
      ! -name 'CONCEPT-COVERAGE.md' -exec basename {} .md \; | sort -u) \
  <(grep -oh '\[\[[^]|#]*' index.md domain-index-*.md 2>/dev/null \
      | sed 's/\[\[//; s#.*/##; s/\.md$//' | sort -u)
```

Add each to the right domain index, and give it at least one inbound link from a topically adjacent page. Re-run the audit after the batch.

**R5b: Re-run and reassess**

```bash
cd "$VAULT" && python3 _scripts/vault-audit.py --json 2>&1 | tail -40
```

Read the binding cap again — it moves as dimensions rise. Stop when every dimension is above 20/25, or when the remaining work is genuine content authoring rather than remediation. Do not iterate toward 100; the last few points are almost always busywork.

**R6: Final ASSUMPTION marker review**

The audit doesn't penalize ASSUMPTION markers (they're synthesis decisions awaiting owner ratification). But they ARE action items for the owner. Surface them:

```bash
grep -rn "ASSUMPTION:" "$VAULT/wiki" ! -path "*/sources/*" 2>/dev/null
```

Present each to the user with the question: "Ratify (remove marker, content stands) or correct (revise the synthesis)?"

### 7. Re-run and report the final band

```bash
cd "$VAULT" && python3 _scripts/vault-audit.py --json 2>&1 | tail -40
```

Report the score, the band, the per-dimension subtotals, and any cap still binding. List the remaining sub-5 criteria and what would close each one — honestly, including the ones that need content work rather than remediation.

**Do not claim the vault is "complete" or "100%".** State what was measured and what was not. The score covers mechanically checkable properties: coverage against the corpus, link and contract integrity, metadata and conflict discipline. It says nothing about whether the content is *correct*.

### 8. Log the optimization pass

Append to `wiki/log.md`:

```markdown
## YYYY-MM-DD — /vault-optimize pass

**Status:** Score: N / 100 — <band>  (scorer: evidence-gated v2)
**Dimensions:** Coverage N/25 · Integrity N/25 · Epistemics N/25 · Currency N/25 or n/a
**Binding cap at close:** <cap and reason, or "none">

Score path: [baseline] → [after R1] → ... → [final]

Toolkit installation: [installed | already present]
CLAUDE.md upgrades: [list of sections added]
SLUG_STOPS added: N triage decisions
Aliases registered: N canonical-page mappings
Pages built: N (list with brief description)
Metadata stamps applied: N pages
GAP → ACKNOWLEDGED conversions: N
CONFLICT → ACKNOWLEDGED conversions: N
Open ASSUMPTION markers: N (for owner review)
```

### 9. Report final state

Print to the user:
- Final score and band, per-dimension subtotals, and any cap still binding
- Toolkit installed at `_scripts/`
- Reference: `python3 _scripts/vault-audit.py` to maintain the score
- Any open ASSUMPTION markers needing owner review
- Recommendation: run audit after every ingest pass and at least quarterly

## What this skill does NOT do

- Skip the audit gate to "save time" — the score IS the validation
- Auto-ratify ASSUMPTION markers without owner input — those are synthesis decisions the owner must confirm
- Modify source files in `raw/` — only touches wiki/, CLAUDE.md, _scripts/, and meta files
- Build concept pages without confirming with the user — every new page is a knowledge artifact that becomes part of the canonical methodology

## Related skills

- `/vault-init` — creates new vaults with the toolkit pre-installed (this skill is the retrofit version)
- `/vault-ingest` — runs the audit automatically as Phase 7; remediates anything below 85 before claiming complete
- `/vault-link` — verifies source vault score before wiring a project to consume it
- `/vault-audit` — single-shot audit (no remediation); useful for quick health-check between ingest passes
