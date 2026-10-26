#!/usr/bin/env python3
"""Composite tiles into the final atlas and draw the annotation layer.

Everything textual in the output is produced here. Tiles are assumed to contain no text at all.
Contrast is measured against the real pixels behind each label and recorded, never assumed.

Usage:
    python3 stitch.py atlas_build/blueprint.json -d atlas_build/tiles -o atlas_build/atlas.png
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_common as ac  # noqa: E402

FLOOR = 4.5
MAX_SCRIM = 0.92


def find_tile(tile_dir, zone, c, r):
    for name in (f"{zone['id']}_{c}_{r}.png", f"{c}_{r}.png",
                 f"{zone['id']}_{c}_{r}.jpg", f"{c}_{r}.jpg"):
        path = os.path.join(tile_dir, name)
        if os.path.exists(path):
            return path
    return None


def placeholder(cell, zone, c, r):
    img = Image.new("RGB", (cell, cell), (32, 33, 36))
    d = ImageDraw.Draw(img, "RGBA")
    step = max(24, cell // 16)
    for i in range(-cell, cell * 2, step):
        d.line([(i, 0), (i + cell, cell)], fill=(70, 70, 74, 90), width=2)
    f = ac.resolve_font(max(20, cell // 18))
    d.text((cell * 0.06, cell * 0.06), f"{zone['id']} / cell {c},{r}", font=f, fill=(150, 60, 55))
    d.text((cell * 0.06, cell * 0.06 + cell // 14), "MISSING TILE", font=f, fill=(150, 60, 55))
    return img


def unify(img, target_mean, strength=0.85):
    """Nudge a tile's mean colour toward the canvas mean, gently."""
    mean = img.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
    gains = []
    for m, t in zip(mean, target_mean):
        g = (t + 1) / (m + 1)
        g = max(0.90, min(1.10, g))
        gains.append(1.0 + (g - 1.0) * strength)
    lut = []
    for g in gains:
        lut.extend(min(255, int(v * g)) for v in range(256))
    return img.point(lut)


def draw_label(canvas, draw, box, text, font, text_rgb, scrim_alpha, scrim_rgb,
               pad_x, pad_y, radius, worst_backdrop, text_pos):
    """Composite a scrim then place text. Returns the achieved ratio at the worst patch."""
    x0, y0, x1, y1 = box
    composite = ac.mix(worst_backdrop, scrim_rgb, scrim_alpha)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                           fill=(scrim_rgb[0], scrim_rgb[1], scrim_rgb[2],
                                 int(scrim_alpha * 255)))
    draw.text(text_pos, text, font=font, fill=text_rgb)
    return ac.contrast_ratio(composite, text_rgb)


