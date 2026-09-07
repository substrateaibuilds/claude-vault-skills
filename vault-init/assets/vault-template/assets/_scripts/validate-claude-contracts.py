#!/usr/bin/env python3
"""Validate CLAUDE.md references resolve to real, non-empty wiki pages.

CLAUDE.md acts as the architectural contract for the vault. Any wiki page it
references via [[wikilink]] or backticked `wiki/path.md` syntax MUST exist
and have substantive content. Prose-only mentions are flagged as advisory
(use wikilinks to make them enforceable).

Output: wiki/CLAUDE-CONTRACTS-AUDIT.md
Exits 1 if any contract fails — usable as a Stop hook.
"""
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
CLAUDE_MD = VAULT / "CLAUDE.md"
WIKI = VAULT / "wiki"
REPORT = WIKI / "CLAUDE-CONTRACTS-AUDIT.md"

MIN_CONTENT_BYTES = 200

WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")
BACKTICK_PATH = re.compile(r"`(wiki/[a-zA-Z0-9_/-]+\.md)`")
EXPLICIT_CONTRACT = re.compile(r"<!--\s*contract:\s*(wiki/[a-zA-Z0-9_/-]+\.md)\s*-->")

# Generated audit reports are not page contracts. CLAUDE.md legitimately points
# at them as outputs ("Output: `wiki/CONCEPT-COVERAGE.md`"), and they only exist
# after the relevant sub-audit has run — so an empty vault failed its own
# documentation.
GENERATED_REPORTS = {
    "CONCEPT-COVERAGE.md", "GAPS-AUDIT.md", "VAULT-AUDIT.md",
    "CLAUDE-CONTRACTS-AUDIT.md", "STATUS.md", "GAPS.md", "CLAUDE.md",
}

# Illustrative placeholder paths in templates and examples. Treating these as
# real contracts made every vault fail on its own instructions.
PLACEHOLDER_SEGMENTS = {
    "X", "page-slug", "slug", "concept-a", "concept-b", "folder", "name",
    "vault-name", "other-source-page",
}


def is_placeholder(link):
    if "..." in link or "<" in link or ">" in link or "{{" in link:
        return True
    stem = link.split("/")[-1].replace(".md", "").strip()
    if stem in PLACEHOLDER_SEGMENTS:
        return True
    return any(seg in PLACEHOLDER_SEGMENTS for seg in link.split("/"))



def resolve_link(link):
    link = link.strip()
    if link.endswith(".md"):
        link = link[:-3]
    if link.startswith("wiki/"):
        return VAULT / f"{link}.md"
    slug = link.split("/")[-1]
    matches = list(WIKI.glob(f"**/{slug}.md"))
    matches = [m for m in matches if "/sources/" not in str(m)]
    return matches[0] if matches else None


def check_page(path):
    if path is None:
        return ("MISSING", "no matching file in vault")
    if not path.exists():
        return ("MISSING", "path does not exist")
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return ("MISSING", f"unreadable: {e}")
    if len(content) < MIN_CONTENT_BYTES:
        return ("STUB", f"only {len(content)} bytes")
    if not re.search(r"^##\s+", content, re.MULTILINE):
        return ("STUB", "no ## headings")
    return ("OK", f"{len(content)} bytes")


def main():
    if not CLAUDE_MD.exists():
        print(f"No CLAUDE.md at {CLAUDE_MD}")
        sys.exit(0)

    content = CLAUDE_MD.read_text(encoding="utf-8", errors="replace")

    # Strip fenced code blocks before extracting contracts. Fenced blocks in
    # CLAUDE.md are documentation — they show the *syntax* of a contract, using
    # placeholder paths that intentionally don't exist. Parsing them as real
    # contracts made every vault fail its own instructions and capped the audit
    # at 84 permanently. A genuine contract is never inside a fence.
    content = re.sub(r"^(```|~~~).*?^\1", "", content, flags=re.S | re.M)

    refs = []
    for m in WIKILINK.finditer(content):
        link = m.group(1).strip()
        if link.startswith("wiki/") or "/" in link or link.endswith(".md"):
            refs.append(("wikilink", link))
    for m in BACKTICK_PATH.finditer(content):
        refs.append(("backtick", m.group(1).strip()))
    for m in EXPLICIT_CONTRACT.finditer(content):
        refs.append(("contract", m.group(1).strip()))

    refs = [(k, l) for k, l in refs
            if l.split('/')[-1] not in GENERATED_REPORTS and not is_placeholder(l)]
    seen = set()
    refs = [(k, l) for k, l in refs if not (l in seen or seen.add(l))]

    results = []
    for kind, link in refs:
        resolved = resolve_link(link)
        status, reason = check_page(resolved)
        results.append((kind, link, resolved, status, reason))

    fails = [r for r in results if r[3] != "OK"]
    ok = [r for r in results if r[3] == "OK"]

    lines = [
        "# CLAUDE.md Contracts Audit",
        "",
        "*Regenerate: `python3 _scripts/validate-claude-contracts.py`*",
        "",
        "CLAUDE.md is the architectural contract for this vault. Every wiki page it references via `[[wikilinks]]`, backticked `` `wiki/path.md` `` paths, or explicit `<!-- contract: ... -->` comments must resolve to a real, non-stub page.",
        "",
        f"**Scanned:** `CLAUDE.md` ({CLAUDE_MD.stat().st_size} bytes)",
        f"**Structured references:** {len(results)}",
        f"**OK:** {len(ok)}  |  **STUB:** {sum(1 for r in results if r[3]=='STUB')}  |  **MISSING:** {sum(1 for r in results if r[3]=='MISSING')}",
        "",
        "---",
        "",
        "## Failures" if fails else "## Failures — none",
        "",
    ]
    if fails:
        lines += [
            "| Type | Reference | Status | Reason |",
            "|------|-----------|--------|--------|",
        ]
        for kind, link, _, status, reason in fails:
            badge = {"STUB": "⚠️", "MISSING": "❌"}[status]
            lines.append(f"| {kind} | `{link}` | {badge} {status} | {reason} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Passing references",
        "",
    ]
    if ok:
        lines += [
            "| Type | Reference |",
            "|------|-----------|",
        ]
        for kind, link, _, _, _ in ok:
            lines.append(f"| {kind} | `{link}` |")
    else:
        lines.append("None.")

    lines += [
        "",
        "---",
        "",
        "## How to fix failures",
        "",
        "- **MISSING** — page doesn't exist. Build it (CLAUDE.md template) or remove the reference.",
        "- **STUB** — page exists but is essentially empty (<200 bytes or no `## ` headings). Flesh it out or remove the reference.",
        "",
        "## Making prose-only examples enforceable",
        "",
        "If CLAUDE.md names a concept in prose (e.g. *Do not combine 'metabolic damage' and 'metabolic adaptation'*), this audit cannot catch a regression on that page. To make the prose enforceable:",
        "",
        "1. Convert it to a wikilink: *Do not combine [[wiki/conditions/metabolic-damage]] and [[wiki/conditions/metabolic-adaptation]]*",
        "2. Or add an HTML comment contract: `<!-- contract: wiki/conditions/metabolic-damage.md -->`",
        "",
        "Both forms are detected by this audit.",
        "",
    ]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Scanned {len(results)} references — {len(ok)} OK, {len(fails)} failures")
    print(f"Wrote {REPORT}")
    if fails:
        print("\nFailures:")
        for kind, link, _, status, reason in fails:
            print(f"  {status:8s}  {kind:10s}  {link}  ({reason})")
        sys.exit(1)


if __name__ == "__main__":
    main()
