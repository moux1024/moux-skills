#!/usr/bin/env python3
"""Anchor calibration — the step between the style proof and the batch run.

Every remote avatar in the atlas is a crop of one home tile. That crop is the only thing
holding a character's face consistent across the canvas, so it has to be verified before
the other tiles are paid for, not after. This script answers the three questions that
neither the skeleton nor the final stitch can answer in time:

  1. Does `portrait.box` actually land on the face? (see the contact sheet)
  2. Is there enough pixel in that box for the largest place the character appears?
  3. Is the box square? A non-square box is silently stretched to a circle by the
     stitcher, so a 0.17 x 0.30 box ships a squashed face.

Run it twice: once after Gate 2 with no tiles (arithmetic only, still catches deformed
and undersized boxes), and again after Gate 3 with the home tiles present (contact sheet
for eye verification).

Usage:
  python3 scripts/anchor.py atlas_build/blueprint.json -t atlas_build/tiles -o atlas_build/anchors
  python3 scripts/anchor.py atlas_build/blueprint.json            # arithmetic only

Exit codes: 0 every portrait usable or awaiting a tile; 2 something must be fixed.
"""

import argparse
import hashlib
import json
import os
import re
import sys

from PIL import Image, ImageDraw

import atlas_common as ac

HERE = os.path.dirname(os.path.abspath(__file__))
METRICS_PATH = os.path.normpath(os.path.join(HERE, "..", "references", "style-metrics.json"))
STYLES_PATH = os.path.normpath(os.path.join(HERE, "..", "references", "art-styles.md"))

ASPECT_TOLERANCE = 0.05     # a box off square by more than this gets stretched visibly
ROW_H = 344
PANEL_TILE = 290
PANEL_AVATAR = 290
GUTTER = 22
SHEET_W = 1560


# ------------------------------------------------------------------ reference data

