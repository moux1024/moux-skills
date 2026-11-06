#!/usr/bin/env python3
"""Asset gate — the three things that must never be redrawn.

Logo, product shot, mascot turnaround sheet. Every one of them arrives from the client
as a file; none of them is ever produced by an image model. This script checks the files
before they cost a run: transparency, resolution, and whether the subject fills the
canvas or floats in 40% of empty margin.

Usage
  python3 assets.py build/blueprint.json              # check assets referenced by blueprint
  python3 assets.py build/blueprint.json -o build/reports/assets.json

Exit codes
  0  all assets usable
  1  at least one asset is unusable (not transparent / too small / missing)
"""

import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402

# Only these must be cut-outs. An app screen or a chart is a rectangle by nature;
# demanding transparent corners from a screenshot rejects the asset that carries the facts.
CUTOUT_KINDS = ("product", "mascot")

MIN_EDGE = {"product": 400, "logo": 200, "mascot": 600,
            # A financial product has no pack shot. What it has is an app screen or a
            # chart — both are facts, both are screenshots, neither may be redrawn.
            "ui": 750, "chart": 600, "other": 300}


def inspect(entry):
    path = entry.get("file", "")
    kind = entry.get("kind", "product")
    rec = {"id": entry.get("id"), "kind": kind, "file": path, "ok": True, "issues": [], "warn": []}

    if not path or not os.path.isfile(path):
        rec["ok"] = False
        rec["issues"].append("文件不存在")
        return rec

    rec["sha256"] = pc.sha256_file(path)
    try:
        img = Image.open(path)
    except Exception as exc:  # noqa: BLE001
        rec["ok"] = False
        rec["issues"].append("打不开: %s" % exc)
        return rec

    rec["size"] = list(img.size)
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info)
    rec["alpha"] = bool(has_alpha)

    min_edge = MIN_EDGE.get(kind, MIN_EDGE["other"])
    if max(img.size) < min_edge:
        rec["ok"] = False
        rec["issues"].append("%d×%d 太小，%s 至少要 %dpx 长边（放大必糊）" % (
            img.size[0], img.size[1], kind, min_edge))

    if not has_alpha:
        if kind in CUTOUT_KINDS:
            rec["ok"] = False
            rec["issues"].append("没有 alpha 通道——这不是去底图。贴进画面会带一块白底")
        else:
            rec["note"] = "矩形资产，按矩形贴入（不裁边）"
            rec["warn"].append("无 alpha：会以矩形贴入，投影按硬边处理")
        return rec

    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        rec["ok"] = False
        rec["issues"].append("整张图透明，没有内容")
        return rec

    w, h = rgba.size
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    rec["content_bbox"] = list(bbox)
    rec["content_ratio"] = round((bw * bh) / float(w * h), 3)
    rec["solid_ratio"] = round((bw * bh) / float(w * h), 3)

    if kind not in CUTOUT_KINDS:
        rec["note"] = "矩形资产，按矩形贴入（不裁边）"
        rec["visible_px"] = [w, h]
        return rec

    # Corner transparency is the cheap test for "was this actually cut out".
    corners = [alpha.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    if min(corners) > 8:
        rec["ok"] = False
        rec["issues"].append("四角不透明（alpha=%s）——背景没去掉，或是白底图" % (corners,))
        return rec

    # Subject crammed into a corner of a huge canvas: pasting it "contain" makes the
    # product tiny in its slot, and the slot was sized for the product, not the canvas.
    if rec["content_ratio"] < 0.45:
        rec["warn"].append("主体只占画布 %.0f%%，建议裁到内容边界后再入库（贴图时已自动按 alpha 裁边）"
                           % (rec["content_ratio"] * 100))
    if bw >= w - 2 or bh >= h - 2:
        rec["warn"].append("主体贴到画布边缘，投影会被裁掉一角")
    rec["visible_px"] = [bw, bh]
    return rec


def main():
    ap = argparse.ArgumentParser(description="promo-atlas asset gate")
    ap.add_argument("blueprint")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    bp_path = os.path.abspath(args.blueprint)
    base = os.path.dirname(bp_path)
    bp = pl.resolve_asset_paths(pl.load(bp_path), base)

    records = [inspect(a) for a in bp.get("assets", [])]
    bad = [r for r in records if not r["ok"]]
    warn = [r for r in records if r["ok"] and r["warn"]]
    used = {s.get("asset") for z in bp["zones"] for s in z.get("slots", [])}

    print("资产检查：%d 个，通过 %d，不可用 %d\n" % (
        len(records), len(records) - len(bad), len(bad)))
    for r in records:
        mark = "✓" if r["ok"] else "✗"
        size = "×".join(str(x) for x in r.get("size", ["?"]))
        vis = "×".join(str(x) for x in r.get("visible_px", [])) or "—"
        usage = "已上图" if r["id"] in used else "未上图"
        print("  %s %-10s %-8s %-12s 主体 %-10s %s" % (
            mark, r["id"], r["kind"], size, vis, usage))
        if r.get("note"):
            print("      · %s" % r["note"])
        for i in r["issues"]:
            print("      ✗ %s" % i)
        for w in r["warn"]:
            print("      · %s" % w)

    if bad:
        print("\n资产未通过：%d 个不可用。不可重绘的三类资产（logo / 产品实拍 / 吉祥物三视图）"
              "必须由客户提供去底文件，不能由模型生成。" % len(bad), file=sys.stderr)

    out = args.out or os.path.join(base, "reports", "assets.json")
    pc.save_json(out, {"assets": records, "used_in_slots": sorted(u for u in used if u),
                       "ok": not bad})
    print("\n记录: %s" % out)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