def text_plate(draw, text, font, x0, y0, pad_x, pad_y):
    """Plate that encloses the glyphs actually drawn, not the font's advance width.

    Advance width excludes the left side bearing, so plating from it always under-pads by
    that bearing — a couple of pixels, which at label scale is a character touching the edge.
    """
    tx, ty = int(x0 + pad_x), int(y0 + pad_y)
    bb = draw.textbbox((tx, ty), text, font=font)
    box = (int(bb[0] - pad_x), int(bb[1] - pad_y), int(bb[2] + pad_x), int(bb[3] + pad_y))
    return box, (tx, ty)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blueprint")
    ap.add_argument("-d", "--tile-dir", default="tiles")
    ap.add_argument("-o", "--out", default="atlas.png")
    ap.add_argument("--no-color-unify", action="store_true")
    ap.add_argument("--no-events", action="store_true", help="skip event dots and connectors")
    ap.add_argument("--no-cartouche", action="store_true", help="skip title/legend block")
    ap.add_argument("--allow-partial", action="store_true",
                    help="exit 0 even when tiles or contrast are unresolved (Gate 3 proof runs)")
    ap.add_argument("--report", default=None)
    ap.add_argument("--jpg-quality", type=int, default=94)
    args = ap.parse_args()

    bp = ac.load_blueprint(args.blueprint)
    cv = bp["meta"]["canvas"]
    cell = int(cv["cell"])
    cols, rows = int(cv["cols"]), int(cv["rows"])
    bleed = float(cv.get("bleed", 0.08))
    W, H = cols * cell, rows * cell

    palette = bp["palette"]
    ink = ac.hex_to_rgb(palette.get("ink", "#f2ece0"))
    accent = ac.hex_to_rgb(palette.get("accent", "#a63d2f"))
    muted = ac.hex_to_rgb(palette.get("muted", "#6f6a63"))

    report = {
        "output": os.path.abspath(args.out),
        "size": [W, H],
        "cell": cell,
        "contrast_floor": FLOOR,
        "tiles": {"expected": 0, "found": [], "missing": []},
        "contrast": {"checked": 0, "failures": []},
        "avatars": {"cropped": [], "symbol": [], "missing": []},
        "warnings": [],
    }

    canvas = Image.new("RGB", (W, H), ac.hex_to_rgb(palette.get("bg", "#17181a")))
    tiles = []

    # ---------------------------------------------------------------- pass 1: tiles
    for z in bp["zones"]:
        for c in range(int(z.get("col", 0)), int(z.get("col", 0)) + int(z.get("w", 1))):
            for r in range(int(z.get("row", 0)), int(z.get("row", 0)) + int(z.get("h", 1))):
                report["tiles"]["expected"] += 1
                path = find_tile(args.tile_dir, z, c, r)
                if path:
                    img = Image.open(path).convert("RGB")
                    report["tiles"]["found"].append(os.path.basename(path))
                    b = int(min(img.width, img.height) * bleed)
                    if b > 0 and img.width - 2 * b > 8 and img.height - 2 * b > 8:
                        img = img.crop((b, b, img.width - b, img.height - b))
                    tiles.append((img, c * cell, r * cell))
                else:
                    report["tiles"]["missing"].append(f"{z['id']}_{c}_{r}")
                    tiles.append((placeholder(cell, z, c, r), c * cell, r * cell))

    # ---------------------------------------------------------------- pass 2: colour unity
    if tiles and not args.no_color_unify:
        means = [t[0].resize((1, 1), Image.BOX).getpixel((0, 0)) for t in tiles]
        target = tuple(sum(m[i] for m in means) // len(means) for i in range(3))
        tiles = [(unify(img, target), x, y) for img, x, y in tiles]

    for img, x, y in tiles:
        if img.size != (cell, cell):
            img = img.resize((cell, cell), Image.LANCZOS)
        canvas.paste(img, (x, y))

    draw = ImageDraw.Draw(canvas, "RGBA")

    # ---------------------------------------------------------------- pass 3: seam dividers
    band = max(4, int(cell * 0.010))
    for z in bp["zones"]:
        x, y, w, h = ac.zone_rect(z, cell)
        reasons = z.get("seam_reason") or {}
        edges = {
            "left": [x, y, x + band, y + h],
            "right": [x + w - band, y, x + w, y + h],
            "top": [x, y, x + w, y + band],
            "bottom": [x, y + h - band, x + w, y + h],
        }
        for side, rect in edges.items():
            if side not in reasons:
                continue
            draw.rectangle(rect, fill=(0, 0, 0, 150))
            if side in ("left", "right"):
                lx = rect[2] if side == "left" else rect[0]
                draw.line([(lx, y), (lx, y + h)], fill=muted + (170,), width=max(1, band // 3))
            else:
                ly = rect[3] if side == "top" else rect[1]
                draw.line([(x, ly), (x + w, ly)], fill=muted + (170,), width=max(1, band // 3))

    # registration ticks at grid intersections — cartographic, not decorative
    tick = int(cell * 0.022)
    for c in range(cols + 1):
        for r in range(rows + 1):
            px, py = c * cell, r * cell
            draw.line([(px - tick, py), (px + tick, py)], fill=ink + (90,), width=2)
            draw.line([(px, py - tick), (px, py + tick)], fill=ink + (90,), width=2)

    # ---------------------------------------------------------------- pass 4: connectors first
    chidx = ac.chars_by_id(bp)
    epos = {}
    for z in bp["zones"]:
        x, y, w, h = ac.zone_rect(z, cell)
        for e in bp.get("events", []):
            if e.get("zone") != z["id"]:
                continue
            epos[e["id"]] = (x + float(e.get("x", 0.5)) * w, y + float(e.get("y", 0.5)) * h)

    if not args.no_events:
        zrect = {z["id"]: ac.zone_rect(z, cell) for z in bp["zones"]}
        ezone = {e.get("id"): e.get("zone") for e in bp.get("events", [])}
        stub = cell * 0.11          # how far a cross-zone link may reach inside a zone

        def exit_t(px, py, dx, dy, rect):
            """Distance from an interior point to the rectangle edge along (dx, dy)."""
            t = float("inf")
            if dx > 1e-9:
                t = min(t, (rect[2] - px) / dx)
            elif dx < -1e-9:
                t = min(t, (rect[0] - px) / dx)
            if dy > 1e-9:
                t = min(t, (rect[3] - py) / dy)
            elif dy < -1e-9:
                t = min(t, (rect[1] - py) / dy)
            return max(0.0, t)

        for e in bp.get("events", []):
            src = epos.get(e.get("id"))
            if not src:
                continue
            for other in e.get("link", []) or []:
                dst = epos.get(other)
                if not dst:
                    continue
                dx, dy = dst[0] - src[0], dst[1] - src[1]
                length = math.hypot(dx, dy) or 1.0
                ux, uy = dx / length, dy / length
                same_zone = ezone.get(e.get("id")) == ezone.get(other)
                if same_zone:
                    a, b = src, dst
                else:
                    # A straight rule laid across the painting reads as a scratch. Cut it to a
                    # stub on each side of the seam: the link still says "it continues over
                    # there", and no line crosses a face to say it.
                    ta = min(stub, exit_t(src[0], src[1], ux, uy, zrect[ezone[e["id"]]]))
                    tb = min(stub, exit_t(dst[0], dst[1], -ux, -uy, zrect[ezone[other]]))
                    a = src
                    b = (src[0] + ta * ux, src[1] + ta * uy)
                draw.line([a, b], fill=ink + (60,), width=max(2, int(cell * 0.0026)))
                if not same_zone:
                    draw.line([(dst[0] - tb * ux, dst[1] - tb * uy), dst],
                              fill=ink + (60,), width=max(2, int(cell * 0.0026)))
                tip = dst if same_zone else b
                ang = math.atan2(dy, dx)
                ah = cell * 0.011
                for sign in (0.5, -0.5):
                    draw.line([tip, (tip[0] - ah * math.cos(ang + sign),
                                     tip[1] - ah * math.sin(ang + sign))],
                              fill=ink + (80,), width=max(2, int(cell * 0.0022)))

    # ---------------------------------------------------------------- pass 5: remote avatars
    zone_map = ac.zone_by_id(bp)
    for z in bp["zones"]:
        x, y, w, h = ac.zone_rect(z, cell)
        for slot in z.get("avatar_slots", []) or []:
            cid = slot.get("character")
            ch = chidx.get(cid)
            name = ch.get("name", cid) if ch else cid
            if not ch:
                report["avatars"]["missing"].append({"character": cid, "zone": z["id"],
                                                     "reason": "unknown character"})
                continue
            port = ch.get("portrait") or {}
            home = zone_map.get(port.get("zone") or ch.get("home_zone"))
            box = port.get("box")
            size = max(24, int(float(slot.get("size", 0.08)) * min(w, h)))
            cx = x + float(slot.get("x", 0.5)) * w
            cy = y + float(slot.get("y", 0.5)) * h

            if home and box and len(box) == 4:
                hx, hy, hw, hh = ac.zone_rect(home, cell)
                crop = (int(hx + box[0] * hw), int(hy + box[1] * hh),
                        int(hx + (box[0] + box[2]) * hw), int(hy + (box[1] + box[3]) * hh))
                # Last line of defence. anchor.py is where these get fixed; by the time the
                # stitcher sees them it can only complain.
                cw, chh = crop[2] - crop[0], crop[3] - crop[1]
                if chh > 0 and abs(cw / float(chh) - 1.0) > 0.05:
                    msg = (f"avatar {name} in {z['id']}: portrait.box is {cw}x{chh}px, not "
                           f"square — the face is being squashed. Fix the box and re-run "
                           f"anchor.py")
                    report["warnings"].append(msg)
                    report["avatars"].setdefault("distorted", []).append(
                        {"character": name, "zone": z["id"], "crop": [cw, chh]})
                if cw and size > min(cw, chh) * 1.05:
                    report["warnings"].append(
                        f"avatar {name} in {z['id']}: drawn at {size}px from a "
                        f"{min(cw, chh)}px crop — upscaled, it will look soft")
                sub = canvas.crop(crop).resize((size, size), Image.LANCZOS)
                mask = Image.new("L", (size * 4, size * 4), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
                mask = mask.resize((size, size), Image.LANCZOS)
                draw.ellipse([cx - size / 2 - 3, cy - size / 2 - 3,
                              cx + size / 2 + 3, cy + size / 2 + 3], fill=ink + (200,))
                canvas.paste(sub, (int(cx - size / 2), int(cy - size / 2)), mask)
                report["avatars"]["cropped"].append({"character": name, "zone": z["id"],
                                                     "source": port.get("zone") or ch.get("home_zone")})
            else:
                # No portrait to crop. Draw a map node, not an empty ring: a hollow circle
                # at avatar size reads as a portrait that failed to load, which invites
                # "why is this person missing" instead of "this is a secondary character".
                r = size * 0.26
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink + (40,),
                             outline=ink + (185,), width=max(2, int(size * 0.022)))
                dot = r * 0.34
                draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=accent + (235,))
                report["avatars"]["symbol"].append({"character": name, "zone": z["id"],
                                                    "reason": "no portrait.box on home character"})

    # ---------------------------------------------------------------- pass 6: labels
    # The cartouche is painted last, on top of every label. Work out its footprint now so
    # that anything it would land on can be named in the report instead of silently sliced.
    cart = None if args.no_cartouche else ac.cartouche_geometry(bp, cell, W, H, draw)
    placed_boxes = []

    def place(text, px, py, px_size, zone_id, anchor="lt", marker=None, tonal=None,
              min_alpha=0.26):
        font = ac.resolve_font(max(10, int(px_size)))
        tw = ac.text_width(draw, text, font)
        th = int(px_size * 1.32)
        pad_x, pad_y = int(px_size * 0.42), int(px_size * 0.20)
        if anchor == "lt":
            ax, ay = px, py
        elif anchor == "ct":
            ax, ay = px - tw / 2, py
        elif anchor == "lm":
            ax, ay = px, py - th / 2
        else:
            ax, ay = px, py

        # Anything painted after the labels (the cartouche) has already claimed its rect.
        # A label straddling that edge is cut in half by it, so record the overlap: the
        # caller fixes it by moving the label, never by nudging it here — a marker dot and
        # the connector line that points at it are both anchored to the declared position.
        bw_, bh_ = tw + pad_x * 2, th + pad_y * 2
        placed_boxes.append((ax, ay, ax + bw_, ay + bh_, text))

        box, text_pos = text_plate(draw, text, font, ax, ay, pad_x, pad_y)
        x0, y0 = box[0], box[1]

        # Label treatment is per-ZONE, not per-label: one plate direction per zone keeps the
        # annotation layer looking drawn rather than accidental. Falls back to the
        # least-visible plate only when the zone's declared tone cannot reach the floor.
        forced = {"light": ((22, 22, 24), ink), "dark": (ink, (10, 10, 12))}.get(tonal)
        chosen = None
        if forced:
            text_rgb, toward = forced
            worst = ac.worst_case_rgb(canvas, box, text_rgb)
            need, _ = ac.scrim_to_reach(worst, text_rgb, FLOOR, toward,
                                        steps=max(5, int(MAX_SCRIM * 100) // 5))
            if need <= MAX_SCRIM:
                chosen = (text_rgb, toward, need, worst)

        if chosen is None:
            best = None
            for text_rgb, toward in ((ink, (10, 10, 12)), ((22, 22, 24), ink)):
                worst = ac.worst_case_rgb(canvas, box, text_rgb)
                need, _ = ac.scrim_to_reach(worst, text_rgb, FLOOR, toward,
                                            steps=max(5, int(MAX_SCRIM * 100) // 5))
                score = need - (0.02 if text_rgb == ink else 0.0)  # tie-break to light text
                if best is None or score < best[0]:
                    best = (score, text_rgb, toward, need, worst)
            _, text_rgb, toward, need, worst = best
            if forced:
                report["warnings"].append(
                    f"zone {zone_id}: declared tone '{tonal}' cannot reach {FLOOR}:1 — "
                    f"label '{text}' inverted to stay readable")
            chosen = (text_rgb, toward, need, worst)

        text_rgb, toward, need, worst = chosen
        # A name is the one label that is always laid over a body, so the auto-scrim
        # under-pads it: 26% reads fine on a wall and disappears on a plated torso.
        alpha = min(max(need, min_alpha), MAX_SCRIM)
        if marker:
            draw.ellipse([x0 - px_size * 0.9, y0 + th * 0.18,
                          x0 - px_size * 0.9 + px_size * 0.55, y0 + th * 0.18 + px_size * 0.55],
                         fill=marker + (240,), outline=ink + (200,), width=2)
        ratio = draw_label(canvas, draw, box, text, font, text_rgb, alpha, toward,
                           pad_x, pad_y, radius=max(2, int(px_size * 0.24)),
                           worst_backdrop=worst, text_pos=text_pos)
        report["contrast"]["checked"] += 1
        if ratio < FLOOR:
            draw.rectangle([box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1],
                           outline=(255, 60, 60, 180), width=2)
            report["contrast"]["failures"].append(
                {"zone": zone_id, "text": text, "ratio": round(ratio, 2),
                 "scrim_alpha": round(alpha, 2)})
        return box

    # ---------------------------------------------------------------- pass 5b: character names
    # A face without a name is a decoration. Both the home figure and every remote avatar
    # carry a name, composited here and never asked of the image model. Same contrast floor
    # as every other label, so a face lit like a nightclub still gets a readable caption.
    for z in bp["zones"]:
        x, y, w, h = ac.zone_rect(z, cell)
        for cid in z.get("characters", []) or []:
            ch = chidx.get(cid)
            if not ch:
                continue
            box = (ch.get("portrait") or {}).get("box")
            if not box or len(box) != 4:
                # A faceless character still gets its name: the skeleton showed one at
                # prop_at, and an unnamed prop on the finished atlas reads as background
                # furniture rather than as the character it stands for.
                if ch.get("faceless") and ch.get("prop_at"):
                    ppx, ppy = float(ch["prop_at"][0]), float(ch["prop_at"][1])
                    place(str(ch.get("name", cid)), x + ppx * w, y + ppy * h + cell * 0.042,
                          30 * cell / 2048.0, z["id"], anchor="ct", tonal=z.get("tonal"),
                          min_alpha=0.58)
                continue
            bx = x + float(box[0]) * w
            by = y + float(box[1]) * h
            bw = float(box[2]) * w
            bh = float(box[3]) * h
            place(str(ch.get("name", cid)), bx + bw * 0.5, by + bh + cell * 0.012,
                  30 * cell / 2048.0, z["id"], anchor="ct", tonal=z.get("tonal"),
                  min_alpha=0.58)
        for slot in z.get("avatar_slots", []) or []:
            ch = chidx.get(slot.get("character"))
            if not ch:
                continue
            size = max(24, int(float(slot.get("size", 0.08)) * min(w, h)))
            cx = x + float(slot.get("x", 0.5)) * w
            cy = y + float(slot.get("y", 0.5)) * h
            place(str(ch.get("name", slot.get("character"))),
                  cx, cy + size / 2 + cell * 0.010,
                  26 * cell / 2048.0, z["id"], anchor="ct", tonal=z.get("tonal"),
                  min_alpha=0.58)

    # ---------------------------------------------------------------- pass 6: zone titles
    for z in bp["zones"]:
        if z.get("hide_name"):
            continue
        x, y, w, h = ac.zone_rect(z, cell)
        place(str(z.get("name", "")), x + w * 0.026, y + h * 0.020,
              62 * cell / 2048.0, z["id"], anchor="lt", tonal=z.get("tonal"))
        if z.get("caption"):
            place(str(z["caption"]), x + w * 0.028, y + h * 0.074,
                  30 * cell / 2048.0, z["id"], anchor="lt", tonal=z.get("tonal"))

    for z in bp["zones"]:
        x, y, w, h = ac.zone_rect(z, cell)
        for lb in z.get("labels", []) or []:
            place(str(lb.get("text", "")),
                  x + float(lb.get("x", 0.5)) * w,
                  y + float(lb.get("y", 0.5)) * h,
                  float(lb.get("size", 40)) * cell / 2048.0,
                  z["id"], anchor=lb.get("anchor", "lt"), tonal=z.get("tonal"))

    if not args.no_events:
        efont = cell * 0.020
        for e in bp.get("events", []):
            pos = epos.get(e.get("id"))
            if not pos:
                continue
            kind = e.get("kind", "event")
            mark = accent if kind == "irreversible" else muted
            label = str(e.get("label", "")).strip()
            if not label:
                # No caption, still a node: the dot is the anchor the connectors point
                # at, and placing empty text would paint a plate with nothing in it.
                r_ = efont * 0.28
                draw.ellipse([pos[0] - r_, pos[1] - r_, pos[0] + r_, pos[1] + r_],
                             fill=mark + (240,), outline=ink + (200,), width=2)
                continue
            place(label, pos[0] + efont * 0.75, pos[1] - efont * 0.55,
                  efont, e.get("zone"), anchor="lt", marker=mark,
                  tonal=(zone_map.get(e.get("zone")) or {}).get("tonal"))

    # ---------------------------------------------------------------- label collisions
    # Labels are placed one by one, so two of them can still land on each other. Same test
    # skeleton.py runs at Gate 2, repeated here because only this pass knows the final plate
    # sizes. Reported, never auto-nudged: a name plate is welded to its portrait, and an
    # event's marker dot and leader line are anchored to its declared position.
    for i in range(len(placed_boxes)):
        for j in range(i + 1, len(placed_boxes)):
            a, b = placed_boxes[i], placed_boxes[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                report["warnings"].append(
                    f"label collision: '{a[4]}' vs '{b[4]}' at [{int(a[0])},{int(a[1])}] — "
                    f"the plates overlap; move one label in the blueprint")

    # ---------------------------------------------------------------- pass 7: cartouche + frame
    if not args.no_cartouche:
        cx0, cy0, cx1, cy1 = cart["rect"]
        for bx0, by0, bx1, by1, text in placed_boxes:
            if bx0 < cx1 and bx1 > cx0 and by0 < cy1 and by1 > cy0:
                report["warnings"].append(
                    f"label under the cartouche: '{text}' at [{int(bx0)},{int(by0)}] — "
                    f"the title block is painted over it. Move the label (not the block).")

        pad = cart["pad"]
        cw, ch_, cx0, cy0 = cart["cw"], cart["ch"], cart["cx0"], cart["cy0"]
        inner, wrapped = cart["inner"], cart["wrapped"]
        f_title, f_sub = cart["f_title"], cart["f_sub"]
        f_body, f_small = cart["f_body"], cart["f_small"]

        # The plate is near-opaque black, so its own colour is what the text sits on —
        # measure that, not the artwork, and lift the dim tone until it is legal.
        plate_alpha = 208 / 255.0
        worst = ac.worst_case_rgb(canvas, (cx0, cy0, cx0 + cw, cy0 + ch_), ink)
        plane = ac.mix(worst, (0, 0, 0), plate_alpha)
        title_rgb = ac.reach_on(plane, ink, (255, 255, 255), FLOOR)
        sub_rgb = ac.reach_on(plane, muted, ink, FLOOR)
        report["cartouche"] = {"plate": list(plane), "floor": FLOOR, "lines": []}

        draw.rectangle([cx0, cy0, cx0 + cw, cy0 + ch_], fill=(0, 0, 0, int(plate_alpha * 255)),
                       outline=accent + (200,), width=max(2, cell // 800))
        x = cx0 + pad
        y = cy0 + pad
        draw.text((x, y), bp["meta"]["title"], font=f_title, fill=title_rgb)
        report["cartouche"]["lines"].append(
            {"text": bp["meta"]["title"], "ratio": round(ac.contrast_ratio(plane, title_rgb), 2)})
        y += int(f_title.size * 1.35)
        sub = bp["meta"].get("subtitle", "")
        if sub:
            draw.text((x, y), sub, font=f_sub, fill=sub_rgb)
            report["cartouche"]["lines"].append(
                {"text": sub, "ratio": round(ac.contrast_ratio(plane, sub_rgb), 2)})
            y += int(f_sub.size * 1.6)
        y += int(f_sub.size * 0.55)
        draw.line([(x, y), (x + inner, y)], fill=accent + (110,), width=max(1, cell // 1100))
        y += int(f_body.size * 0.55)
        for text, font, strong, lh in wrapped:
            rgb = title_rgb if strong else sub_rgb
            draw.text((x, y), text, font=font, fill=rgb)
            report["cartouche"]["lines"].append(
                {"text": text, "ratio": round(ac.contrast_ratio(plane, rgb), 2)})
            y += lh
        if y > cy0 + ch_:
            report["warnings"].append(
                f"cartouche overflow: content ends at y={y}, plate bottom is {cy0 + ch_} — "
                f"lower the body font size or shorten the coverage lines")

    draw.rectangle([1, 1, W - 2, H - 2], outline=accent + (140,),
                   width=max(2, cell // 900))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    if args.out.lower().endswith((".jpg", ".jpeg")):
        canvas.save(args.out, quality=args.jpg_quality, subsampling=1)
    else:
        canvas.save(args.out)

    report_path = args.report or os.path.join(os.path.dirname(os.path.abspath(args.out)),
                                              "stitch_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"wrote {args.out}  ({W}x{H})")
    print(f"tiles  {len(report['tiles']['found'])}/{report['tiles']['expected']} found")
    print(f"labels {report['contrast']['checked']} checked, "
          f"{len(report['contrast']['failures'])} below {FLOOR}:1")
    print(f"avatars {len(report['avatars']['cropped'])} cropped, "
          f"{len(report['avatars']['symbol'])} symbol-only")
    if report["tiles"]["missing"]:
        print("\nMISSING TILES (shown as hatched placeholders):")
        for m in report["tiles"]["missing"][:20]:
            print("  - " + m)
    if report["contrast"]["failures"]:
        print("\nCONTRAST FAILURES — fix the label or its placement, then re-stitch:")
        for f_ in report["contrast"]["failures"][:20]:
            print(f"  - {f_['zone']} '{f_['text']}' at {f_['ratio']}:1")
    if report["warnings"]:
        print("\nWARNINGS:")
        for w in report["warnings"][:12]:
            print("  - " + w)
    print(f"report {report_path}")
    if ((report["tiles"]["missing"] or report["contrast"]["failures"]
         or report["avatars"].get("distorted")) and not args.allow_partial):
        sys.exit(2)


if __name__ == "__main__":
    main()
