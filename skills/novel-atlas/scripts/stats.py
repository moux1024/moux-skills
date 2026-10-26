#!/usr/bin/env python3
"""Compute per-character chapter appearance rates from a chapter index.

This exists so that T1 tiering is a measurement, not an impression. Never let a model
decide a character is "important" when the hit rate is a computation away.

Usage:
    python3 stats.py atlas_build/chapters.json aliases.json --out atlas_build/stats.json

aliases.json maps ONE canonical name to every surface form the text uses:
    {"林冲": ["林冲", "林教头", "豹子头"]}
"""

import argparse
import json
import os
import re
import sys

T1_RATE = 0.15


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_aliases(raw):
    out = {}
    for key, val in raw.items():
        if isinstance(val, str):
            val = [val]
        forms = [v.strip() for v in val if v and v.strip()]
        if key.strip() not in forms:
            forms.insert(0, key.strip())
        # Longest form first: the counting regex tries alternatives left to right, so
        # "松岛宏" must precede "松岛" or one mention of the long form would be counted
        # again under the short one.
        out[key.strip()] = sorted(set(forms), key=len, reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters_json")
    ap.add_argument("aliases_json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--t1-rate", type=float, default=T1_RATE)
    args = ap.parse_args()

    index = load_json(args.chapters_json)
    aliases = normalize_aliases(load_json(args.aliases_json))

    book_path = index.get("book")
    if not book_path or not os.path.exists(book_path):
        book_path = os.path.join(os.path.dirname(args.chapters_json), "book.txt")
    if not os.path.exists(book_path):
        sys.exit(f"book text not found: {book_path}")
    with open(book_path, encoding="utf-8") as f:
        book = f.read()

    chapters = index["chapters"]
    total = len(chapters)
    results = []

    for canon, forms in aliases.items():
        # one consumed match per occurrence, so nested aliases count once
        # (a 松岛 inside 松岛宏 is part of the same mention, not a second one)
        rx = re.compile("|".join(re.escape(f) for f in forms))
        hits, mentions, first, last = 0, 0, None, None
        for ch in chapters:
            body = book[ch["start"]:ch["end"]]
            n = len(rx.findall(body))
            if n:
                hits += 1
                mentions += n
                if first is None:
                    first = ch["index"]
                last = ch["index"]
        rate = hits / total if total else 0.0
        results.append(
            {
                "name": canon,
                "forms": forms,
                "hit_chapters": hits,
                "hit_rate": round(rate, 4),
                "mentions": mentions,
                "first": first,
                "last": last,
                "tier_hint": "T1" if rate >= args.t1_rate else "below-threshold",
            }
        )

    results.sort(key=lambda r: (-r["hit_rate"], -r["mentions"]))
    payload = {
        "chapters_total": total,
        "t1_rate": args.t1_rate,
        "characters": results,
        "note": ("tier_hint only encodes the hit-rate test. Promote a below-threshold character "
                 "to T1 manually if it drives 2+ irreversible turning points; demote a "
                 "hit-rate-qualified character if it never changes anything."),
    }

    width = max([len(r["name"]) for r in results], default=4)
    print(f"{'name'.ljust(width)}  rate   chapters  mentions  first  last   hint")
    for r in results:
        print(f"{r['name'].ljust(width)}  {r['hit_rate']:>5.2f}  "
              f"{r['hit_chapters']:>8}  {r['mentions']:>8}  "
              f"{str(r['first']):>5}  {str(r['last']):>4}   {r['tier_hint']}")
    print(f"\n{total} chapters. T1 threshold {args.t1_rate:.0%}. "
          f"{len([r for r in results if r['tier_hint'] == 'T1'])} candidates — cap is 12, "
          f"demote by lowest rate if over.")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
