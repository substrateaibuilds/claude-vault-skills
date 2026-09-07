#!/usr/bin/env python3
"""Concept frequency audit for the coaching brain vault.

Finds noun phrases mentioned in many source-summary pages but missing as wiki concept pages.
Writes wiki/CONCEPT-COVERAGE.md.

Run: python3 _scripts/concept-frequency-audit.py
"""
import re
from collections import defaultdict
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
SOURCES = VAULT / "wiki" / "sources"
WIKI = VAULT / "wiki"
REPORT = WIKI / "CONCEPT-COVERAGE.md"

MIN_PAGES = 5
MAX_RESULTS = 300

WORD_STOPS = {
    "a","an","the","of","in","on","at","by","to","for","with","from","into","onto","upon",
    "about","around","across","through","between","over","under","up","down","out","off",
    "you","your","yours","yourself","he","she","it","they","them","their","his","her","hers",
    "we","us","our","ours","i","me","my","mine","its","itself","themselves",
    "is","are","was","were","be","been","being","am","aint",
    "has","have","had","having",
    "do","does","did","doing","done",
    "can","could","should","would","will","wont","must","may","might","shall",
    "and","but","or","so","if","then","that","this","these","those",
    "which","when","where","why","how","what","who","whom","whose",
    "very","really","just","only","also","even","still","again","here","there","now","always","never",
    "all","some","any","no","not","none","every","each","few","many","much","more","most","less","least","both","other","another",
    "than","as","like","such","because","while","during","after","before",
    "said","says","saying","talked","talking","mentioned","asked","told","explained","explains",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "first","second","third","fourth","fifth",
    "yes","yeah","okay","ok","alright","well","right","sure","fine","good","bad","great",
    "going","getting","got","get","gets","goes","gone","went","go",
    "make","made","making","makes",
    "see","seeing","seen","saw","seem","seems","seemed",
    "use","used","using","uses",
    "look","looks","looking","looked","looking",
    "think","thought","thinks","thinking",
    "know","knew","known","knows","knowing","known",
    "want","wanted","wants","wanting",
    "need","needs","needed","needing",
    "feel","feels","felt","feeling",
    "take","takes","took","taken","taking",
    "give","gives","gave","given","giving",
    "come","comes","came","coming",
    "actually","basically","essentially","literally","probably","maybe","definitely","absolutely",
    "lot","lots","kind","sort","kinds","sorts",
    "thing","things","stuff",
    "way","ways",
    "people","person","someone","everyone","anyone","everybody","anybody",
    "time","times","day","days","week","weeks","year","years","month","months","hour","hours","minute","minutes",
    "today","tomorrow","yesterday","tonight","morning","evening","night","afternoon",
    "side","sides","point","points",
    "case","cases",
    "fact","facts",
    "part","parts",
    "youre","im","were","theyre","its","thats","theres","whats","thatd",
    "doesnt","dont","didnt","isnt","arent","wasnt","werent","cant","wont","wouldnt","shouldnt",
    "ive","weve","theyve","youve",
    "hes","shes",
    "every","any","none","each",
    "put","puts","putting",
    "set","sets","setting",
    "find","finds","found","finding",
    "talk","talks","talked","talking",
    "show","shows","showed","shown","showing",
    "work","works","worked","working",
    "help","helps","helped","helping",
    "want","wants","wanted","wanting",
    "start","starts","started","starting",
    "begin","begins","began","begun","beginning",
    "end","ends","ended","ending",
    "try","tries","tried","trying",
    "live","lives","lived","living",
    "let","lets","letting",
    "tell","tells","told","telling",
    "ask","asks","asked","asking",
    "happen","happens","happened","happening",
    "mean","means","meant","meaning",
    "call","calls","called","calling",
    "around","into","through",
    "between","without","within","along",
    "lord","sake","wow","huh","oh","ah","um","uh",
    # vault-meta words at phrase boundaries
    "justin","justins","wiki","gap","client","section","sections","structure",
    "long","short","term","high","low",
    "central","key","main","important","specific","general",
    "pdf","txt","md",
    "demonstrates","reflects","applies","appears","invokes","references",
    "maps","direct","directly","indirectly",
    "full","new","old","existing","prior","later","earlier",
    "above","below","throughout",
    # source-page metadata leakage
    "impromptu","zoom","meeting","path","file",
}

