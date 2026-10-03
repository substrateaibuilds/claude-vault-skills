#!/usr/bin/env python3
"""Master vault audit — evidence-gated scorecard across four dimensions.

Rewritten 2026-09-06. The previous version started at 100 and subtracted tiny
deductions (0.03-0.05 per gap), which made a failing score arithmetically
almost unreachable: four production vaults reported 100/100 while printing
real deductions on the same screen. Coverage gaps could not move the number.

This version earns from zero. Five criteria per dimension, each scored 0/1/3/5
from a measured ratio or count — never interpolated, never "start full and
deduct". Hard caps then override the arithmetic so a large, well-formatted
vault cannot buy its way past a structurally weak dimension.

Dimensions:
  Coverage   (25) — does the wiki actually cover the corpus it was built from?
  Integrity  (25) — do the vault's own contracts, links, and indexes resolve?
  Epistemics (25) — is knowledge qualified (confidence, review, conflicts)?
  Currency   (25) — is live/changing information fresh? (opt-in; see below)

Currency is scored only for vaults that declare themselves operational in
_scripts/audit-config.json. Static expert corpora are scored over the other
three dimensions and scaled to 100. A vault that stays silent is treated as
non-operational and the report says so explicitly.

Output: wiki/VAULT-AUDIT.md   (add --json for a machine-readable summary)
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
WIKI = VAULT / "wiki"
SCRIPTS = VAULT / "_scripts"
REPORT = WIKI / "VAULT-AUDIT.md"
CONFIG = SCRIPTS / "audit-config.json"

SUB_AUDITS = [
    "concept-frequency-audit.py",
    "validate-claude-contracts.py",
    "gap-rollup.py",
]

DEFAULTS = {
    "operational": False,
    "operational_reason": "Not declared. Defaulting to static corpus; Currency not scored.",
    "high_freq_threshold": 15,
    "freshness_days": 90,
    "stub_bytes": 600,
}

META_FILES = {
    "index.md", "log.md", "hot.md", "GAPS.md", "STATUS.md", "corrections.md",
    "CONCEPT-COVERAGE.md", "CLAUDE-CONTRACTS-AUDIT.md", "GAPS-AUDIT.md",
    "VAULT-AUDIT.md", "ASSESSMENT-ENGINE-EXPORT.md", "_ingest-briefing.md",
    "_aliases.md",
}

BANDS = [
    (85, "Maintained and evidenced"),
    (70, "Dependable in the verified scope"),
    (50, "Working, with gaps"),
    (25, "Foundation"),
    (0, "Unproven"),
]


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG.exists():
        try:
            cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARN  audit-config.json unreadable ({e}); using defaults")
    return cfg


# ---------------------------------------------------------------- scoring core

def anchor(value, one, three, five, higher_is_better=True):
    """Return 0/1/3/5 — the highest anchor fully met. Never interpolates."""
    if higher_is_better:
        if value >= five:
            return 5
        if value >= three:
            return 3
        if value >= one:
            return 1
        return 0
    if value <= five:
        return 5
    if value <= three:
        return 3
    if value <= one:
        return 1
    return 0


def ratio(num, den):
    return (num / den) if den else 0.0


def gated(evidence_base, points):
    """Evidence gate.

    An inverse criterion ('0 conflicts found') scores full marks on an empty
    vault, which is vacuous completeness, not quality. Where a criterion is only
    meaningful against a real evidence base, absent evidence scores 0 — a
    verification gap, never a pass.
    """
    return points if evidence_base else 0


class Dimension:
    def __init__(self, key, name, applicable=True, na_reason=""):
        self.key = key
        self.name = name
        self.applicable = applicable
        self.na_reason = na_reason
        self.criteria = []

    def add(self, cid, label, points, evidence):
        self.criteria.append({"id": cid, "label": label, "points": points, "evidence": evidence})

    @property
    def score(self):
        return sum(c["points"] for c in self.criteria)


# ------------------------------------------------------------------ collectors

def run_sub_audits():
    print("Running sub-audits...")
    for script in SUB_AUDITS:
        path = SCRIPTS / script
        if not path.exists():
            print(f"  SKIP {script} (not found)")
            continue
        try:
            r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=180)
            print(f"  {'OK' if r.returncode == 0 else 'WARN':4s} {script}")
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT {script}")
        except Exception as e:
            print(f"  ERROR {script}: {e}")


def is_concept_page(md):
    s = str(md)
    if "/sources/" in s:
        return False
    if md.name in META_FILES or md.name.startswith("domain-index-") or md.name.startswith("_"):
        return False
    return True


LINK_RE = re.compile(r"\[\[([^\]|#]+)")
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def scan_pages(cfg):
    """Read every concept page once. Returns page dicts + the link graph."""
    pages = []
    for md in WIKI.rglob("*.md"):
        if not is_concept_page(md):
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = md.relative_to(WIKI).as_posix()
        links = {t.strip() for t in LINK_RE.findall(content)}
        fm_ok = content.lstrip().startswith("---") and "\n---" in content[:2000]
        dates = [datetime(int(y), int(mo), int(d))
                 for y, mo, d in DATE_RE.findall(content[:1200])
                 if 1900 < int(y) < 2200 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31]
        pages.append({
            "rel": rel,
            "stem": md.stem,
            "bytes": len(content.encode("utf-8")),
            "has_confidence": bool(re.search(r"^confidence::?\s*\S+", content, re.MULTILINE)),
            "has_review": bool(re.search(r"last-reviewed::?\s*\d{4}", content)),
            "frontmatter_ok": fm_ok,
            "links": links,
            "newest_date": max(dates) if dates else None,
        })
    return pages


def source_pages():
    src = WIKI / "sources"
    return sorted(src.glob("*.md")) if src.exists() else []


SOURCE_EXTS = {".md", ".pdf", ".txt", ".vtt", ".srt", ".docx", ".rtf", ".epub"}
SOURCE_SKIP = {"CLAUDE.md", "INGESTION-PROMPT.md", "README.md", "AGENTS.md",
               "connections.md", "GAPS.md"}


def discover_source_files():
    """Mirror vault-ingest Phase 1: vault root first, then raw/ recursively."""
    root = [p for p in VAULT.iterdir()
            if p.is_file() and p.suffix.lower() in SOURCE_EXTS and p.name not in SOURCE_SKIP]
    if root:
        return root
    raw = VAULT / "raw"
    if raw.exists():
        return [p for p in raw.rglob("*")
                if p.is_file() and p.suffix.lower() in SOURCE_EXTS
                and not p.name.startswith(".")]
    return []


FILEFIELD_RE = re.compile(r"\*\*File[^:]*:\*\*\s*(.+)")


def ingested_basenames(srcs):
    """Basenames recorded in source pages' '**File path:**' fields.

    vault-ingest Phase 1 Step 2 tracks what has been ingested by this field, not
    by counting source pages — one source page can summarise several raw files
    (a course module covering six transcripts). Counting pages instead of
    recorded paths understates coverage badly on multi-file corpora.
    """
    names = set()
    for s in srcs:
        try:
            text = s.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in FILEFIELD_RE.finditer(text):
            val = m.group(1).strip().strip("`").strip()
            if val:
                names.add(Path(val).name.strip().lower())
    return names


def parse_high_freq_gaps(threshold):
    p = WIKI / "CONCEPT-COVERAGE.md"
    if not p.exists():
        return 0
    content = p.read_text(encoding="utf-8")
    return sum(1 for m in re.finditer(r"^\|\s*\d+\s*\|\s*`[^`]+`\s*\|\s*(\d+)\s*\|",
                                      content, re.MULTILINE)
               if int(m.group(1)) >= threshold)


def parse_contract_failures():
    """→ (failures, references_checked). failures is None if the audit never ran."""
    p = WIKI / "CLAUDE-CONTRACTS-AUDIT.md"
    if not p.exists():
        return None, 0
    content = p.read_text(encoding="utf-8")

    def n(pat):
        m = re.search(pat, content)
        return int(m.group(1)) if m else 0

    ok, stub, missing = n(r"\*\*OK:\*\*\s*(\d+)"), n(r"\*\*STUB:\*\*\s*(\d+)"), n(r"\*\*MISSING:\*\*\s*(\d+)")
    return stub + missing, ok + stub + missing


def parse_gap_counts():
    p = WIKI / "GAPS-AUDIT.md"
    out = {"concept": 0, "source": 0, "conflict": 0}
    if not p.exists():
        return out
    content = p.read_text(encoding="utf-8")
    m = (re.search(r"\*\*Concept-page GAP-only.*?:\*\*\s*(\d+)", content)
         or re.search(r"\*\*Concept-page markers:\*\*\s*(\d+)", content))
    out["concept"] = int(m.group(1)) if m else 0
    m = re.search(r"\*\*Source-page markers:\*\*\s*(\d+)", content)
    out["source"] = int(m.group(1)) if m else 0
    # Prefer the concept-scoped CONFLICT count. Source pages are REQUIRED by the
    # source-page template to carry "## Where This Contradicts Other Sources"
    # with `- CONFLICT:` lines, so counting wiki-wide conflicts penalised a vault
    # for following its own contract — and was inconsistent with E4, which was
    # already concept-scoped. justin-brand-strategy reported 44 conflicts when
    # only 5 were unresolved concept-page disagreements; the other 37 were
    # correct authorship.
    m = re.search(r"\*\*Concept-page CONFLICT-only.*?:\*\*\s*(\d+)", content)
    if m:
        out["conflict"] = int(m.group(1))
    else:
        m = re.search(r"\((\d+)\s*GAP\s*·\s*(\d+)\s*CONFLICT", content)
        out["conflict"] = int(m.group(2)) if m else 0
    return out


def indexed_stems():
    """Every page slug reachable from index.md or any domain index."""
    stems = set()
    targets = [WIKI / "index.md"] + sorted(WIKI.glob("domain-index-*.md"))
    for t in targets:
        if not t.exists():
            continue
        text = t.read_text(encoding="utf-8", errors="ignore")
        for raw in LINK_RE.findall(text):
            stems.add(raw.strip().split("/")[-1].replace(".md", ""))
        for m in re.finditer(r"\(([^)]+\.md)\)|`([^`]+\.md)`", text):
            path = m.group(1) or m.group(2)
            stems.add(Path(path).stem)
    return stems


def connections_rows(cfg):
    """Parse connections.md → (total_rows, real_rows, rows_checked_recently).

    A row is 'real' once it names an actual mechanism; template placeholder rows
    ('_filled by /onboard_', 'not yet connected') are declared intent, not reach.
    """
    p = VAULT / "connections.md"
    if not p.exists():
        return 0, 0, 0
    cutoff = datetime.now() - timedelta(days=cfg["freshness_days"])
    total = real = fresh = 0
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() in {"#", "domain"} or set(cells[0]) <= {"-", ":"}:
            continue
        total += 1
        body = " ".join(cells).lower()
        if "filled by" in body or "not yet connected" in body:
            continue
        real += 1
        m = DATE_RE.search(cells[-1])
        if m and datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))) >= cutoff:
            fresh += 1
    return total, real, fresh


def file_recent(path, days):
    if not path.exists():
        return False
    return datetime.fromtimestamp(path.stat().st_mtime) >= datetime.now() - timedelta(days=days)


# ----------------------------------------------------------------- dimensions

def score_coverage(cfg, pages, srcs, src_files, high_freq, idx_stems):
    d = Dimension("coverage", "Coverage")
    n_pages, n_src, n_files = len(pages), len(srcs), len(src_files)

    # Match by recorded File-path basename, the way vault-ingest builds its skip
    # list — NOT source-page count, which understates multi-file source pages.
    if n_files:
        done = ingested_basenames(srcs)
        covered = sum(1 for p in src_files if p.name.strip().lower() in done)
        r = ratio(covered, n_files)
        d.add("V1", "Corpus ingested (raw files with a recorded source page)",
              anchor(r, 0.25, 0.60, 0.90),
              f"{covered} / {n_files} raw files recorded across {n_src} source pages ({r:.0%})")
    else:
        d.add("V1", "Corpus ingested (raw files with a recorded source page)",
              5 if n_src >= 10 else 1 if n_src else 0,
              f"{n_src} source pages; no raw corpus on disk to compare against")

    d.add("V2", f"Concept coverage (gaps at ≥{cfg['high_freq_threshold']} source mentions)",
          gated(n_src, anchor(high_freq, 10, 3, 0, higher_is_better=False)),
          f"{high_freq} high-frequency concepts mentioned across sources with no canonical page"
          if n_src else "no source pages — coverage unmeasurable, scored 0")

    r = ratio(n_pages, n_src)
    d.add("V3", "Synthesis depth (concept pages per source page)",
          anchor(r, 0.10, 0.30, 0.50) if n_src else 0,
          f"{n_pages} concept / {n_src} source = {r:.2f}" if n_src else "no source pages — synthesis unmeasurable")

    reachable = sum(1 for p in pages if p["stem"] in idx_stems)
    r = ratio(reachable, n_pages)
    d.add("V4", "Index reachability (pages listed in master or a domain index)",
          anchor(r, 0.50, 0.85, 0.98) if n_pages else 0,
          f"{reachable} / {n_pages} reachable ({r:.0%})")

    substantial = sum(1 for p in pages if p["bytes"] >= cfg["stub_bytes"])
    r = ratio(substantial, n_pages)
    d.add("V5", f"Substance (concept pages ≥{cfg['stub_bytes']} bytes)",
          anchor(r, 0.60, 0.85, 0.97) if n_pages else 0,
          f"{substantial} / {n_pages} non-stub ({r:.0%})")
    return d


def score_integrity(cfg, pages, srcs, contract_fails, contract_checked):
    d = Dimension("integrity", "Integrity")
    n_pages = len(pages)

    if contract_fails is None:
        d.add("I1", "CLAUDE.md contracts resolve", 0,
              "validate-claude-contracts.py did not run — unverified, scored 0")
    elif not contract_checked:
        d.add("I1", "CLAUDE.md contracts resolve", 0,
              "CLAUDE.md declares no checkable page references — nothing verified, scored 0")
    else:
        d.add("I1", "CLAUDE.md contracts resolve",
              anchor(contract_fails, 5, 2, 0, higher_is_better=False),
              f"{contract_fails} broken or stub of {contract_checked} references from CLAUDE.md")

    # Any page that exists under wiki/ resolves, including root files like
    # domain-index-*.md and index.md that aren't concept pages.
    known = {p["stem"] for p in pages} | {s.stem for s in srcs} | {f.stem for f in WIKI.rglob("*.md")}
    total_links = resolved = 0
    inbound = {p["stem"]: 0 for p in pages}
    for p in pages:
        for raw in p["links"]:
            stem = raw.split("/")[-1].replace(".md", "").strip()
            if not stem:
                continue
            total_links += 1
            if stem in known:
                resolved += 1
                if stem in inbound and stem != p["stem"]:
                    inbound[stem] += 1
    r = ratio(resolved, total_links)
    d.add("I2", "Wikilinks resolve to real pages",
          anchor(r, 0.70, 0.90, 0.99) if total_links else 0,
          f"{resolved} / {total_links} resolve ({r:.0%})" if total_links else "no wikilinks found")

    di = sorted(WIKI.glob("domain-index-*.md"))
    populated = sum(1 for f in di
                    if len(LINK_RE.findall(f.read_text(encoding="utf-8", errors="ignore"))) >= 10)
    if di:
        r = ratio(populated, len(di))
        d.add("I3", "Domain indexes populated (≥10 page links each)",
              anchor(r, 0.50, 0.80, 1.0),
              f"{populated} / {len(di)} domain indexes populated")
    else:
        d.add("I3", "Domain indexes populated", 0, "no domain-index-*.md files exist")

    orphans = sum(1 for p in pages if inbound.get(p["stem"], 0) == 0)
    r = 1 - ratio(orphans, n_pages)
    d.add("I4", "Pages have inbound links (not orphaned)",
          anchor(r, 0.50, 0.80, 0.95) if n_pages else 0,
          f"{orphans} / {n_pages} orphaned ({1-r:.0%})")

    fm = sum(1 for p in pages if p["frontmatter_ok"])
    r = ratio(fm, n_pages)
    d.add("I5", "YAML frontmatter present and fenced",
          anchor(r, 0.60, 0.85, 0.98) if n_pages else 0,
          f"{fm} / {n_pages} with parseable frontmatter ({r:.0%})")
    return d


def score_epistemics(cfg, pages, gaps, srcs):
    d = Dimension("epistemics", "Epistemics")
    n = len(pages)
    # Resolve links against the real source-page stems, the way I2 does. An
    # earlier version tested for the literal substring "sources/" in the link
    # target, which only matches path-style wikilinks. Vaults use Obsidian's
    # bare-slug form ([[caleb-ralston-start-personal-brand]]), so every vault
    # scored 0 here regardless of how well its pages cited their sources —
    # justin-brand-strategy reported 0% when the true figure is 96%.
    src_stems = {s.stem for s in srcs}

    r = ratio(sum(1 for p in pages if p["has_confidence"]), n)
    d.add("E1", "Confidence label on concept pages",
          anchor(r, 0.60, 0.85, 0.98) if n else 0,
          f"{sum(1 for p in pages if p['has_confidence'])} / {n} labelled ({r:.0%})")

    r = ratio(sum(1 for p in pages if p["has_review"]), n)
    d.add("E2", "last-reviewed stamp on concept pages",
          anchor(r, 0.60, 0.85, 0.98) if n else 0,
          f"{sum(1 for p in pages if p['has_review'])} / {n} stamped ({r:.0%})")

    d.add("E3", "CONFLICT markers resolved or acknowledged",
          gated(n, anchor(gaps["conflict"], 20, 5, 0, higher_is_better=False)),
          f"{gaps['conflict']} unresolved CONFLICT markers" if n
          else "no concept pages — scored 0, not vacuously clean")

    per100 = (gaps["concept"] / n * 100) if n else 0
    d.add("E4", "Concept-page GAP markers under control (per 100 pages)",
          gated(n, anchor(per100, 50, 20, 5, higher_is_better=False)),
          f"{gaps['concept']} GAP markers across {n} pages ({per100:.0f} per 100)" if n
          else "no concept pages — scored 0, not vacuously clean")

    cites = sum(1 for p in pages
                if any(l.split("/")[-1].replace(".md", "").strip() in src_stems
                       or "sources/" in l
                       for l in p["links"]))
    r = ratio(cites, n)
    d.add("E5", "Concept pages cite a source page",
          anchor(r, 0.40, 0.70, 0.90) if (n and src_stems) else 0,
          f"{cites} / {n} cite a source page ({r:.0%})" if src_stems
          else "no source pages exist to cite — scored 0")
    return d


def score_currency(cfg, pages):
    if not cfg["operational"]:
        return Dimension("currency", "Currency", applicable=False,
                         na_reason=cfg["operational_reason"])
    d = Dimension("currency", "Currency")
    days = cfg["freshness_days"]
    total, real, fresh = connections_rows(cfg)

    d.add("U1", "connections.md has real (non-placeholder) rows",
          anchor(real, 1, 4, 7),
          f"{real} wired / {total} declared rows")

    r = ratio(fresh, real)
    d.add("U2", f"Connected rows checked within {days} days",
          anchor(r, 0.34, 0.67, 1.0) if real else 0,
          f"{fresh} / {real} wired rows with a fresh last-checked date" if real
          else "no wired connections to check")

    cutoff = datetime.now() - timedelta(days=days)
    dated = [p for p in pages if p["newest_date"]]
    curr = sum(1 for p in dated if p["newest_date"] >= cutoff)
    r = ratio(curr, len(pages))
    d.add("U3", f"Concept pages carrying a date within {days} days",
          anchor(r, 0.20, 0.50, 0.80) if pages else 0,
          f"{curr} / {len(pages)} pages dated within window ({r:.0%})")

    d.add("U4", f"hot.md refreshed within {days} days",
          5 if file_recent(WIKI / "hot.md", days) else 0,
          "hot.md recent" if file_recent(WIKI / "hot.md", days) else "hot.md missing or stale")

    d.add("U5", f"log.md written within {days} days",
          5 if file_recent(WIKI / "log.md", days) else 0,
          "log.md recent" if file_recent(WIKI / "log.md", days) else "log.md missing or stale")
    return d


# ---------------------------------------------------------------------- caps

def apply_caps(dims, raw, n_src, contract_fails):
    caps = []
    if n_src == 0:
        caps.append((24, "No source pages — nothing has been ingested; system is Unproven"))
    applicable = [d for d in dims if d.applicable]
    worst = min((d.score for d in applicable), default=0)
    worst_name = min(applicable, key=lambda d: d.score).name if applicable else "-"
    if worst < 10:
        caps.append((49, f"{worst_name} scored {worst}/25 (below 10)"))
    elif worst < 15:
        caps.append((69, f"{worst_name} scored {worst}/25 (below 15)"))
    elif worst < 20:
        caps.append((84, f"{worst_name} scored {worst}/25 (below 20)"))
    if contract_fails:
        caps.append((84, f"{contract_fails} unresolved CLAUDE.md contract failure(s) — the manual claims things that are not true"))
    final = min([raw] + [c for c, _ in caps])
    return final, caps


def band_for(score):
    for threshold, name in BANDS:
        if score >= threshold:
            return name
    return "Unproven"


# ---------------------------------------------------------------------- main

def main():
    cfg = load_config()
    run_sub_audits()
    print()

    pages = scan_pages(cfg)
    srcs = source_pages()
    src_files = discover_source_files()
    high_freq = parse_high_freq_gaps(cfg["high_freq_threshold"])
    contract_fails, contract_checked = parse_contract_failures()
    gaps = parse_gap_counts()
    idx = indexed_stems()

    dims = [
        score_coverage(cfg, pages, srcs, src_files, high_freq, idx),
        score_integrity(cfg, pages, srcs, contract_fails, contract_checked),
        score_epistemics(cfg, pages, gaps, srcs),
        score_currency(cfg, pages),
    ]

    applicable = [d for d in dims if d.applicable]
    raw_sum = sum(d.score for d in applicable)
    max_sum = 25 * len(applicable)
    raw = round(raw_sum / max_sum * 100) if max_sum else 0

    final, caps = apply_caps(dims, raw, len(srcs), contract_fails or 0)
    band = band_for(final)

    # ---- report
    L = [
        "# Vault Audit — Master Report",
        "",
        f"*Regenerate: `python3 _scripts/vault-audit.py` · {datetime.now():%Y-%m-%d %H:%M}*",
        "",
        f"## Score: {final} / 100 — {band}",
        "",
        f"Raw: {raw_sum}/{max_sum} across {len(applicable)} scored dimensions = {raw}/100.",
    ]
    if caps:
        L.append(f"Capped to **{final}** by the lowest applicable cap.")
    L += [
        "",
        "Points are earned from zero against measured evidence. Each criterion takes the "
        "highest anchor (0/1/3/5) its measurement fully supports — never interpolated. "
        "Caps then override the arithmetic so a large, tidy vault cannot compensate for a "
        "structurally weak dimension.",
        "",
        "| Dimension | Score | Status |",
        "|---|---|---|",
    ]
    for d in dims:
        if d.applicable:
            L.append(f"| {d.name} | {d.score} / 25 | — |")
        else:
            L.append(f"| {d.name} | n/a | {d.na_reason} |")
    L.append("")

    if caps:
        L += ["## Applied caps", "", "| Cap | Reason |", "|---|---|"]
        for c, why in sorted(caps):
            mark = " ← binding" if c == final else ""
            L.append(f"| {c}{mark} | {why} |")
        L.append("")

    L += ["## Criteria detail", ""]
    for d in dims:
        L.append(f"### {d.name} — {d.score}/25" if d.applicable else f"### {d.name} — not scored")
        L.append("")
        if not d.applicable:
            L += [d.na_reason,
                  "",
                  "Enable by setting `\"operational\": true` in `_scripts/audit-config.json`.",
                  ""]
            continue
        L += ["| ID | Criterion | Pts | Evidence |", "|---|---|---|---|"]
        for c in d.criteria:
            L.append(f"| {c['id']} | {c['label']} | {c['points']} | {c['evidence']} |")
        L.append("")

    # ---- actions, ordered by points lost
    actions = []
    for d in dims:
        if not d.applicable:
            continue
        for c in sorted(d.criteria, key=lambda x: x["points"]):
            if c["points"] < 5:
                actions.append((c["points"], f"**{d.name} / {c['id']}** — {c['label']}: {c['evidence']}"))
    actions.sort(key=lambda x: x[0])
    L += ["## Top action items", ""]
    if actions:
        for i, (_, a) in enumerate(actions[:8], 1):
            L.append(f"{i}. {a}")
    else:
        L.append("Every scored criterion is at full marks. Rerun after the next ingest.")
    L += [
        "",
        "## Vault statistics",
        "",
        f"- **Concept pages:** {len(pages)}",
        f"- **Source-summary pages:** {len(srcs)}",
        f"- **Source files discovered on disk:** {len(src_files)}",
        f"- **High-frequency concept gaps:** {high_freq}",
        f"- **CLAUDE.md contract failures:** {'not run' if contract_fails is None else contract_fails}",
        f"- **GAP markers:** {gaps['concept']} concept + {gaps['source']} source",
        f"- **CONFLICT markers:** {gaps['conflict']}",
        "",
        "## Detailed reports",
        "",
        "- [[CONCEPT-COVERAGE]] — concepts mentioned often but missing as pages",
        "- [[CLAUDE-CONTRACTS-AUDIT]] — CLAUDE.md references with PASS/STUB/MISSING status",
        "- [[GAPS-AUDIT]] — every GAP, CONFLICT, ASSUMPTION marker in the vault",
        "",
        "## Bands",
        "",
        "| Score | Band |",
        "|---|---|",
        "| 0–24 | Unproven |",
        "| 25–49 | Foundation |",
        "| 50–69 | Working, with gaps |",
        "| 70–84 | Dependable in the verified scope |",
        "| 85–100 | Maintained and evidenced |",
        "",
        "A high score states that the *sampled, measurable* properties hold. It is not a "
        "claim that the vault is complete or that its content is correct.",
        "",
    ]

    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"Vault Audit Score: {final} / 100 ({band})")
    print(f"  raw {raw_sum}/{max_sum} = {raw}/100")
    for d in dims:
        print(f"  {d.name:11s} {str(d.score)+'/25' if d.applicable else 'n/a':>6s}")
    if caps:
        print("Caps applied:")
        for c, why in sorted(caps):
            print(f"  {c:3d} {'← binding' if c == final else '         '}  {why}")
    print(f"\nWrote {REPORT}")

    if "--json" in sys.argv:
        print("\n" + json.dumps({
            "score": final, "raw": raw, "band": band,
            "dimensions": {d.key: (d.score if d.applicable else None) for d in dims},
            "caps": [{"cap": c, "reason": w} for c, w in sorted(caps)],
            "concept_pages": len(pages), "source_pages": len(srcs),
            "contract_failures": contract_fails,
        }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
