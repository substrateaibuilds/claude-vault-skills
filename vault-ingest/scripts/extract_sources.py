#!/usr/bin/env python3
"""Find every source document under a base dir, convert non-plain-text formats to text,
and write a TSV manifest: status, kind, original_path, read_path, note.

Statuses: NATIVE (read as-is), CONVERTED, OCR (image or image-only PDF read by OCR),
EMPTY (no usable text even after OCR), UNSUPPORTED (known document format, no converter),
NON-TEXT (audio/video/binary, or an image with no readable text), FAILED.

OCR engine: tesseract (images at native resolution, PDF pages rasterized at 300 dpi).
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile

NATIVE = {
    "md", "markdown", "txt", "text", "csv", "tsv", "json", "jsonl", "ndjson", "yaml", "yml",
    "xml", "srt", "vtt", "log", "rst", "org", "tex", "adoc", "ipynb", "sbv", "opml",
}
CONVERTERS = {
    "pdf": "pdftotext",
    "docx": "pandoc", "odt": "pandoc", "pptx": "pandoc", "epub": "pandoc",
    "xlsx": "openpyxl", "xlsm": "openpyxl",
    "doc": "textutil", "rtf": "textutil", "rtfd": "textutil", "html": "textutil",
    "htm": "textutil", "webarchive": "textutil", "wordml": "textutil",
}
UNSUPPORTED = {
    "xls": "legacy Excel — re-save as .xlsx or .csv",
    "ods": "re-save as .xlsx or .csv",
    "numbers": "export from Numbers as .xlsx or .csv",
    "pages": "export from Pages as .docx",
    "key": "export from Keynote as .pptx or .pdf",
    "ppt": "legacy PowerPoint — re-save as .pptx",
}
IMAGES = {"png", "jpg", "jpeg", "heic", "heif", "tif", "tiff", "gif", "bmp", "webp"}
BUNDLES = {"rtfd", "pages", "numbers", "key"}
META = {"claude.md", "ingestion-prompt.md", "agents.md", "gemini.md"}
SKIP_DIRS = {"wiki", "_scripts", "node_modules"}
MIN_CHARS = 200
MIN_IMAGE_CHARS = 20


def ocr_engine():
    return "tesseract" if shutil.which("tesseract") else ""


def ocr_image(path):
    if not ocr_engine():
        raise FileNotFoundError("tesseract not installed (brew install tesseract)")
    out = subprocess.run(["tesseract", path, "-", "--psm", "3"], check=True, capture_output=True, timeout=180)
    return out.stdout.decode(errors="replace").strip()


def ocr_pdf(src, dst):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "300", "-png", src, os.path.join(tmp, "p")], check=True, capture_output=True)
        pages = sorted(os.listdir(tmp), key=lambda n: int(re.search(r"(\d+)\.png$", n).group(1)))
        with open(dst, "w") as f:
            for i, name in enumerate(pages, 1):
                f.write(f"## Page {i}\n{ocr_image(os.path.join(tmp, name))}\n\n")


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def ext_of(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def is_text(path):
    try:
        mime = subprocess.run(["file", "--mime-type", "-b", path], capture_output=True, text=True).stdout.strip()
    except OSError:
        return False
    return mime.startswith("text/") or mime in {"application/json", "application/xml"}


def walk(base, maxdepth):
    base = os.path.abspath(base)
    for root, dirs, files in os.walk(base):
        depth = 0 if root == base else os.path.relpath(root, base).count(os.sep) + 1
        bundles = [d for d in dirs if ext_of(d) in BUNDLES]
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in SKIP_DIRS and d not in bundles and depth + 1 < maxdepth
        ]
        for name in sorted(files) + sorted(bundles):
            if name.startswith(".") or name.lower() in META or name.lower().startswith("readme"):
                continue
            yield os.path.join(root, name)


def convert(tool, src, dst):
    if tool == "pdftotext":
        subprocess.run(["pdftotext", "-layout", src, dst], check=True, capture_output=True)
    elif tool == "pandoc":
        subprocess.run(["pandoc", src, "-t", "gfm", "--wrap=none", "-o", dst], check=True, capture_output=True)
    elif tool == "textutil":
        subprocess.run(["textutil", "-convert", "txt", "-output", dst, src], check=True, capture_output=True)
    elif tool == "openpyxl":
        import openpyxl
        wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
        with open(dst, "w", newline="") as f:
            for ws in wb.worksheets:
                f.write(f"## Sheet: {ws.title}\n")
                w = csv.writer(f)
                for row in ws.iter_rows(values_only=True):
                    if any(c is not None for c in row):
                        w.writerow(["" if c is None else c for c in row])
                f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--out", default="/tmp/vault-ingest-extract")
    ap.add_argument("--maxdepth", type=int, default=99)
    ap.add_argument("--manifest", default="/tmp/vault-ingest-manifest.tsv")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    base = os.path.abspath(a.base)
    rows = []
    for path in walk(base, a.maxdepth):
        rel = os.path.relpath(path, base)
        ext = ext_of(path)
        if ext in NATIVE:
            rows.append(("NATIVE", ext, path, path, ""))
        elif ext in CONVERTERS:
            tool = CONVERTERS[ext]
            dst = os.path.join(a.out, slug(rel) + (".csv" if tool == "openpyxl" else ".md" if tool == "pandoc" else ".txt"))
            try:
                convert(tool, path, dst)
                n = len(open(dst, errors="ignore").read().strip())
                status, note = "CONVERTED", f"{tool}, {n} chars"
                if n < MIN_CHARS and ext == "pdf":
                    ocr_pdf(path, dst)
                    n = len(open(dst, errors="ignore").read().strip())
                    status, note = "OCR", f"image-only PDF, {ocr_engine()} OCR, {n} chars"
                if n < MIN_CHARS:
                    status, note = "EMPTY", f"{note} — blank or unreadable; check for a sibling text file"
            except FileNotFoundError:
                status, note = "FAILED", f"{tool} not installed"
            except subprocess.CalledProcessError as e:
                err = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode(errors="ignore")
                err = err.strip().splitlines()
                status, note = "FAILED", f"{tool}: {(err[0] if err else 'exit ' + str(e.returncode))[:120]}"
            except Exception as e:
                status, note = "FAILED", f"{tool}: {str(e).splitlines()[0][:120]}"
            rows.append((status, ext, path, dst if status in ("CONVERTED", "OCR") else "", note))
        elif ext in IMAGES:
            dst = os.path.join(a.out, slug(rel) + ".txt")
            try:
                text = ocr_image(path)
                if len(text) >= MIN_IMAGE_CHARS:
                    with open(dst, "w") as f:
                        f.write(text + "\n")
                    rows.append(("OCR", ext, path, dst, f"image, {ocr_engine()} OCR, {len(text)} chars"))
                else:
                    rows.append(("NON-TEXT", ext, path, "", f"image with no readable text ({len(text)} chars OCR'd)"))
            except FileNotFoundError as e:
                rows.append(("FAILED", ext, path, "", str(e)))
            except subprocess.CalledProcessError as e:
                err = (e.stderr or b"").decode(errors="replace").strip().splitlines()
                rows.append(("FAILED", ext, path, "", f"OCR: {(err[-1] if err else 'exit ' + str(e.returncode))[:120]}"))
            except Exception as e:
                rows.append(("FAILED", ext, path, "", f"OCR: {str(e).splitlines()[0][:120]}"))
        elif ext in UNSUPPORTED:
            rows.append(("UNSUPPORTED", ext, path, "", UNSUPPORTED[ext]))
        elif os.path.isfile(path) and is_text(path):
            rows.append(("NATIVE", ext or "noext", path, path, "detected as text by mime type"))
        else:
            rows.append(("NON-TEXT", ext or "noext", path, "", "audio/video/binary — not ingested"))
    with open(a.manifest, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["status", "kind", "original_path", "read_path", "note"])
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print(f"Manifest: {a.manifest} ({len(rows)} files)")
    for k in ("NATIVE", "CONVERTED", "OCR", "EMPTY", "UNSUPPORTED", "NON-TEXT", "FAILED"):
        if counts.get(k):
            print(f"  {k}: {counts[k]}")
    for r in rows:
        if r[0] not in ("NATIVE", "CONVERTED", "OCR"):
            print(f"  {r[0]}: {os.path.relpath(r[2], base)} — {r[4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