SLUG_STOPS = {
    "key-finding","key-findings","main-point","for-example","such-as",
    "private-coaching","group-call","intake-call","assessment-call",
    "next-step","next-steps","action-item","action-items",
    "open-loop","follow-up","check-in",
    "ai-clone","ai-bot",
    "good-question","high-level",
    "second-thought","first-thought",
    "side-effect","side-effects",
    # source-template boilerplate
    "pages-created","created-updated","pages-created-updated","pending-pass",
    "candidate-new","candidate-new-pages","new-pages","new-pages-pass","pages-pass",
    "cross-domain","cross-domain-connections","domain-connections",
    "abstract-key","abstract-key-question","key-question",
    "content-date","file-path","historical-context",
    "justins-language","related-pages","supporting-quote",
    "metabolism-reset","testosterone-call","ccmr-call","reset-call",
    "coaching-call","intake-assessment","intro-assessment",
    "txt-pdf","pdf-md","md-pdf",
    "source-private","source-private-coaching","metabolism-reset-call",
    "online-course","social-media",
}

DOMAIN_STOPS = {
    "metabolic","identity","masculinity","business","wiki",
    "client","clients","coaching","coach","session","sessions",
    "justin","framework","frameworks","page","pages",
    "source","sources","domain","domains","concept","concepts",
    "approach","approaches","method","methods","model","models",
    "system","systems","process","processes",
    "people","person",
    "type","types","kind","kinds",
    "level","levels",
    "result","results","outcome","outcomes",
    "problem","problems","issue","issues","challenge","challenges",
    "question","questions","answer","answers",
    "example","examples","point","points",
    "topic","topics","subject","subjects",
    "discussion","conversation","talk",
    "story","stories","example","experience","experiences",
    "thought","thoughts","idea","ideas",
    "feeling","feelings","emotion","emotions",
}

WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")
WORD = re.compile(r"[a-zA-Z][a-zA-Z']+")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)


def slugify(phrase):
    s = phrase.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9 -]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def existing_concept_slugs():
    slugs = set()
    for md in WIKI.rglob("*.md"):
        if "/sources/" in str(md):
            continue
        slugs.add(md.stem.lower())
    return slugs


def covered_by_existing(slug, existing):
    if slug in existing:
        return True
    if "-" not in slug:
        return False
    for es in existing:
        if es == slug:
            return True
        if es.startswith(f"{slug}-") or es.endswith(f"-{slug}"):
            return True
        if f"-{slug}-" in f"-{es}-":
            return True
    return False


def extract_wikilink_slugs(content):
    out = []
    for m in WIKILINK.finditer(content):
        link = m.group(1)
        if "/" in link:
            link = link.rsplit("/", 1)[-1]
        if link.endswith(".md"):
            link = link[:-3]
        s = slugify(link)
        if s:
            out.append(s)
    return out


def extract_phrases(content):
    content = FRONTMATTER.sub("", content)
    content = CODE_BLOCK.sub("", content)
    phrases = []
    in_template_section = False
    template_section_headers = {
        "## pages created/updated",
        "## candidate new pages",
        "## pages created/updated: (pending pass b)",
        "## related pages",
        "## sources",
    }
    for line in content.split("\n"):
        stripped = line.lstrip()
        if not stripped:
            continue
        # Detect template sections we want to skip entirely (mostly boilerplate)
        lower = stripped.lower()
        if lower.startswith("## "):
            in_template_section = any(lower.startswith(h) for h in template_section_headers)
            continue  # always skip heading lines themselves
        if in_template_section:
            continue
        # Skip table separator lines
        if stripped.startswith("|---") or set(stripped) <= set("-| "):
            continue
        # Skip provenance lines that preserve real filenames (anonymization standard)
        if "**File path:**" in stripped or "**Type:**" in stripped or "**Content Date:**" in stripped or "**Domain(s):**" in stripped:
            continue
        words = [w.lower().replace("'", "") for w in WORD.findall(line)]
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 in WORD_STOPS or w2 in WORD_STOPS:
                continue
            if len(w1) < 3 or len(w2) < 3:
                continue
            phrases.append(f"{w1}-{w2}")
            if i + 2 < len(words):
                w3 = words[i + 2]
                if w3 not in WORD_STOPS and len(w3) >= 3:
                    phrases.append(f"{w1}-{w2}-{w3}")
    return phrases


