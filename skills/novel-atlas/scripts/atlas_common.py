#!/usr/bin/env python3
"""Shared geometry, typography and contrast helpers for the novel-atlas scripts."""

import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]

PRIMITIVE_COLORS = {
    "timeline_spine": (196, 148, 74),
    "relational_web": (96, 148, 168),
    "genealogy_tree": (128, 156, 108),
    "event_cloud": (168, 116, 148),
    "concentric_rings": (172, 132, 96),
    "confrontation_board": (176, 92, 78),
    "parallel_tracks": (110, 126, 172),
}

BLACK_TEXT = (18, 18, 18)
WHITE_TEXT = (245, 242, 236)

# Default annotation treatment: every label sits on its own opaque plate, black on white,
# below the thing it names. Measured scrims (`meta.label_plate: "tone"`) are still available,
# but they are the exception: a label that has to win a contrast fight with the artwork is a
# label that disappears the first time the picture is viewed at 25%.
PLATE_BG = (255, 255, 255)
PLATE_INK = (23, 22, 21)
PLATE_BORDER = (23, 22, 21, 48)


# ------------------------------------------------------------------ blueprint

def load_blueprint(path):
    with open(path, encoding="utf-8") as f:
        bp = json.load(f)
    meta = bp.setdefault("meta", {})
    canvas = meta.setdefault("canvas", {})
    canvas.setdefault("cols", 4)
    canvas.setdefault("rows", 3)
    canvas.setdefault("cell", 2048)
    canvas.setdefault("bleed", 0.08)
    meta.setdefault("title", "Novel Atlas")
    meta.setdefault("subtitle", "")
    meta.setdefault("style_id", "unspecified")
    bp.setdefault("palette", {})
    bp.setdefault("zones", [])
    bp.setdefault("characters", [])
    bp.setdefault("events", [])
    bp.setdefault("primitives", [])
    return bp


def canvas_size(bp):
    c = bp["meta"]["canvas"]
    return c["cols"] * c["cell"], c["rows"] * c["cell"]


def zone_rect(zone, cell):
    return (
        int(zone.get("col", 0)) * cell,
        int(zone.get("row", 0)) * cell,
        int(zone.get("w", 1)) * cell,
        int(zone.get("h", 1)) * cell,
    )


def zone_by_id(bp):
    return {z["id"]: z for z in bp["zones"]}


def chars_by_id(bp):
    return {c["id"]: c for c in bp.get("characters", [])}


def find_zone_at(bp, col, row):
    for z in bp["zones"]:
        if (int(z.get("col", 0)) <= col < int(z.get("col", 0)) + int(z.get("w", 1))
                and int(z.get("row", 0)) <= row < int(z.get("row", 0)) + int(z.get("h", 1))):
            return z
    return None


# ------------------------------------------------------------------ typography

_font_cache = {}


def resolve_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[key] = font
                return font
            except OSError:
                continue
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def text_width(draw, text, font):
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_cjk(draw, text, font, max_width):
    """Wrap mixed CJK/latin text by measured width. Keeps latin words intact."""
    lines, line = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(line)
            line = ""
            continue
        probe = line + ch
        if text_width(draw, probe, font) <= max_width or not line:
            line = probe
        else:
            if ch.isascii() and ch not in " ,.;:!?)]}" and " " in line:
                head, _, tail = line.rpartition(" ")
                lines.append(head)
                line = tail + ch
            else:
                lines.append(line)
                line = ch
    if line:
        lines.append(line)
    return lines


# ------------------------------------------------------------------ title block

