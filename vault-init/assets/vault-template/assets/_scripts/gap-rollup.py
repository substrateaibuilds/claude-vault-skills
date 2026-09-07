#!/usr/bin/env python3
"""Scan the entire wiki for GAP: and CONFLICT: markers and roll them up.

Finds markers wherever they live — concept-page Gaps sections, source-page
Gaps sections, inline prose, anywhere. Produces a unified report grouped by
location so action-items are scannable.

Output: wiki/GAPS-AUDIT.md
"""
import re
from collections import defaultdict
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
WIKI = VAULT / "wiki"
REPORT = WIKI / "GAPS-AUDIT.md"

MARKER = re.compile(r"(?<!`)\b(GAP|CONFLICT|ASSUMPTION|ACKNOWLEDGED):\s*(.+)$", re.MULTILINE)

# Markers styled with backticks at the start of a line — `GAP:` or `- `CONFLICT:``.
# Authors backtick the marker word for visual emphasis in Obsidian, and the
# backtick lookbehind above made every one of them invisible to the audit. That
# INFLATED scores (fewer markers counted = better Epistemics), which is the
# dangerous direction: 246 real markers portfolio-wide, 164 on concept pages,
# were being hidden. Line-initial position is what distinguishes a real marker
# from prose that merely mentions the vocabulary ("use the `GAP:` marker"),
# which stays excluded.
MARKER_STYLED = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*)?`(GAP|CONFLICT|ASSUMPTION|ACKNOWLEDGED):`?(?:\*\*)?\s*(.+)$")

# Generated reports and meta files are EXCLUDED from the scan.
#
# Without this the rollup counts markers inside its own output: every run wrote
# the marker text into GAPS-AUDIT.md, and the next run counted those lines as
# fresh findings, so counts compounded run over run. It also counted the files
# that merely *document* the marker vocabulary (_ingest-briefing.md, GAPS.md),
# reporting the instructions as though they were defects. On justin-brand-strategy
# this inflated CONFLICT from ~14 real markers to 53.
SKIP_FILES = {
    "GAPS-AUDIT.md", "GAPS.md", "VAULT-AUDIT.md", "CONCEPT-COVERAGE.md",
    "CLAUDE-CONTRACTS-AUDIT.md", "STATUS.md", "_ingest-briefing.md",
    "_aliases.md", "corrections.md", "log.md", "hot.md",
}


def classify(rel_path):
    parts = rel_path.split("/")
    if len(parts) <= 1:
        return "root"
    if parts[0] == "sources":
        return "source"
    return "concept"


