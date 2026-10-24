#!/usr/bin/env python3
"""Turn a raw generation into a tile the stitcher can accept.

Two things go wrong between "the model returned an image" and "this is a 2048 tile":

1. **The watermark.** Every returned image carries one. Cloning clean artwork from beside
   it looks fine on paper and fails on screen — the floor is a gradient, so a cloned patch
   is one tone off and reads as a rectangle. Continuing the vertical gradient downward from
   the rows just above the stamp is invisible, because it *is* the same gradient.
2. **The size.** Image-to-image returns at most 1024 while the batch is 2048, so one tile
   in twelve arrives at half resolution. Upscaling it is the only option that does not
   punish the other eleven, but the fact has to be declared, not hidden — that is what
   `--stamp` writes back into the audit.

    python3 scripts/finalize.py gen/raw.png -o tiles/z9_0_2.png --cell 2048 \\
        --wm 880,946,1024,1024

Prints the source size, the scale factor and a warning when the tile was upscaled.
"""

import argparse
import hashlib
import json
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_rect(text):
    parts = [p for p in text.replace(" ", "").split(",") if p]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--wm needs x0,y0,x1,y1 in source pixels")
    return tuple(int(float(p)) for p in parts)


def remove_watermark(im, box, feather=10):
    """Fill `box` by continuing the vertical gradient found just above it.

    Column by column: read the mean of the four rows sitting immediately above the box, and
    the mean of eight rows a little further up, and extrapolate that slope down through the
    box. Blur the result so the extrapolation does not band, then feather only the edges that
    are interior — an edge on the image boundary needs no blending.
    """
    W, H = im.size
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return im

    px = im.load()
    fill = Image.new("RGB", (w, h))
    fp = fill.load()
    for x in range(x0, x1):
        near = [sum(px[x, y][c] for y in range(max(0, y0 - 6), max(1, y0 - 2))) /
                max(1, len(range(max(0, y0 - 6), max(1, y0 - 2)))) for c in range(3)]
        far_rows = range(max(0, y0 - 22), max(1, y0 - 14))
        far = [sum(px[x, y][c] for y in far_rows) / max(1, len(far_rows)) for c in range(3)]
        step = [(near[c] - far[c]) / 14.0 for c in range(3)]
        for i in range(h):
            yy = y0 + i - (y0 - 4)
            fp[x - x0, i] = tuple(
                max(0, min(255, int(near[c] + step[c] * yy))) for c in range(3))

    fill = fill.filter(ImageFilter.GaussianBlur(3.0))
    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            a = 255
            if x < feather and x0 > 0:
                a = min(a, int(255 * x / feather))
            if y < feather and y0 > 0:
                a = min(a, int(255 * y / feather))
            mp[x, y] = a
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    im.paste(fill, (x0, y0), mask)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cell", type=int, default=2048)
    ap.add_argument("--wm", type=parse_rect, action="append", default=[],
                    metavar="x0,y0,x1,y1",
                    help="watermark rect in SOURCE pixels; repeatable")
    ap.add_argument("--stamp", metavar="TILE_ID",
                    help="write provenance (source size, scale) into cast_audit.json")
    ap.add_argument("--audit", default=None,
                    help="path to cast_audit.json (default: beside --out)")
    args = ap.parse_args()

    im = Image.open(args.src)
    src_size = im.size
    if im.mode != "RGB":
        im = im.convert("RGB")

    for box in args.wm:
        im = remove_watermark(im, box)
        print(f"watermark filled  {box}")

    if im.size != (args.cell, args.cell):
        k = args.cell / float(max(im.size))
        up = max(im.size) < args.cell
        im = im.resize((args.cell, args.cell), Image.LANCZOS)
        if up:
            im = im.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=2))
        print(f"resized {src_size[0]}x{src_size[1]} -> {args.cell}x{args.cell}"
              f"  ({k:.2f}x, {'upscaled' if up else 'downscaled'})")
        if k > 1.45:
            print("[warn] source is far below the cell size — this tile will read softer "
                  "than its neighbours. Prefer a text-to-image reroll at full resolution.")
    else:
        print(f"size ok  {args.cell}x{args.cell}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    im.save(args.out)
    digest = hashlib.sha256(open(args.out, "rb").read()).hexdigest()
    print(f"wrote {args.out}  sha256 {digest[:16]}")

    if args.stamp:
        audit_path = args.audit or os.path.join(os.path.dirname(os.path.abspath(args.out)),
                                                "cast_audit.json")
        audit = {}
        if os.path.exists(audit_path):
            with open(audit_path, encoding="utf-8") as f:
                audit = json.load(f)
        entry = audit.setdefault(args.stamp, {})
        entry["tile"] = os.path.join(os.path.basename(os.path.dirname(args.out)),
                                     os.path.basename(args.out))
        entry["sha256"] = digest
        entry["source_px"] = list(src_size)
        entry["upscaled"] = max(src_size) < args.cell
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)
        print(f"stamped {args.stamp} in {audit_path} "
              f"(source {src_size[0]}x{src_size[1]}, upscaled={entry['upscaled']})")


if __name__ == "__main__":
    main()
