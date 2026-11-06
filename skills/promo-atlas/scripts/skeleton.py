#!/usr/bin/env python3
"""Gate 2 — skeleton: the flat diagram, and every target previewed, before a single tile.

Zero generation cost, seconds to run, and the last moment a coordinate mistake is free.

Checks run at the atlas's REAL cell size (plates, fonts, character capacity), while the
preview renders at a smaller cell: the layout is purely ratio-driven, so a caption that
fits at 2048 fits at 720, and a caption that overflows here overflows there. Judging the
preview instead of the numbers is how a collision reaches the stitcher.

Usage
  python3 skeleton.py build/blueprint.json -o build/skeleton.png --targets
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402
import stitch  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="promo-atlas gate 2: skeleton + target previews")
    ap.add_argument("blueprint")
    ap.add_argument("-o", "--out", default="skeleton.png")
    ap.add_argument("--cell", type=int, default=640, help="preview cell size in px")
    ap.add_argument("--targets", action="store_true", help="also preview every target")
    ap.add_argument("--no-check", action="store_true")
    args = ap.parse_args()

    bp_path = os.path.abspath(args.blueprint)
    base = os.path.dirname(bp_path)
    bp = pl.resolve_asset_paths(pl.load(bp_path), base)

    problems, warnings = ([], []) if args.no_check else pl.check_geometry(bp)

    grid, row_map, col_map = pl.make_grid(bp, cell=args.cell)
    mapping = pl.matrix_mapping(row_map, col_map)
    img, tstats, nzones = stitch.render(bp, grid, mapping, tiles_dir=None,
                                        mode="skeleton", allow_partial=True, cell=args.cell)
    out = os.path.abspath(args.out)
    pc.ensure_dir(os.path.dirname(out))
    img.save(out)
    print("skeleton: %s  (%d×%d, %d zones)" % (out, img.width, img.height, nzones))

    if args.targets:
        stem, ext = os.path.splitext(out)
        for t in bp.get("targets", []):
            if t.get("type") == "carousel":
                # A carousel has no single frame to preview: every page must be checked,
                # because a page that only works after the previous one dies on a screenshot.
                try:
                    pages = stitch.render_carousel(bp, t, tiles_dir=None, mode="skeleton",
                                                   allow_partial=True, cell=args.cell)
                except Exception as exc:  # noqa: BLE001
                    problems.append("target %s 轮播渲染失败: %s" % (t.get("id"), exc))
                    continue
                for pg in pages:
                    ppath = "%s_%s_p%02d%s" % (stem, t.get("id"), pg["index"], ext or ".png")
                    pg["image"].save(ppath)
                    print("  target %-12s p%02d/%02d %-6s %4d×%-4d" % (
                        t.get("id"), pg["index"], len(pages), pg["kind"],
                        pg["image"].width, pg["image"].height))
                continue
            try:
                timg, tgrid, st = stitch.render_target(
                    bp, t, tiles_dir=None, mode="skeleton", allow_partial=True, cell=args.cell)
            except Exception as exc:  # noqa: BLE001
                problems.append("target %s 渲染失败: %s" % (t.get("id"), exc))
                continue
            tpath = "%s_%s%s" % (stem, t.get("id"), ext or ".png")
            timg.save(tpath)
            flag = "  ⚠ 留白 %.0f%%" % st["pad_pct"] if st["pad_pct"] > 18 else ""
            print("  target %-12s %4d×%-4d  zones=%2d  留白 %5.1f%%%s" % (
                t.get("id"), timg.width, timg.height, st["zones"], st["pad_pct"], flag))
            if st["pad_pct"] > 18:
                warnings.append("target %s 留白 %.0f%%：比例与版面不匹配，投到该渠道会显空"
                                % (t.get("id"), st["pad_pct"]))

    if warnings:
        print("\n提醒 %d 项：" % len(warnings))
        for w in warnings:
            print("  · %s" % w)
    if problems:
        print("\n骨架未通过，%d 个问题：" % len(problems), file=sys.stderr)
        for p in problems:
            print("  ✗ %s" % p, file=sys.stderr)
        return 1
    print("\n骨架通过。下一步：单区风格样张（Gate 3），通过后再批量出 tile。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
