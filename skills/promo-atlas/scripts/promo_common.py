#!/usr/bin/env python3
"""Shared geometry, typography and compositing helpers for the promo-atlas scripts.

Everything positional in this skill is derived from one Grid object, so the skeleton
preview, the stitcher and the copy linter cannot disagree about where a plate sits.
If two scripts need a rectangle, it is computed here exactly once.
"""

import hashlib
import json
import math
import os
import re

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

# (path, index, weight) — first working candidate wins.
FONT_CANDIDATES = [
    ("/System/Library/Fonts/PingFang.ttc", 2, "bold"),
    ("/System/Library/Fonts/PingFang.ttc", 0, "regular"),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2, "bold"),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0, "regular"),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 1, "bold"),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0, "regular"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0, "bold"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0, "regular"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0, "regular"),
    ("C:/Windows/Fonts/msyhbd.ttc", 0, "bold"),
    ("C:/Windows/Fonts/msyh.ttc", 0, "regular"),
]

_FONT_CACHE = {}


def load_font(size, weight="regular"):
    """Return a CJK-capable font at `size`. Falls back to regular if bold is absent."""
    key = (int(size), weight)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    order = [c for c in FONT_CANDIDATES if c[2] == weight] + [
        c for c in FONT_CANDIDATES if c[2] != weight
    ]
    last_err = None
    for path, index, _w in order:
        try:
            font = ImageFont.truetype(path, int(size), index=index)
            _FONT_CACHE[key] = font
            return font
        except Exception as exc:  # noqa: BLE001 - any font failure just moves on
            last_err = exc
    raise RuntimeError("no CJK-capable font found; install Noto Sans CJK. last error: %s" % last_err)


# ---------------------------------------------------------------------------
# Palette (cartoon_flat preset; see references/cartoon-style.md)
# ---------------------------------------------------------------------------

PAPER = (247, 242, 232)
PAPER_DEEP = (238, 230, 216)
INK = (43, 38, 34)
INK_SOFT = (96, 88, 80)
ACCENT = (211, 84, 60)
ACCENT_ALT = (52, 106, 138)
TILE_MISSING = (226, 216, 200)
TILE_MISSING_INK = (168, 154, 134)

PLATE_BG = (255, 255, 255)
PLATE_INK = (23, 22, 21)
PLATE_BORDER = (23, 22, 21)

# Row tints for the skeleton preview: same family, different value, so the matrix
# reads as rows without pretending to be artwork.
ROW_TINTS = [
    (236, 226, 210),
    (228, 233, 226),
    (232, 224, 233),
    (234, 231, 218),
    (225, 230, 234),
]


def hex_rgb(s, default=None):
    if not s:
        return default
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def rgb_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


# ---------------------------------------------------------------------------
# Text measurement and plates
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9%\.\-+/:@#&']+|\s+|.", re.UNICODE)


def text_w(text, font):
    if not text:
        return 0
    box = font.getbbox(text)
    return box[2] - box[0]


def text_h(text, font):
    box = font.getbbox(text or "字")
    return box[3] - box[1]


def wrap_text(text, font, max_w):
    """Wrap CJK by character, latin by word. Never returns an empty list for non-empty text."""
    text = (text or "").strip()
    if not text:
        return []
    if max_w <= 4:
        return [text]
    lines, cur = [], ""
    for tok in _TOKEN_RE.findall(text):
        trial = cur + tok
        if cur and text_w(trial, font) > max_w:
            lines.append(cur.rstrip())
            cur = tok.lstrip()
        else:
            cur = trial
    if cur.strip():
        lines.append(cur.rstrip())
    # A single token longer than max_w is broken by force rather than overflowing the plate.
    out = []
    for line in lines:
        while text_w(line, font) > max_w and len(line) > 1:
            cut = len(line) - 1
            while cut > 1 and text_w(line[:cut], font) > max_w:
                cut -= 1
            out.append(line[:cut])
            line = line[cut:]
        out.append(line)
    return [l for l in out if l != ""] or [text]


