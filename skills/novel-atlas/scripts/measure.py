#!/usr/bin/env python3
"""Read a portrait box off a tile, and preview the crop it produces.

Anchor calibration fails for one reason: the box in `blueprint.json` is hand-written and
nobody knows where the head actually is. Guessing from the contact sheet costs a round trip
per guess, and two blind rounds still leave the box on a console instead of a face.

This tool closes that loop with the tile itself:

    # 1. bake a coordinate grid onto the home tile and read the head off it
    python3 scripts/measure.py atlas_build/tiles/z4_3_0.png

    # 2. try candidate boxes as the circular avatars they will become
    python3 scripts/measure.py atlas_build/tiles/z4_3_0.png \
        --box 0.4755,0.156,0.165,0.165 --box 0.486,0.156,0.165,0.165

The grid is labelled in normalized 0-1 coordinates, the same space `portrait.box` uses, so
what you read off the image is what you write into the blueprint. The candidate strip prints
the pixel side each box will yield and its mean luminance — a crop can be arithmetically
correct and still be too dark for a 204px avatar to read.
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_common as ac


def parse_box(text):
    parts = [p for p in text.replace(" ", "").split(",") if p]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"box needs 4 values x,y,w,h — got '{text}'")
    x, y, w, h = (float(p) for p in parts)
    if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
        raise argparse.ArgumentTypeError(f"box values are normalized 0-1 — got '{text}'")
    if abs(w - h) > 0.002:
        print(f"[warn] box {text} is not square ({w:.4f} x {h:.4f}); "
              f"the stitcher will squash it", file=sys.stderr)
    return (x, y, w, h)


def draw_grid(im, step, label_every):
    im = im.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    W, H = im.size
    size = max(10, int(W / 157.0))          # ~13px at 2048, scales with the tile
    font = ac.resolve_font(size)
    n = int(round(1.0 / step))
    for i in range(1, n):
        x, y = int(round(i * step * W)), int(round(i * step * H))
        d.line([(x, 0), (x, H)], fill=(0, 255, 120), width=1)
        d.line([(0, y), (W, y)], fill=(0, 255, 120), width=1)
    for i in range(0, n, label_every):
        for j in range(0, n, label_every):
            d.text((i * step * W + 4, j * step * H + 2),
                   f"{i * step:.2f},{j * step:.2f}", font=font, fill=(255, 240, 90))
    # border ticks so edge boxes are readable too
    for i in range(0, n + 1, label_every):
        d.text((min(W - 34, i * step * W + 2), H - size - 4),
               f"{i * step:.2f}", font=font, fill=(255, 240, 90))
    return im


def circular_crop(src, box, side):
    W, H = src.size
    px = (int(box[0] * W), int(box[1] * H),
          int((box[0] + box[2]) * W), int((box[1] + box[3]) * H))
    px = (max(0, px[0]), max(0, px[1]), min(W, px[2]), min(H, px[3]))
    crop = src.crop(px).convert("RGB")
    crop = crop.resize((side, side), Image.LANCZOS)
    mask = Image.new("L", (side * 4, side * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, side * 4 - 1, side * 4 - 1), fill=255)
    mask = mask.resize((side, side), Image.LANCZOS)
    out = Image.new("RGB", (side, side), (20, 20, 22))
    out.paste(crop, (0, 0), mask)
    return out, px, crop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tile")
    ap.add_argument("--box", type=parse_box, action="append", default=[],
                    metavar="x,y,w,h",
                    help="normalized box to preview as a circular avatar; repeatable")
    ap.add_argument("--step", type=float, default=0.05, help="grid step (normalized)")
    ap.add_argument("--label-every", type=int, default=2,
                    help="label every Nth grid line")
    ap.add_argument("--side", type=int, default=204,
                    help="avatar render size in px (match demand_px from anchor.py)")
    ap.add_argument("-o", "--out", help="output path (default: beside the source, /tmp)")
    args = ap.parse_args()

    src = Image.open(args.tile)
    stem = os.path.splitext(os.path.basename(args.tile))[0]

    if not args.box:
        out = args.out or f"/tmp/grid_{stem}.png"
        im = draw_grid(src, args.step, args.label_every)
        im.save(out)
        print(f"wrote {out}  ({im.width}x{im.height})")
        print(f"grid step {args.step}  ·  read x-min,y-min,x-max,y-max in normalized 0-1,")
        print("then convert to a blueprint box as x, y, (x-max - x-min), (y-max - y-min).")
        return

    cells = []
    for box in args.box:
        avatar, px, crop = circular_crop(src, box, args.side)
        mean = ImageStat.Stat(crop.convert("L")).mean[0]
        cells.append((box, avatar, px, mean))
        print(f"box {box[0]:.4f},{box[1]:.4f},{box[2]:.4f},{box[3]:.4f}"
              f"  -> {px[2] - px[0]}x{px[3] - px[1]}px source"
              f"  side {px[2] - px[0]}px  mean lum {mean:.0f}")

    gap = 20
    sheet = Image.new("RGB", (args.side * len(cells) + gap * (len(cells) - 1),
                              args.side + 30), (20, 20, 22))
    d = ImageDraw.Draw(sheet)
    font = ac.resolve_font(12)
    for i, (box, avatar, px, mean) in enumerate(cells):
        x = i * (args.side + gap)
        sheet.paste(avatar, (x, 0))
        d.text((x + 3, args.side + 6),
               f"{px[2] - px[0]}px  L{mean:.0f}", font=font, fill=(205, 205, 205))

    out = args.out or f"/tmp/box_{stem}.png"
    sheet.save(out)
    print(f"wrote {out}")
    if any(c[3] < 55 for c in cells):
        print("[note] a crop is dark (mean lum < 55): at avatar size the face may not read; "
              "try the same character in another zone or a better-lit box.")


if __name__ == "__main__":
    main()