def main():
    by_location = defaultdict(list)
    counts = {"GAP": 0, "CONFLICT": 0, "ASSUMPTION": 0, "ACKNOWLEDGED": 0}
    # Split counts: GAP-only per location (the "real" action item count)
    gap_only_by_location = defaultdict(int)
    # CONFLICT-only per location. Source pages are REQUIRED by the source-page
    # template to carry a "## Where This Contradicts Other Sources" section with
    # `- CONFLICT:` lines, so a well-authored source page necessarily has them.
    # Counting those as defects penalises a vault for following its own contract.
    # Only concept-page conflicts are unresolved-disagreement action items.
    conflict_only_by_location = defaultdict(int)

    for md in sorted(WIKI.rglob("*.md")):
        if md.name in SKIP_FILES:
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = md.relative_to(WIKI).as_posix()
        location = classify(rel)
        for line_no, line in enumerate(content.splitlines(), 1):
            matches = list(MARKER.finditer(line))
            if not matches:
                sm = MARKER_STYLED.match(line)
                matches = [sm] if sm else []
            for m in matches:
                kind = m.group(1)
                text = m.group(2).strip()
                counts[kind] += 1
                if kind == "GAP":
                    gap_only_by_location[location] += 1
                if kind == "CONFLICT":
                    conflict_only_by_location[location] += 1
                by_location[location].append({
                    "kind": kind,
                    "file": rel,
                    "line": line_no,
                    "text": text,
                })

    total = sum(counts.values())

    lines = [
        "# Gaps Audit",
        "",
        "*Regenerate: `python3 _scripts/gap-rollup.py`*",
        "",
        f"All `GAP:`, `CONFLICT:`, and `ASSUMPTION:` markers across the wiki, grouped by location. Concept-page markers are action items (you can fix them). Source-page markers usually reflect limitations of the original source material.",
        "",
        f"**Total markers:** {total} ({counts['GAP']} GAP · {counts['CONFLICT']} CONFLICT · {counts['ASSUMPTION']} ASSUMPTION · {counts['ACKNOWLEDGED']} ACKNOWLEDGED)",
        f"**Concept-page markers:** {len(by_location.get('concept', []))}",
        f"**Concept-page GAP-only (real action items):** {gap_only_by_location.get('concept', 0)}",
        f"**Concept-page CONFLICT-only (unresolved disagreements):** {conflict_only_by_location.get('concept', 0)}",
        f"**Source-page CONFLICT-only (template-mandated cross-source notes):** {conflict_only_by_location.get('source', 0)}",
        f"**Source-page markers:** {len(by_location.get('source', []))}",
        f"**Root-file markers:** {len(by_location.get('root', []))}",
        "",
        "---",
        "",
    ]

    for section_key, title, hint in [
        ("root", "Root wiki files", "These are meta-files (index, GAPS, hot, log). Markers here usually need top-priority resolution."),
        ("concept", "Concept pages", "Most actionable. Each marker is something that should be added to or resolved within an existing wiki page."),
        ("source", "Source-summary pages", "Lower priority. These usually reflect gaps in the original recording — what wasn't said or wasn't covered. Useful for prioritizing future content."),
    ]:
        rows = by_location.get(section_key, [])
        lines.append(f"## {title} ({len(rows)})")
        lines.append("")
        lines.append(f"_{hint}_")
        lines.append("")
        if not rows:
            lines.append("None.")
            lines.append("")
            continue
        lines.append("| Kind | Page | Line | Text |")
        lines.append("|------|------|------|------|")
        # Group by file for readability
        rows_by_file = defaultdict(list)
        for r in rows:
            rows_by_file[r["file"]].append(r)
        for file_path in sorted(rows_by_file.keys()):
            for r in rows_by_file[file_path]:
                badge = {"GAP": "🔍", "CONFLICT": "⚔️", "ASSUMPTION": "❓", "ACKNOWLEDGED": "✅"}[r["kind"]]
                # Truncate very long text
                text = r["text"][:180] + ("…" if len(r["text"]) > 180 else "")
                text = text.replace("|", "\\|")
                link = f"[[{file_path[:-3]}]]" if file_path.endswith(".md") else f"`{file_path}`"
                lines.append(f"| {badge} {r['kind']} | {link} | {r['line']} | {text} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## How to triage",
        "",
        "- **GAP** — knowledge that should exist but doesn't yet. Either fill it in or document why it can't be filled (no source material, etc).",
        "- **CONFLICT** — two sources disagree. Surface both positions in the wiki, don't silently merge. If resolved, log in `wiki/corrections.md` and remove the marker.",
        "- **ASSUMPTION** — a claim made without verification. Either verify and remove the marker, or downgrade the confidence label on the page.",
        "",
        "Rerun this audit after every GAP/CONFLICT resolution pass to confirm the count is dropping.",
        "",
    ]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Found {total} markers across the wiki")
    print(f"  GAP: {counts['GAP']}")
    print(f"  CONFLICT: {counts['CONFLICT']}")
    print(f"  ASSUMPTION: {counts['ASSUMPTION']}")
    print(f"\nBy location:")
    print(f"  concept pages: {len(by_location.get('concept', []))}")
    print(f"  source pages: {len(by_location.get('source', []))}")
    print(f"  root files: {len(by_location.get('root', []))}")
    print(f"\nWrote {REPORT}")


if __name__ == "__main__":
    main()
