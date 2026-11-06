#!/usr/bin/env python3
"""Step 6 — render the atlas, and the skeleton preview, from one code path.

`skeleton.py` imports `render(..., mode="skeleton")` from here. That is deliberate: a
preview produced by a second implementation is a preview that lies, because the only
thing it proves is that the second implementation agrees with itself.

Usage
  python3 stitch.py build/blueprint.json -d build/tiles -o build/atlas.png
  python3 stitch.py build/blueprint.json -d build/tiles -o build/atlas.png --target row_a_01
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402


# ---------------------------------------------------------------------------
# small drawing helpers
# ---------------------------------------------------------------------------


def draw_wrapped(draw, xy, text, font, max_w, fill, line_gap=1.3, max_lines=None, align="left"):
    lines = pc.wrap_text(text, font, max_w)
    if max_lines:
        lines = lines[:max_lines]
    x, y = xy
    lh = pc.text_h("字测", font) * line_gap
    for line in lines:
        lw = pc.text_w(line, font)
        draw.text((x if align == "left" else x + (max_w - lw) / 2, y), line, font=font, fill=fill)
        y += lh
    return y - xy[1]


def chip(draw, xy, text, font, bg, ink, pad_x=None, pad_y=None, radius=None):
    pad_x = pad_x if pad_x is not None else int(font.size * 0.5)
    pad_y = pad_y if pad_y is not None else int(font.size * 0.26)
    w = pc.text_w(text, font) + 2 * pad_x
    h = pc.text_h("字测", font) + 2 * pad_y
    x, y = xy
    r = radius if radius is not None else int(h * 0.34)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=bg)
    draw.text((x + pad_x, y + pad_y - font.getbbox("字")[1]), text, font=font, fill=ink)
    return (x, y, w, h)


def ellipsize(text, font, max_w):
    if pc.text_w(text, font) <= max_w:
        return text
    while text and pc.text_w(text + "…", font) > max_w:
        text = text[:-1]
    return text + "…"


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------


def draw_header(canvas, draw, grid, meta, cell, override=None):
    rect = grid.header_rect
    if not rect:
        return
    x, y, w, h = rect
    draw.rounded_rectangle([x, y, x + w, y + h], radius=int(cell * 0.02), fill=pc.PAPER_DEEP)
    pad = int(cell * 0.035)
    bar_w = int(cell * 0.016)
    draw.rounded_rectangle([x + pad, y + int(h * 0.18), x + pad + bar_w, y + int(h * 0.82)],
                           radius=bar_w // 2, fill=pc.ACCENT)
    head = dict(meta.get("header", {}))
    if override:
        # `k in override`, not `if v`: an explicit empty string means "this slice prints no
        # subtitle here". Filtering on truthiness silently reinstated the master's subtitle
        # on every 0.105-tall page header, where it got clipped mid-glyph — which is why the
        # old build blanked rows[].line2 for the whole blueprint instead.
        head.update({k: v for k, v in override.items() if k in head or v})
    tx = x + pad + bar_w + int(cell * 0.022)
    avail = int(w * 0.66)

    title = head.get("title") or meta.get("campaign", "")
    f_title, _ = pc.fit_text_to_box(title, avail, int(h * 0.50), "bold",
                                    hi=int(min(cell * 0.105, h * 0.40)),
                                    lo=int(cell * 0.05), pad_x=0, pad_y=0)
    ty = y + int(h * 0.16)
    ty += draw_wrapped(draw, (tx, ty), title, f_title, avail, pc.INK, 1.16, max_lines=2)

    sub = head.get("subtitle", "")
    if sub:
        f_sub = pc.load_font(max(11, int(min(cell * 0.040, h * 0.15))), "regular")
        draw_wrapped(draw, (tx, ty + int(h * 0.035)), sub, f_sub, avail, pc.INK_SOFT, 1.25, 2)

    meta_line = head.get("meta_line", "")
    if meta_line:
        f_m = pc.load_font(max(10, int(cell * 0.034)), "regular")
        lines = pc.wrap_text(meta_line, f_m, int(w * 0.26))
        my = y + int(h * 0.20)
        for line in lines:
            lw = pc.text_w(line, f_m)
            draw.text((x + w - pad - lw, my), line, font=f_m, fill=pc.INK_SOFT)
            my += pc.text_h("字测", f_m) * 1.3


def draw_band(canvas, draw, grid, bp, cell):
    """The campaign rhythm, as a spine rather than three floating markers.

    A band of loose labels reads as decoration; a single horizontal spine with dots on
    it reads as time, which is the only thing this strip is for.
    """
    rect = grid.band_rect
    if not rect:
        return
    phases = bp.get("band", {}).get("phases", [])
    if not phases:
        return
    x, y, w, h = rect
    draw.rounded_rectangle([x, y, x + w, y + h], radius=int(cell * 0.016), fill=(255, 255, 255),
                           outline=pc.INK, width=max(2, int(cell * 0.0035)))
    n = len(phases)
    seg = w / n
    spine = y + int(h * 0.56)
    pad = int(cell * 0.030)
    draw.line([(x + pad, spine), (x + w - pad, spine)], fill=pc.INK,
              width=max(2, int(cell * 0.0035)))
    tip = int(cell * 0.016)
    draw.polygon([(x + w - pad + tip * 2, spine), (x + w - pad, spine - tip),
                  (x + w - pad, spine + tip)], fill=pc.INK)

    f_num = pc.load_font(max(10, int(cell * 0.030)), "bold")
    f_label = pc.load_font(max(12, int(cell * 0.056)), "bold")
    f_date = pc.load_font(max(10, int(cell * 0.034)), "regular")
    f_note = pc.load_font(max(9, int(cell * 0.028)), "regular")
    r = int(cell * 0.027)
    for i, ph in enumerate(phases):
        cx = x + seg * (i + 0.5)
        draw.ellipse([cx - r, spine - r, cx + r, spine + r], fill=pc.ACCENT)
        num = str(i + 1)
        nw = pc.text_w(num, f_num)
        draw.text((cx - nw / 2, spine - f_num.size * 0.60), num, font=f_num, fill=(255, 255, 255))
        label = ph.get("label", "")
        lw = pc.text_w(label, f_label)
        draw.text((cx - lw / 2, spine - r - int(cell * 0.075)), label, font=f_label, fill=pc.INK)
        date = ph.get("date", "")
        dw = pc.text_w(date, f_date)
        draw.text((cx - dw / 2, spine + r + int(cell * 0.022)), date, font=f_date,
                  fill=pc.ACCENT_ALT)
        note = ph.get("note", "")
        if note:
            lines = pc.wrap_text(note, f_note, int(seg * 0.86))
            ny = spine + r + int(cell * 0.068)
            for line in lines[:2]:
                lw2 = pc.text_w(line, f_note)
                draw.text((cx - lw2 / 2, ny), line, font=f_note, fill=pc.INK_SOFT)
                ny += pc.text_h("字测", f_note) * 1.25


def draw_col_headers(draw, grid, bp, cell):
    cols = bp.get("columns", [])
    f_idx = pc.load_font(max(10, int(cell * 0.032)), "bold")
    f_t = pc.load_font(max(12, int(cell * 0.058)), "bold")
    f_n = pc.load_font(max(9, int(cell * 0.030)), "regular")
    for j, rect in enumerate(grid.col_header_rects):
        x, y, w, h = rect
        title = cols[j]["title"] if j < len(cols) else ""
        note = cols[j].get("note", "") if j < len(cols) else ""
        draw.text((x, y + int(h * 0.10)), "%02d" % (j + 1), font=f_idx, fill=pc.ACCENT)
        draw.text((x + int(cell * 0.048), y + int(h * 0.02)),
                  ellipsize(title, f_t, w - int(cell * 0.055)), font=f_t, fill=pc.INK)
        if note:
            draw.text((x, y + int(h * 0.60)), ellipsize(note, f_n, w), font=f_n, fill=pc.INK_SOFT)
        draw.line([(x, y + h - 1), (x + w, y + h - 1)], fill=pc.INK, width=max(2, int(cell * 0.003)))


def draw_row_labels(draw, grid, bp, cell):
    """Persona strip: who this row is for, in one glance.

    Centred vertically rather than pinned to the top, because a tall cell with a name
    floating at the very top reads as an empty column with a label leaking out of it.
    """
    rows = bp.get("rows", [])
    f_tag = pc.load_font(max(8, int(cell * 0.026)), "regular")
    f_name = pc.load_font(max(13, int(cell * 0.082)), "bold")
    f_l1 = pc.load_font(max(10, int(cell * 0.038)), "regular")
    f_l2 = pc.load_font(max(10, int(cell * 0.043)), "regular")
    for i, rect in enumerate(grid.row_label_rects):
        x, y, w, h = rect
        row = rows[i] if i < len(rows) else {}
        pad = int(cell * 0.030)
        avail_w = w - 2 * pad
        gap = int(cell * 0.014)

        tag_h = pc.text_h("字测", f_tag) * 1.3
        name_lines = pc.wrap_text(row.get("name", "—"), f_name, avail_w)[:2]
        name_h = len(name_lines) * pc.text_h("字测", f_name) * 1.14
        l1_lines = pc.wrap_text(row.get("line1", ""), f_l1, avail_w)[:1] if row.get("line1") else []
        l1_h = len(l1_lines) * pc.text_h("字测", f_l1) * 1.3
        l2_lines = pc.wrap_text(row.get("line2", ""), f_l2, avail_w)[:4] if row.get("line2") else []
        l2_h = sum(pc.text_h("字测", f_l2) * 1.38 for _ in l2_lines)

        total = tag_h + gap + name_h + (gap // 2 + l1_h if l1_lines else 0) + \
            (gap + l2_h if l2_lines else 0)
        ty = y + max(int(cell * 0.05), (h - total) // 2)

        draw.text((x + pad, ty), "人群 %d" % (i + 1), font=f_tag, fill=pc.ACCENT)
        ty += tag_h + gap
        for line in name_lines:
            draw.text((x + pad, ty), line, font=f_name, fill=pc.INK)
            ty += pc.text_h("字测", f_name) * 1.14
        if l1_lines:
            ty += gap // 2
            for line in l1_lines:
                draw.text((x + pad, ty), line, font=f_l1, fill=pc.ACCENT_ALT)
                ty += pc.text_h("字测", f_l1) * 1.3
        if l2_lines:
            ty += gap
            for line in l2_lines:
                draw.text((x + pad, ty), line, font=f_l2, fill=pc.INK)
                ty += pc.text_h("字测", f_l2) * 1.38

        # An arrow into the row's home cell: the full-body shot is the row's anchor.
        ay = y + h - int(cell * 0.048)
        draw.line([(x + w - int(cell * 0.026), ay), (x + w - 2, ay)], fill=pc.ACCENT,
                  width=max(2, int(cell * 0.006)))
        draw.polygon([(x + w - 2, ay - int(cell * 0.012)), (x + w - 2, ay + int(cell * 0.012)),
                      (x + w + int(cell * 0.012), ay)], fill=pc.ACCENT)


def draw_caption(draw, view, cell, mode):
    x, y, w, h = view.caption_rect
    m = int(cell * 0.012)
    # Corner coords once, width/height once. Mixing the two puts the text 600px below
    # its plate and looks exactly like "the caption never rendered".
    rx, ry, rw, rh = x + m, y + m, w - 2 * m, h - 2 * m
    rect = [rx, ry, rx + rw, ry + rh]
    text = (view.zone.get("caption") or "").strip()
    if not text or text.startswith("TODO"):
        draw.rounded_rectangle(rect, radius=int(cell * 0.010), fill=(255, 236, 232),
                               outline=pc.ACCENT, width=max(2, int(cell * 0.003)))
        f = pc.load_font(max(10, int(cell * 0.036)), "regular")
        draw.text((rx + int(cell * 0.014), ry + int(cell * 0.020)),
                  "caption 未写" if mode == "skeleton" else "—", font=f, fill=pc.ACCENT)
        return
    cap = pl.caption_capacity(cell, view.caption_rect)
    font = pc.load_font(cap["font_size"], "regular")
    lines = pc.wrap_text(text, font, int(rw - 2 * cap["pad_x"]))
    overflow = len(lines) > cap["max_lines"]
    if overflow:
        font, lines = pc.fit_text_to_box(text, rw, rh, "regular",
                                         hi=cap["font_size"], lo=max(9, int(cap["font_size"] * 0.5)),
                                         pad_x=cap["pad_x"], pad_y=cap["pad_y"])
    draw.rounded_rectangle(rect, radius=int(cell * 0.010), fill=pc.PLATE_BG,
                           outline=pc.PLATE_BORDER if mode == "final" else pc.ACCENT_ALT,
                           width=max(2, int(cell * 0.0022)))
    lh = pc.text_h("字测", font) * 1.28
    total = len(lines) * lh
    ty = ry + (rh - total) / 2
    for line in lines:
        lw = pc.text_w(line, font)
        draw.text((rx + (rw - lw) / 2, ty), line, font=font, fill=pc.PLATE_INK)
        ty += lh


def draw_zone(canvas, draw, view, grid, cell, tiles_dir, mode, allow_partial, tstats,
              tag_text=None, persona_tag=None):
    x, y, w, h = view.rect
    ix, iy, iw, ih = view.image_rect
    frame_w = max(2, int(cell * 0.004))
    radius = int(cell * 0.014)

    if mode == "skeleton":
        tint = pc.ROW_TINTS[(view.row - 1) % len(pc.ROW_TINTS)]
        draw.rounded_rectangle([ix, iy, ix + iw, iy + ih], radius=radius, fill=tint,
                               outline=pc.INK_SOFT, width=frame_w)
        f_id = pc.load_font(max(10, int(cell * 0.030)), "bold")
        chip(draw, (ix + int(cell * 0.022), iy + int(cell * 0.022)), view.id, f_id,
             pc.INK, (255, 255, 255))
        f_kind = pc.load_font(max(9, int(cell * 0.024)), "regular")
        kind_txt = "定妆 face" if view.zone.get("face_allowed") else "figure（不给脸）"
        chip(draw, (ix + int(cell * 0.022), iy + int(cell * 0.074)), kind_txt, f_kind,
             (255, 255, 255), pc.ACCENT_ALT)
        f_duty = pc.load_font(max(10, int(cell * 0.034)), "regular")
        dy = iy + int(ih * 0.24)
        draw_wrapped(draw, (ix + int(cell * 0.030), dy), view.zone.get("duty", ""), f_duty,
                     iw - int(cell * 0.060), pc.INK_SOFT, 1.35, 7)
    else:
        tile_path = _tile_path(tiles_dir, view.id)
        tile = None
        if tile_path and os.path.isfile(tile_path):
            tile = Image.open(tile_path).convert("RGB")
        if tile is None:
            tstats["missing"].append(view.id)
            draw.rounded_rectangle([ix, iy, ix + iw, iy + ih], radius=radius,
                                   fill=pc.TILE_MISSING, outline=pc.ACCENT, width=frame_w)
            f = pc.load_font(max(11, int(cell * 0.036)), "bold")
            msg = "缺 tile" if allow_partial else "缺 tile（--allow-partial 才允许出图）"
            tw = pc.text_w(msg, f)
            draw.text((ix + (iw - tw) / 2, iy + ih / 2 - f.size * 0.6), msg, font=f, fill=pc.ACCENT)
            tstats["placeholder"] += 1
        else:
            tile = _fit_cover(tile, iw, ih)
            canvas.paste(tile, (ix, iy))
            tstats["used"] += 1
            # A tile is not information just because the file exists. Two independent
            # checks: what the blueprint promised, and what the pixels actually contain.
            if _declared_low_info(view.zone):
                tstats["low_information"].append(view.id)
                tstats["placeholder"] += 1
            elif tile_is_blank(tile_path):
                tstats["blank_tile"].append(view.id)
                tstats["placeholder"] += 1
        for slot in view.slots:
            path = slot["asset"].get("file", "")
            if path and os.path.isfile(path):
                box = slot["abs"]
                pc.paste_asset(canvas, path, box, slot["spec"].get("shadow", "hard_ellipse"))
                tstats["slots_placed"] += 1
            else:
                tstats["slots_missing"].append(slot["asset"]["id"])
        draw.rounded_rectangle([ix, iy, ix + iw, iy + ih], radius=radius,
                               outline=pc.INK, width=frame_w)

    # On a slice there is no column header, so the scenario name travels with the cell.
    # Drawn in both modes: a preview that hides it cannot show whether the label collides.
    if tag_text:
        f_tag = pc.load_font(max(9, int(cell * 0.028)), "bold")
        tw = pc.text_w(tag_text, f_tag) + int(f_tag.size * 1.0)
        chip(draw, (ix + iw - int(cell * 0.024) - tw, iy + int(cell * 0.024)), tag_text, f_tag,
             pc.PLATE_BG, pc.INK)

    # A long image has no persona row strip, so each block of cells announces whose it is
    # at its first cell. Without this the only thing tying four cells to one person is
    # vertical adjacency, which is exactly what a screenshot loses.
    if persona_tag:
        f_p = pc.load_font(max(9, int(cell * 0.030)), "bold")
        label = ellipsize(persona_tag, f_p, int(iw * 0.72))
        tw = pc.text_w(label, f_p) + int(f_p.size * 1.1)
        ch_h = pc.text_h("字测", f_p) + int(f_p.size * 0.52)
        py = (iy + int(cell * 0.128) if mode == "skeleton"
              else iy + ih - ch_h - int(cell * 0.024))
        chip(draw, (ix + int(cell * 0.024), py), label, f_p, pc.ACCENT_ALT, (255, 255, 255),
             pad_x=int(f_p.size * 0.55))

    draw_caption(draw, view, cell, mode)


def _tile_path(tiles_dir, zone_id):
    if not tiles_dir:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(tiles_dir, zone_id + ext)
        if os.path.isfile(p):
            return p
    return None


_INFO_CACHE = {}


def tile_is_blank(path):
    """A file that exists can still be an empty picture.

    The v1.1.1 build filled eight cells with flat paper geometry and stitch reported
    `placeholder: 0`, because `placeholder` only counted missing files. This is the
    pixel-side half of the fix (the blueprint-side half is lint_density.py): a tile with
    almost no distinct colours or no edges carries no information to composite.
    """
    try:
        key = (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path))
    except OSError:
        return True
    if key in _INFO_CACHE:
        return _INFO_CACHE[key]
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((96, 96))
        w, h = im.size
        # RGB is 3 bytes/pixel; tobytes() avoids Image.getdata(), deprecated in Pillow
        # 12 and scheduled for removal in 14. Same pixels, no version-dependent branch.
        raw = im.tobytes()
        px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
        colors = {(r >> 3, g >> 3, b >> 3) for r, g, b in px}
        edges = 0
        for y in range(1, h):
            row = y * w
            for x in range(1, w):
                i = row + x
                a, b, c = px[i], px[i - 1], px[i - w]
                if (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) > 60
                        or abs(a[0] - c[0]) + abs(a[1] - c[1]) + abs(a[2] - c[2]) > 60):
                    edges += 1
        density = edges / float(max(1, (w - 1) * (h - 1)))
        blank = len(colors) <= 3 or density < 0.004
    except Exception:
        blank = True
    _INFO_CACHE[key] = blank
    return blank


def _declared_low_info(zone):
    """A rule/evidence card with no facts is an empty card, however pretty its outlines."""
    origin = (zone.get("tile_origin") or "").strip()
    return origin in ("code_card", "evidence", "chart") and not (zone.get("facts") or [])


def _fit_cover(img, w, h):
    """Cover the cell without distorting: scale to fill, centre-crop the overhang."""
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def draw_disclosure(draw, grid, bp, cell, mode):
    """The bottom band: risk disclosure, institution, sign-off.

    For a financial product this band is the part that must survive every crop, every
    reflow and every "make the logo bigger" round. It is measured at a minimum legible
    size and it does not shrink; if it does not fit, the layout is wrong, not the text.
    """
    rect = grid.footer_rect
    if not rect:
        return False
    meta = bp["meta"]
    x, y, w, h = rect
    draw.line([(x, y), (x + w, y)], fill=pc.INK, width=max(2, int(cell * 0.003)))

    f = pc.load_font(max(10, int(cell * 0.023)), "regular")
    fs = pc.load_font(max(9, int(cell * 0.021)), "regular")
    d = meta.get("disclosure") or {}
    body = pl.footer_body(bp)
    sign = meta.get("footer", {}).get("signoff", "")
    right_bits = [b for b in [d.get("institution", ""), sign] if b]
    has_asof = bool(d.get("data_asof"))

    lh = pc.text_h("字测", f) * 1.38
    asof_lh = lh if has_asof else 0
    # Fixed inset, matching disclosure_height_px. A percentage inset silently shrinks the
    # usable body as the band grows, which is how a band that was sized correctly still
    # clips its last line.
    top = y + int(cell * 0.012)
    body_bottom = y + h - asof_lh - int(cell * 0.012)

    right_w = max((pc.text_w(b, fs) for b in right_bits), default=0)
    avail = w - (right_w + int(cell * 0.030) if right_bits else 0)
    ty = top
    overflow = False
    for para in body:
        for line in pc.wrap_text(para, f, avail):
            if ty + lh > body_bottom:
                overflow = True
                break
            draw.text((x, ty), line, font=f, fill=pc.INK)
            ty += lh

    ry = top
    for bit in right_bits:
        bw = pc.text_w(bit, fs)
        draw.text((x + w - bw, ry), bit, font=fs, fill=pc.INK_SOFT)
        ry += pc.text_h("字测", fs) * 1.45
    if d.get("risk_level") and ry + fs.size * 1.6 < body_bottom:
        fk = pc.load_font(max(9, int(cell * 0.021)), "bold")
        label = d["risk_level"]
        kw = pc.text_w(label, fk) + int(cell * 0.020)
        draw.rounded_rectangle([x + w - kw, ry, x + w, ry + int(fk.size * 1.6)],
                               radius=int(fk.size * 0.4), outline=pc.ACCENT, width=2)
        draw.text((x + w - kw + int(cell * 0.010), ry + int(fk.size * 0.25)),
                  label, font=fk, fill=pc.ACCENT)
    if has_asof:
        fa = pc.load_font(max(9, int(cell * 0.020)), "regular")
        draw.text((x, y + h - asof_lh - int(cell * 0.004)), "数据截至 %s" % d["data_asof"],
                  font=fa, fill=pc.INK_SOFT)
    return overflow


def draw_page_label(draw, grid, label, cell):
    """Top-right, inside the safe area. The bottom belongs to the disclosure, and a page
    number printed over an institution name is the kind of detail a compliance reviewer
    screenshots back to you."""
    f = pc.load_font(max(9, int(cell * 0.022)), "bold")
    lw = pc.text_w(label, f)
    x = grid.width - grid.pad_r - lw
    y = max(2, grid.pad_t - pc.text_h("字测", f) * 1.35)
    draw.text((x, y), label, font=f, fill=pc.INK_SOFT)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render(bp, grid, mapping, tiles_dir=None, mode="final",
           allow_partial=False, cell=None, header_override=None, tag_mode=False,
           page_label=None, safe=None):
    # Geometry and typography both come from the grid. Passing a cell size that differs
    # from the grid's produces huge cells full of tiny text — one source of truth only.
    cell = grid.cell
    canvas = Image.new("RGBA", (grid.width, grid.height), pc.PAPER + (255,))
    draw = ImageDraw.Draw(canvas)
    tstats = {"used": 0, "missing": [], "blank_tile": [], "low_information": [],
              "placeholder": 0, "slots_placed": 0, "slots_missing": []}

    draw_header(canvas, draw, grid, bp["meta"], cell, header_override)
    draw_band(canvas, draw, grid, bp, cell)
    draw_col_headers(draw, grid, bp, cell)
    draw_row_labels(draw, grid, bp, cell)

    scene_titles = {c.get("id"): c.get("title", "") for c in bp.get("columns", [])}
    rows_by_persona = {r.get("persona"): r for r in bp.get("rows", [])}
    views = pl.zone_views(bp, grid, mapping)
    for v in views:
        tag = scene_titles.get(v.zone.get("scene"), "") if tag_mode else None
        ptag = None
        if tag_mode == "long" and v.local_col == 0:
            p = rows_by_persona.get(v.zone.get("persona"), {})
            name = p.get("name", "")
            line1 = p.get("line1", "")
            ptag = ("%s · %s" % (name, line1)) if (name and line1) else name
        draw_zone(canvas, draw, v, grid, cell, tiles_dir, mode, allow_partial, tstats,
                  tag_text=tag or None, persona_tag=ptag or None)

    overflow = draw_disclosure(draw, grid, bp, cell, mode)
    if page_label:
        draw_page_label(draw, grid, page_label, cell)
    if mode == "skeleton" and safe:
        sx, sy, sw_, sh_ = pl.safe_rect(grid, safe)
        dash = ImageDraw.Draw(canvas)
        _dashed(dash, (sx, sy, sw_, sh_), pc.ACCENT_ALT, width=max(2, int(cell * 0.004)),
                dash=int(cell * 0.03), gap=int(cell * 0.02))
        f_lbl = pc.load_font(max(9, int(cell * 0.024)), "bold")
        dash.text((sx + int(cell * 0.012), sy + int(cell * 0.010)),
                  "平台 UI 安全区（框外会被遮挡）", font=f_lbl, fill=pc.ACCENT_ALT)
    tstats["disclosure_overflow"] = overflow
    return canvas.convert("RGB"), tstats, len(views)


def _dashed(draw, rect, color, width=3, dash=18, gap=12):
    x, y, w, h = rect
    for x0 in range(x, x + w, dash + gap):
        draw.line([(x0, y), (min(x0 + dash, x + w), y)], fill=color, width=width)
        draw.line([(x0, y + h), (min(x0 + dash, x + w), y + h)], fill=color, width=width)
    for y0 in range(y, y + h, dash + gap):
        draw.line([(x, y0), (x, min(y0 + dash, y + h))], fill=color, width=width)
        draw.line([(x + w, y0), (x + w, min(y0 + dash, y + h))], fill=color, width=width)


def slice_title(bp, target):
    """The one line a slice carries so it stands alone outside the atlas."""
    t = target.get("type", "full")
    rows = {r.get("id"): r for r in bp.get("rows", [])}
    cols = {c.get("id"): c for c in bp.get("columns", [])}
    if t == "row" and target.get("rows"):
        r = rows.get(bp["rows"][target["rows"][0] - 1].get("id"), {})
        name = r.get("name", "")
        return "%s · %s" % (name, r.get("line1", "")) if name else target.get("id", "")
    if t == "col" and target.get("cols"):
        c = cols.get(bp["columns"][target["cols"][0] - 1].get("id"), {})
        return c.get("title", "") or target.get("id", "")
    return ""


def _safe_of(target):
    return target.get("safe") or pl.platform_spec(target.get("platform")).get("safe")


def _platform_width(target, fallback=1242):
    px = pl.platform_spec(target.get("platform")).get("px")
    return int(px[0]) if px else fallback


def platform_px(target):
    """Exact deliverable pixels for a platform-bound target.

    Width comes from the platform table; height is derived from the ratio, not copied
    from px[1]. A table that said 3:4 and 1242x1660 was a table arguing with itself:
    the cover rendered at 1656 while the manifest claimed 1660.
    """
    spec = pl.platform_spec(target.get("platform"))
    px = spec.get("px")
    if not px:
        return None
    ratio = _ratio_of(target)
    if not ratio or not ratio[0]:
        return (int(px[0]), int(px[1]))
    w = int(px[0])
    return (w, int(round(w * ratio[1] / ratio[0])))


def normalize_to_platform(img, target):
    """Land a reflowed page on the channel's real pixel size.

    pad_to_ratio only ever ADDS borders; it cannot shrink. Without this step one upload
    ships a 1242px cover beside 1256px inner pages and a 1259px long image, so the
    platform resamples every page differently. The correction here is ~1%, far smaller
    than the resample the platform would have applied anyway.
    """
    want = platform_px(target)
    if not want or tuple(img.size) == want:
        return img, None
    native = tuple(img.size)
    return img.resize(want, Image.LANCZOS), native


def _cell_for_width(bp, target, width):
    """Pick the cell size that lands the page on the channel's real pixel width.

    A carousel whose cover is 1242px wide and whose inner pages are 2619px wide is not a
    carousel — it is nine files that will be resampled differently by the same platform.
    """
    probe, _m, _p, _n = pl.flow_plan(bp, target, cell=1000)
    return max(200, int(round(width * 1000.0 / probe.width)))


def _ratio_of(target):
    return pc.parse_ratio(target.get("ratio")) or pc.parse_ratio(
        pl.platform_spec(target.get("platform")).get("ratio"))


def render_target(bp, target, tiles_dir=None, mode="final", allow_partial=False, cell=None):
    """Render one target. `full` with no ratio is the master; everything else reflows.

    `long` reflows like a channel frame, with two differences that matter: the column
    count is restricted to divisors of the scene count (so a persona's cells stay one
    block), and the block's first cell carries a persona chip (a long image has no row
    strip to say whose four cells these are).
    """
    ttype = target.get("type", "full")
    ratio = pc.parse_ratio(target.get("ratio"))
    safe = _safe_of(target)
    long_mode = ttype == "long"
    if ttype == "full" and not ratio:
        grid, row_map, col_map = pl.make_grid(bp, cell=cell)
        mapping = pl.matrix_mapping(row_map, col_map)
        img, tstats, nzones = render(bp, grid, mapping, tiles_dir, mode, allow_partial,
                                     cell=cell)
        return img, grid, {"pad_pct": 0.0, "zones": nzones, "mode": "master", **tstats}

    if cell is None and target.get("platform"):
        cell = _cell_for_width(bp, target, _platform_width(target))
    block_cols = int(bp["meta"]["grid"].get("cols", 0) or 0) if long_mode else None
    grid, mapping, pad, ncells = pl.flow_plan(bp, target, cell=cell, block_cols=block_cols)
    title = slice_title(bp, target)
    campaign = bp["meta"].get("campaign", "")
    t_title = title or bp["meta"].get("header", {}).get("title", "")
    # Printing the campaign name twice — once as the title, once as the right-hand line —
    # is the most common way a slice announces that nobody looked at it.
    meta_line = "" if t_title.strip() == campaign.strip() else campaign
    override = {"title": t_title, "subtitle": "", "meta_line": meta_line}
    if long_mode:
        # The feed only shows the top quarter. Before v1.2 that quarter said what the
        # product was and nothing else; a screenshot of it lost both the conclusion and
        # every line of disclosure. Both now sit inside the first screen.
        first = target.get("first_screen") or {}
        parts = ([first["takeaway"]] if first.get("takeaway") else [])
        parts += _fact_texts(bp, first.get("facts"), limit=3)
        override["subtitle"] = " · ".join(p for p in parts if p)
        if first.get("disclosure"):
            lines = pl.disclosure_lines(bp)
            if lines:
                override["meta_line"] = lines[0][:26]
    # A reflow has no persona strip. When its column count equals the scene count, every
    # local row is exactly one persona, so the block-start chip is the only thing saying
    # whose row this is (a 1:1 版 without it is twelve anonymous cells in three stripes).
    persona_tags = long_mode or grid.cols == int(bp["meta"]["grid"].get("cols", 0) or 0)
    img, tstats, nzones = render(bp, grid, mapping, tiles_dir, mode, allow_partial,
                                 cell=cell, header_override=override,
                                 tag_mode="long" if persona_tags else True, safe=safe)
    img, actual_pad = pc.pad_to_ratio(img, _ratio_of(target) or ratio)
    return img, grid, {"pad_pct": round(actual_pad * 100, 2), "zones": nzones,
                       "mode": "long" if long_mode else "reflow",
                       "shape": [grid.cols, grid.rows],
                       "aspect": round(img.width / float(img.height), 3),
                       "cells": ncells, **tstats}


# ---------------------------------------------------------------------------
# carousel pages: cover, end
# ---------------------------------------------------------------------------


def _page_size(cell, ratio):
    rw, rh = ratio
    W = int(cell)
    return W, int(round(cell * rh / rw))


def _insets(W, H, safe, base=0.06):
    if not safe:
        return int(W * base), int(W * base), int(H * base * 0.8), int(H * base * 0.8)
    l = int(max(W * base, safe.get("left", 0) * W * 1.05))
    r = int(max(W * base, safe.get("right", 0) * W * 1.05))
    t = int(max(H * base * 0.6, safe.get("top", 0) * H * 1.05))
    b = int(max(H * base * 0.6, safe.get("bottom", 0) * H * 1.05))
    return l, r, t, b


def _cover_hero_zone(bp, page):
    zid = page.get("hero")
    if zid:
        for z in bp["zones"]:
            if z["id"] == zid:
                return z
    for z in bp["zones"]:
        if z.get("face_allowed"):
            return z
    return bp["zones"][0] if bp["zones"] else None


def _fact_texts(bp, ids, limit=None):
    """Resolve fact ids to their printed text. Numbers never come from the image model."""
    facts = {f.get("id"): f for f in (bp.get("meta", {}).get("key_facts") or [])
             if isinstance(f, dict) and f.get("id")}
    out = [(facts.get(i) or {}).get("text", "") for i in (ids or [])]
    out = [t for t in out if t]
    return out[:limit] if limit else out


def _draw_fact_band(draw, x, y, w, h, texts, W, max_rows=4):
    """Checkable numbers, printed by code on their own plate. Returns (height, printed).

    Four Chinese clauses at cover size do not fit one line. v1.2.0 hard-capped this at
    two rows: the density sheet counted four cover facts, the picture printed three, and
    the takeaway still said "四个数字". The band grows instead — the hero picture gives
    up height, not facts. max_rows equals the cover fact cap so nothing can be dropped.
    """
    if not texts:
        return 0, 0
    f = pc.load_font(max(11, int(W * 0.027)), "bold")
    fw = pc.load_font(max(10, int(W * 0.021)), "regular")
    pad = int(W * 0.026)
    gap = int(W * 0.012)
    label = "关键数字" if len(texts) > 1 else "要点"
    start = pad + pc.text_w(label, fw) + int(W * 0.018)
    avail = w - start - pad
    row_h = max(int(W * 0.048), pc.text_h("字测", f) + int(W * 0.020))
    rows, cur, cur_w = [], [], 0
    for t in texts:
        cw = pc.text_w(t, f) + int(W * 0.028)
        if cur and cur_w + cw + gap > avail:
            rows.append(cur)
            cur, cur_w = [], 0
        cur.append((t, cw))
        cur_w += cw + gap
    if cur:
        rows.append(cur)
    rows = rows[:max_rows]
    printed = sum(len(r) for r in rows)
    total = max(h, len(rows) * row_h + int(W * 0.022))
    draw.rounded_rectangle([x, y, x + w, y + total], radius=int(W * 0.012),
                           fill=pc.PAPER_DEEP, outline=pc.INK_SOFT,
                           width=max(1, int(W * 0.002)))
    draw.text((x + pad, y + (total - pc.text_h("字测", fw)) / 2), label, font=fw,
              fill=pc.INK_SOFT)
    for ri, row in enumerate(rows):
        cx = x + start
        cy = y + int(W * 0.011) + ri * row_h
        for t, cw in row:
            draw.rounded_rectangle([cx, cy, cx + cw, cy + row_h - int(W * 0.008)],
                                   radius=int(row_h * 0.20), fill=pc.PLATE_BG,
                                   outline=pc.ACCENT, width=max(1, int(W * 0.002)))
            draw.text((cx + int(W * 0.014), cy + (row_h - pc.text_h("字测", f)) / 2
                       - int(W * 0.004)), t, font=f, fill=pc.INK)
            cx += cw + gap
    return total, printed


def render_cover(bp, target, page, tiles_dir=None, mode="final", allow_partial=False,
                 page_label=None, cell=None):
    ratio = _ratio_of(target) or (3, 4)
    W, H = _page_size(cell or 1242, ratio)
    safe = _safe_of(target)
    l, r, t, b = _insets(W, H, safe)
    canvas = Image.new("RGBA", (W, H), pc.PAPER + (255,))
    draw = ImageDraw.Draw(canvas)
    inner_w = W - l - r

    meta = bp["meta"]
    eyebrow = meta.get("campaign", "")
    f_eb = pc.load_font(max(11, int(W * 0.026)), "bold")
    draw.text((l, t), eyebrow, font=f_eb, fill=pc.ACCENT)

    title = page.get("title") or meta.get("header", {}).get("title", "")
    f_title, _ = pc.fit_text_to_box(title, inner_w, int(H * 0.30), "bold",
                                    hi=int(W * 0.098), lo=int(W * 0.045), pad_x=0, pad_y=0)
    ty = t + int(H * 0.045)
    ty += draw_wrapped(draw, (l, ty), title, f_title, inner_w, pc.INK, 1.12, 3)

    sub = page.get("subtitle") or meta.get("header", {}).get("subtitle", "")
    if sub:
        f_s = pc.load_font(max(11, int(W * 0.034)), "regular")
        ty += int(H * 0.012)
        ty += draw_wrapped(draw, (l, ty), sub, f_s, inner_w, pc.INK_SOFT, 1.35, 3)

    # A cover used to be a title, a subtitle and a picture — zero new facts. The feed
    # shows only this page to most readers, so the agreed key numbers are printed here.
    if page.get("takeaway"):
        f_t = pc.load_font(max(11, int(W * 0.030)), "regular")
        ty += int(H * 0.010)
        ty += draw_wrapped(draw, (l, ty), page["takeaway"], f_t, inner_w, pc.ACCENT, 1.30, 2)
    declared = len(page.get("facts") or [])
    nums = _fact_texts(bp, page.get("facts"))
    printed = 0
    if nums:
        ty += int(H * 0.014)
        band_h, printed = _draw_fact_band(draw, l, ty, inner_w, int(H * 0.062), nums, W)
        ty += band_h

    foot_lines = pl.disclosure_lines(bp) or [
        ln for ln in [meta.get("footer", {}).get("note", "")] if ln]
    f_foot = pc.load_font(max(9, int(W * 0.019)), "regular")
    foot_h = len(foot_lines) * pc.text_h("字测", f_foot) * 1.4 + int(H * 0.03)
    hero_top = int(ty) + int(H * 0.030)
    hero_h = max(int(H * 0.2), int(H - b - foot_h - hero_top - int(H * 0.02)))
    hero_rect = (int(l), hero_top, int(inner_w), hero_h)

    zone = _cover_hero_zone(bp, page)
    if zone:
        tp = _tile_path(tiles_dir, zone["id"]) if tiles_dir else None
        if tp and os.path.isfile(tp):
            tile = _fit_cover(Image.open(tp).convert("RGB"), hero_rect[2], hero_rect[3])
            canvas.paste(tile, (hero_rect[0], hero_rect[1]))
        else:
            draw.rounded_rectangle([hero_rect[0], hero_rect[1], hero_rect[0] + hero_rect[2],
                                    hero_rect[1] + hero_rect[3]],
                                   radius=int(W * 0.02), fill=pc.ROW_TINTS[0])
            f = pc.load_font(max(11, int(W * 0.028)), "bold")
            msg = "封面主图：%s（Gate 3 样张）" % zone["id"]
            draw.text((hero_rect[0] + int(W * 0.03), hero_rect[1] + int(H * 0.02)), msg,
                      font=f, fill=pc.INK_SOFT)
        draw.rounded_rectangle([hero_rect[0], hero_rect[1], hero_rect[0] + hero_rect[2],
                                hero_rect[1] + hero_rect[3]],
                               radius=int(W * 0.02), outline=pc.INK, width=max(2, int(W * 0.004)))

    fy = H - b - foot_h
    draw.line([(l, fy), (W - r, fy)], fill=pc.INK, width=max(2, int(W * 0.003)))
    yy = fy + int(H * 0.012)
    for para in foot_lines:
        for line in pc.wrap_text(para, f_foot, inner_w):
            draw.text((l, yy), line, font=f_foot, fill=pc.INK_SOFT)
            yy += pc.text_h("字测", f_foot) * 1.4
    if page_label:
        draw_page_label(draw, _PseudoGrid(W, H, l, r, b, t), page_label, W)
    tstats = {"used": 1 if zone else 0, "missing": [], "blank_tile": [], "low_information": [], "placeholder": 0,
              "slots_placed": 0, "slots_missing": [], "disclosure_overflow": False,
              "facts_declared": declared,
              "facts_printed": printed,
              "facts_clipped": max(0, declared - printed)}
    return canvas.convert("RGB"), tstats


class _PseudoGrid:
    """Just enough grid for the page-label helper on bespoke pages."""

    def __init__(self, w, h, pad_l, pad_r, pad_b, pad_t=0):
        self.width, self.height = w, h
        self.pad_l, self.pad_r, self.pad_b = pad_l, pad_r, pad_b
        self.pad_t = pad_t


def render_end(bp, target, page, tiles_dir=None, mode="final", allow_partial=False,
               page_label=None, cell=None):
    """The closing page: what the product is, who stands behind it, what the risk is."""
    ratio = _ratio_of(target) or (3, 4)
    W, H = _page_size(cell or 1242, ratio)
    safe = _safe_of(target)
    l, r, t, b = _insets(W, H, safe)
    canvas = Image.new("RGBA", (W, H), pc.PAPER + (255,))
    draw = ImageDraw.Draw(canvas)
    inner_w = W - l - r
    meta = bp["meta"]
    d = meta.get("disclosure") or {}
    fin = pl.is_financial(bp)

    f_eb = pc.load_font(max(11, int(W * 0.026)), "bold")
    draw.text((l, t), page.get("eyebrow") or ("信息披露" if fin else "关于这套产品"),
              font=f_eb, fill=pc.ACCENT)

    title = page.get("title") or meta.get("header", {}).get("title", "")
    f_t, _ = pc.fit_text_to_box(title, inner_w, int(H * 0.12), "bold",
                                hi=int(W * 0.062), lo=int(W * 0.038), pad_x=0, pad_y=0)
    ty = t + int(H * 0.030)
    ty += draw_wrapped(draw, (l, ty), title, f_t, inner_w, pc.INK, 1.15, 2)

    # Evidence row: real files, never redrawn. A fund has no pack shot — what it has is an
    # app screen and a NAV chart, and those are the things a reader is meant to trust.
    prods = [a for a in bp.get("assets", [])
             if a.get("kind") in ("product", "mascot", "ui", "chart")]
    row_h = int(H * (0.34 if prods else 0.0))
    if prods:
        n = min(len(prods), 3)
        gap = int(W * 0.03)
        cw = (inner_w - gap * (n - 1)) // n
        cy = int(ty) + int(H * 0.030)
        stage = int(H * 0.035)
        draw.rounded_rectangle([l, cy + row_h - stage, W - r, cy + row_h],
                               radius=int(stage * 0.5), fill=pc.PAPER_DEEP)
        for i, a in enumerate(prods[:n]):
            box = (int(l + i * (cw + gap)), int(cy), int(cw), int(row_h - stage))
            if os.path.isfile(a.get("file", "")) and mode == "final":
                # A screenshot is not standing on a table; it sits on the plinth already
                # drawn behind it. A shadow under a rectangle reads as a grey smear.
                shadow = "none" if a.get("kind") in ("ui", "chart", "logo") else "hard_ellipse"
                fit = pc.paste_asset(canvas, a["file"], box, shadow)
                if a.get("kind") in ("ui", "chart", "logo"):
                    # Rectangular evidence gets a frame, so it reads as a screenshot rather
                    # than as part of the drawing.
                    draw.rounded_rectangle([fit[0], fit[1], fit[0] + fit[2], fit[1] + fit[3]],
                                           radius=int(W * 0.008), outline=pc.INK,
                                           width=max(2, int(W * 0.003)))
            elif mode == "skeleton":
                draw.rounded_rectangle([box[0], box[1], box[0] + box[2], box[1] + box[3]],
                                       radius=int(W * 0.02), outline=pc.INK_SOFT, width=2)
                f = pc.load_font(max(10, int(W * 0.022)), "bold")
                draw.text((box[0] + int(W * 0.01), box[1] + int(W * 0.02)), a["id"],
                          font=f, fill=pc.INK_SOFT)
        ty = cy + row_h + int(H * 0.025)

    lines = page.get("lines") or []
    f_l = pc.load_font(max(11, int(W * 0.030)), "regular")
    for line in lines[:3]:
        ty += draw_wrapped(draw, (l, ty), line, f_l, inner_w, pc.INK, 1.4, 2)
        ty += int(H * 0.008)

    if fin:
        blk = [("机构", d.get("institution", "")), ("资质", d.get("license", "")),
               ("风险等级", d.get("risk_level", ""))]
        f_k = pc.load_font(max(10, int(W * 0.024)), "bold")
        f_v = pc.load_font(max(10, int(W * 0.026)), "regular")
        ty += int(H * 0.020)
        for k, v in blk:
            if not v:
                continue
            draw.text((l, ty), k, font=f_k, fill=pc.ACCENT_ALT)
            ty += draw_wrapped(draw, (l + int(W * 0.14), ty), v, f_v,
                               inner_w - int(W * 0.14), pc.INK, 1.3, 2)
            ty += int(H * 0.006)

    foot_lines = pl.disclosure_lines(bp) or [
        ln for ln in [meta.get("footer", {}).get("note", "")] if ln]
    f_foot = pc.load_font(max(9, int(W * 0.018)), "regular")
    foot_h = len(foot_lines) * pc.text_h("字测", f_foot) * 1.4 + int(H * 0.03)
    fy = H - b - foot_h
    draw.line([(l, fy), (W - r, fy)], fill=pc.INK, width=max(2, int(W * 0.003)))
    yy = fy + int(H * 0.012)
    for para in foot_lines:
        for line in pc.wrap_text(para, f_foot, inner_w):
            draw.text((l, yy), line, font=f_foot, fill=pc.INK_SOFT)
            yy += pc.text_h("字测", f_foot) * 1.4
    if meta.get("footer", {}).get("signoff"):
        f_s = pc.load_font(max(9, int(W * 0.018)), "regular")
        s = meta["footer"]["signoff"]
        draw.text((W - r - pc.text_w(s, f_s), fy - int(H * 0.018)), s, font=f_s,
                  fill=pc.INK_SOFT)
    if d.get("data_asof"):
        f_a = pc.load_font(max(9, int(W * 0.017)), "regular")
        a_txt = "数据截至 %s" % d["data_asof"]
        draw.text((W - r - pc.text_w(a_txt, f_a), H - b - pc.text_h("字测", f_a) * 1.1),
                  a_txt, font=f_a, fill=pc.INK_SOFT)
    if page_label:
        draw_page_label(draw, _PseudoGrid(W, H, l, r, b, t), page_label, W)
    tstats = {"used": 0, "missing": [], "blank_tile": [], "low_information": [], "placeholder": 0, "slots_placed": 0,
              "slots_missing": [], "disclosure_overflow": False}
    return canvas.convert("RGB"), tstats


def render_carousel(bp, target, tiles_dir=None, mode="final", allow_partial=False, cell=None):
    """A social-media carousel: every page stands alone, so every page repeats the
    disclosure and carries its own number. A page that only works after the previous
    one has been read is a page that dies when somebody screenshots it."""
    pages = target.get("pages") or pl.default_pages(bp)
    total = len(pages)
    W_page = cell or _platform_width(target)
    out = []
    for i, page in enumerate(pages):
        label = "%02d/%02d" % (i + 1, total)
        kind = page.get("kind", "row")
        if kind == "cover":
            img, st = render_cover(bp, target, page, tiles_dir, mode, allow_partial,
                                   label, W_page)
        elif kind == "end":
            img, st = render_end(bp, target, page, tiles_dir, mode, allow_partial,
                                 label, W_page)
        else:
            sub = {"id": "%s_p%d" % (target.get("id", "carousel"), i + 1), "type": kind,
                   "rows": page.get("rows"), "cols": page.get("cols"),
                   "ratio": target.get("ratio") or "3:4",
                   "platform": target.get("platform"), "safe": target.get("safe")}
            cell_px = _cell_for_width(bp, sub, W_page)
            grid, mapping, pad, ncells = pl.flow_plan(bp, sub, cell=cell_px)
            title = page.get("title") or slice_title(bp, sub)
            person = ""
            # A page header is 0.105×cell tall. When the page already carries its own title
            # (which is where "姓名 · 年龄 · 情境" belongs), stacking the persona's trigger
            # moment underneath it clips the second line — the old workaround was to blank
            # rows[].line2 for the whole build, which then cost the master and the long image
            # their persona description. Keep the moment on the row data, drop it here only.
            if kind == "row" and page.get("rows") and not page.get("title"):
                idx = page["rows"][0] - 1
                if 0 <= idx < len(bp.get("rows", [])):
                    person = bp["rows"][idx].get("line2", "")
            override = {"title": title or bp["meta"].get("header", {}).get("title", ""),
                        "subtitle": person, "meta_line": bp["meta"].get("campaign", "")}
            img, st, nz = render(bp, grid, mapping, tiles_dir, mode, allow_partial,
                                 cell=cell_px, header_override=override, tag_mode=True,
                                 page_label=label, safe=_safe_of(target))
            img, _p = pc.pad_to_ratio(img, _ratio_of(target))
            st = {**st, "pad_pct": round(_p * 100, 2), "zones": nz,
                  "mode": "reflow", "shape": [grid.cols, grid.rows], "cells": ncells}
        out.append({"index": i + 1, "kind": kind, "label": label, "image": img, **st})
    return out


def main():
    ap = argparse.ArgumentParser(description="promo-atlas step 6: stitch tiles, labels, assets")
    ap.add_argument("blueprint")
    ap.add_argument("-d", "--tiles", default="tiles")
    ap.add_argument("-o", "--out", default="atlas.png")
    ap.add_argument("--target", default=None,
                    help="target id from blueprint, or 'all' (default: the blueprint's first target)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="render with placeholders where tiles are missing (proof pass only)")
    ap.add_argument("--strict-info", action="store_true",
                    help="fail when a tile exists but carries no information "
                         "(blank pixels, or a declared card with no facts)")
    ap.add_argument("--cell", type=int, default=None, help="override cell size in px")
    args = ap.parse_args()

    bp_path = os.path.abspath(args.blueprint)
    base = os.path.dirname(bp_path)
    bp = pl.resolve_asset_paths(pl.load(bp_path), base)
    tiles = args.tiles if os.path.isabs(args.tiles) else os.path.join(base, args.tiles)

    targets = bp.get("targets", []) or [{"id": "main", "type": "full", "ratio": "auto"}]
    if not args.target:
        # Omitting --target means "the master", whatever the blueprint calls it. Hardcoding
        # the id "main" made the documented command fail on any blueprint that named its
        # first target "master" — which the demo and every real build does.
        args.target = targets[0]["id"]
    if args.target == "all":
        chosen = targets
    else:
        chosen = [t for t in targets if t.get("id") == args.target]
        if not chosen:
            print("找不到 target %r；可选: %s" % (args.target, ", ".join(t["id"] for t in targets)),
                  file=sys.stderr)
            return 2

    outdir = os.path.dirname(os.path.abspath(args.out))
    pc.ensure_dir(outdir)
    stem, ext = os.path.splitext(os.path.abspath(args.out))
    report = {"targets": [], "grid": None}
    rc = 0
    causes = []
    for t in chosen:
        plat = pl.platform_spec(t.get("platform"))
        # An explicit --cell is a preview/probe: keep its native size. A delivery run has
        # no --cell and must land on the channel's exact pixels.
        want = platform_px(t) if args.cell is None else None
        if t.get("type") == "carousel":
            pages = render_carousel(bp, t, tiles_dir=tiles, mode="final",
                                    allow_partial=args.allow_partial, cell=args.cell)
            for p in pages:
                img, native = (normalize_to_platform(p["image"], t) if want
                               else (p["image"], None))
                path = "%s_%s_p%02d%s" % (stem, t.get("id"), p["index"], ext or ".png")
                img.save(path)
                # None = this target has no platform contract (the master); False would
                # read as "failed" to anyone scanning the report.
                exact = ([img.width, img.height] == list(want)) if want else None
                report["targets"].append({
                    **{k: v for k, v in p.items() if k != "image"},
                    "id": "%s#%d" % (t.get("id"), p["index"]),
                    "path": path,
                    "size": [img.width, img.height],
                    "platform": t.get("platform"),
                    "platform_px": list(want) if want else None,
                    "size_exact": exact,
                    "normalized_from": list(native) if native else None})
                print("wrote %s  (%d×%d)  %s  %s%s" % (
                    path, img.width, img.height, p["kind"], p["label"],
                    "  [normalized from %d×%d]" % native if native else ""))
                if want and not exact:
                    print("  ✗ 交付尺寸与平台像素不一致：%s ≠ %s" % (img.size, want),
                          file=sys.stderr)
                    rc = 1
                    causes.append("交付尺寸与平台像素不一致")
                # The density sheet counts the cover's declared facts. If the plate drops
                # one while the takeaway still says "四个数字", the ledger and the picture
                # disagree — the exact class of silent loss this whole gate exists for.
                if p.get("facts_clipped"):
                    print("  ✗ 封面声明 %d 条关键数字，只印出 %d 条——结论句与画面不符"
                          % (p.get("facts_declared", 0), p.get("facts_printed", 0)),
                          file=sys.stderr)
                    rc = 1
                    causes.append("封面关键数字被裁掉")
                if p["missing"] or p["slots_missing"]:
                    rc = 1
                    causes.append("缺 tile 或资产")
                low = list(p.get("blank_tile") or []) + list(p.get("low_information") or [])
                if low:
                    print("  ⚠ 无信息图 %d 格: %s" % (len(low), ", ".join(low)))
                    if args.strict_info:
                        rc = 1
                        causes.append("有文件但无信息的图")
                if p.get("disclosure_overflow"):
                    print("  ✗ 披露文字超出版面（%s）" % p["label"], file=sys.stderr)
                    rc = 1
                    causes.append("披露文字超出版面")
            continue

        img, grid, st = render_target(bp, t, tiles_dir=tiles, mode="final",
                                      allow_partial=args.allow_partial, cell=args.cell)
        native = None
        if want:
            img, native = normalize_to_platform(img, t)
        path = args.out if len(chosen) == 1 else "%s_%s%s" % (stem, t.get("id", "t"), ext or ".png")
        img.save(path)
        exact = ([img.width, img.height] == list(want)) if want else None
        report["grid"] = grid.describe()
        report["targets"].append({**st,
                                  "id": t.get("id"), "path": path,
                                  "size": [img.width, img.height],
                                  "platform": t.get("platform"),
                                  "platform_px": list(want) if want else None,
                                  "size_exact": exact,
                                  "normalized_from": list(native) if native else None})
        print("wrote %s  (%d×%d)  zones=%d  tiles=%d  placeholder=%d "
              "(missing=%d blank=%d no-facts=%d)  pad=%.1f%%%s%s" % (
                  path, img.width, img.height, st["zones"], st["used"], st["placeholder"],
                  len(st.get("missing") or []), len(st.get("blank_tile") or []),
                  len(st.get("low_information") or []), st["pad_pct"],
                  "  [%s]" % plat["label"] if plat else "",
                  "  [normalized from %d×%d]" % native if native else ""))
        if want and not exact:
            print("  ✗ 交付尺寸与平台像素不一致：%s ≠ %s" % (img.size, want),
                  file=sys.stderr)
            rc = 1
            causes.append("交付尺寸与平台像素不一致")
        low = list(st.get("blank_tile") or []) + list(st.get("low_information") or [])
        if low:
            print("  ⚠ 无信息图 %d 格: %s（文件存在，但没印出任何事实）"
                  % (len(low), ", ".join(low)))
            if args.strict_info:
                rc = 1
                causes.append("有文件但无信息的图")
        if t.get("type") == "long":
            tall = img.height / float(img.width)
            print("  长图 1:%.2f  分栏 %d×%d%s" % (
                tall, st["shape"][0], st["shape"][1],
                "" if tall <= pl.LONG_MAX_ASPECT + 0.01 else "  ✗ 超过 1:4 上限"))
            if tall > pl.LONG_MAX_ASPECT + 0.01:
                rc = 1
                causes.append("长图超过 1:4")
        if st["missing"]:
            print("  缺 tile: %s" % ", ".join(st["missing"]))
            if not args.allow_partial:
                rc = 1
                causes.append("缺 tile 或资产")
        if st["slots_missing"]:
            print("  缺资产: %s" % ", ".join(st["slots_missing"]))
            rc = 1
            causes.append("缺 tile 或资产")
        if st.get("disclosure_overflow"):
            print("  ✗ 披露文字超出版面——这是版面问题，不是文字问题，调大 footer_ratio",
                  file=sys.stderr)
            rc = 1
            causes.append("披露文字超出版面")
        if st["pad_pct"] > 18:
            print("  ⚠ 留白 %.0f%%：这个 target 的比例与版面不匹配，投到该渠道会显得空" % st["pad_pct"])

    pc.save_json(os.path.join(outdir, "stitch_report.json"), report)
    if rc:
        uniq = []
        for c in causes:
            if c not in uniq:
                uniq.append(c)
        print("stitch 未通过：%s" % ("；".join(uniq) if uniq else "见上方报错"),
              file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
