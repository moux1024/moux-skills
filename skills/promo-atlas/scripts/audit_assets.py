#!/usr/bin/env python3
"""Step 5.5 — asset & cast audit, bound to pixels.

Two questions, and they are separate:

  * Is every face in this tile somebody? (cast)
  * Did the model keep its hands off the reserved slot, and is the picture the picture
    the zone was built around? (intent / plausibility / taste)

The script judges none of that — it only refuses three kinds of dishonesty: a tile with
no record, a record whose hash no longer matches the image, and a "pass" with no sentence
in it. Fixing a failure means regenerating the tile with a corrected prompt, never editing
the record until it goes green.

Usage
  python3 audit_assets.py build/blueprint.json -d build/tiles --init
  python3 audit_assets.py build/blueprint.json -d build/tiles
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402

# The fourth axis was added after a build in which eight cells contained nothing but
# blank paper geometry and all three original axes passed: the picture was on-style,
# plausible and tasteful. It just did not say anything. Style is not information.
AXES = ("intent", "plausibility", "taste", "information")

# A rule/evidence card's one-line description has to name something checkable. "两张空白
# 登记票据" names nothing; "余额 80%、上限 800 元、免赔 100 元" does.
CARD_SIGNAL = re.compile(
    r"[0-9]|[%‰]|免赔|上限|限额|等待期|给付|结算|补偿|条款|余额|周期|比例|费率|元|日")
CARD_ORIGINS = ("code_card", "evidence", "chart")


def tile_path(tiles_dir, zone_id):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(tiles_dir, zone_id + ext)
        if os.path.isfile(p):
            return p
    return None


def init_records(bp, tiles_dir, audit_path):
    recs = {}
    for z in bp["zones"]:
        p = tile_path(tiles_dir, z["id"])
        recs[z["id"]] = {
            "tile": os.path.basename(p) if p else None,
            "sha256": pc.sha256_file(p) if p else None,
            "verdict": "pending",
            "figures": [{"character": cid, "prominence": "face", "note": ""}
                        for cid in z["cast"]["named"]],
            "slots": [{"asset": s.get("asset"), "slot_clean": None, "note": ""}
                      for s in z.get("slots", [])],
            "axes": {k: None for k in AXES},
            "sentence": "",
            "reviewer_note": "",
            "fix": "",
        }
    pc.save_json(audit_path, recs)
    return recs


def verify(bp, tiles_dir, recs):
    fails, warns = [], []
    zones = {z["id"]: z for z in bp["zones"]}
    for zid, z in zones.items():
        rec = recs.get(zid)
        p = tile_path(tiles_dir, zid)
        if not rec:
            fails.append("%s: 没有审核记录" % zid)
            continue
        if not p:
            fails.append("%s: 找不到 tile 文件" % zid)
            continue
        cur = pc.sha256_file(p)
        if rec.get("sha256") != cur:
            fails.append("%s: 图片已重生成，旧结论不继承（hash 不匹配），重新审" % zid)
            continue
        if rec.get("verdict") == "pending":
            fails.append("%s: 未审核（verdict=pending）" % zid)
        if rec.get("verdict") == "fix":
            fails.append("%s: 已判 fix：%s" % (zid, rec.get("fix") or "未写原因"))

        # A visible face must be somebody, and somebody the zone declared.
        named = set(z["cast"]["named"])
        extras = 0
        for fig in rec.get("figures", []):
            prom = fig.get("prominence")
            cid = fig.get("character")
            if prom not in ("face", "figure", "prop"):
                fails.append("%s: figure prominence=%r 非法" % (zid, prom))
            if prom == "face" and not cid:
                fails.append("%s: 画面里有可辨认的脸，但没有对应人物——这是全图最贵的错" % zid)
            if cid and cid not in named:
                fails.append("%s: %s 不在本格 cast 白名单里" % (zid, cid))
            if prom == "figure" and cid is None:
                extras += 1
        if extras > int(z["cast"].get("extras_max", 0)):
            fails.append("%s: 无名人物 %d 个，上限 %d" % (zid, extras, z["cast"].get("extras_max")))

        # The inverse rule: cells built to be faceless must stay faceless.
        if not z.get("face_allowed"):
            faces = [f for f in rec.get("figures", []) if f.get("prominence") == "face"]
            if faces:
                fails.append("%s: 本格设计为不给脸（figure），却出现了 %d 张可辨认的脸" % (zid, len(faces)))

        # Slots: the model must not have drawn the product itself.
        rec_slots = {s.get("asset"): s for s in rec.get("slots", [])}
        for s in z.get("slots", []):
            aid = s.get("asset")
            rs = rec_slots.get(aid)
            if not rs:
                fails.append("%s: 贴图位 %s 未审核" % (zid, aid))
            elif rs.get("slot_clean") is None:
                fails.append("%s: 贴图位 %s 未判断是否被模型预先画了东西" % (zid, aid))
            elif rs.get("slot_clean") is False:
                fails.append("%s: 贴图位 %s 区域里模型自己画了物体，必须重生成" % (zid, aid))

        missing_axes = [k for k in AXES if rec.get("axes", {}).get(k) not in ("pass", "fail")]
        if missing_axes:
            fails.append("%s: 未评的三轴: %s" % (zid, ", ".join(missing_axes)))
        for k in AXES:
            if rec.get("axes", {}).get(k) == "fail":
                fails.append("%s: %s 不通过——%s" % (zid, k, rec.get("fix") or "未写修法"))
        if not (rec.get("sentence") or "").strip():
            fails.append("%s: 没有一句话描述画面内容——pass 不能是橡皮章" % zid)
        elif (z.get("tile_origin") or "") in CARD_ORIGINS:
            if not pl.zone_fact_ids(z):
                fails.append("%s: 声明为信息卡，blueprint 里却没有 facts——空白卡不能过审" % zid)
            if not CARD_SIGNAL.search(rec["sentence"]):
                fails.append("%s: 信息卡的画面描述里没有任何数字或条款要素——"
                            "「空白纸片」不是一条 information=pass 的证据" % zid)
        if not (rec.get("reviewer_note") or "").strip():
            warns.append("%s: reviewer_note 为空（暗角提亮复核了吗）" % zid)
    return fails, warns


def main():
    ap = argparse.ArgumentParser(description="promo-atlas audit: cast, slots, intent")
    ap.add_argument("blueprint")
    ap.add_argument("-d", "--tiles", default="tiles")
    ap.add_argument("--init", action="store_true", help="write pending records for every tile")
    ap.add_argument("--sheet", action="store_true", help="also write tile_sheet.png")
    args = ap.parse_args()

    bp_path = os.path.abspath(args.blueprint)
    base = os.path.dirname(bp_path)
    bp = pl.resolve_asset_paths(pl.load(bp_path), base)
    tiles = args.tiles if os.path.isabs(args.tiles) else os.path.join(base, args.tiles)
    audit_path = os.path.join(tiles, "audit.json")

    if args.init:
        recs = init_records(bp, tiles, audit_path)
        n = sum(1 for r in recs.values() if r["sha256"])
        print("已写入待审记录 %d 条（其中 %d 条已有 tile）: %s" % (len(recs), n, audit_path))
        print("逐格看图后填 figures / slots / axes / sentence，再跑一次本脚本验证。")
        return 0

    if not os.path.isfile(audit_path):
        print("没有 %s，先跑 --init" % audit_path, file=sys.stderr)
        return 2
    recs = pc.load_json(audit_path)

    if args.sheet:
        import stitch
        grid, row_map, col_map = pl.make_grid(bp)
        mapping = pl.matrix_mapping(row_map, col_map)
        img, _st, _n = stitch.render(bp, grid, mapping, tiles_dir=tiles,
                                     mode="final", allow_partial=True,
                                     cell=max(320, int(4096 / max(1, len(col_map)))))
        out = os.path.join(tiles, "tile_sheet.png")
        img.save(out)
        print("拼版预览: %s  (%d×%d)" % (out, img.width, img.height))

    fails, warns = verify(bp, tiles, recs)
    print("\n审核：%d 格，失败 %d 项，提醒 %d 项" % (len(bp["zones"]), len(fails), len(warns)))
    for w in warns:
        print("  · %s" % w)
    for f in fails:
        print("  ✗ %s" % f, file=sys.stderr)
    if fails:
        print("\n未通过。修法是重生成那一格并改提示词，不是改记录。", file=sys.stderr)
        return 1
    print("\n全部通过，可以 stitch。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
