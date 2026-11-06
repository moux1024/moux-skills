#!/usr/bin/env python3
"""Step 7 — tile intake: strip the watermark, fit the cell, declare the size.

Image models return a watermark in the corner and a size that is close to, but not,
the cell. Both have to be dealt with by code, not by hope: a stitched atlas with one
tile 4% narrower than the rest shows up as a seam that looks like a design mistake.

The watermark fill continues the vertical gradient found just above the stamp, column by
column. Cloning clean artwork from beside the stamp looks fine in theory and fails on
screen: if the surface is a gradient, the clone sits one tone off and reads as a
rectangle of slightly different paper.

Usage
  python3 finalize.py gen/raw.png -o tiles/z_r1c1.png --cell 2048 --wm 880,946,1024,1024
"""

import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402


def erase_watermark(img, box, rows_above=6):
    """Fill `box` (x0,y0,x1,y1) by extrapolating the gradient above it, per column."""
    px = img.load()
    x0, y0, x1, y1 = box
    w, h = img.size
    x0, x1 = max(0, x0), min(w, x1)
    y0, y1 = max(rows_above + 1, y0), min(h, y1)
    for x in range(x0, x1):
        top = px[x, y0 - 1]
        ref = px[x, max(0, y0 - 1 - rows_above)]
        slope = [(top[i] - ref[i]) / float(rows_above) for i in range(3)]
        for y in range(y0, y1):
            d = y - (y0 - 1)
            px[x, y] = tuple(
                max(0, min(255, int(top[i] + slope[i] * d))) for i in range(3))
    return img


def fit_cell(img, cell):
    """Cover-fit to a square cell: scale to fill, centre-crop the overhang."""
    w, h = img.size
    scale = max(cell / w, cell / h)
    nw, nh = max(cell, int(round(w * scale))), max(cell, int(round(h * scale)))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - cell) // 2, (nh - cell) // 2
    return img.crop((left, top, left + cell, top + cell))


def main():
    ap = argparse.ArgumentParser(description="promo-atlas tile intake")
    ap.add_argument("raw")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cell", type=int, default=2048)
    ap.add_argument("--wm", default=None, help="watermark box x0,y0,x1,y1 (pixels of the raw image)")
    ap.add_argument("--no-fit", action="store_true", help="keep the source framing, only strip the mark")
    args = ap.parse_args()

    img = Image.open(args.raw).convert("RGB")
    src = list(img.size)
    if args.wm:
        box = [int(v) for v in args.wm.split(",")]
        if len(box) != 4:
            print("--wm 需要 x0,y0,x1,y1", file=sys.stderr)
            return 2
        img = erase_watermark(img, box)
    if not args.no_fit:
        img = fit_cell(img, args.cell)

    pc.ensure_dir(os.path.dirname(os.path.abspath(args.out)))
    img.save(args.out)
    flag = "upscaled" if max(src) < args.cell else "native"
    print("%s  %s → %d×%d  (%s)" % (args.out, "×".join(str(s) for s in src),
                                    img.width, img.height, flag))
    if flag == "upscaled":
        print("  ⚠ 源图小于 cell，已被放大。超高分只能来自大 tile，不能来自重采样。",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
