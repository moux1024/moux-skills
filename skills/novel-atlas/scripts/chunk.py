#!/usr/bin/env python3
"""Plan how a long novel is read: chunk sizes, digest budgets, and how many passes are needed.

A novel that fits in one reliable read needs none of this. Past that point the binding
constraint is not the context window — it is that every chunk's digest must survive into
the assembly call. So the arithmetic runs backwards from the assembly budget:

    chunks       = ceil(total_chars / chunk_chars)
    digest_budget = assembly_budget / chunks        # characters allowed per chunk digest

When `digest_budget` is too thin to hold the facts a chunk contains, one more level is
needed: chunk digests roll up into arc briefs, and only the briefs reach the assembly call.

Usage:
    python3 chunk.py atlas_build/chapters.json -o atlas_build/context
    python3 chunk.py chapters.json -o context --window 1000000 --chunk-chars 25000
    python3 chunk.py chapters.json -o context --write-text   # also emit one file per chunk
"""

import argparse
import json
import math
import os
import re
import sys

# Chinese runs at roughly 1.5 characters per token across current tokenizers. It is an
# estimate, and deliberately the optimistic end: if a tokenizer is worse than this the
# budget shrinks, which errs toward more chunks rather than fewer.
DEFAULT_CHARS_PER_TOKEN = 1.5

# Benchmarks put reliable recall at 50-65% of the advertised window (RULER), and accuracy
# degrades with length even when retrieval succeeds (context rot). 0.5 is the cautious half.
EFFECTIVE_RATIO = 0.5

# The assembly call must hold every digest AND write the blueprint. Leave a bit under half
# of the read budget for digests alone.
ASSEMBLY_SHARE = 0.55

# A chunk digest thinner than this cannot carry events with chapter numbers plus quotes.
MIN_DIGEST_CHARS = 500
COMFORTABLE_DIGEST_CHARS = 600

# Arc briefs: a brief is written from its digests only, so cap how many it must read.
ARC_MAX_DIGESTS = 8
ARC_BRIEF_CHARS = 800

VOLUME_RE = re.compile(r"^第[一二三四五六七八九十百零]+卷")


