#!/usr/bin/env python3
"""Step 3.5 — the information-density gate.

Every other gate in this skill asks "is this legal, sourced, toned and geometrically
safe?". None of them asked "did this cell tell the reader something they did not already
know?". v1.1.1 shipped eight code-drawn cards with no words or numbers on them, and
stitch reported `placeholder: 0` because a file existed. This script is the missing
question.

It works on the blueprint, before any image is generated:

  * `meta.key_facts[]` — the facts this campaign is obliged to land, each with a source.
  * `zones[].facts[]` — ids of the facts that cell adds; every cell adds at least one.
  * `zones[].tile_origin` — ai / code_card / evidence / chart. A code_card with no
    number, condition, boundary or evidence fact is an empty card and is refused.
  * Pages must carry a minimum number of NEW information units (repeats do not count).
  * Information-bearing rectangles / usable page area must clear `min_info_area`.

Output is `reports/density_sheet.md` — Gate 1 pastes it verbatim.

Usage
  python3 lint_density.py build/blueprint.json -o build/reports/density_sheet.md
  python3 lint_density.py build/blueprint.json --no-area     # structure only

Exit codes
  0  density gate passed
  1  blocking density problems
  2  bad input
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402

FACT_KINDS = ("number", "condition", "boundary", "evidence", "object", "action")
CARD_KINDS = ("number", "condition", "boundary", "evidence")
DIGIT = re.compile(r"[0-9]")


def _rect_area(r):
    return max(0, r[2]) * max(0, r[3])


def _new_or_repeat(bp):
    """First appearance of a fact id is information; every later one is a restatement."""
    seen, flags = set(), {}
    for z in sorted(bp["zones"], key=lambda x: (int(x.get("row", 0)), int(x.get("col", 0)))):
        zid = z["id"]
        flags[zid] = []
        for fid in pl.zone_fact_ids(z):
            fresh = fid not in seen
            seen.add(fid)
            flags[zid].append((fid, fresh))
    return flags


def _page_units(bp, target):
    """(label, kind, new-unit count, threshold, fact ids) for every page in a target."""
    limits = pl.density_limits(bp)
    flags = _new_or_repeat(bp)
    zones_by_cell = {(int(z["row"]), int(z["col"])): z for z in bp["zones"]}
    ttype = target.get("type", "full")
    out = []

    if ttype == "carousel":
        pages = target.get("pages") or pl.default_pages(bp)
        for i, pg in enumerate(pages, 1):
            kind = pg.get("kind", "row")
            if kind == "row":
                cells = [(r, c) for r in pg.get("rows") or []
                         for c in range(1, int(bp["meta"]["grid"]["cols"]) + 1)]
                zs = [zones_by_cell[k] for k in cells if k in zones_by_cell]
                ids = [fid for z in zs for fid, fresh in flags.get(z["id"], []) if fresh]
                need = limits["units_per_page"]
            else:
                ids = list(pg.get("facts") or [])
                need = limits["units_cover"] if kind == "cover" else limits["units_end"]
            out.append(("%s 第 %d 页" % (target.get("id"), i), kind, len(ids), need, ids))
        return out

    cells = pl.target_cells(bp, target)
    zs = [zones_by_cell[k] for k in cells if k in zones_by_cell]
    ids = [fid for z in zs for fid, fresh in flags.get(z["id"], []) if fresh]
    out.append((target.get("id"), ttype, len(ids), limits["units_per_page"], ids))
    return out


def _info_area(bp):
    """Information-bearing rectangles / page area, measured from the resolved grid.

    Only rectangles that carry a NEW fact count: caption plates, information cards and
    evidence slots. Headers, page numbers, column titles, persona strips and the
    disclosure band are structural overhead — counting them is how an empty poster
    used to score as full.
    """
    limits = pl.density_limits(bp)
    grid, row_map, col_map = pl.make_grid(bp)
    mapping = pl.matrix_mapping(row_map, col_map)
    views = pl.zone_views(bp, grid, mapping)
    flags = _new_or_repeat(bp)
    weight = limits["info_weight"]
    area = 0.0
    for v in views:
        fresh = [fid for fid, ok in flags.get(v.id, []) if ok]
        if not fresh:
            continue
        origin = (v.zone.get("tile_origin") or "").strip()
        area += _rect_area(v.caption_rect)
        area += _rect_area(v.image_rect) * weight.get(origin, 0.25)
        for s in v.slots:
            area += _rect_area(s["abs"])
    total = float(grid.width * grid.height) or 1.0
    return area / total, area, total


def analyse(bp, skip_area=False):
    limits = pl.density_limits(bp)
    facts = pl.facts_of(bp)
    problems, warnings = [], []
    flags = _new_or_repeat(bp)

    # 1 — the brief's twelfth item. Without it there is nothing to measure against.
    declared = bp.get("meta", {}).get("key_facts") or []
    if not declared:
        problems.append("meta.key_facts 为空：Step 0 第 12 项没采。没有事实清单，"
                        "「这一格有没有信息」无从判断")
    ids = [f.get("id") for f in declared if isinstance(f, dict)]
    if len(ids) != len(set(ids)):
        problems.append("meta.key_facts 里有重复 id")
    for f in declared:
        if not isinstance(f, dict):
            problems.append("meta.key_facts 里有非对象条目")
            continue
        fid = f.get("id") or "（缺 id）"
        if not (f.get("text") or "").strip():
            problems.append("事实 %s 缺 text" % fid)
        if not (f.get("source") or "").strip():
            problems.append("事实 %s 缺 source——指不回素材的数字不许上图" % fid)
        if (f.get("kind") or "") not in FACT_KINDS:
            problems.append("事实 %s 的 kind=%r 非法，可用 %s"
                            % (fid, f.get("kind"), "/".join(FACT_KINDS)))
        if pl.is_financial(bp) and not (f.get("source") or "").startswith("client-confirmed:"):
            problems.append("事实 %s：金融/保险类事实的 source 必须 client-confirmed:*" % fid)

    # 2 — every cell adds something, and a code card is not allowed to be a blank slip.
    usage, repeats = 0, 0
    for z in bp["zones"]:
        zid = z["id"]
        fids = pl.zone_fact_ids(z)
        fresh = [fid for fid, ok in flags.get(zid, []) if ok]
        usage += len(fids)
        repeats += len(fids) - len(fresh)
        if len(fids) < limits["facts_per_zone"]:
            problems.append("%s: 没有新增事实（facts 为空）——一格不能只靠 caption 撑着" % zid)
        for fid in fids:
            if fid not in facts:
                problems.append("%s: facts 引用了不存在的 %r" % (zid, fid))
        origin = (z.get("tile_origin") or "").strip()
        if origin and origin not in pl.INFO_ORIGINS:
            problems.append("%s: tile_origin=%r 非法，可用 %s"
                            % (zid, origin, "/".join(pl.INFO_ORIGINS)))
        if origin in ("code_card", "evidence", "chart"):
            kinds = [(facts.get(fid) or {}).get("kind") for fid in fids]
            if not any(k in CARD_KINDS for k in kinds):
                problems.append("%s: tile_origin=%s 却没有一条数字/条件/边界/原文类事实——"
                                "这是一张空白卡，不是规则卡" % (zid, origin))
        if origin == "ai" and z.get("slots"):
            warnings.append("%s: 插画格带贴图位，别忘了 [SLOT] 句子" % zid)

    # 3 — restatements are not information.
    ratio = (repeats / float(usage)) if usage else 0.0
    if usage and ratio > limits["max_repeat_ratio"]:
        problems.append("事实复述率 %.0f%% 超过 %.0f%%：%d/%d 次引用是在重复别格说过的话"
                        % (ratio * 100, limits["max_repeat_ratio"] * 100, repeats, usage))
    unused = sorted(set(facts) - {fid for z in bp["zones"] for fid in pl.zone_fact_ids(z)})
    if unused:
        warnings.append("采集了但没上图的 facts：%s（Gate 1 说明为什么）" % ", ".join(unused))

    # 4 — page-level information units.
    pages = []
    for t in bp.get("targets", []):
        if t.get("type") == "full" and t.get("ratio") == "auto":
            continue  # internal master, not a delivery page
        for label, kind, n, need, pids in _page_units(bp, t):
            pages.append({"page": label, "kind": kind, "units": n, "need": need,
                          "facts": pids, "ok": n >= need})
            if n < need:
                problems.append("%s（%s）：只有 %d 个新信息单元，门槛 %d"
                                % (label, kind, n, need))

    # 5 — information-bearing area.
    area_ratio, area_px, total_px = _info_area(bp)
    if not skip_area and area_ratio < limits["min_info_area"]:
        problems.append("信息面积比 %.1f%% 低于 %.0f%%：画面里承载新事实的矩形太少"
                        % (area_ratio * 100, limits["min_info_area"] * 100))

    return {"limits": limits, "facts_total": len(facts), "usage": usage,
            "repeats": repeats, "repeat_ratio": ratio, "pages": pages,
            "area_ratio": area_ratio, "area_px": area_px, "total_px": total_px,
            "flags": flags, "problems": problems, "warnings": warnings}


def sheet_markdown(bp, res):
    facts = pl.facts_of(bp)
    lim = res["limits"]
    L = ["# 信息密度台账", "",
         "口径：一个「信息单元」= 一条 `meta.key_facts` 里的新事实；同一事实第二次出现算复述，不计入。",
         "信息面积比 = 承载新事实的矩形（说明板 + 信息卡 + 证据贴图）/ 页面面积；",
         "标题、页码、列标题、人群条、披露带是结构开销，不计入。", "",
         "## 总账", "",
         "| 项 | 实测 | 门槛 | 判定 |", "|---|---|---|---|",
         "| 采集事实 | %d 条 | ≥1 | %s |" % (
             res["facts_total"], "通过" if res["facts_total"] else "阻断"),
         "| 每格新增事实 | 见下表 | ≥%d | — |" % lim["facts_per_zone"],
         "| 事实引用 / 复述 | %d / %d | 复述率 ≤%.0f%% | %s |" % (
             res["usage"], res["repeats"], lim["max_repeat_ratio"] * 100,
             "通过" if res["repeat_ratio"] <= lim["max_repeat_ratio"] else "阻断"),
         "| 信息面积比 | %.1f%% | ≥%.0f%% | %s |" % (
             res["area_ratio"] * 100, lim["min_info_area"] * 100,
             "通过" if res["area_ratio"] >= lim["min_info_area"] else "阻断"),
         "", "## 逐页信息增量", "",
         "| 页 | 类型 | 新信息单元 | 门槛 | 判定 |", "|---|---|---|---|---|"]
    for p in res["pages"]:
        L.append("| %s | %s | %d | %d | %s |" % (
            p["page"], p["kind"], p["units"], p["need"], "通过" if p["ok"] else "阻断"))
    L += ["", "## 逐格新增事实", "",
          "| 格 | 图片来源 | facts | 新增 / 复述 | caption |", "|---|---|---|---|---|"]
    for z in sorted(bp["zones"], key=lambda x: (int(x.get("row", 0)), int(x.get("col", 0)))):
        fl = res["flags"].get(z["id"], [])
        fresh = [f for f, ok in fl if ok]
        rest = [f for f, ok in fl if not ok]
        tags = ", ".join(fresh) or "—"
        if rest:
            tags += "（复述：%s）" % ", ".join(rest)
        L.append("| %s | %s | %s | %d / %d | %s |" % (
            z["id"], z.get("tile_origin") or "未声明", tags, len(fresh), len(rest),
            (z.get("caption") or "").replace("|", "/")))
    L += ["", "## 事实清单（Gate 1 逐条核对来源）", "",
          "| id | 类型 | 事实 | 来源 |", "|---|---|---|---|"]
    for fid, f in facts.items():
        L.append("| %s | %s | %s | %s |" % (
            fid, f.get("kind", ""), (f.get("text") or "").replace("|", "/"),
            (f.get("source") or "").replace("|", "/")))
    L += ["", "## 阻断项", ""]
    L += ["- %s" % p for p in res["problems"]] or ["- 无"]
    L += ["", "## 提醒项", ""]
    L += ["- %s" % w for w in res["warnings"]] or ["- 无"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="promo-atlas step 3.5: information density gate")
    ap.add_argument("blueprint")
    ap.add_argument("-o", "--out", default=None, help="write density_sheet.md here")
    ap.add_argument("--no-area", action="store_true", help="skip the area threshold")
    ap.add_argument("--json", action="store_true", help="print the analysis as JSON")
    args = ap.parse_args()

    path = os.path.abspath(args.blueprint)
    if not os.path.isfile(path):
        print("找不到 %s" % path, file=sys.stderr)
        return 2
    bp = pl.load(path)
    res = analyse(bp, skip_area=args.no_area)

    out = args.out or os.path.join(os.path.dirname(path), "reports", "density_sheet.md")
    pc.ensure_dir(os.path.dirname(os.path.abspath(out)))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(sheet_markdown(bp, res))

    if args.json:
        printable = {k: v for k, v in res.items() if k != "flags"}
        print(json.dumps(printable, ensure_ascii=False, indent=2))
    else:
        print("信息密度：事实 %d 条，引用 %d 次，复述 %d 次（%.0f%%），信息面积比 %.1f%%" % (
            res["facts_total"], res["usage"], res["repeats"],
            res["repeat_ratio"] * 100, res["area_ratio"] * 100))
        for p in res["pages"]:
            print("  %-24s %-6s %2d/%d %s" % (
                p["page"], p["kind"], p["units"], p["need"], "ok" if p["ok"] else "BLOCK"))
        print("台账: %s" % out)
        for w in res["warnings"]:
            print("  · %s" % w)
        for p in res["problems"]:
            print("  ✗ %s" % p, file=sys.stderr)
        if res["problems"]:
            print("\n未通过。补的是 facts 与画面内容，不是把板子撑大。", file=sys.stderr)
    return 1 if res["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
