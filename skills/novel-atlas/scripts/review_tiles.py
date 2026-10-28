#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tile review — judge the picture, not only the people in it.

`audit_cast.py` answers "is every face somebody". It cannot answer the three questions
that decide whether a tile is usable at all:

  intent        does this depict the thing the prompt asked for, or merely a scene of the
                right genre in the right costume?
  plausibility  does the world hold together — anatomy, weight, one light source, one era,
                one material? A figure standing inside a wall is not a style question.
  aesthetic     composition, negative space for the plates, tone against the proof tile.
                Hands with six fingers, a smeared face, self-similar texture: the model's
                three recurring uglies.

None of that is measurable, so this script does not measure it. It builds the artifact you
have to look at (a contact sheet assembled on the atlas grid, so drift and seam continuity
are visible in one picture), writes the checklist with each zone's own promise printed
above its questions, and then refuses to let a rubber stamp through: every tile needs a
hash-bound record with three axes and **one sentence of what the reviewer actually saw**.
An entry that says "pass" three times and nothing else is not a review, and the gate says
so.

Usage:
  review_tiles.py blueprint.json -d tiles                 # build sheet + checklist, verify
  review_tiles.py blueprint.json -d tiles --init          # pending entries for existing tiles
  review_tiles.py blueprint.json -d tiles --init z7 z9    # ...only those zones

Record (tiles/tile_review.json):
  { "z7": { "tile": "tiles/z7_2_1.png", "sha256": "...", "verdict": "pass",
            "axes": { "intent": "pass", "plausibility": "pass", "aesthetic": "pass" },
            "reviewer_note": "画的是排座次，人都在名单上，光从左上来；右手多一根指头已避开",
            "fix": "" } }