def measure_plate(text, font, max_w, pad_x=14, pad_y=10, line_gap=1.28, max_lines=None):
    """Measure a white plate for `text` without drawing. Returns (w, h, lines)."""
    lines = wrap_text(text, font, max_w - 2 * pad_x)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    lh = text_h("字测", font) * line_gap
    w = max((text_w(l, font) for l in lines), default=0) + 2 * pad_x
    h = (len(lines) * lh if lines else text_h("字", font)) + 2 * pad_y
    return int(math.ceil(w)), int(math.ceil(h)), lines


def draw_plate(draw, xy, text, font, max_w, pad_x=14, pad_y=10, line_gap=1.28,
               align="left", bg=PLATE_BG, ink=PLATE_INK, radius=None,
               border=PLATE_BORDER, border_w=2, max_lines=None):
    """Draw an opaque white plate with black text. Returns (rect, lines).

    A plate, not a scrim: contrast is 18:1 by construction, so legibility is a fact
    rather than a bet against whatever artwork ended up underneath.
    """
    w, h, lines = measure_plate(text, font, max_w, pad_x, pad_y, line_gap, max_lines)
    x, y = int(xy[0]), int(xy[1])
    r = int(radius if radius is not None else min(w, h) * 0.12)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=bg,
                           outline=border if border_w else None, width=border_w)
    lh = text_h("字测", font) * line_gap
    ty = y + pad_y
    for line in lines:
        lw = text_w(line, font)
        tx = x + pad_x if align == "left" else x + (w - lw) // 2
        draw.text((tx, ty), line, font=font, fill=ink)
        ty += lh
    return (x, y, w, h), lines


def fit_text_to_box(text, max_w, max_h, weight="regular", hi=40, lo=12, pad_x=14, pad_y=10,
                    line_gap=1.28):
    """Largest font size at which `text` still fits the given box. Returns (font, lines)."""
    size = max(lo, int(hi))
    best = (load_font(lo, weight), wrap_text(text, load_font(lo, weight), max(16, max_w - 2 * pad_x)))
    while size >= lo:
        font = load_font(size, weight)
        lines = wrap_text(text, font, max(16, max_w - 2 * pad_x))
        lh = text_h("字测", font) * line_gap
        if len(lines) * lh + 2 * pad_y <= max_h and all(
                text_w(l, font) <= max_w - 2 * pad_x for l in lines):
            return font, lines
        size -= 1
    return best


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------


