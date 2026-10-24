#!/usr/bin/env python3
"""Normalize a novel file into plain text plus a chapter index, and report on segmentation quality.

Stdlib only for parsing (.txt/.md/.docx/.epub). No external reader dependencies.

Usage:
    python3 normalize.py book.epub -o atlas_build/
    python3 normalize.py book.txt -o atlas_build/ --chapter-regex '^\\s*卷[一二三四五六七八九十]+'
"""

import argparse
import json
import os
import posixpath
import re
import statistics
import sys
import unicodedata
import zipfile
from html.parser import HTMLParser

# ---------------------------------------------------------------- extraction

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read_plain(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def read_docx(path):
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    out = []
    for p in root.iter(W + "p"):
        buf = []
        for node in p.iter():
            if node.tag == W + "t":
                buf.append(node.text or "")
            elif node.tag == W + "tab":
                buf.append("\t")
            elif node.tag == W + "br":
                buf.append("\n")
        out.append("".join(buf))
    return "\n".join(out)


class _TextExtractor(HTMLParser):
    BLOCK = {
        "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
        "section", "article", "blockquote", "hr", "title",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.buf = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.buf.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def text(self):
        return "".join(self.buf)


def html_to_text(html):
    p = _TextExtractor()
    p.feed(html)
    return p.text()


def read_epub(path):
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        opf = None
        if "META-INF/container.xml" in names:
            try:
                c = ET.fromstring(z.read("META-INF/container.xml"))
                for node in c.iter():
                    if node.tag.endswith("rootfile") and node.get("full-path"):
                        opf = node.get("full-path")
                        break
            except ET.ParseError:
                opf = None
        base = posixpath.dirname(opf) if opf else ""
        order = []
        if opf:
            root = ET.fromstring(z.read(opf))
            manifest = {}
            for node in root.iter():
                if node.tag.endswith("item") and node.get("id"):
                    manifest[node.get("id")] = node.get("href")
            for node in root.iter():
                if node.tag.endswith("itemref"):
                    href = manifest.get(node.get("idref"))
                    if href:
                        order.append(posixpath.normpath(posixpath.join(base, href)))
        if not order:
            order = sorted(n for n in names if n.lower().endswith((".xhtml", ".html", ".htm")))
        parts = []
        for name in order:
            try:
                html = z.read(name).decode("utf-8", "ignore")
            except KeyError:
                continue
            parts.append(html_to_text(html))
    return "\n".join(parts)


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return read_docx(path)
    if ext == ".epub":
        return read_epub(path)
    if ext in (".txt", ".md", ".markdown", ".text"):
        return read_plain(path)
    raise SystemExit(f"Unsupported input: {ext}. Convert to .txt first (see SKILL.md).")


# ---------------------------------------------------------------- cleaning

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\ufeff\u2060"), None)


def clean(text):
    text = unicodedata.normalize("NFC", text)
    text = text.translate(ZERO_WIDTH)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    out, blanks = [], 0
    for ln in lines:
        if ln.strip():
            out.append(ln)
            blanks = 0
        else:
            blanks += 1
            if blanks <= 1:
                out.append("")
    return "\n".join(out).strip() + "\n"


# ---------------------------------------------------------------- chapters

DEFAULT_RE = (
    r"^\s*(?:"
    r"第\s*[一二三四五六七八九十百千零〇两0-9]+\s*[章回節节卷篇集幕话話]"
    r"|Chapter\s+[0-9IVXLCivxlc]+"
    r"|CHAPTER\s+[0-9IVXLC]+"
    r"|(?:序章|楔子|引子|尾声|尾聲|终章|終章|后记|後記|番外)"
    r")"
)


def split_chapters(text, pattern, max_heading=60):
    rx = re.compile(pattern)
    lines = text.split("\n")
    marks = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or len(s) > max_heading:
            continue
        if rx.match(s):
            marks.append((i, s))
    if len(marks) < 2:
        return None, 0

    offsets, acc = [], 0
    for ln in lines:
        offsets.append(acc)
        acc += len(ln) + 1

    chapters = []
    front = "".join(lines[: marks[0][0]]).strip()
    for n, (li, title) in enumerate(marks):
        start_line = li
        end_line = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        body = "\n".join(lines[start_line:end_line]).strip()
        chapters.append(
            {
                "index": n + 1,
                "title": title,
                "start": offsets[start_line],
                "end": offsets[end_line - 1] + len(lines[end_line - 1]) + 1,
                "chars": len(body),
            }
        )
    return chapters, len(front)


def fallback_split(text, target=4000):
    """No headings found: cut on blank-line gaps near the target size."""
    spans, cursor = [], 0
    for m in re.finditer(r"\n\s*\n", text):
        spans.append((cursor, m.start()))
        cursor = m.end()
    spans.append((cursor, len(text)))
    spans = [(a, b) for a, b in spans if text[a:b].strip()]

    def make(idx, group):
        a, b = group[0][0], group[-1][1]
        return {"index": idx, "title": f"[untitled {idx}]", "start": a, "end": b,
                "chars": len(text[a:b])}

    chapters, group, size, idx = [], [], 0, 1
    for a, b in spans:
        group.append((a, b))
        size += b - a
        if size >= target:
            chapters.append(make(idx, group))
            idx += 1
            group, size = [], 0
    if group:
        chapters.append(make(idx, group))
    return chapters


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--out-dir", default="atlas_build")
    ap.add_argument("--chapter-regex", default=DEFAULT_RE)
    ap.add_argument("--fallback-chars", type=int, default=4000,
                    help="chapter size used when no headings are found")
    args = ap.parse_args()

    raw = extract(args.input)
    text = clean(raw)
    os.makedirs(args.out_dir, exist_ok=True)
    book_path = os.path.join(args.out_dir, "book.txt")
    with open(book_path, "w", encoding="utf-8") as f:
        f.write(text)

    chapters, front_chars = split_chapters(text, args.chapter_regex)
    used_fallback = False
    if chapters is None:
        used_fallback = True
        chapters = fallback_split(text, args.fallback_chars)

    sizes = [c["chars"] for c in chapters if c["chars"] > 0]
    median = statistics.median(sizes) if sizes else 0

    flags = []
    if used_fallback:
        flags.append(
            ("NO_HEADINGS",
             "No chapter headings matched. Fell back to fixed-size cuts — the timeline and "
             "appearance rates will be unreliable. Re-run with --chapter-regex tuned to this book.")
        )
    if front_chars > 200:
        flags.append(("FRONT_MATTER", f"{front_chars} chars before the first heading "
                                      f"(title page / preface?) — excluded from the chapter list."))
    if median:
        short = [c["index"] for c in chapters if 0 < c["chars"] < median * 0.3]
        long_ = [c["index"] for c in chapters if c["chars"] > median * 3]
        if short:
            flags.append(("SHORT_CHAPTERS", f"{len(short)} chapters under 30% of median "
                                            f"({median:.0f} chars): {short[:15]}"))
        if long_:
            flags.append(("LONG_CHAPTERS", f"{len(long_)} chapters over 300% of median: {long_[:15]} "
                                           f"— likely merged chapters or a heading missed inside them."))

    index = {
        "source": os.path.abspath(args.input),
        "book": os.path.abspath(book_path),
        "chars": len(text),
        "chapters_total": len(chapters),
        "chapters": chapters,
        "flags": [{"code": c, "detail": d} for c, d in flags],
    }
    idx_path = os.path.join(args.out_dir, "chapters.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"book.txt      {len(text):>9,} chars")
    print(f"chapters.json {len(chapters):>9,} chapters   median {median:,.0f} chars")
    if sizes:
        print(f"              min {min(sizes):,} / max {max(sizes):,}")
    print()
    if flags:
        print("SEGMENTATION FLAGS — resolve these before designing anything:")
        for code, detail in flags:
            print(f"  [{code}] {detail}")
        if used_fallback:
            print("\nDO NOT CONTINUE. Fix the chapter regex first.")
    else:
        print("Segmentation looks sane. Eyeball the first and last chapter titles before continuing.")
    print(f"\nwrote {idx_path}")


if __name__ == "__main__":
    main()