`sha256` is the hash of the zone's whole tile set in cell order — for a single-cell zone
that is the file's own hash, and for a spanning zone it covers every cell, so regenerating
one cell invalidates the verdict instead of hiding behind its neighbours.
"""
import argparse
import hashlib
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_common as ac

AXES = ('intent', 'plausibility', 'aesthetic')
# An axis that is not explicitly passed is not a pass. Silence is the failure mode this
# gate exists to catch, so the default value is the failing one.
AXIS_QUESTIONS = {
    'intent': '画的是上面那句话吗——不是「一个像这个题材的场景」',
    'plausibility': '人体、受力、光源、年代、材质自洽；没人穿模、悬空、同框重复、影子打架',
    'aesthetic': '重心与留白够不够放标注；色调与证明格一致；没有六指、糊脸、纹理自相似',
}


def zone_cells(zone):
    """(path-name, col, row) for every cell a zone occupies."""
    col0, row0 = int(zone.get('col', 0)), int(zone.get('row', 0))
    for dc in range(int(zone.get('w', 1))):
        for dr in range(int(zone.get('h', 1))):
            yield f"{zone['id']}_{col0 + dc}_{row0 + dr}.png", col0 + dc, row0 + dr


def zone_tiles(tiles_dir, zone):
    out = []
    for name, c, r in zone_cells(zone):
        p = os.path.join(tiles_dir, name)
        if os.path.exists(p):
            out.append((p, c, r))
    return out


def zone_sha(paths):
    """Hash of the zone's tile set, in the order given.

    Identical to the file's own sha256 when the zone is one cell, which keeps records
    written by earlier versions valid; different for a spanning zone, which is the point.
    """
    h = hashlib.sha256()
    for p in paths:
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
    return h.hexdigest()


def measure(path):
    """Mean colour of a tile, as reference — not as a verdict.

    Deliberately not automated into a drift check: zones differ in tone by design, and no
    statistic can tell designed variety from a tile that drifted. The numbers are here so a
    tile that looks wrong on the sheet can be quantified, not so the script can pass or fail
    it from arithmetic.
    """
    raw = Image.open(path).convert('RGB').resize((64, 64), Image.BILINEAR).tobytes()
    n = float(len(raw) // 3)
    r = sum(raw[0::3]) / n
    g = sum(raw[1::3]) / n
    b = sum(raw[2::3]) / n
    return {'mean': [round(r), round(g), round(b)],
            'hex': '#%02x%02x%02x' % (round(r), round(g), round(b)),
            'lum': round(0.2126 * r + 0.7152 * g + 0.0722 * b)}


def build_sheet(bp, tiles_dir, out, px):
    """Contact sheet assembled on the atlas grid — the drift and seam test.

    Tiles are pasted exactly where they will be stitched, so two things a per-tile look
    cannot show become visible in one image: a zone whose palette or light direction
    disagrees with its neighbours, and a `seam_reason` that was declared but not drawn.
    """
    cv = bp['meta']['canvas']
    cols, rows = int(cv['cols']), int(cv['rows'])
    W, H = cols * px, rows * px
    bg = ac.hex_to_rgb((bp.get('palette') or {}).get('bg', '#141414'))
    canvas = Image.new('RGB', (W, H), bg)
    missing, placed = [], []

    for z in bp['zones']:
        tiles = {c * 10000 + r: p for p, c, r in zone_tiles(tiles_dir, z)}
        for _, c, r in zone_cells(z):
            p = tiles.get(c * 10000 + r)
            if not p:
                missing.append(f"{z['id']}_{c}_{r}")
                continue
            im = Image.open(p).convert('RGB').resize((px, px), Image.LANCZOS)
            canvas.paste(im, (c * px, r * px))
        placed.append(z)

    # Seam lines on their own layer: colour coordinates read off the finished atlas are in
    # the same numbers, which is the point of drawing them at all.
    grid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for c in range(1, cols):
        gd.line([(c * px, 0), (c * px, H)], fill=(255, 255, 255, 70), width=1)
    for r in range(1, rows):
        gd.line([(0, r * px), (W, r * px)], fill=(255, 255, 255, 70), width=1)
    canvas = Image.alpha_composite(canvas.convert('RGBA'), grid).convert('RGB')

    draw = ImageDraw.Draw(canvas)
    f_id = ac.resolve_font(max(11, int(px * 0.042)), bold=True)
    f_duty = ac.resolve_font(max(9, int(px * 0.028)))
    for z in placed:
        x, y = int(z.get('col', 0)) * px, int(z.get('row', 0)) * px
        zx = int(z.get('w', 1)) * px
        chip = f"{z['id']}  {z.get('name', '')}"
        tw = ac.text_width(draw, chip, f_id)
        draw.rectangle([x, y, x + min(zx, tw + 18), y + int(px * 0.075)], fill=(0, 0, 0))
        draw.text((x + 8, y + int(px * 0.012)), chip, font=f_id, fill=(255, 255, 255))
        duty = str(z.get('duty', ''))
        if duty:
            lines = ac.wrap_cjk(draw, duty, f_duty, zx - 16)[:2]
            dy = y + int(px * 0.082)
            for line in lines:
                lw = ac.text_width(draw, line, f_duty)
                draw.rectangle([x, dy - 2, x + lw + 12, dy + f_duty.size + 3], fill=(0, 0, 0))
                draw.text((x + 7, dy), line, font=f_duty, fill=(255, 210, 120))
                dy += int(f_duty.size * 1.34)
        if not any(p for p, _, _ in zone_tiles(tiles_dir, z)):
            draw.text((x + 12, y + int(px * 0.30)), "NO TILE", font=f_id, fill=(255, 80, 80))

    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
    canvas.save(out, optimize=True)
    return missing


def cast_summary(zone):
    named = (zone.get('cast') or {}).get('named') or []
    bits = [f"{n.get('character')}×{n.get('figures', 1)}" for n in named]
    cap = (zone.get('cast') or {}).get('extras_max')
    if cap is not None:
        bits.append(f"无脸群像 ≤{cap}")
    return '，'.join(bits) if bits else '无具名角色'


def write_sheet_md(bp, tiles_dir, records, out):
    lines = [f"# 分格审图单 — {bp['meta'].get('title', '')}", '',
             f"{len(bp['zones'])} 格 · 三轴 · 一轴不过就重生成，不改记录", '',
             '审的是图，不是名单。名单另有一道（`audit_cast.py`）。', '']
    lines += ['| 格 | 分区 | 判 | 意图 | 合理 | 审美 | 实测底色 |', '|---|---|---|---|---|---|---|']
    mark = lambda v: '·' if v == 'pass' else ('×' if v == 'fail' else '—')
    for z in bp['zones']:
        rec = records.get(z['id']) or {}
        axes = rec.get('axes') or {}
        tiles = zone_tiles(tiles_dir, z)
        meas = measure(tiles[0][0]) if tiles else {}
        lines.append(
            f"| {z['id']} | {z.get('name', '')} | {rec.get('verdict', '—')} | "
            f"{mark(axes.get('intent'))} | {mark(axes.get('plausibility'))} | "
            f"{mark(axes.get('aesthetic'))} | {meas.get('hex', '—')} L{meas.get('lum', '—')} |")
    lines.append('')

    for z in bp['zones']:
        rec = records.get(z['id']) or {}
        tiles = zone_tiles(tiles_dir, z)
        lines += [f"## {z['id']}　{z.get('name', '')}", '']
        if not tiles:
            lines += ['**还没有图**，先出这一格。', '']
            continue
        lines.append('`' + '` `'.join(os.path.basename(p) for p, _, _ in tiles) + '`')
        lines.append('')
        lines.append(f"**这一格该画什么**：{z.get('duty', '（没写 duty）')}")
        lines.append(f"**该有谁**：{cast_summary(z)}")
        if z.get('caption'):
            lines.append(f"**图上会印的副题**：{z['caption']}")
        lines.append('')
        for ax in AXES:
            got = (rec.get('axes') or {}).get(ax)
            box = 'x' if got == 'pass' else ' '
            lines.append(f"- [{box}] **{ax}** — {AXIS_QUESTIONS[ax]}")
        if rec.get('reviewer_note'):
            lines += ['', f"> {rec['reviewer_note']}"]
        if rec.get('fix'):
            lines += ['', f"**修法**：{rec['fix']}"]
        lines.append('')

    lines += ['## 脚本不判什么', '',
              '- **不判漂移。** 每格实测底色印在上表右侧，只作参考：分区本来就按明暗设计，'
              '任何统计量都分不清「设计好的差异」和「跑偏的那一格」。漂移靠总览图并排看。',
              '- **不判接缝。** `seam_reason` 声明的东西有没有真画出来，也只能看——'
              '总览图是按拼接位置贴的，接缝就在那一列像素上。',
              '- **不判美。** 它只要求你写下一句看过的话：三个 pass 加一句空话不算审过。', '']
    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser(description="Review every tile for intent, plausibility and taste")
    ap.add_argument('blueprint')
    ap.add_argument('-d', '--tiles', default=None)
    ap.add_argument('-a', '--review', default=None,
                    help='review json (default: <tiles>/tile_review.json)')
    ap.add_argument('--init', nargs='*', metavar='ZONE', help='create pending entries')
    ap.add_argument('--px', type=int, default=520, help='contact-sheet cell size in px')
    ap.add_argument('--no-sheet', action='store_true', help='skip the contact sheet')
    ap.add_argument('--require', action='store_true', help='fail when a zone has no tile yet')
    ap.add_argument('-o', '--out', default=None, help='write the verdict table as json')
    args = ap.parse_args()

    bp = json.load(open(args.blueprint, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(args.blueprint))
    tdir = args.tiles or os.path.join(base, 'tiles')
    rpath = args.review or os.path.join(tdir, 'tile_review.json')

    records = {}
    if os.path.exists(rpath):
        records = json.load(open(rpath, encoding='utf-8'))

    if args.init is not None:
        only = set(args.init) if args.init else None
        n = 0
        for z in bp['zones']:
            if only and z['id'] not in only:
                continue
            tiles = zone_tiles(tdir, z)
            if not tiles:
                continue
            records[z['id']] = {
                'tile': os.path.relpath(tiles[0][0], base),
                'sha256': zone_sha([p for p, _, _ in tiles]),
                'verdict': 'pending',
                'axes': {a: 'pending' for a in AXES},
                'claim': str(z.get('duty', '')),
                'reviewer_note': '',
                'fix': '',
            }
            n += 1
        os.makedirs(tdir, exist_ok=True)
        json.dump(records, open(rpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"wrote {n} pending entr{'y' if n == 1 else 'ies'} to {os.path.relpath(rpath, base)}")
        print("Open the contact sheet, answer the three axes per tile, write one sentence "
              "about what you saw, then re-run without --init.")
        return 0

    if not args.no_sheet:
        sheet = os.path.join(tdir, 'tile_sheet.png')
        missing = build_sheet(bp, tdir, sheet, max(160, args.px))
        write_sheet_md(bp, tdir, records, os.path.join(tdir, 'review_sheet.md'))
        print(f"sheet     {os.path.relpath(sheet, base)}")
        print(f"checklist {os.path.relpath(os.path.join(tdir, 'review_sheet.md'), base)}")
        if missing:
            print(f"  {len(missing)} cell(s) with no tile: {', '.join(missing)}\n")

    hard, soft, rows = [], [], []
    for z in bp['zones']:
        tiles = zone_tiles(tdir, z)
        if not tiles:
            if args.require:
                hard.append(f"{z['id']}: no tile — the atlas cannot be reviewed with a hole in it")
            continue
        rec = records.get(z['id'])
        if not rec:
            hard.append(f"{z['id']}: tile exists but has no review — "
                        f"run --init, look at the sheet, fill it in")
            continue
        cur = zone_sha([p for p, _, _ in tiles])
        if rec.get('sha256') != cur:
            hard.append(f"{z['id']}: tile set changed since the review (sha mismatch) — "
                        f"a regenerated image cannot inherit the verdict; look at it again")
            continue

        axes = rec.get('axes') or {}
        note = str(rec.get('reviewer_note') or '').strip()
        if rec.get('verdict') in (None, 'pending'):
            hard.append(f"{z['id']}: not reviewed — verdict is '{rec.get('verdict')}'; "
                        f"the sheet is right there")
            continue
        missing_ax = [a for a in AXES if a not in axes]
        if missing_ax:
            hard.append(f"{z['id']}: axes missing {', '.join(missing_ax)} — "
                        f"an axis nobody answered is not a pass")
            continue

        failed = [a for a in AXES if axes[a] != 'pass']
        if failed:
            # Name the axis and carry the reviewer's own fix sentence into the failure, so
            # the next generation run starts from the observation instead of from a rerun.
            detail = '；'.join(f"{a} {axes[a]}" for a in failed)
            fix = str(rec.get('fix') or '').strip()
            hard.append(f"{z['id']}: {detail} — " +
                        (f"重出这一格：{fix[:110]}" if fix else
                         "重出这一格或裁掉问题部分，并在 fix 里写清改了什么"))
            continue
        if rec.get('verdict') not in ('pass', 'fixed'):
            hard.append(f"{z['id']}: all three axes pass but verdict is "
                        f"'{rec.get('verdict')}' — the record contradicts itself")
            continue
        # Three passes and no sentence is the shape of a rubber stamp. The whole value of
        # this step is that somebody described what they saw; a record without that is a
        # claim nobody can check later.
        if len(note) < 8:
            hard.append(f"{z['id']}: all three axes pass with no reviewer_note — "
                        f"write the one sentence you will want in three weeks")
            continue
        if rec.get('verdict') == 'fixed' and not str(rec.get('fix') or '').strip():
            soft.append(f"{z['id']}: marked fixed but `fix` is empty — "
                        f"say what was regenerated or cropped")

        rows.append({'zone': z['id'], 'verdict': rec.get('verdict'),
                     'axes': {a: axes[a] for a in AXES}, 'note': note[:60],
                     'tiles': len(tiles)})

    print(f"\ntile review — {len(rows)}/{len(bp['zones'])} tile set(s) reviewed, "
          f"{len(hard)} problem(s), {len(soft)} note(s)\n")
    for r in rows:
        print(f"  {r['zone']:<4} {r['verdict']:<6} intent {r['axes']['intent']:<5} "
              f"plausibility {r['axes']['plausibility']:<5} aesthetic {r['axes']['aesthetic']}")
    for m in soft:
        print(f"\n[note]  {m}")
    for m in hard:
        print(f"\n[FAIL]  {m}")

    if args.out:
        json.dump({'rows': rows, 'problems': hard, 'notes': soft},
                  open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    if hard:
        print("\nA tile is not approved because it is on the cast list. Fix these before stitching.")
        return 2
    print("\nEvery tile was looked at, three ways, by somebody who said what they saw.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