def load_metrics():
    with open(METRICS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {k: int(v["min_avatar_edge"]) for k, v in data["styles"].items()}


def style_table_edges():
    """Pull `Min avatar edge` out of art-styles.md so the doc and the json can be compared."""
    if not os.path.exists(STYLES_PATH):
        return {}
    out, current = {}, None
    with open(STYLES_PATH, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^##\s+\d+\.\s+`([A-Za-z_]+)`", line)
            if m:
                current = m.group(1)
                continue
            if current:
                m2 = re.match(r"^\|\s*Min avatar edge\s*\|\s*(\d+)\s*px", line)
                if m2:
                    out[current] = int(m2.group(1))
                    current = None
    return out


def check_style_sync(metrics):
    """A rule written in the docs but not in the code is a rule nobody enforces."""
    table = style_table_edges()
    problems = []
    for style, edge in table.items():
        if style not in metrics:
            problems.append(f"{style}: documented ({edge}px) but missing from style-metrics.json")
        elif metrics[style] != edge:
            problems.append(
                f"{style}: art-styles.md says {edge}px, style-metrics.json says {metrics[style]}px")
    for style in metrics:
        if style not in table:
            problems.append(f"{style}: in style-metrics.json but no documented table entry")
    return problems


# ------------------------------------------------------------------ geometry

def tile_path(tiles_dir, zone_id, col, row):
    if not tiles_dir:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(tiles_dir, f"{zone_id}_{col}_{row}{ext}")
        if os.path.exists(p):
            return p
    return None


def tile_fingerprint(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:10]


def demand_for(bp, cid, cell):
    """Largest on-canvas diameter this character is asked to appear at, across every zone."""
    best, where = 0, None
    for z in bp["zones"]:
        zw = int(z.get("w", 1)) * cell
        zh = int(z.get("h", 1)) * cell
        for slot in z.get("avatar_slots") or []:
            if slot.get("character") != cid:
                continue
            size = int(float(slot.get("size", 0.08)) * min(zw, zh))
            if size > best:
                best, where = size, z.get("id")
    return best, where


def analyse_one(bp, ch, cell, floor, style, zmap):
    """Geometry verdict for one T1 character. No pixels needed."""
    cid = ch.get("id")
    name = ch.get("name", cid)
    port = ch.get("portrait") or {}
    zid = port.get("zone") or ch.get("home_zone")
    zone = zmap.get(zid)

    row = {"id": cid, "name": name, "tier": ch.get("tier"), "home_zone": zid,
           "box": port.get("box"), "issues": [], "verdict": "pending"}

    if not zone:
        row["issues"].append({"code": "home_zone_missing",
                              "detail": f"home zone '{zid}' is not in the grid"})
        row["verdict"] = "fix"
        return row

    zw = int(zone.get("w", 1)) * cell
    zh = int(zone.get("h", 1)) * cell
    box = port.get("box")

    if not box or len(box) != 4:
        row["issues"].append({"code": "no_box",
                              "detail": "no portrait.box — every remote avatar degrades to a symbol"})
        row["verdict"] = "fix"
        demand, demand_zone = demand_for(bp, cid, cell)
        row.update({"demand_px": demand, "demand_zone": demand_zone, "floor_px": floor})
        return row

    bx, by, bw, bh = [float(v) for v in box]
    px, py = bw * zw, bh * zh
    side = min(px, py)
    aspect = (px / py) if py else 0.0
    demand, demand_zone = demand_for(bp, cid, cell)

    row.update({
        "crop_px": [int(round(px)), int(round(py))],
        "crop_side": int(round(side)),
        "aspect": round(aspect, 3),
        "demand_px": demand,
        "demand_zone": demand_zone,
        "floor_px": floor,
    })

    # 1. the box has to sit inside its home zone
    if bx < 0 or by < 0 or bx + bw > 1.0001 or by + bh > 1.0001:
        row["issues"].append({"code": "out_of_bounds",
                              "detail": "portrait.box extends past its home zone; the crop "
                                        "reads pixels from the neighbouring zone"})

    # 2. the box has to be square, because the stitcher force-fits it into a circle
    if abs(aspect - 1.0) > ASPECT_TOLERANCE:
        keep = min(px, py)
        nsx, nsy = keep / zw, keep / zh
        if aspect < 1.0:
            # tall box: almost always a standing-figure box mistaken for a portrait box.
            # The head is at the top, so take the square from there, not from the centre.
            nby = by
            why = "tall box reads as a standing figure, not a head; the square is taken from the top"
        else:
            nby = by + (bh - nsy) / 2
            why = "wide box; the square is taken from the centre"
        row["issues"].append({
            "code": "aspect",
            "detail": f"box is {px:.0f}x{py:.0f}px ({aspect:.2f}:1); the stitcher force-fits it "
                      f"into a circle, so the face arrives squashed. {why}",
            "suggested_box": [round(bx + (bw - nsx) / 2, 3), round(nby, 3),
                              round(nsx, 3), round(nsy, 3)],
        })

    # 3. enough pixel for the style's detail retention
    if floor and side < floor:
        row["issues"].append({
            "code": "below_style_floor",
            "detail": f"{int(side)}px crop against a {floor}px floor for {style}; the face "
                      f"will not survive",
        })

    # 4. enough pixel for the largest place the character actually appears
    if demand and side < demand:
        row["issues"].append({
            "code": "upscaled",
            "detail": f"cropped at {int(side)}px but drawn at {demand}px in {demand_zone}; "
                      f"the stitcher would upscale it",
        })

    # 5. never a real failure, but worth saying: no remote appearance means the box only
    #    needs to satisfy the style floor, and the character costs one tile and nothing else
    if not demand:
        row["issues"].append({"code": "home_only",
                              "detail": "no remote appearance — this portrait is never cropped",
                              "severity": "note"})

    hard = [i for i in row["issues"] if i.get("severity") != "note"]
    row["verdict"] = "fix" if hard else "ok"
    return row


def dashed_rect(draw, box, colour, width=2, dash=9, gap=7):
    x0, y0, x1, y1 = box
    for edge in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                 ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        (ax, ay), (bx, by) = edge
        length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if length <= 0:
            continue
        ux, uy = (bx - ax) / length, (by - ay) / length
        t = 0.0
        while t < length:
            t2 = min(t + dash, length)
            draw.line([(ax + ux * t, ay + uy * t), (ax + ux * t2, ay + uy * t2)],
                      fill=colour, width=width)
            t += dash + gap


# ------------------------------------------------------------------ contact sheet

def crop_avatar(bp, row, tiles_dir, cell, zmap):
    """Crop the box out of the tile that contains its centre. Returns (image, note)."""
    zone = zmap.get(row["home_zone"])
    box = row.get("box")
    if not zone or not box:
        return None, "no box"
    zw = int(zone.get("w", 1)) * cell
    zh = int(zone.get("h", 1)) * cell
    bx, by, bw, bh = [float(v) for v in box]

    cx = (bx + bw / 2) * zw
    cy = (by + bh / 2) * zh
    ci, cj = int(cx // cell), int(cy // cell)
    col = int(zone.get("col", 0)) + ci
    rw = int(zone.get("row", 0)) + cj
    path = tile_path(tiles_dir, zone["id"], col, rw)
    if not path:
        return None, f"no tile {zone['id']}_{col}_{rw}"

    img = Image.open(path).convert("RGB")
    sx, sy = img.width / float(cell), img.height / float(cell)
    x0 = (bx * zw - ci * cell) * sx
    y0 = (by * zh - cj * cell) * sy
    x1 = ((bx + bw) * zw - ci * cell) * sx
    y1 = ((by + bh) * zh - cj * cell) * sy
    img = img.crop((int(x0), int(y0), int(x1), int(y1)))
    if img.width < 8 or img.height < 8:
        return None, "crop empty"
    return img, os.path.basename(path)


def build_contact_sheet(bp, rows, tiles_dir, cell, metrics, style, out_path, sync_problems):
    """One row per T1: where the box sits on the artwork, what the crop looks like as a
    circle, and the numbers behind both. The sheet exists to be argued with by eye."""
    zmap = ac.zone_by_id(bp)
    palette = bp.get("palette") or {}
    ink = ac.hex_to_rgb(palette.get("ink"), (238, 232, 222))
    accent = ac.hex_to_rgb(palette.get("accent"), (166, 61, 47))
    bg = (17, 17, 19)
    panel = (28, 28, 31)
    dim = (146, 143, 138)

    shown = [r for r in rows if r["tier"] == "T1"]
    floor = metrics.get(style)
    header_h = 140
    footer_h = 118 + (24 * len(sync_problems) if sync_problems else 0)
    W = SHEET_W
    H = header_h + ROW_H * max(1, len(shown)) + footer_h

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img, "RGBA")
    f_title = ac.resolve_font(36)
    f_body = ac.resolve_font(22)
    f_small = ac.resolve_font(17)
    f_tiny = ac.resolve_font(15)

    draw.text((30, 20), "Anchor calibration · 锚点验收", font=f_title, fill=ink)
    draw.text((30, 72),
              f"style {style}   ·   min avatar edge {floor}px   ·   cell {cell}px"
              f"   ·   {len(shown)} T1",
              font=f_small, fill=dim)
    draw.text((30, 102),
              "红框是 portrait.box 在主图上的位置。它要框住的是脸，不是「那个人站在这里」。",
              font=f_tiny, fill=(124, 122, 118))
    draw.line([(0, header_h - 1), (W, header_h - 1)], fill=accent + (170,), width=2)

    thumb_x = 30
    avatar_x = thumb_x + PANEL_TILE + 34
    text_x = avatar_x + PANEL_AVATAR + 40
    text_w = W - text_x - 34
    pad_top = (ROW_H - PANEL_TILE) // 2

    pending = 0
    for i, row in enumerate(shown):
        y0 = header_h + i * ROW_H
        draw.rectangle([0, y0, W, y0 + ROW_H - 1], fill=panel if i % 2 == 0 else bg)
        py0 = y0 + pad_top

        # ---- left: the home tile as generated, with the crop rectangle on it
        zone = zmap.get(row.get("home_zone"))
        box = row.get("box")
        placed = False
        if zone and box:
            zw = int(zone.get("w", 1)) * cell
            zh = int(zone.get("h", 1)) * cell
            cx = (float(box[0]) + float(box[2]) / 2) * zw
            cy = (float(box[1]) + float(box[3]) / 2) * zh
            ci, cj = int(cx // cell), int(cy // cell)
            col = int(zone.get("col", 0)) + ci
            rw = int(zone.get("row", 0)) + cj
            path = tile_path(tiles_dir, zone["id"], col, rw)
            if path:
                tile = Image.open(path).convert("RGB")
                sc = min(PANEL_TILE / float(tile.width), PANEL_TILE / float(tile.height))
                tw, th = max(1, int(tile.width * sc)), max(1, int(tile.height * sc))
                thumb = tile.resize((tw, th), Image.LANCZOS)
                px = thumb_x + (PANEL_TILE - tw) // 2
                py = py0 + (PANEL_TILE - th) // 2
                img.paste(thumb, (px, py))
                rx0 = px + (float(box[0]) * zw - ci * cell) / cell * tw
                ry0 = py + (float(box[1]) * zh - cj * cell) / cell * th
                rx1 = px + ((float(box[0]) + float(box[2])) * zw - ci * cell) / cell * tw
                ry1 = py + ((float(box[1]) + float(box[3])) * zh - cj * cell) / cell * th
                draw.rectangle([rx0, ry0, rx1, ry1], outline=accent + (255,), width=3)
                suggestion = None
                for issue in row["issues"]:
                    if issue.get("suggested_box"):
                        suggestion = issue["suggested_box"]
                        break
                if suggestion:
                    sx0 = px + (suggestion[0] * zw - ci * cell) / cell * tw
                    sy0 = py + (suggestion[1] * zh - cj * cell) / cell * th
                    sx1 = px + ((suggestion[0] + suggestion[2]) * zw - ci * cell) / cell * tw
                    sy1 = py + ((suggestion[1] + suggestion[3]) * zh - cj * cell) / cell * th
                    dashed_rect(draw, (sx0, sy0, sx1, sy1), ink + (225,), width=2)
                tag = f"{zone['id']}  {col},{rw}"
                tagw = ac.text_width(draw, tag, f_tiny)
                draw.rectangle([px + 4, py + th - 24, px + 16 + tagw, py + th - 4],
                               fill=(0, 0, 0, 175))
                draw.text((px + 9, py + th - 23), tag, font=f_tiny, fill=ink)
                placed = True
        if not placed:
            pending += 1
            draw.rectangle([thumb_x, py0, thumb_x + PANEL_TILE, py0 + PANEL_TILE],
                           outline=(62, 62, 66), width=2)
            draw.text((thumb_x + 18, py0 + PANEL_TILE // 2 - 9),
                      "awaiting home tile", font=f_tiny, fill=(104, 102, 98))

        # ---- middle: the crop as it will actually be pasted — circular, square-fitted
        ay = y0 + pad_top
        av, note = crop_avatar(bp, row, tiles_dir, cell, zmap)
        if av:
            crop_side = int(min(av.size))
            big = av.resize((PANEL_AVATAR, PANEL_AVATAR), Image.LANCZOS)
            mask = Image.new("L", (PANEL_AVATAR * 4, PANEL_AVATAR * 4), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, PANEL_AVATAR * 4 - 1, PANEL_AVATAR * 4 - 1),
                                         fill=255)
            mask = mask.resize((PANEL_AVATAR, PANEL_AVATAR), Image.LANCZOS)
            draw.ellipse([avatar_x - 3, ay - 3,
                          avatar_x + PANEL_AVATAR + 2, ay + PANEL_AVATAR + 2],
                         fill=(44, 44, 48))
            img.paste(big, (avatar_x, ay), mask)
            draw.ellipse([avatar_x, ay, avatar_x + PANEL_AVATAR - 1, ay + PANEL_AVATAR - 1],
                         outline=ink + (110,), width=2)
            label = f"{av.width}×{av.height}px → {PANEL_AVATAR} 方"
            draw.text((avatar_x, ay + PANEL_AVATAR + 6), label, font=f_tiny, fill=dim)
        else:
            draw.rectangle([avatar_x, ay, avatar_x + PANEL_AVATAR, ay + PANEL_AVATAR],
                           outline=(62, 62, 66), width=1)
            draw.text((avatar_x + 16, ay + PANEL_AVATAR // 2 - 8), note or "no crop",
                      font=f_tiny, fill=(110, 108, 104))

        # ---- right: the numbers behind the verdict
        ty = y0 + 22
        draw.text((text_x, ty), row["name"], font=f_body, fill=ink)
        ty += 31
        draw.text((text_x, ty), f"{row['id']}    home {row.get('home_zone')}",
                  font=f_tiny, fill=dim)
        ty += 23
        if row.get("box"):
            b = row["box"]
            draw.text((text_x, ty), f"box  [{b[0]}, {b[1]}, {b[2]}, {b[3]}]",
                      font=f_tiny, fill=(174, 171, 166))
            ty += 20
        if row.get("crop_px"):
            draw.text((text_x, ty),
                      f"crop  {row['crop_px'][0]}×{row['crop_px'][1]}px    aspect "
                      f"{row.get('aspect')}",
                      font=f_tiny, fill=(174, 171, 166))
            ty += 20
        if row.get("demand_px"):
            draw.text((text_x, ty),
                      f"drawn at  {row['demand_px']}px  in {row.get('demand_zone')}    "
                      f"floor {floor}px",
                      font=f_tiny, fill=(174, 171, 166))
            ty += 20
        ty += 8

        hard = [x for x in row["issues"] if x.get("severity") != "note"]
        notes = [x for x in row["issues"] if x.get("severity") == "note"]
        for issue in hard[:2] + notes[:1]:
            colour = accent if issue.get("severity") != "note" else (126, 124, 120)
            draw.text((text_x, ty), "· " + issue["code"].replace("_", " "),
                      font=f_tiny, fill=colour)
            ty += 19
            for line in ac.wrap_cjk(draw, issue["detail"], f_tiny, text_w)[:2]:
                draw.text((text_x + 12, ty), line, font=f_tiny, fill=(150, 148, 144))
                ty += 18
            if issue.get("suggested_box"):
                draw.text((text_x + 12, ty), "→ " + str(issue["suggested_box"]),
                          font=f_tiny, fill=accent)
                ty += 19
        extra = len(hard) - 2
        if extra > 0:
            draw.text((text_x, ty), f"+{extra} more in anchor_report.json",
                      font=f_tiny, fill=(120, 118, 114))

    # ---- footer
    fy = H - footer_h + 12
    draw.line([(0, fy - 10), (W, fy - 10)], fill=accent + (120,), width=1)
    ok = len([r for r in rows if r["verdict"] == "ok"])
    fix = len([r for r in rows if r["verdict"] == "fix"])
    draw.text((30, fy), f"ok {ok}     fix {fix}     awaiting tile {pending}",
              font=f_small, fill=ink)
    draw.text((30, fy + 30),
              "框偏了就改 box —— 这几个数是手写的，不是算出来的。框准了但脸糊，说明主场人物在画里占得太小。",
              font=f_tiny, fill=(132, 130, 126))
    draw.text((30, fy + 54),
              "box 改为方框后要重跑本脚本，并再核对一次红框是否仍罩在脸上。",
              font=f_tiny, fill=(112, 110, 106))
    if sync_problems:
        yy = fy + 80
        for p in sync_problems[:8]:
            draw.text((30, yy), "style metric drift: " + p, font=f_tiny, fill=accent)
            yy += 24

    img.save(out_path)
    return img.size


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description="Verify T1 portrait crops before batch generation")
    ap.add_argument("blueprint")
    ap.add_argument("-t", "--tiles", help="directory of generated tiles; omit for arithmetic only")
    ap.add_argument("-o", "--out", help="output directory (default: <blueprint dir>/anchors)")
    ap.add_argument("--write-back", action="store_true",
                    help="apply square-aspect suggestions to the blueprint in place")
    args = ap.parse_args()

    bp = ac.load_blueprint(args.blueprint)
    cell = int(bp["meta"]["canvas"]["cell"])
    style = bp["meta"].get("style_id", "unspecified")
    metrics = load_metrics()
    floor = metrics.get(style)
    sync_problems = check_style_sync(metrics)
    zmap = ac.zone_by_id(bp)

    if floor is None:
        print(f"style '{style}' has no entry in references/style-metrics.json — "
              f"avatar size cannot be verified", file=sys.stderr)
        return 2

    # Faceless characters have no crop to verify. Listing them as "fix" would push the author
    # to invent a face; leaving them out silently would hide that the cast has a member with
    # no portrait, so they are reported separately.
    faceless = [ch.get("name", ch.get("id")) for ch in bp.get("characters", [])
                if ch.get("tier") == "T1" and ch.get("faceless")]
    rows = [analyse_one(bp, ch, cell, floor, style, zmap)
            for ch in bp.get("characters", [])
            if ch.get("tier") == "T1" and not ch.get("faceless")]

    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.blueprint)), "anchors")
    os.makedirs(out_dir, exist_ok=True)
    sheet_path = os.path.join(out_dir, "contact_sheet.png")
    report_path = os.path.join(out_dir, "anchor_report.json")

    # A box points at pixels. If the tile behind those pixels was regenerated, the box is
    # stale and nothing about the blueprint looks wrong — so the script has to remember.
    previous = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, encoding="utf-8") as f:
                previous = (json.load(f) or {}).get("tile_hashes") or {}
        except (ValueError, OSError):
            previous = {}
    current = {}
    if args.tiles:
        for z in bp["zones"]:
            tp = tile_path(args.tiles, z["id"], int(z.get("col", 0)), int(z.get("row", 0)))
            if tp:
                current[z["id"]] = tile_fingerprint(tp)
    stale = sorted(z for z, h in current.items()
                   if z in previous and previous[z] != h)
    size = build_contact_sheet(bp, rows, args.tiles, cell, metrics, style,
                               sheet_path, sync_problems)

    changed = False
    if args.write_back:
        for row in rows:
            for issue in row["issues"]:
                if issue["code"] == "aspect" and issue.get("suggested_box"):
                    for ch in bp["characters"]:
                        if ch.get("id") == row["id"]:
                            ch.setdefault("portrait", {})["box"] = issue["suggested_box"]
                            changed = True
        if changed:
            with open(args.blueprint, "w", encoding="utf-8") as f:
                json.dump(bp, f, ensure_ascii=False, indent=2)
            # Re-derive every verdict from the corrected boxes. Reporting a pass off the
            # pre-fix analysis would be a lie: squaring a box can drop it below the floor.
            rows = [analyse_one(bp, ch, cell, floor, style, zmap)
                    for ch in bp.get("characters", []) if ch.get("tier") == "T1"]
            build_contact_sheet(bp, rows, args.tiles, cell, metrics, style,
                                sheet_path, sync_problems)

    for row in rows:
        if row["verdict"] == "ok":
            continue
        print(f"[fix] {row['name']}  ({row['id']})")
        for issue in row["issues"]:
            if issue.get("severity") == "note":
                continue
            print(f"      {issue['code']}: {issue['detail']}")
            if issue.get("suggested_box"):
                print(f"      suggested box: {issue['suggested_box']}")

    notes = [(r["name"], i["detail"]) for r in rows for i in r["issues"]
             if i.get("severity") == "note"]
    for name, detail in notes:
        print(f"[note] {name}: {detail}")

    if sync_problems:
        print("\nstyle metric drift:", file=sys.stderr)
        for p in sync_problems:
            print("  - " + p, file=sys.stderr)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"style_id": style, "min_avatar_edge": floor, "cell": cell,
                   "rows": rows, "faceless": faceless, "tile_hashes": current, "stale_home_tiles": stale,
                   "summary": {"ok": len([r for r in rows if r["verdict"] == "ok"]),
                               "fix": len([r for r in rows if r["verdict"] == "fix"])},
                   "style_metric_drift": sync_problems}, f, ensure_ascii=False, indent=2)

    if stale:
        print("\n[stale] these home tiles were regenerated since the last calibration:")
        for zid in stale:
            print(f"  - {zid}: every portrait.box inside it now points at different pixels")
        print("  Look at the contact sheet again before generating anything else.")

    print(f"\ncontact sheet {sheet_path}  ({size[0]}x{size[1]})")
    print(f"report {report_path}")
    if changed:
        print("blueprint updated with square-aspect boxes")

    hard = any(r["verdict"] == "fix" for r in rows) or bool(sync_problems) or bool(stale)
    return 2 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