class Grid:
    """Composes the poster: header strip, timeline band, column headers, row labels,
    matrix cells, footer strip. All sizes are ratios of `cell`, so a target render is
    the same layout at a different cell size — never a crop of the master.
    """

    def __init__(self, cols, rows, cell=2048, cell_h=None, gutter_ratio=0.016, pad_ratio=0.035,
                 row_label_ratio=0.0, header_ratio=0.0, footer_ratio=0.0,
                 band=False, col_header_ratio=0.0, caption_ratio=0.135,
                 pads=None):
        self.cols = int(cols)
        self.rows = int(rows)
        self.cell = int(cell)
        # Cells may be taller than wide for a vertical channel. The artwork is still
        # generated square and cover-cropped, which is why the prompt must keep the
        # subject centred with side margin (see references/cartoon-style.md).
        self.cell_h = int(cell_h or cell)
        self.gutter = int(round(cell * gutter_ratio))
        base_pad = int(round(cell * pad_ratio))
        self.pad = base_pad
        # Social platforms lay their own UI over the image: a like button on the right,
        # a caption bar along the bottom. Padding is asymmetric so the poster can keep
        # its title and its risk disclosure out of that furniture.
        p = pads or {}
        self.pad_l = int(p.get("left", base_pad))
        self.pad_r = int(p.get("right", base_pad))
        self.pad_t = int(p.get("top", base_pad))
        self.pad_b = int(p.get("bottom", base_pad))
        self.row_label_w = int(round(cell * row_label_ratio)) if row_label_ratio else 0
        self.header_h = int(round(cell * header_ratio)) if header_ratio else 0
        self.footer_h = int(round(cell * footer_ratio)) if footer_ratio else 0
        self.band_h = int(round(cell * 0.62)) if band else 0
        self.col_header_h = int(round(cell * col_header_ratio)) if col_header_ratio else 0
        self.caption_h = int(round(self.cell_h * caption_ratio))

        g = self.gutter
        content_w = self.cols * self.cell + (self.cols - 1) * g
        if self.row_label_w:
            content_w += self.row_label_w + g
        self.content_w = content_w
        self.width = self.pad_l + content_w + self.pad_r

        y = self.pad_t
        self.header_rect = None
        if self.header_h:
            self.header_rect = (self.pad_l, y, content_w, self.header_h)
            y += self.header_h + g
        self.band_rect = None
        x0 = self.pad_l + (self.row_label_w + g if self.row_label_w else 0)
        if self.band_h:
            self.band_rect = (x0, y, self.width - x0 - self.pad_r, self.band_h)
            y += self.band_h + g
        self.col_header_rects = []
        if self.col_header_h:
            for j in range(self.cols):
                self.col_header_rects.append(
                    (x0 + j * (self.cell + g), y, self.cell, self.col_header_h))
            y += self.col_header_h + g

        self.grid_top = y
        self.row_label_rects = []
        self.zone_rects = {}
        y_next = y
        for i in range(self.rows):
            ry = y + i * (self.cell_h + g)
            if self.row_label_w:
                self.row_label_rects.append((self.pad_l, ry, self.row_label_w, self.cell_h))
            for j in range(self.cols):
                cx = x0 + j * (self.cell + g)
                self.zone_rects[(i, j)] = (cx, ry, self.cell, self.cell_h)
            y_next = ry + self.cell_h
        y = y_next + g
        self.footer_rect = None
        if self.footer_h:
            self.footer_rect = (self.pad_l, y, content_w, self.footer_h)
            y += self.footer_h
        self.height = y + self.pad_b

        # Image area inside a cell: the caption plate gets its own reserved strip so a
        # caption can never land on artwork.
        self.zone_image_h = self.cell_h - self.caption_h

    # -- lookups ---------------------------------------------------------
    def zone_rect(self, row, col):
        return self.zone_rects[(row, col)]

    def zone_image_rect(self, row, col):
        x, y, w, _h = self.zone_rects[(row, col)]
        return (x, y, w, self.zone_image_h)

    def caption_rect(self, row, col):
        x, y, w, _h = self.zone_rects[(row, col)]
        return (x, y + self.zone_image_h, w, self.caption_h)

    def to_px(self, box, rect):
        """Map a zone-local normalized box [x,y,w,h] onto an absolute rect."""
        rx, ry, rw, rh = rect
        return (int(rx + box[0] * rw), int(ry + box[1] * rh),
                int(box[2] * rw), int(box[3] * rh))

    def describe(self):
        return {
            "width": self.width, "height": self.height, "cell": self.cell,
            "cell_h": self.cell_h,
            "gutter": self.gutter, "pad": self.pad, "cols": self.cols, "rows": self.rows,
            "row_label_w": self.row_label_w, "header_h": self.header_h,
            "band_h": self.band_h, "col_header_h": self.col_header_h,
            "footer_h": self.footer_h, "caption_h": self.caption_h,
            "zone_image_h": self.zone_image_h,
        }


def grid_from_meta(meta, rows=None, cols=None, cell=None):
    gmeta = meta.get("grid", {})
    lay = meta.get("layout", {})
    return Grid(
        cols=cols if cols is not None else gmeta.get("cols"),
        rows=rows if rows is not None else gmeta.get("rows"),
        cell=cell if cell is not None else gmeta.get("cell", 2048),
        gutter_ratio=gmeta.get("gutter_ratio", 0.016),
        pad_ratio=gmeta.get("pad_ratio", 0.035),
        row_label_ratio=lay.get("row_label_ratio", 0.0),
        header_ratio=lay.get("header_ratio", 0.0),
        footer_ratio=lay.get("footer_ratio", 0.0),
        band=lay.get("band", False),
        col_header_ratio=lay.get("col_header_ratio", 0.0),
        caption_ratio=lay.get("caption_ratio", 0.135),
    )


