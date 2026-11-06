#!/usr/bin/env python3
"""v1.2.0 — the official "fewer illustrations than cells" fallback.

In v1.1.1 a build that only paid for four AI illustrations filled the other eight cells
with hand-written flat paper geometry. The cards had no words and no numbers; stitch saw
eight PNG files and reported `placeholder: 0`. That is not a fallback, it is a way of
hiding an empty cell.

This script renders a **rule card** instead: the cell's caption plus the facts already
declared in `meta.key_facts`, printed by code. No number is invented here — a fact that
cannot point at `caption_source` / `key_facts[].source` never reaches the image. The
model is not involved at all, which is also why financial products can use it: the
figures come from the client's own clause text, not from a generated picture.

Usage
  python3 make_rule_card.py build/blueprint.json -d build/tiles
  python3 make_rule_card.py build/blueprint.json -d build/tiles --only z_r1c2,z_r2c3
  python3 make_rule_card.py build/blueprint.json -d build/tiles --size 1024

Only cells with `tile_origin: code_card` (or explicitly named by --only) are written.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

KIND_LABEL = {
    "number": "数字", "condition": "条件", "boundary": "边界",
    "evidence": "条款原文", "object": "物件", "action": "动作",
}
KIND_INK = {
    "number": (153, 60, 29), "condition": (15, 110, 86),
    "boundary": (133, 56, 46), "evidence": (24, 68, 124),
    "object": (95, 94, 90), "action": (95, 94, 90),
}
PAPER = (247, 242, 232)
PAPER_DEEP = (238, 230, 216)
WHITE = (255, 253, 247)
INK = (43, 38, 34)
INK_SOFT = (110, 104, 96)
ROW_ACCENT = [(122, 156, 148), (190, 110, 75), (196, 166, 100), (122, 132, 176), (170, 140, 120)]


def _wrap(draw_text, font, width):
    return pc.wrap_text(draw_text, font, width)


def _chip(d, x, y, text, font, fill, ink=WHITE):
    tw = pc.text_w(text, font)
    th = pc.text_h("字测", font)
    pad = int(font.size * 0.55)
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + th + pad], radius=int(th * 0.35),
                        fill=fill)
    d.text((x + pad, y + pad // 2), text, font=font, fill=ink)
    return tw + pad * 2


def render_card(zone, facts, size=1024, row=1):
    """One square tile. The bottom 18% stays clear for stitch.py's caption plate."""
    S = size
    k = S / 1024.0
    im = Image.new("RGB", (S, S), PAPER)
    d = ImageDraw.Draw(im)
    accent = ROW_ACCENT[(int(row) - 1) % len(ROW_ACCENT)]

    def P(v):
        return int(v * k)

    frame = (P(100), P(150), P(924), P(742))
    d.rounded_rectangle([frame[0] + P(14), frame[1] + P(16),
                         frame[2] + P(14), frame[3] + P(16)],
                        radius=P(28), fill=PAPER_DEEP)
    d.rounded_rectangle(list(frame), radius=P(28), fill=WHITE, outline=INK, width=P(6))
    d.rounded_rectangle([frame[0] + P(6), frame[1] + P(6),
                         frame[2] - P(6), frame[1] + P(78)],
                        radius=P(20), fill=accent)
    d.rectangle([frame[0] + P(6), frame[1] + P(58),
                 frame[2] - P(6), frame[1] + P(80)], fill=accent)

    f_tag = pc.load_font(max(10, P(30)), "bold")
    d.text((frame[0] + P(30), frame[1] + P(20)), "规则解读 / RULE", font=f_tag, fill=WHITE)
    f_zone = pc.load_font(max(9, P(24)), "regular")
    zt = zone.get("id", "")
    d.text((frame[2] - P(30) - pc.text_w(zt, f_zone), frame[1] + P(26)), zt,
           font=f_zone, fill=WHITE)

    # The caption is the one line the reader already sees on the plate. On the card it
    # is the heading, and the facts underneath are the reason that line is true.
    x0, y = frame[0] + P(40), frame[1] + P(110)
    avail = frame[2] - frame[0] - P(80)
    f_head, _ = pc.fit_text_to_box(zone.get("caption") or "", avail, P(120), "bold",
                                   hi=P(56), lo=P(30), pad_x=0, pad_y=0)
    for line in _wrap(zone.get("caption") or "", f_head, avail)[:2]:
        d.text((x0, y), line, font=f_head, fill=INK)
        y += pc.text_h("字测", f_head) * 1.25
    y += P(14)
    d.line([(x0, y), (frame[2] - P(40), y)], fill=INK_SOFT, width=max(1, P(2)))
    y += P(24)

    f_kind = pc.load_font(max(10, P(24)), "bold")
    f_text = pc.load_font(max(11, P(34)), "regular")
    f_src = pc.load_font(max(9, P(20)), "regular")
    line_h = pc.text_h("字测", f_text) * 1.30
    src_lines = []
    rows = []
    for f in facts[:3]:
        kind = f.get("kind") or "condition"
        rows.append((KIND_LABEL.get(kind, kind), KIND_INK.get(kind, INK_SOFT),
                     _wrap(f.get("text") or "", f_text,
                           max(10, frame[2] - P(40) - x0 - P(150)))[:2]))
        src = (f.get("source") or "").replace("client-confirmed:", "")
        if src:
            src_lines.append(src)

    # Two facts in a 592px panel otherwise leave a void in the lower half — the card
    # would be "a card with words" instead of an information surface. Lay the rows out
    # as a checklist and centre the whole block in the available height.
    row_h = max(P(104), 2 * line_h + P(26))
    area_top, area_bot = y, frame[3] - P(86)
    total = min(len(rows) * row_h, max(0, area_bot - area_top))
    cy = area_top + max(0, (area_bot - area_top - total) // 2)
    for label, ink, lines in rows:
        if cy + row_h > area_bot + P(4):
            break
        cw = _chip(d, x0, cy + P(12), label, f_kind, ink)
        tx = x0 + cw + P(20)
        ty = cy + P(8)
        for ln in lines:
            d.text((tx, ty), ln, font=f_text, fill=INK)
            ty += line_h
        d.line([(x0, cy + row_h - P(10)), (frame[2] - P(40), cy + row_h - P(10))],
               fill=PAPER_DEEP, width=max(1, P(2)))
        cy += row_h

    if src_lines:
        sy = frame[3] - P(56)
        d.line([(x0, sy - P(12)), (frame[2] - P(40), sy - P(12))],
               fill=PAPER_DEEP, width=max(1, P(2)))
        note = "事实来源：" + "；".join(dict.fromkeys(src_lines))
        for ln in _wrap(note, f_src, avail)[:1]:
            d.text((x0, sy), ln, font=f_src, fill=INK_SOFT)

    # A quiet plinth, same as the illustrated cells, keeps the card from floating.
    d.ellipse((P(140), P(748), P(884), P(806)), fill=PAPER_DEEP)
    return im


def main():
    ap = argparse.ArgumentParser(description="promo-atlas v1.2: code-drawn rule cards")
    ap.add_argument("blueprint")
    ap.add_argument("-d", "--tiles", default="tiles", help="tile directory")
    ap.add_argument("--only", default="", help="comma-separated zone ids (default: all code_card)")
    ap.add_argument("--size", type=int, default=1024, help="tile edge in px")
    args = ap.parse_args()

    bp_path = os.path.abspath(args.blueprint)
    base = os.path.dirname(bp_path)
    bp = pl.load(bp_path)
    tiles = args.tiles if os.path.isabs(args.tiles) else os.path.join(base, args.tiles)
    pc.ensure_dir(tiles)
    facts = pl.facts_of(bp)
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    written, skipped = [], []
    for z in bp["zones"]:
        chosen = z["id"] in only if only else (z.get("tile_origin") == "code_card")
        if not chosen:
            continue
        items = [facts[i] for i in pl.zone_fact_ids(z) if i in facts]
        if not items:
            print("  ✗ %s: 没有 facts，拒绝生成空白卡（先补 blueprint）" % z["id"],
                  file=sys.stderr)
            return 1
        img = render_card(z, items, size=args.size, row=int(z.get("row", 1)))
        path = os.path.join(tiles, z["id"] + ".png")
        img.save(path)
        written.append((z["id"], [i.get("text") for i in items]))
    for zid, lines in written:
        print("%s -> %s" % (zid, " / ".join(lines)))
    print("规则卡 %d 张，跳过 %d 格，目录 %s" % (len(written), len(skipped), tiles))
    print("下一步：audit_assets.py --init 重新绑定 hash，再逐格填 information 轴。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