def main():
    existing = existing_concept_slugs()
    mentions = defaultdict(set)

    src_files = list(SOURCES.glob("*.md"))
    if not src_files:
        print(f"No source files at {SOURCES}")
        return
    print(f"Scanning {len(src_files)} source pages against {len(existing)} existing concept pages...")

    for src in src_files:
        try:
            content = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        src_name = src.stem
        for s in extract_wikilink_slugs(content):
            mentions[s].add(src_name)
        for s in extract_phrases(content):
            mentions[s].add(src_name)

    candidates = []
    for slug, srcs in mentions.items():
        if len(srcs) < MIN_PAGES:
            continue
        if slug in SLUG_STOPS:
            continue
        if slug in DOMAIN_STOPS:
            continue
        if len(slug) < 6:
            continue
        if covered_by_existing(slug, existing):
            continue
        parts = slug.split("-")
        if all(p in DOMAIN_STOPS for p in parts):
            continue
        candidates.append((slug, len(srcs), srcs))

    candidates.sort(key=lambda x: (-x[1], x[0]))
    candidates = candidates[:MAX_RESULTS]

    lines = [
        "# Concept Coverage Audit",
        "",
        "*Regenerate: `python3 _scripts/concept-frequency-audit.py`*",
        "",
        f"Noun phrases mentioned in **≥{MIN_PAGES} distinct source-summary pages** but missing as wiki concept pages.",
        "Ranked by source-page count. Each row is either a real coverage gap, an alias of an existing page (the alias is fine, move on), or a false positive (add to `SLUG_STOPS` in the script and rerun).",
        "",
        f"**Threshold:** ≥{MIN_PAGES} distinct source pages. **Showing top {len(candidates)}** of all surfaced.",
        "",
        "---",
        "",
        "| Rank | Candidate slug | Source pages | Sample sources |",
        "|------|----------------|--------------|----------------|",
    ]
    for i, (slug, count, srcs) in enumerate(candidates, 1):
        sample = sorted(srcs)[:3]
        sample_str = " · ".join(f"[[{s}]]" for s in sample)
        lines.append(f"| {i} | `{slug}` | {count} | {sample_str} |")

    lines.extend([
        "",
        "---",
        "",
        "## How to triage",
        "",
        "Three outcomes per candidate:",
        "",
        "1. **Build** — real concept, no existing page covers it, build it following the CLAUDE.md page template using the sample sources as input.",
        "2. **Alias** — an existing page already covers this under a different name. The aliasing is acceptable; move on.",
        "3. **Reject** — too generic to be a concept page; add slug to `SLUG_STOPS` in `_scripts/concept-frequency-audit.py` and rerun the audit.",
        "",
        "After each ingest pass, rerun this audit. Anything still surfacing after triage is a real gap.",
        "",
        "## Tuning",
        "",
        f"- `MIN_PAGES = {MIN_PAGES}` — lower to widen, raise to focus on highest-frequency only.",
        f"- `MAX_RESULTS = {MAX_RESULTS}` — cap report length.",
        "- `WORD_STOPS` — common English / coaching-talk words filtered at phrase boundaries.",
        "- `SLUG_STOPS` — full-slug rejections; expand as you triage false positives.",
        "- `DOMAIN_STOPS` — vault-organizing words that aren't concepts on their own.",
        "",
        "## Known limitations",
        "",
        "- Plural vs singular not normalized (`seed-oils` and `seed-oil` count separately).",
        "- Concepts that exist as section headings inside larger pages will surface as candidates — accept as aliases.",
        "- No POS tagging — false positives are filtered by stop lists, not grammar.",
        "",
    ])

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {len(candidates)} candidates → {REPORT}")
    print(f"\nTop 20:")
    for slug, count, _ in candidates[:20]:
        print(f"  {count:3d}  {slug}")


if __name__ == "__main__":
    main()
