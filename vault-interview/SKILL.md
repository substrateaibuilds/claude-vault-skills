---
name: vault-interview
description: Extract knowledge that exists only in someone's head into an ingestible vault source file, through a relentless one-question-at-a-time interview that checkpoints every answer to disk immediately. Use when a vault has no corpus to ingest because the knowledge is tacit — "interview me about X", "grill me on my business", "get this out of my head", "build a brain about me", "capture how I actually do this". Also use for client discovery when building a Brain deliverable for someone else.
---

# vault-interview

Every other vault skill presupposes a corpus. `vault-ingest` needs source files; `vault-optimize` needs pages to audit. This skill is the front door for the case where **the corpus doesn't exist yet because it's in a person's head**.

Output is a normal source file in the vault's source location, so it flows through the existing pipeline: interview → source file → `vault-ingest` → wiki pages → `vault-audit`. This is deliberately *not* a parallel knowledge store.

## When to use

- A `personal-brain` archetype vault with an empty corpus
- Client Brain discovery — the client's methodology is undocumented
- A domain in an existing vault that sources cover thinly (audit shows a GAP cluster, but no source material addresses it)
- Capturing operating context for a business brain: priorities, constraints, decision rules, who does what

## When NOT to use

- A corpus already exists on disk → use `vault-ingest`
- You want to fix pages that already exist → use `vault-optimize`
- The knowledge is public/researchable rather than personal → find real sources instead. Interviewing someone about facts they half-remember produces worse material than the primary source.

## Arguments

`/vault-interview <topic>` — optional. If omitted, ask what to interview about.

## Steps

### 1. Locate the vault and its source convention

```bash
VAULT=<vault-path or cwd>
test -f "$VAULT/CLAUDE.md" && test -d "$VAULT/wiki" || echo "not a vault"
```

Read `CLAUDE.md`. Determine where source files live — vault root or `raw/` — using the same rule as `vault-ingest` Phase 1: if the vault root holds source files, that's the location; otherwise `raw/`.

Read the vault's confidence taxonomy and voice rule from `CLAUDE.md`. The interview file must be written to match them.

### 2. Scope the interview

Ask the subject (one question, plainly):

> "What should this session cover? Narrow beats broad — 'how I price a retainer' produces better material than 'my business'."

Then check what the vault already knows, so the interview doesn't re-collect it:

```bash
grep -ril "<topic keywords>" "$VAULT/wiki" 2>/dev/null | head -20
```

Tell the subject what's already covered and confirm the angle.

### 3. Open the capture file immediately

Before asking the first substantive question, create the file. It is appended to after every answer, so an interrupted session loses nothing.

Path: `<source-location>/interview-<topic-slug>-<YYYY-MM-DD>.md`

```markdown
# Interview: <Topic>

- **Type:** interview capture
- **Subject:** <who is being interviewed>
- **Content Date:** <YYYY-MM-DD>
- **Status:** IN PROGRESS
- **Domain(s):** <from CLAUDE.md domain list>

> Captured through /vault-interview. Answers are the subject's own words, lightly
> cleaned for filler only. Interviewer questions are preserved so the framing that
> produced each answer stays visible.

---
```

### 4. Interview — one question at a time

**The discipline is the skill.** Violating any of these produces shallow material:

- **One question per turn.** Never a numbered list. A batch of questions gets a batch of shallow answers.
- **Follow the energy, not the outline.** When an answer contains something specific and surprising, the next question drills into *that*, not the next planned topic.
- **Chase the concrete.** Abstractions are where knowledge goes to hide. "It depends on the client" → "Give me the last two clients where it went differently. What was different?"
- **Ask for the exception.** "When does that *not* work?" surfaces more real methodology than any direct question.
- **Ask for the number.** Prices, durations, thresholds, counts. Vague quantities are the most common thing a vault is missing.
- **Play back what you heard** when an answer is dense, and let them correct it. Corrections are high-value content.
- **Don't teach.** Do not offer your own frameworks, validate, or improve on the answer. You're a recorder with good questions.
- **Push once when an answer is thin,** then move on. Two pushes on the same point is an interrogation.

Good opening moves, in rough order:
1. Concrete instance — "Walk me through the last time you did this, start to finish."
2. Decision rule — "At what point do you decide X instead of Y?"
3. Failure mode — "What goes wrong most often? What causes it?"
4. Exception — "When does your usual approach not apply?"
5. Tacit contrast — "What would someone competent-but-new get wrong here?"
6. Numbers — "What are the actual figures?"
7. Language — "How do you explain this to a client, in your words?"

### 5. Checkpoint after every answer

Append immediately. Never batch writes — an interrupted session must lose at most one answer.

```markdown
## Q: <the question as asked>

<the answer, in the subject's own words>

<!-- optional interviewer note, only when needed:
FOLLOW-UP: <thread worth returning to>
GAP: <something they couldn't answer>
CONFLICT: <contradicts wiki/<page> or an earlier answer in this session>
-->
```

Preserve their phrasing. If `CLAUDE.md` sets `VOICE_PRESERVATION = yes`, their exact terminology **is** the methodology — do not normalize it into neutral business prose. Mark anything you inferred rather than heard with `ASSUMPTION:`.

### 6. Close the session

Stop at the natural end, at ~45 minutes, or when the subject's answers get shorter and more general — that's saturation, not laziness. Then:

1. Flip `**Status:** IN PROGRESS` → `COMPLETE`
2. Append the standard source-page tail so `vault-ingest` can process it unchanged:

```markdown
## Key Findings
1. **<header>** <substantive paragraph drawn from the answers>
   ... (aim for 5–10)

## <VOICE_SECTION_HEADER from CLAUDE.md>
<8–15 verbatim quotes, each with a Q-anchor>

## Cross-Domain Connections
> **Cross-domain:** <how this connects to other domains in this vault>

## Related Pages
- [[slug]] — <why related>

## Candidate New Pages (Pass B)
- `wiki/<folder>/<slug>.md` — <description> — Supporting quote: "<verbatim>"

## Gaps
- GAP: <what the subject couldn't answer and where it might be found>
```

3. Report: file path, question count, candidate pages proposed, open GAPs.

### 7. Hand off to the pipeline

Offer, don't auto-run:

> "Captured N answers to `<path>`. Run `/vault-ingest` to turn this into wiki pages, or run another interview first — batching two or three sessions before ingesting produces better cross-source synthesis, since Pass B promotes concepts nominated by 3+ sources."

That last point matters: `vault-ingest` Phase 4 promotes a concept when **≥3 source pages** nominate it. A single interview can rarely trigger promotion on its own. Say so rather than letting a thin first ingest disappoint.

## Resuming an interrupted session

```bash
grep -l "Status:.*IN PROGRESS" "$VAULT"/interview-*.md "$VAULT"/raw/interview-*.md 2>/dev/null
```

Read the file, summarize what's covered in two lines, and ask whether to continue or close it out.

## What this skill does NOT do

- Write wiki pages directly — that's `vault-ingest`'s job, and routing around it skips Pass B synthesis and the audit gate
- Research or fact-check answers — it records what the subject says; verification is a separate pass
- Score the vault — that's `/vault-audit`

## Related skills

- `vault-init` — scaffold the vault first
- `vault-ingest` — turn the capture into wiki pages
- `vault-audit` / `vault-optimize` — measure and remediate afterward