def cartouche_geometry(bp, cell, W, H, draw):
    """Where the title block lands, worked out before anything else is drawn.

    Two tools need this number and they must agree. `stitch.py` paints the block last, on
    top of the artwork, so its footprint has to be known before the label pass or every
    label it lands on gets sliced in half. `skeleton.py` has to show the same footprint at
    Gate 2 — otherwise the layout the user approves is a layout without a title block, and
    the collision only surfaces after every tile has been paid for.

    Measure at the atlas's real `cell`, never at preview scale, then scale the rect: text
    wrapped at 420px does not break in the same places as text wrapped at 2048px.
    """
    pad = int(cell * 0.030)
    f_title = resolve_font(int(cell * 0.038))
    f_sub = resolve_font(int(cell * 0.0165))
    f_body = resolve_font(int(cell * 0.0145))
    f_small = resolve_font(int(cell * 0.0125))

    cov = bp.get("coverage", {})
    t1 = len([c for c in bp.get("characters", []) if c.get("tier") == "T1"])
    t2 = len([e for e in bp.get("events", []) if e.get("tier") == "T2"])
    body_lines = [
        f"覆盖 {len(cov.get('chapters_covered', []))}/{cov.get('chapters_total', '?')} 章"
        f"   ·   转折 {cov.get('turning_covered', '?')}/{cov.get('turning_total', '?')}"
        f"   ·   T1 {t1} / T2 {t2}",
        "画风 " + str(bp["meta"].get("style_id", "?")) + "   ·   "
        + "  ".join(str(p.get("id")) for p in bp.get("primitives", [])),
    ]
    miss = cov.get("chapters_missing") or []
    if miss:
        body_lines.append("省略章节 " + ", ".join(str(m) for m in miss[:18])
                          + (" 等" if len(miss) > 18 else ""))
    miss_t = cov.get("turning_missing") or []
    if miss_t:
        body_lines.append("省略转折 " + "；".join(str(t) for t in miss_t[:2]))

    cw = int(min(W * 0.40, cell * 1.70))
    inner = cw - pad * 2
    wrapped = []
    for i, line in enumerate(body_lines):
        font = f_body if i == 0 else f_small
        lh = int(font.size * 1.55)
        for sub_line in wrap_cjk(draw, line, font, inner):
            wrapped.append((sub_line, font, i == 0, lh))

    ch_ = (pad + int(f_title.size * 1.35)
           + (int(f_sub.size * 1.6) if bp["meta"].get("subtitle") else 0)
           + pad // 2 + sum(w[3] for w in wrapped) + pad)
    cx0, cy0 = pad, H - ch_ - pad

    return {"pad": pad, "cw": cw, "ch": ch_, "cx0": cx0, "cy0": cy0,
            "inner": inner, "wrapped": wrapped,
            "f_title": f_title, "f_sub": f_sub, "f_body": f_body, "f_small": f_small,
            "rect": (cx0, cy0, cx0 + cw, cy0 + ch_)}


# ------------------------------------------------------------------ label geometry

def plate_mode(bp):
    """`"white"` (default) or `"tone"` (measured scrim, the pre-0.3 behaviour)."""
    v = str((bp.get("meta") or {}).get("label_plate", "white")).lower()
    return "tone" if v in ("tone", "tonal", "scrim") else "white"


def text_box(draw, text, px, py, size, anchor="lt"):
    """The plate a string occupies, and where its glyphs start.

    One implementation, because Gate 2 and the stitcher have to agree on this or the layout
    the user approves is not the layout that ships. Anchors:
      lt  left-top      — plate grows right and down from the point
      ct  centre-top    — horizontally centred on the point, grows down
      cb  centre-below  — centred under the point, with a gap: the default, so a label
                          hangs beneath its subject instead of sitting on top of it
      lm  left-middle   — vertically centred on the point, grows right
      rm  right-middle  — vertically centred on the point, grows left
    """
    size = max(10, int(round(size)))
    font = resolve_font(size)
    tw = text_width(draw, text, font)
    th = int(size * 1.32)
    pad_x, pad_y = int(round(size * 0.42)), int(round(size * 0.22))
    gap = int(round(size * 0.45))
    if anchor == "ct":
        x0, y0 = px - tw / 2.0, py
    elif anchor == "cb":
        x0, y0 = px - tw / 2.0, py + gap
    elif anchor == "lm":
        x0, y0 = px, py - th / 2.0
    elif anchor == "rm":
        x0, y0 = px - tw, py - th / 2.0
    else:
        x0, y0 = px, py
    box = (int(x0 - pad_x), int(y0 - pad_y),
           int(x0 + tw + pad_x), int(y0 + th + pad_y))
    return {"box": box, "text_pos": (int(x0), int(y0)), "font": font, "size": size,
            "tw": tw, "th": th, "pad_x": pad_x, "pad_y": pad_y}



def _anchor_box(draw, text, px, py, size, anchor):
    return text_box(draw, text, px, py, size, anchor)["box"]


def zone_caption_geometry(bp, zone, cell, draw, avoid=None):
    """A zone's name and caption as one plate under the picture.

    The caption is part of the layout, not an afterthought: it is the one piece of
    editorial prose the reader sees, and it is painted on the same artwork as everything
    else. `meta.zone_caption_side` selects `"bottom"` (default — the plate hangs below the
    picture, the way a caption belongs under a plate) or `"top"` (the old header band).

    `avoid` is the title block's rect. A caption that lands under it would be painted over,
    so it flips to the top of its zone and says so (`flipped`), rather than colliding with
    the one block on the canvas that is guaranteed to be painted last. Both the skeleton and
    the stitcher call this with the same rect, so the band the user approves at Gate 2 is
    the band that ships.
    """
    x, y, w, h = zone_rect(zone, cell)
    f_name = resolve_font(max(10, int(round(62 * cell / 2048.0))))
    f_cap = resolve_font(max(10, int(round(30 * cell / 2048.0))))
    pad_x = int(round(f_name.size * 0.42))
    pad_y = int(round(f_name.size * 0.22))
    margin = int(round(w * 0.022))
    max_text_w = int(w * 0.78) - 2 * pad_x

    lines = []
    if zone.get("name") and not zone.get("hide_name"):
        lines.append((str(zone["name"]), f_name, "name"))
    if zone.get("caption"):
        for sub in wrap_cjk(draw, str(zone["caption"]), f_cap, max_text_w)[:3]:
            lines.append((sub, f_cap, "caption"))
    if not lines:
        return None

    block_w = max(text_width(draw, t, f) for t, f, _ in lines) + 2 * pad_x
    line_h = [int(f.size * (1.34 if kind == "name" else 1.52)) for _, f, kind in lines]
    total_h = sum(line_h) + 2 * pad_y

    side = str(zone.get("caption_side")
               or (bp.get("meta") or {}).get("zone_caption_side", "bottom")).lower()
    left = x + margin
    top = (y + margin) if side == "top" else (y + h - margin - total_h)
    rect = (left, top, left + block_w, top + total_h)

    flipped = False
    if avoid is not None and side != "top" and rects_overlap(rect, tuple(avoid)):
        top = y + margin
        rect = (left, top, left + block_w, top + total_h)
        flipped = True

    placed = []
    cy = top + pad_y
    for (text, font, kind), lh in zip(lines, line_h):
        placed.append((text, font, kind, cy))
        cy += lh

    return {"rect": rect, "lines": placed, "pad": pad_x, "side": side, "flipped": flipped}


def cartouche_rect(bp, cell, draw=None):
    """The title block's footprint at this cell, for callers that must steer around it."""
    W, H = canvas_size(bp)
    d = draw or ImageDraw.Draw(Image.new("RGB", (4, 4)))
    return cartouche_geometry(bp, cell, W, H, d)["rect"]



def event_label_pos(draw, text, ex, ey, cell, zrect, avoid=None, taken=None, prefer="below"):
    """Where an event's label goes. First fit wins: below, above, right, left.

    Below is the default because a label above the dot covers the thing the dot is pointing
    at. But a dense cluster of events — or a legend block at the bottom of the panel — can
    leave no room below and no room above, and the honest answer there is the side, not a
    second overlap. `label_side` on the event puts one side first; the rest stay as fallbacks.

    The dot stays the anchor in every case; only the side the plate hangs on changes, so the
    leader line still points at something. `avoid` / `taken` are rects (or lists of them) the
    plate must not land on: the zone caption, the title block, and the plates already placed.
    """
    size = cell * 0.020
    r = cell * 0.016
    gap = int(round(size * 0.30))
    th = int(size * 1.32)
    zx, zy, zw, zh = zrect
    blocks = _as_rects(avoid) + _as_rects(taken)

    sides = {
        "below": (ex, ey + r + gap, "cb"),
        "above": (ex, ey - r - gap - th, "ct"),
        "right": (ex + r + gap, ey, "lm"),
        "left": (ex - r - gap, ey, "rm"),
    }
    order = [prefer] + [k for k in ("below", "above", "right", "left") if k != prefer]

    fallback = None
    for side in order:
        if side not in sides:
            continue
        px, py, anchor = sides[side]
        box = text_box(draw, text, px, py, size, anchor)["box"]
        if fallback is None:
            fallback = (px, py, anchor)
        inside = (box[0] >= zx and box[2] <= zx + zw
                  and box[1] >= zy and box[3] <= zy + zh)
        if inside and not any(rects_overlap(box, b) for b in blocks):
            return px, py, anchor
    return fallback


def _as_rects(value):
    if not value:
        return []
    if isinstance(value[0], (list, tuple)):
        return [tuple(r) for r in value]
    return [tuple(value)]


def label_boxes(bp, cell):
    """Every text plate the stitcher will paint, in atlas pixels.

    These formulas live in one place because preview and output have to agree. When
    `skeleton.py` measured its own approximations at preview scale it both invented
    collisions (two labels 93px apart) and missed real ones (a name plate sitting on an
    event's tail), so Gate 2 approved a layout the stitcher then broke.

    Returns [(zone_id, kind, text, rect)], kind ∈ caption/label/event/name.
    """
    draw = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    out = []
    cart = cartouche_rect(bp, cell, draw)

    for z in bp["zones"]:
        x, y, w, h = zone_rect(z, cell)
        cap = zone_caption_geometry(bp, z, cell, draw, avoid=cart)
        if cap:
            out.append((z["id"], "caption",
                        " / ".join(str(t) for t, _, _, _ in cap["lines"]), cap["rect"]))
        for lb in z.get("labels") or []:
            text = str(lb.get("text", ""))
            if not text:
                continue
            out.append((z["id"], "label", text,
                        _anchor_box(draw, text,
                                    x + float(lb.get("x", 0.5)) * w,
                                    y + float(lb.get("y", 0.5)) * h,
                                    float(lb.get("size", 40)) * cell / 2048.0,
                                    lb.get("anchor", "cb"))))

    chidx = chars_by_id(bp)
    for z in bp["zones"]:
        x, y, w, h = zone_rect(z, cell)
        for cid in z.get("characters") or []:
            ch = chidx.get(cid) or {}
            box = (ch.get("portrait") or {}).get("box")
            if not box or len(box) != 4:
                continue
            bx, by = x + float(box[0]) * w, y + float(box[1]) * h
            bw, bh = float(box[2]) * w, float(box[3]) * h
            name = str(ch.get("name", cid))
            out.append((z["id"], "name", name,
                        _anchor_box(draw, name, bx + bw * 0.5, by + bh + cell * 0.012,
                                    30 * cell / 2048.0, "ct")))
        for slot in z.get("avatar_slots") or []:
            ch = chidx.get(slot.get("character")) or {}
            size = max(24, int(float(slot.get("size", 0.08)) * min(w, h)))
            cx = x + float(slot.get("x", 0.5)) * w
            cy = y + float(slot.get("y", 0.5)) * h
            name = str(ch.get("name", slot.get("character")))
            out.append((z["id"], "name", name,
                        _anchor_box(draw, name, cx, cy + size / 2 + cell * 0.010,
                                    26 * cell / 2048.0, "ct")))

    # Events last: which side a label hangs on depends on what is already on the panel,
    # so they are placed against the plates above rather than in blueprint order alone.
    zones = zone_by_id(bp)
    taken = [r[3] for r in out]
    for e in bp.get("events", []):
        z = zones.get(e.get("zone"))
        if not z:
            continue
        zrect = zone_rect(z, cell)
        ex = zrect[0] + float(e.get("x", 0.5)) * zrect[2]
        ey = zrect[1] + float(e.get("y", 0.5)) * zrect[3]
        text = str(e.get("label", ""))
        zc = zone_caption_geometry(bp, z, cell, draw, avoid=cart)
        avoid = [cart] + ([zc["rect"]] if zc else [])
        px, py, anchor = event_label_pos(draw, text, ex, ey, cell, zrect, avoid, taken,
                                       e.get("label_side", "below"))
        box = _anchor_box(draw, text, px, py, cell * 0.020, anchor)
        out.append((z["id"], "event", text, box))
        taken.append(box)
    return out


def rects_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


# ------------------------------------------------------------------ contrast

def _channel(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(rgb_a, rgb_b):
    la, lb = luminance(rgb_a), luminance(rgb_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mean_rgb(image, box):
    """Mean colour of a region, clipped to the image."""
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(image.width, x1), min(image.height, y1)
    if x1 <= x0 or y1 <= y0:
        return (128, 128, 128)
    region = image.crop((x0, y0, x1, y1)).convert("RGB")
    region = region.resize((1, 1), Image.BOX)
    return region.getpixel((0, 0))


def best_text_color(backdrop):
    if contrast_ratio(backdrop, BLACK_TEXT) >= contrast_ratio(backdrop, WHITE_TEXT):
        return BLACK_TEXT, (255, 255, 255)
    return WHITE_TEXT, (0, 0, 0)


def worst_case_rgb(image, box, text_rgb, grid=(7, 3)):
    """The pixel under a label that is hardest for the text to sit on.

    Mean luminance is not enough: a label centred on a mid-tone patch can still be crossed by
    white highlights. Scrim strength is driven by the worst patch, not the average one.
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(image.width, x1), min(image.height, y1)
    if x1 <= x0 or y1 <= y0:
        return (128, 128, 128)
    region = image.crop((x0, y0, x1, y1)).convert("RGB").resize(grid, Image.BOX)
    worst, worst_ratio = None, 99.0
    for y in range(grid[1]):
        for x in range(grid[0]):
            px = region.getpixel((x, y))
            r = contrast_ratio(px, text_rgb)
            if r < worst_ratio:
                worst, worst_ratio = px, r
    return worst or (128, 128, 128)


def mix(rgb, target, alpha):
    return tuple(int(round(c * (1 - alpha) + t * alpha)) for c, t in zip(rgb[:3], target[:3]))


def scrim_to_reach(backdrop, text_rgb, floor=4.5, toward=(0, 0, 0), steps=17):
    """Return (alpha, colour) of a scrim over backdrop so text reaches the contrast floor."""
    for i in range(steps):
        alpha = i / (steps - 1)
        trial = mix(backdrop, toward, alpha)
        if contrast_ratio(trial, text_rgb) >= floor:
            return alpha, trial
    return 1.0, mix(backdrop, toward, 1.0)


def reach_on(backdrop, colour, toward=(255, 255, 255), floor=4.5, steps=20):
    """Push a colour toward `toward` until it clears `floor` against `backdrop`.

    Used for secondary text that must be dimmer than the primary ink but still legal —
    the dimmer tone is a design choice, the floor is not.
    """
    if contrast_ratio(backdrop, colour) >= floor:
        return colour
    for i in range(1, steps + 1):
        trial = mix(colour, toward, i / float(steps))
        if contrast_ratio(backdrop, trial) >= floor:
            return trial
    return tuple(toward[:3])


def hex_to_rgb(value, fallback=(24, 24, 24)):
    if not value:
        return fallback
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        return fallback
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback
