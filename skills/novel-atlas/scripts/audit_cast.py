#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cast audit — block the stitch if a tile invented somebody the book never wrote.

The image model does not know the cast. Given "a hall of eleven alcoves" it will happily
put eleven faces in them, and every one of those faces is a lie the reader will try to
place. This step is the only thing standing between the model's improvisation and the
finished atlas, so it is a gate, not a note: every tile needs a recorded audit that is
newer than the tile, and any readable face that is not in the zone's `cast.named`
whitelist fails the run.

The audit itself is written by the reviewer (a vision pass over the tile), because
counting faces is a reading task, not a pixel task. This script only holds the record
honest: it re-hashes the tile so a regenerated image cannot inherit an old verdict.

Usage:
  audit_cast.py blueprint.json -d tiles                  # verify, exit 2 on any failure
  audit_cast.py blueprint.json -d tiles --init           # write empty entries for existing tiles
  audit_cast.py blueprint.json -d tiles --init z7        # ...only for z7

Audit file format (tiles/cast_audit.json):
  { "z7": { "tile": "tiles/z7_2_1.png", "sha256": "...", "verdict": "pass",
            "figures": [ {"character": "c_jeanne", "prominence": "face", "note": "..."},
                         {"character": null, "prominence": "figure", "note": "..."} ],
            "reviewer_note": "...", "fix": "..." } }

prominence:
  face     — a face a reader could recognise and try to name
  figure   — a body without a readable face
  prop     — an object that stands in for a non-humanoid character
"""
import argparse
import hashlib
import json
import os
import sys

PROM = ('face', 'figure', 'prop')


def tile_path(tiles_dir, z):
    return os.path.join(tiles_dir, f"{z['id']}_{z.get('col', 0)}_{z.get('row', 0)}.png")


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Verify every tile against its zone's cast whitelist")
    ap.add_argument('blueprint')
    ap.add_argument('-d', '--tiles', default=None, help='tiles directory (default: <blueprint dir>/tiles)')
    ap.add_argument('-a', '--audit', default=None, help='audit json (default: <tiles>/cast_audit.json)')
    ap.add_argument('--init', nargs='*', metavar='ZONE', help='create empty pending entries')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--require', action='store_true',
                    help='also fail when a zone has no tile yet (full-run mode)')
    args = ap.parse_args()

    bp = json.load(open(args.blueprint, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(args.blueprint))
    tdir = args.tiles or os.path.join(base, 'tiles')
    apath = args.audit or os.path.join(tdir, 'cast_audit.json')

    audit = {}
    if os.path.exists(apath):
        audit = json.load(open(apath, encoding='utf-8'))

    if args.init is not None:
        only = set(args.init) if args.init else None
        n = 0
        for z in bp['zones']:
            if only and z['id'] not in only:
                continue
            p = tile_path(tdir, z)
            if not os.path.exists(p):
                continue
            audit[z['id']] = {
                'tile': os.path.relpath(p, base),
                'sha256': sha(p),
                'verdict': 'pending',
                'figures': [],
                'reviewer_note': '',
                'fix': '',
            }
            n += 1
        os.makedirs(tdir, exist_ok=True)
        json.dump(audit, open(apath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"wrote {n} pending entr{'y' if n == 1 else 'ies'} to {os.path.relpath(apath, base)}")
        print("Fill in `figures` from a vision pass over each tile, then re-run without --init.")
        return 0

    hard, soft, rows = [], [], []
    for z in bp['zones']:
        p = tile_path(tdir, z)
        if not os.path.exists(p):
            if args.require:
                hard.append(f"{z['id']}: no tile at {os.path.relpath(p, base)}")
            continue
        rec = audit.get(z['id'])
        if not rec:
            hard.append(f"{z['id']}: tile exists but has no cast audit — run --init and fill it in")
            continue
        cur = sha(p)
        if rec.get('sha256') != cur:
            hard.append(f"{z['id']}: tile changed since the audit (sha mismatch) — "
                        f"the verdict belongs to a different image; re-audit")
            continue
        if rec.get('verdict') not in ('pass', 'fixed'):
            hard.append(f"{z['id']}: verdict is '{rec.get('verdict')}' — only pass/fixed may stitch")
            continue

        named = {n['character']: n for n in (z.get('cast') or {}).get('named', [])}
        extra_max = int((z.get('cast') or {}).get('extras_max', 0) or 0)
        seen, faceless_seen, extras = set(), [], 0
        for f in rec.get('figures', []):
            cid = f.get('character')
            pr = f.get('prominence')
            if pr not in PROM:
                hard.append(f"{z['id']}: figure entry has prominence '{pr}' (use face/figure/prop)")
            if cid is None:
                if pr == 'face':
                    hard.append(f"{z['id']}: unnamed face in frame "
                                f"({(f.get('note') or '')[:60]}) — a reader will try to name it")
                elif pr == 'figure':
                    extras += 1
                continue
            if cid not in named:
                hard.append(f"{z['id']}: figure '{cid}' is not in cast.named — "
                            f"the tile invented a character")
                continue
            seen.add(cid)
            if named[cid].get('prominence') == 'prop' and pr != 'prop':
                hard.append(f"{z['id']}: {cid} must appear as a prop, not as a {pr}")
            if pr == 'face':
                faceless_seen.append(cid)

        if extras > extra_max:
            hard.append(f"{z['id']}: {extras} extra figures against extras_max {extra_max} — "
                        f"cut the crowd or raise the cap and re-audit")
        expect = {c for c, n in named.items() if n.get('prominence') != 'prop'}
        for cid in sorted(expect - seen):
            soft.append(f"{z['id']}: {cid} is in the cast but was not found in the tile — "
                        f"it may have been cropped out or buried in shadow")
        for c, n in named.items():
            if n.get('prominence') == 'prop' and c in seen:
                r = next((f for f in rec['figures'] if f.get('character') == c), {})
                if r.get('prominence') == 'prop':
                    soft.append(f"{z['id']}: {c} appears as an object, as designed — "
                                f"make sure no face was drawn on it")

        rows.append({'zone': z['id'], 'tile': rec.get('tile'), 'verdict': rec.get('verdict'),
                     'named': len(seen), 'faces': len(faceless_seen), 'extras': extras})

    print(f"cast audit — {len(rows)} tile(s) checked, {len(hard)} problem(s), {len(soft)} note(s)\n")
    for r in rows:
        print(f"  {r['zone']:<4} {r['verdict']:<6} named {r['named']}  faces {r['faces']}  "
              f"extras {r['extras']}")
    for m in soft:
        print(f"\n[note]  {m}")
    for m in hard:
        print(f"\n[FAIL]  {m}")

    if args.out:
        json.dump({'rows': rows, 'problems': hard, 'notes': soft},
                  open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    if hard:
        print("\nEvery face on the atlas has to be somebody. Fix these before stitching.")
        return 2
    print("\nCast clean. Every readable face is on the list.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
