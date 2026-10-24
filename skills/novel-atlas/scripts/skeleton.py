#!/usr/bin/env python3
"""Render a blueprint as a flat local diagram, and validate its geometry.

This is Gate 2. It costs nothing, takes seconds, and is the only chance to catch layout
mistakes before spending a full tile set on them.

Usage:
    python3 skeleton.py atlas_build/blueprint.json -o atlas_build/skeleton.png
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_common as ac  # noqa: E402


def dashed_rect(draw, box, colour, width=2, dash=14, gap=10):
    x0, y0, x1, y1 = [int(v) for v in box]
    for x in range(x0, x1, dash + gap):
        draw.line([(x, y0), (min(x + dash, x1), y0)], fill=colour, width=width)
        draw.line([(x, y1), (min(x + dash, x1), y1)], fill=colour, width=width)
    for y in range(y0, y1, dash + gap):
        draw.line([(x0, y), (x0, min(y + dash, y1))], fill=colour, width=width)
        draw.line([(x1, y), (x1, min(y + dash, y1))], fill=colour, width=width)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blueprint")
    ap.add_argument("-o", "--out", default="skeleton.png")
    ap.add_argument("--cell", type=int, default=420, help="preview pixels per grid cell")
    ap.add_argument("--show-duty", action="store_true",
                    help="also print each zone's internal duty line (design intent, never printed "
                         "on the final image). Off by default: this view should preview the "
                         "reader's view, and duty collides with bottom-edge seam chips.")
    args = ap.parse_args()

    bp = ac.load_blueprint(args.blueprint)
    cell = args.cell
    FOOTER_H = int(cell * 0.46)
    cols = bp["meta"]["canvas"]["cols"]
    rows = bp["meta"]["canvas"]["rows"]
    W, H = cols * cell, rows * cell

    palette = bp["palette"]
    bg = ac.hex_to_rgb(palette.get("bg", "#17181a"))
    ink = ac.hex_to_rgb(palette.get("ink", "#f2ece0"))
    accent = ac.hex_to_rgb(palette.get("accent", "#a63d2f"))
    muted = ac.hex_to_rgb(palette.get("muted", "#6f6a63"))

    img = Image.new("RGB", (W, H + FOOTER_H), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    problems = []
    f_zone = ac.resolve_font(max(14, int(cell * 0.062)))
    f_small = ac.resolve_font(max(11, int(cell * 0.032)))
    f_tiny = ac.resolve_font(max(10, int(cell * 0.026)))
    f_title = ac.resolve_font(max(18, int(cell * 0.085)))

    # --- grid
    for c in range(cols + 1):
        draw.line([(c * cell, 0), (c * cell, H)], fill=(255, 255, 255, 26), width=1)
    for r in range(rows + 1):
        draw.line([(0, r * cell), (W, r * cell)], fill=(255, 255, 255, 26), width=1)

    # --- zones
    zones = bp["zones"]
    header_boxes = []
    char_boxes = []
    for z in zones:
        x, y, w, h = ac.zone_rect(z, cell)
        pcol = ac.PRIMITIVE_COLORS.get(z.get("primitive", ""), (120, 120, 120))
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=pcol + (38,))
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=pcol + (235,), width=3)
        # header block mirrors what stitch.py will draw on the final image.
        # 0.16 of the zone height is the reserved band; labels must sit below it.
        head_h = int(cell * 0.158)
        draw.rectangle([x, y, x + w - 1, y + head_h], fill=(0, 0, 0, 130))
        label = f"{z.get('id', '?')}  {z.get('name', '')}"
        ny = y + int(cell * 0.008)
        draw.text((x + 8, ny), label, font=f_zone, fill=ink)
        hy = ny + int(f_zone.size * 1.34)
        if z.get("caption"):
            # Wrapped at the zone's own width. An unwrapped caption silently runs into the
            # neighbouring zone and the collision pass below never sees it.
            cap_lines = ac.wrap_cjk(draw, str(z["caption"]), f_small, w - 20)[:2]
            for i, line in enumerate(cap_lines):
                draw.text((x + 10, hy + i * int(f_small.size * 1.3)), line,
                          font=f_small, fill=ink + (215,))
        header_boxes.append((z["id"], label, (x, y, x + w, y + head_h)))
        # duty — design intent, not printed on the final image. Off by default so this
        # view previews exactly what the reader will see; bottom-edge seam chips would
        # otherwise cut through the sentence.
        if args.show_duty:
            duty_lines = ac.wrap_cjk(draw, z.get("duty", ""), f_tiny, w - 24)[:3]
            dy = y + h - int(cell * 0.02) - len(duty_lines) * int(f_tiny.size * 1.35)
            for line in duty_lines:
                draw.text((x + 12, dy), line, font=f_tiny, fill=(255, 255, 255, 120))
                dy += int(f_tiny.size * 1.35)

    # --- seams
    seam_seen = set()
    for z in zones:
        x, y, w, h = ac.zone_rect(z, cell)
        reasons = z.get("seam_reason") or {}
        edges = {
            "left": [(x, y), (x, y + h)],
            "right": [(x + w - 1, y), (x + w - 1, y + h)],
            "top": [(x, y), (x + w, y)],
            "bottom": [(x, y + h - 1), (x + w, y + h - 1)],
        }
        for side, pts in edges.items():
            if side in reasons:
                draw.line(pts, fill=accent + (210,), width=6)
                mx = (pts[0][0] + pts[1][0]) // 2
                my = (pts[0][1] + pts[1][1]) // 2
                key = (round(mx / 24), round(my / 24))
                if key in seam_seen:
                    continue
                seam_seen.add(key)
                txt = str(reasons[side])
                tw = ac.text_width(draw, txt, f_tiny)
                th = int(f_tiny.size * 1.5)
                # Sit beside the line, never on it: a label buried in the divider it
                # describes is the one thing this view exists to rule out.
                off = 14
                if side == "left":
                    lx = mx + off
                elif side == "right":
                    lx = mx - off - tw - 12
                else:
                    lx = mx - tw // 2 - 6
                ly = my - th // 2 if side in ("left", "right") else (
                    my + off - th // 2 if side == "top" else my - off - th // 2)
                draw.rectangle([lx, ly, lx + tw + 12, ly + th], fill=(0, 0, 0, 255),
                               outline=accent + (200,), width=1)
                draw.text((lx + 6, ly + 1), txt, font=f_tiny, fill=ink)

    # --- characters (home full-body boxes)
    cidx = ac.chars_by_id(bp)
    for z in zones:
        x, y, w, h = ac.zone_rect(z, cell)
        for cid in z.get("characters", []) or []:
            ch = cidx.get(cid)
            if not ch:
                problems.append(f"zone {z['id']}: unknown character '{cid}'")
                continue
            if ch.get("faceless"):
                # A character with no human face cannot own a portrait box: there is no face
                # to crop, and forcing one produces either a symbol that reads as a failure
                # or a face the book never described. Mark the prop's place instead.
                px, py = ch.get("prop_at") or [0.5, 0.5]
                cx, cy = x + float(px) * w, y + float(py) * h
                s = cell * 0.030
                draw.rectangle([cx - s, cy - s, cx + s, cy + s],
                               outline=(255, 255, 255, 190), width=2)
                draw.line([cx - s, cy - s, cx + s, cy + s], fill=(255, 255, 255, 120), width=1)
                nm = ch.get("name", cid)
                draw.text((cx - ac.text_width(draw, nm, f_tiny) / 2, cy + s + cell * 0.008),
                          nm, font=f_tiny, fill=(255, 255, 255, 235))
                char_boxes.append((z["id"], nm, (cx - s, cy - s, cx + s, cy + s)))
                if ch.get("home_zone") and ch["home_zone"] != z["id"]:
                    problems.append(
                        f"character {ch['name']}: home_zone {ch['home_zone']} but placed in zone {z['id']}")
                continue

            box = (ch.get("portrait") or {}).get("box")
            if box and len(box) == 4:
                bx = x + box[0] * w
                by = y + box[1] * h
                bw = box[2] * w
                bh = box[3] * h
            else:
                bw, bh = w * 0.16, h * 0.40
                bx, by = x + w * 0.5 - bw / 2, y + h * 0.55 - bh / 2
                if not box:
                    problems.append(
                        f"character {ch['name']}: no portrait.box — the home tile will be "
                        f"cropped by guesswork, remote avatars will point at the wrong pixels")
            dashed_rect(draw, (bx, by, bx + bw, by + bh), (255, 255, 255, 190), width=2)
            # Name goes under the figure, not above it: above collides with the zone's
            # header band as soon as portrait.box.y is near 0.105.
            nm = ch.get("name", cid)
            nlx, nly = bx, by + bh + int(cell * 0.010)
            draw.text((nlx, nly), nm, font=f_tiny, fill=(255, 255, 255, 235))
            char_boxes.append((z["id"], nm, (nlx, nly,
                                            nlx + ac.text_width(draw, nm, f_tiny),
                                            nly + int(f_tiny.size * 1.2))))
            if ch.get("home_zone") and ch["home_zone"] != z["id"]:
                problems.append(
                    f"character {ch['name']}: home_zone {ch['home_zone']} but placed in zone {z['id']}")

            # Geometry only. Whether the crop lands on the face and whether it holds enough
            # pixel both need the artwork, and belong to anchor.py after the style proof.
            if box and len(box) == 4:
                fx, fy, fw, fh = [float(v) for v in box]
                if fx < 0 or fy < 0 or fx + fw > 1.0001 or fy + fh > 1.0001:
                    problems.append(
                        f"character {ch['name']}: portrait.box leaves its home zone "
                        f"{z['id']} — the crop would read the neighbouring zone's pixels")
                if fh > 0 and abs((fw * w) / (fh * h) - 1.0) > 0.05:
                    problems.append(
                        f"character {ch['name']}: portrait.box is {fw * w:.0f}x{fh * h:.0f}px, "
                        f"not square — stitch.py force-fits it into a circle, so the face "
                        f"arrives squashed. A standing figure is not a portrait box; "
                        f"square it by hand or with `anchor.py --write-back`")

    # --- cast whitelist
    # One authority for who may be drawn in a zone. Both the home characters and the remote
    # avatars must appear here, and the prompt repeats the count, so a tile that invents a
    # bystander is contradicted by the blueprint instead of quietly accepted.
    for z in zones:
        cast = z.get("cast") or {}
        named = cast.get("named") or []
        ids = [n.get("character") for n in named]
        for cid2 in ids:
            if cid2 not in cidx:
                problems.append(f"zone {z['id']}: cast.named references unknown character '{cid2}'")
        if not named:
            continue
        for cid2 in z.get("characters", []) or []:
            if cid2 not in ids:
                problems.append(
                    f"zone {z['id']}: home character '{cid2}' is not in cast.named — "
                    f"the cast list is the whitelist, so it would be drawn but never audited")
        for slot in z.get("avatar_slots", []) or []:
            if slot.get("character") not in ids:
                problems.append(
                    f"zone {z['id']}: remote avatar '{slot.get('character')}' is not in cast.named")

    # --- remote avatars
    for z in zones:
        x, y, w, h = ac.zone_rect(z, cell)
        for slot in z.get("avatar_slots", []) or []:
            cid = slot.get("character")
            ch = cidx.get(cid)
            name = ch.get("name", cid) if ch else cid
            if not ch:
                problems.append(f"zone {z['id']}: avatar slot for unknown character '{cid}'")
            elif ch.get("faceless"):
                problems.append(
                    f"zone {z['id']}: {name} is faceless — a remote avatar would have to "
                    f"invent a face the book never gives; draw the prop instead")
            elif not (ch.get("portrait") or {}).get("box"):
                problems.append(
                    f"zone {z['id']}: remote avatar for {name} has no home portrait.box — "
                    f"it will fall back to a symbol marker")
            size = max(18, int(float(slot.get("size", 0.08)) * min(w, h)))
            cx = x + float(slot.get("x", 0.5)) * w
            cy = y + float(slot.get("y", 0.5)) * h
            draw.ellipse([cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2],
                         outline=(255, 255, 255, 200), width=2)
            # Name under the circle, centred: beside it, a tight cluster of four avatars
            # pushes each caption into its neighbour.
            ntw = ac.text_width(draw, name, f_tiny)
            nlx = cx - ntw / 2
            nly = cy + size / 2 + int(cell * 0.010)
            if nly + f_tiny.size * 1.2 > y + h - 4:       # no room below: sit above
                nly = cy - size / 2 - int(cell * 0.010) - f_tiny.size * 1.2
            draw.text((nlx, nly), name, font=f_tiny, fill=(255, 255, 255, 220))
            char_boxes.append((z["id"], name, (nlx, nly,
                                              nlx + ntw, nly + int(f_tiny.size * 1.2))))

    # --- events and connectors
    epos = {}
    event_boxes = []
    for e in bp.get("events", []):
        z = next((zz for zz in zones if zz["id"] == e.get("zone")), None)
        if not z:
            problems.append(f"event {e.get('id')}: unknown zone '{e.get('zone')}'")
            continue
        x, y, w, h = ac.zone_rect(z, cell)
        ex = x + float(e.get("x", 0.5)) * w
        ey = y + float(e.get("y", 0.5)) * h
        epos[e.get("id")] = (ex, ey)
        r = max(5, int(cell * 0.016))
        irreversible = e.get("kind") == "irreversible"
        draw.ellipse([ex - r, ey - r, ex + r, ey + r],
                     fill=(accent if irreversible else muted) + (235,),
                     outline=(255, 255, 255, 220), width=2)
        txt = e.get("label", "")
        lh = int(f_tiny.size * 1.2)
        for i, line in enumerate(ac.wrap_cjk(draw, txt, f_tiny, int(cell * 0.40))):
            tw = ac.text_width(draw, line, f_tiny)
            ty = ey - r + i * lh
            draw.text((ex + r + 6, ty), line, font=f_tiny, fill=(255, 255, 255, 230))
            event_boxes.append((z["id"], f"{e.get('id')}:{txt}",
                                (ex + r + 6, ty, ex + r + 6 + tw, ty + lh)))

    for e in bp.get("events", []):
        src = epos.get(e.get("id"))
        if not src:
            continue
        for other in e.get("link", []) or []:
            dst = epos.get(other)
            if dst:
                draw.line([src, dst], fill=(255, 255, 255, 70), width=2)
            else:
                problems.append(f"event {e.get('id')}: link to unknown event '{other}'")

    # --- labels drawn for preview
    boxes = list(header_boxes) + list(event_boxes) + list(char_boxes)
    for z in zones:
        x, y, w, h = ac.zone_rect(z, cell)
        for lb in z.get("labels", []) or []:
            lx = x + float(lb.get("x", 0.5)) * w
            ly = y + float(lb.get("y", 0.5)) * h
            size = max(9, int(float(lb.get("size", 40)) * cell / 2048.0))
            font = ac.resolve_font(size)
            text = lb.get("text", "")
            tw = ac.text_width(draw, text, font)
            th = int(size * 1.3)
            draw.rectangle([lx - 2, ly - 2, lx + tw + 2, ly + th], fill=bg + (150,))
            draw.text((lx, ly - 1), text, font=font, fill=ink)

    # --- label collision, measured at the atlas's real cell, not at preview scale
    # Preview-scale boxes are quantised: at 420px a 93px gap in the shipped image is 19px,
    # and a 9px minimum font is wider than the label really is. That both invented
    # collisions and hid a name plate sitting on an event's tail, so measure where the
    # stitcher will actually paint and report those rects.
    full_cell = int(bp["meta"]["canvas"]["cell"])
    k = cell / float(full_cell)
    lbx = ac.label_boxes(bp, full_cell)
    solid = [r for r in lbx if r[1] not in ("zone", "caption")]

    for i in range(len(solid)):
        for j in range(i + 1, len(solid)):
            if ac.rects_overlap(solid[i][3], solid[j][3]):
                problems.append(
                    f"label collision: '{solid[i][2]}' ({solid[i][0]}) vs "
                    f"'{solid[j][2]}' ({solid[j][0]})")

    # A zone's header band is reserved: nothing may sit on the title it carries.
    for z in zones:
        x, y, w, _ = ac.zone_rect(z, full_cell)
        band = (x, y, x + w, y + int(full_cell * 0.158))
        for zi, kind, ti, bi in solid:
            if ac.rects_overlap(band, bi):
                problems.append(
                    f"label in the zone header band: '{ti}' ({zi}) sits on zone {z['id']}'s "
                    f"title band; move it below y {0.158:.3f} of that zone")

    # --- grid coverage / overlap check
    owner = {}
    for z in zones:
        for c in range(int(z.get("col", 0)), int(z.get("col", 0)) + int(z.get("w", 1))):
            for r in range(int(z.get("row", 0)), int(z.get("row", 0)) + int(z.get("h", 1))):
                if (c, r) in owner:
                    problems.append(f"cells ({c},{r}) claimed by both {owner[(c, r)]} and {z['id']}")
                owner[(c, r)] = z["id"]
                if c >= cols or r >= rows:
                    problems.append(f"zone {z['id']} extends outside the {cols}x{rows} grid")
    missing = [(c, r) for c in range(cols) for r in range(rows) if (c, r) not in owner]
    if missing:
        problems.append(f"{len(missing)} grid cells have no zone: {missing[:8]}")

    # --- title block: reserved here, painted by stitch.py after the labels
    # Measured at the atlas's real cell, then scaled to preview. Measuring at preview size
    # would wrap the coverage lines differently and hand back a shorter block than the one
    # stitch.py ships, so the reservation would under-report the area it steals.
    cart = ac.cartouche_geometry(bp, full_cell, cols * full_cell, rows * full_cell,
                                 ImageDraw.Draw(Image.new("RGB", (8, 8))))
    crx0, cry0, crx1, cry1 = [v * k for v in cart["rect"]]
    for zi, kind, ti, bi in lbx:
        if ac.rects_overlap(cart["rect"], bi):
            problems.append(
                f"label under the title block: '{ti}' ({zi}) at "
                f"[{int(bi[0])},{int(bi[1])}] — stitch.py paints the block after the "
                f"labels and will slice this one in half; move the label, not the block")
    draw.rectangle([crx0, cry0, crx1, cry1], outline=(255, 208, 88, 235), width=2)
    draw.text((crx0 + 6, cry0 + 4), "title block — painted last, keep clear",
              font=f_tiny, fill=(255, 208, 88, 235))

    # --- footer cartouche (appended below the canvas so it never hides the layout)
    fh = FOOTER_H
    fy = H
    draw.rectangle([0, fy, W, H + fh], fill=(0, 0, 0, 235))
    draw.line([(0, fy), (W, fy)], fill=accent, width=3)

    cur = fy + int(cell * 0.022)
    left = int(cell * 0.03)
    draw.text((left, cur), bp["meta"]["title"], font=f_title, fill=ink)
    cur += int(f_title.size * 1.30)
    sub = f"{bp['meta'].get('subtitle', '')}   ·   style: {bp['meta'].get('style_id', '')}"
    draw.text((left, cur), sub, font=f_small, fill=muted)
    cur += int(f_small.size * 1.75)
    st = bp.get("structure", {})
    st_line = ("time:" + st.get("time_continuity", "?") +
               "   causal:" + st.get("causal_chain", "?") +
               "   centrality:" + st.get("centrality", "?") +
               "   asymmetry:" + st.get("info_asymmetry", "?"))
    draw.text((left, cur), st_line, font=f_small, fill=ink)
    cur += int(f_small.size * 1.75)
    prim = "  ".join(f"{p.get('id')}[{p.get('role')}]" for p in bp.get("primitives", []))
    draw.text((left, cur), prim, font=f_small, fill=accent)
    cur += int(f_small.size * 1.75)
    cov = bp.get("coverage", {})
    cov_line = (f"chapters {len(cov.get('chapters_covered', []))}/{cov.get('chapters_total', '?')}"
                f"   turning {cov.get('turning_covered', '?')}/{cov.get('turning_total', '?')}"
                f"   T1 {len([c for c in bp.get('characters', []) if c.get('tier') == 'T1'])}"
                f"   T2 {len([e for e in bp.get('events', []) if e.get('tier') == 'T2'])}")
    draw.text((left, cur), cov_line, font=f_small, fill=ink)
    cur += int(f_tiny.size * 1.75)
    miss = cov.get("chapters_missing") or []
    if miss:
        draw.text((left, cur),
                  "missing chapters: " + ", ".join(str(m) for m in miss[:24]) +
                  (" …" if len(miss) > 24 else ""), font=f_tiny, fill=muted)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    img.save(args.out)
    print(f"wrote {args.out}  ({img.width}x{img.height})")
    print(f"zones {len(zones)}  events {len(bp.get('events', []))}  "
          f"labels {len(boxes)}  characters {len(bp.get('characters', []))}")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S) — fix before Gate 3:")
        for p in problems:
            print("  - " + p)
        sys.exit(2)
    print("\nGeometry clean. Show this to the user before generating any tile.")


if __name__ == "__main__":
    main()