def load_chapters(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    chapters = data["chapters"] if isinstance(data, dict) else data
    if not chapters:
        sys.exit(f"{path}: no chapters found")
    return data, chapters


def plan_chunks(chapters, chunk_chars):
    """Greedy contiguous grouping. A chapter longer than the budget gets its own chunk."""
    chunks, buf = [], []
    for ch in chapters:
        if buf and sum(c["chars"] for c in buf) + ch["chars"] > chunk_chars:
            chunks.append(buf)
            buf = []
        buf.append(ch)
    if buf:
        chunks.append(buf)
    return chunks


def plan_arcs(chunks, volumes):
    """Group chunks into arcs: volumes first, then split each volume into balanced parts.

    A volume is the natural summarisation unit, so arcs should not straddle volumes when the
    volume is small enough to hold one or two arcs. Splitting each volume evenly (rather than
    greedily every ARC_MAX_DIGESTS chunks) keeps brief boundaries on narrative boundaries,
    which is what makes a brief readable on its own.
    """
    if not volumes:
        return [chunks[i:i + ARC_MAX_DIGESTS] for i in range(0, len(chunks), ARC_MAX_DIGESTS)]

    def volume_of(chunk):
        idx = chunk[0]["index"]
        title = None
        for v in volumes:
            if v["index"] <= idx:
                title = v["title"]
        return title

    groups, current, current_title = [], [], None
    for ck in chunks:
        t = volume_of(ck)
        if current and t != current_title:
            groups.append(current)
            current = []
        current.append(ck)
        current_title = t
    if current:
        groups.append(current)

    arcs = []
    for group in groups:
        n = len(group)
        parts = max(1, math.ceil(n / ARC_MAX_DIGESTS))
        base, extra = divmod(n, parts)
        pos = 0
        for i in range(parts):
            size = base + (1 if i < extra else 0)
            arcs.append(group[pos:pos + size])
            pos += size
    return arcs


def main():
    ap = argparse.ArgumentParser(description="Plan chunking and digest budgets for a long novel.")
    ap.add_argument("chapters", help="chapters.json produced by normalize.py")
    ap.add_argument("-o", "--out", default="atlas_build/context", help="output directory")
    ap.add_argument("--window", type=int, default=200000,
                    help="context window in tokens of the model doing the reading (default 200000)")
    ap.add_argument("--chars-per-token", type=float, default=DEFAULT_CHARS_PER_TOKEN,
                    help=f"characters per token for this language (default {DEFAULT_CHARS_PER_TOKEN})")
    ap.add_argument("--chunk-chars", type=int, default=0,
                    help="characters per extraction chunk (default: derived from the read budget)")
    ap.add_argument("--assembly-budget", type=int, default=0,
                    help="characters of digest allowed in one assembly call (default: derived)")
    ap.add_argument("--write-text", action="store_true",
                    help="also write one text file per chunk, for hosts that hand files to subagents")
    args = ap.parse_args()

    data, chapters = load_chapters(args.chapters)
    total = sum(c["chars"] for c in chapters)

    read_budget = int(args.window * EFFECTIVE_RATIO * args.chars_per_token)
    assembly_budget = args.assembly_budget or int(read_budget * ASSEMBLY_SHARE)
    chunk_chars = args.chunk_chars or min(25000, max(12000, read_budget // 6))

    volumes = []
    seen = set()
    for c in chapters:
        m = VOLUME_RE.match(c["title"])
        if not m:
            continue
        # "第五卷卷末小结" is not a seventh volume — it belongs to the fifth. One heading
        # per volume number, the first one wins.
        key = re.match(r"^第[一二三四五六七八九十百零]+卷", c["title"]).group(0)
        if key in seen:
            continue
        seen.add(key)
        volumes.append(c)
    chunks = plan_chunks(chapters, chunk_chars)
    n_chunks = len(chunks)
    digest_budget = int(assembly_budget / n_chunks)

    fits_whole = total <= read_budget
    if fits_whole:
        mode = "single_pass"
    elif total <= 4 * read_budget and digest_budget >= COMFORTABLE_DIGEST_CHARS:
        mode = "two_pass"
    else:
        mode = "three_pass"

    arcs = plan_arcs(chunks, volumes) if mode == "three_pass" else []
    assembly_chars = (len(arcs) * ARC_BRIEF_CHARS) if arcs else n_chunks * digest_budget

    plan = {
        "source": data.get("source") if isinstance(data, dict) else None,
        "chapters_file": os.path.abspath(args.chapters),
        "total_chars": total,
        "chapters_total": len(chapters),
        "assumptions": {
            "window_tokens": args.window,
            "chars_per_token": args.chars_per_token,
            "effective_ratio": EFFECTIVE_RATIO,
            "read_budget_chars": read_budget,
            "assembly_budget_chars": assembly_budget,
            "tokens_estimate": round(total / args.chars_per_token),
            "windows_worth": round(total / (args.window * args.chars_per_token), 2),
        },
        "mode": mode,
        "chunk": {
            "used": not fits_whole,
            "chapters": [c["index"] for c in chunks[0]] if n_chunks == 1 else None,
            "chunk_chars": chunk_chars,
            "count": n_chunks,
            "digest_budget_chars": digest_budget,
            "digest_is_thin": digest_budget < MIN_DIGEST_CHARS,
        },
        "arc": {
            "count": len(arcs),
            "max_digests": ARC_MAX_DIGESTS,
            "brief_chars": ARC_BRIEF_CHARS,
            "assembly_chars": assembly_chars,
        },
        "chunks": [
            {
                "id": f"k{i + 1:03d}",
                "chapters": [ck[0]["index"], ck[-1]["index"]],
                "count": len(ck),
                "chars": sum(c["chars"] for c in ck),
                "first_title": ck[0]["title"],
                "last_title": ck[-1]["title"],
                "offset": [ck[0]["start"], ck[-1]["end"]],
                "arc": None,
            }
            for i, ck in enumerate(chunks)
        ],
        "arcs": [],
        "volumes": [
            {"index": v["index"], "title": v["title"]} for v in volumes
        ],
        "warnings": [],
    }

    if arcs:
        pos = 0
        for i, arc in enumerate(arcs):
            ids = [f"k{pos + j + 1:03d}" for j in range(len(arc))]
            for j in range(len(arc)):
                plan["chunks"][pos + j]["arc"] = f"a{i + 1:02d}"
            plan["arcs"].append({
                "id": f"a{i + 1:02d}",
                "chunks": ids,
                "chapters": [arc[0][0]["index"], arc[-1][-1]["index"]],
                "chars": sum(c["chars"] for ck in arc for c in ck),
                "brief_input_chars": len(arc) * digest_budget,
            })
            pos += len(arc)

    spans = {v["title"]: volume_span(chapters, plan["volumes"], v["index"]) for v in plan["volumes"]}
    over = {t: s for t, s in spans.items() if s and s > read_budget}
    if over and len(over) == len(spans):
        msg = (f"every volume is over the {read_budget}-char read budget (smallest "
               f"{min(over.values())}) — a volume is not a usable reading unit for this book")
        if plan["arcs"]:
            counts = []
            for v in plan["volumes"]:
                inside = [a for a in plan["arcs"]
                          if _arc_volume(plan, a, plan["volumes"]) == v["title"]]
                counts.append(f"{v['title'].split(' ')[0]} {len(inside)}")
            msg += "; arcs per volume: " + ", ".join(counts)
        plan["warnings"].append(msg)
    else:
        for title, span in over.items():
            plan["warnings"].append(
                f"volume '{title}' is {span} chars, over the {read_budget}-char read budget "
                f"— never read a whole volume in one call; arcs already cut inside it"
            )

    biggest = max(chapters, key=lambda c: c["chars"])
    if biggest["chars"] > chunk_chars * 0.6:
        plan["warnings"].append(
            f"chapter {biggest['index']} is {biggest['chars']} chars, over 60% of a chunk "
            f"({chunk_chars}) — it will dominate its chunk; consider --chunk-chars "
            f"{int(biggest['chars'] * 1.5)}"
        )

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "context_plan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    if args.write_text:
        write_text(args.out, plan, data, chapters)

    report(plan, out_path)
    return 0


def volume_span(chapters, volumes, index):
    starts = [v["index"] for v in volumes]
    i = starts.index(index)
    end = starts[i + 1] if i + 1 < len(starts) else chapters[-1]["index"] + 1
    return sum(c["chars"] for c in chapters if index <= c["index"] < end)


def _arc_volume(plan, arc, volumes):
    """Which volume an arc starts in — arcs may straddle a volume edge, and that is fine."""
    best = None
    for v in volumes:
        if v["index"] <= arc["chapters"][0]:
            best = v["title"]
    return best


def write_text(out_dir, plan, data, chapters):
    book_path = data.get("book") if isinstance(data, dict) else None
    if not book_path or not os.path.exists(book_path):
        print("note: book path unavailable, wrote no chunk text", file=sys.stderr)
        return
    with open(book_path, encoding="utf-8") as f:
        text = f.read()
    cdir = os.path.join(out_dir, "chunks")
    os.makedirs(cdir, exist_ok=True)
    for ck in plan["chunks"]:
        a, b = ck["offset"]
        head = (f"=== {ck['id']}  chapters {ck['chapters'][0]}-{ck['chapters'][1]}  "
                f"{ck['chars']} chars ===\n\n")
        with open(os.path.join(cdir, ck["id"] + ".txt"), "w", encoding="utf-8") as f:
            f.write(head + text[a:b])
    print(f"wrote {len(plan['chunks'])} chunk file(s) to {cdir}")


def report(plan, out_path):
    a = plan["assumptions"]
    print(f"source        {plan['chapters_total']} chapters, {plan['total_chars']} chars "
          f"(~{a['tokens_estimate']} tokens, {a['windows_worth']}x a {a['window_tokens']}-token window)")
    print(f"read budget   {a['read_budget_chars']} chars  (window x {a['effective_ratio']} x "
          f"{a['chars_per_token']} chars/token)")
    print(f"assembly      {a['assembly_budget_chars']} chars of digest per call")
    print(f"mode          {plan['mode']}")
    if plan["mode"] == "single_pass":
        print(f"chunks        none needed — {plan['total_chars']} chars fits one read")
    else:
        print(f"chunks        {plan['chunk']['count']} x {plan['chunk']['chunk_chars']} chars "
              f"-> {plan['chunk']['digest_budget_chars']} chars of digest each")
    if plan["arcs"]:
        print(f"arcs          {len(plan['arcs'])} briefs, assembly sees "
              f"{plan['arc']['assembly_chars']} chars")
    for w in plan["warnings"]:
        print(f"[warn] {w}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
