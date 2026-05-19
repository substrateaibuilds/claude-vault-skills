#!/usr/bin/env python3
"""
migrate_vault_frontmatter.py

Adds YAML frontmatter to wiki pages that don't have it.

Rules:
- Skip navigation/meta files and source pages (see SKIP_NAMES and SKIP_PREFIXES)
- Extract tags from existing "**Domain(s):**" line OR fall back to folder-based mapping
- Default confidence: doctrinal
- Leave source-date blank (populated manually or during future ingest)
- Dry-run by default; pass --execute to write changes

Tag mapping is data-driven. The script looks for `tag-map.json` alongside itself.
If absent, all tag maps default to empty (pages get tagged []). See
`tag-map.example.json` next to this script for the schema and a sample taxonomy.

The tag-map.json file has three sections:
- domain_map  — exact match: normalized "Domain(s)" value -> tag
- folder_map  — fallback when no Domain(s) line is present: parent folder name -> tag
- keyword_map — substring match against Domain(s) value -> tag (first hit wins)

Usage:
    python scripts/migrate_vault_frontmatter.py --wiki /path/to/wiki
    python scripts/migrate_vault_frontmatter.py --wiki /path/to/wiki --execute
    python scripts/migrate_vault_frontmatter.py --wiki /path/to/wiki --tag-map /custom/path/tag-map.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKIP_NAMES = {
    "index.md", "hot.md", "log.md", "GAPS.md", "corrections.md",
    "STATUS.md", "ASSESSMENT-ENGINE-EXPORT.md", "_ingest-briefing.md",
    "_ingestion-manifest.md",
}
SKIP_PREFIXES = ("domain-index-",)

_DOMAIN_LINE_RE = re.compile(r'\*\*Domain\(s\)\:\*\*\s*(.+)', re.IGNORECASE)


def load_tag_map(path: Path | None) -> dict:
    """Load tag mappings from JSON. Returns dict with three keys, each a (possibly empty) mapping."""
    if path is None:
        path = Path(__file__).parent / "tag-map.json"
    empty = {"domain_map": {}, "folder_map": {}, "keyword_map": {}}
    if not path.exists():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"WARN: {path} is not valid JSON ({e}); using empty tag maps", file=sys.stderr)
        return empty
    return {
        "domain_map": data.get("domain_map", {}) or {},
        "folder_map": data.get("folder_map", {}) or {},
        "keyword_map": data.get("keyword_map", {}) or {},
    }


def extract_tags(content: str, source_path: Path, tag_map: dict) -> list[str]:
    """Extract tags from **Domain(s):** line, falling back to folder-based mapping."""
    domain_map = tag_map["domain_map"]
    folder_map = tag_map["folder_map"]
    keyword_map = tag_map["keyword_map"]

    match = _DOMAIN_LINE_RE.search(content)
    if match:
        raw = match.group(1)
        parts = [p.strip().lower() for p in re.split(r'[,/]', raw) if p.strip()]
        tags = []
        for p in parts:
            normalized = p.replace(" ", "-")
            if normalized in domain_map:
                tags.append(domain_map[normalized])
                continue
            for keyword, tag in keyword_map.items():
                if keyword in normalized:
                    tags.append(tag)
                    break
        if tags:
            return sorted(set(tags))
    parent = source_path.parent.name
    fallback = folder_map.get(parent)
    return [fallback] if fallback else []


def should_skip(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    if any(path.name.startswith(pfx) for pfx in SKIP_PREFIXES):
        return True
    if "sources" in path.parts:
        return True
    return False


def has_yaml_frontmatter(content: str) -> bool:
    """True if the file already starts with a complete YAML block (---...---)."""
    stripped = content.lstrip('﻿').lstrip()
    if not stripped.startswith("---"):
        return False
    rest = stripped[3:]
    return "\n---" in rest


def has_required_fields(content: str) -> bool:
    """True if existing YAML frontmatter has confidence, source-date, and tags."""
    stripped = content.lstrip('﻿').lstrip()
    if not stripped.startswith("---"):
        return False
    end = stripped.find("\n---", 3)
    if end == -1:
        return False
    yaml_block = stripped[3:end]
    return (
        "confidence:" in yaml_block
        and "source-date:" in yaml_block
        and "tags:" in yaml_block
    )


def build_frontmatter(tags: list[str]) -> str:
    tags_yaml = ", ".join(tags) if tags else ""
    return f"---\nconfidence: doctrinal\nsource-date: \ntags: [{tags_yaml}]\n---\n\n"


def process_file(path: Path, tag_map: dict, execute: bool) -> str | None:
    """Return a description of what changed, or None if skipped."""
    content = path.read_text(encoding="utf-8-sig")

    if has_yaml_frontmatter(content):
        if has_required_fields(content):
            return None
        rel = path.relative_to(path.parents[1])
        return f"  [PARTIAL] {rel} — has YAML but missing confidence/source-date/tags; fix manually"

    tags = extract_tags(content, path, tag_map)
    frontmatter = build_frontmatter(tags)
    new_content = frontmatter + content

    rel = path.relative_to(path.parents[1])
    action = "WRITE" if execute else "DRY-RUN"
    msg = f"  [{action}] {rel} — tags: {tags}"

    if execute:
        path.write_text(new_content, encoding="utf-8")

    return msg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", required=True, help="Path to wiki/ directory")
    parser.add_argument("--execute", action="store_true", help="Write changes (default: dry-run)")
    parser.add_argument("--tag-map", default=None,
                        help="Path to tag-map.json (default: ./tag-map.json next to this script)")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki).expanduser().resolve()
    if not wiki_dir.exists():
        print(f"ERROR: {wiki_dir} not found")
        return

    tag_map_path = Path(args.tag_map).expanduser().resolve() if args.tag_map else None
    tag_map = load_tag_map(tag_map_path)
    if not any(tag_map[k] for k in ("domain_map", "folder_map", "keyword_map")):
        loc = tag_map_path if tag_map_path else (Path(__file__).parent / "tag-map.json")
        print(f"NOTE: no tag mappings loaded from {loc}; pages will be tagged []")
        print(f"      see tag-map.example.json for the schema and a sample taxonomy")

    files = sorted(wiki_dir.rglob("*.md"))
    changed = 0
    partial = 0
    skipped = 0

    for path in files:
        if should_skip(path):
            skipped += 1
            continue
        result = process_file(path, tag_map, execute=args.execute)
        if result:
            print(result)
            if "[PARTIAL]" in result:
                partial += 1
            else:
                changed += 1

    mode = "EXECUTED" if args.execute else "DRY-RUN"
    print(f"\n[{mode}] {changed} pages {'updated' if args.execute else 'would be updated'}; "
          f"{partial} partial (manual fix needed); {skipped} skipped")


if __name__ == "__main__":
    main()