# ---------------------------------------------------------------------------
# Cartoon shadow + asset paste
# ---------------------------------------------------------------------------

SHADOW_MODES = ("hard_ellipse", "hard_oblique", "none")


def draw_cartoon_shadow(canvas, box, mode="hard_ellipse", color=(30, 26, 22), alpha=64):
    """Paint a hard-edged shadow under an asset slot.

    Deliberately not a soft blur: a physically-correct soft shadow belongs to a
    different world's lighting rules and is the single clearest tell that a real
    product photograph was pasted into a drawing. A hard ellipse or a 45 degree
    oblique reads as "this object is in this drawing".
    """
    if mode == "none":
        return
    x, y, w, h = box
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fill = (color[0], color[1], color[2], alpha)
    if mode == "hard_ellipse":
        dy = int(h * 0.055)
        d.ellipse([x + int(w * 0.02), y + h - dy, x + int(w * 0.98), y + h + dy], fill=fill)
    elif mode == "hard_oblique":
        skew = int(h * 0.16)
        pts = [(x + skew, y + h), (x + w + skew, y + h),
               (x + w - skew // 2, y + h + int(h * 0.12)), (x - skew // 2, y + h + int(h * 0.12))]
        d.polygon(pts, fill=fill)
    canvas.alpha_composite(layer)


def paste_asset(canvas, asset_path, box, shadow="hard_ellipse", shadow_alpha=64):
    """Paste a transparent PNG into `box`, scaled to fit while preserving aspect.

    The asset is trimmed to its alpha bounding box first. A product shot delivered with
    40% empty margin would otherwise be pasted at 60% of the slot it was sized for, and
    "the product looks small" would be blamed on the layout instead of the file.
    """
    x, y, w, h = box
    draw_cartoon_shadow(canvas, box, shadow, alpha=shadow_alpha)
    img = Image.open(asset_path).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    sw, sh = img.size
    scale = min(w / sw, h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas.alpha_composite(img, (x + (w - nw) // 2, y + (h - nh) // 2))
    return (x + (w - nw) // 2, y + (h - nh) // 2, nw, nh)


def dashed_rect(draw, rect, color, width=3, dash=18, gap=12, radius=10):
    x, y, w, h = rect
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=color, width=width)


# ---------------------------------------------------------------------------
# Ratio, IO, hashing
# ---------------------------------------------------------------------------


def parse_ratio(s):
    if not s or s in ("auto", "natural"):
        return None
    if ":" in str(s):
        a, b = str(s).split(":", 1)
        return (float(a), float(b))
    return None


def pad_to_ratio(img, ratio, bg=PAPER):
    """Letterbox to the requested aspect. Never crops: cropping removes heads and plates."""
    if not ratio:
        return img, 0.0
    tw, th = ratio
    target = tw / th
    cur = img.width / img.height
    if abs(cur - target) < 0.001:
        return img, 0.0
    if cur < target:
        nw = int(round(img.height * target))
        canvas = Image.new("RGB", (nw, img.height), bg)
        ox = (nw - img.width) // 2
        canvas.paste(img, (ox, 0))
        return canvas, (nw - img.width) / nw
    nh = int(round(img.width / target))
    canvas = Image.new("RGB", (img.width, nh), bg)
    oy = (nh - img.height) // 2
    canvas.paste(img, (0, oy))
    return canvas, (nh - img.height) / nh


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    return path


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, obj):
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(s, fallback="zone"):
    s = re.sub(r"[^\w\-]+", "_", (s or "").strip(), flags=re.UNICODE)
    return (s or fallback).strip("_") or fallback
