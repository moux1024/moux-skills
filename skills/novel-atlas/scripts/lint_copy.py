#!/usr/bin/env python3
"""Read the reader-facing copy before any of it is drawn.

Every word on the finished atlas is written by hand into `blueprint.json`, and the label
geometry is measured from those words. So a copy problem is also a layout problem: a caption
two characters too long either wraps into a third line or lands on the plate below it, and
both are discovered after the tiles are paid for. This script reads the copy in reading
order, checks what a machine can check, and writes `copy_sheet.md` so a human reads it once
as a reader instead of skimming it as its author.

What it can check: lengths against the real geometry, duplicates, placeholders, punctuation,
bracket balance, chapter coverage arithmetic, year order inside a zone, and the wording tics
that survive machine authorship (every caption opening the same way, every event missing its
chapter anchor). What it cannot check: whether a caption is *true*, whether a name is the one
the book uses, and whether a zone is describing the thing the picture shows. Those are the
four questions at the bottom of the sheet, and they are why this is a gate and not a linter.

Usage:
    python3 lint_copy.py atlas_build/blueprint.json -o atlas_build/copy_sheet.md
"""

import argparse
import json
import os
import re
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_common as ac  # noqa: E402

PLACEHOLDERS = ("todo", "tbd", "待定", "待补", "占位", "xxx", "lorem", "???")
BRACKETS = {"《": "》", "「": "」", "『": "』", "（": "）", "〈": "〉", "“": "”"}
HALF_PUNCT = re.compile(r"[\u4e00-\u9fff][,;:!?](?![0-9])")
YEAR = re.compile(r"(19|20)\d{2}")
CHAPTER_REF = re.compile(r"第\s*(\d+)\s*[回章]")


class Copy:
    def __init__(self):
        self.errors = []
        self.warns = []          # (group, message) — printed grouped, not once per item
        self.records = []

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, group, where, msg):
        self.warns.append((group, f"{where}: {msg}"))


def check_text(cp, where, kind, text, lines, max_lines, width_px, max_width, size_px):
    t = text
    if not t.strip():
        cp.err(where, "是空的——图上会留一块无字的板")
        return
    if t != t.strip():
        cp.err(where, "首尾有空白，排版会多出一块白边")
    low = t.lower()
    for ph in PLACEHOLDERS:
        if ph in low:
            cp.err(where, f"含有占位词「{ph}」，这不是给读者看的话")
    if "  " in t or " \u3000" in t or "\u3000 " in t:
        cp.warn("空格", where, "连续空格或全角/半角空格混用，宽度会抖")
    if HALF_PUNCT.search(t):
        cp.warn("标点", where, "中文里用了半角标点（, ; : ! ?）")
    for open_ch, close_ch in BRACKETS.items():
        if t.count(open_ch) != t.count(close_ch):
            cp.err(where, f"括号不配对：{open_ch}×{t.count(open_ch)} vs {close_ch}×{t.count(close_ch)}")
        if t.count(open_ch) > 3:
            cp.warn("括号", where, f"{open_ch}{close_ch} 用了 {t.count(open_ch)} 次，读者会数不清")
    if re.search(r"([，。、；：！？])\1", t):
        cp.err(where, "重复标点")
    if re.search(r"\s+[，。、；：！？）】」』]", t):
        cp.warn("标点", where, "标点前有空格")
    if kind in ("label", "event", "name") and t.rstrip().endswith(("。", "，", "、", "；")):
        cp.warn("标点", where, "短标注不必以句号或逗号收尾")
    if len(t) > 80:
        cp.warn("长度", where, f"{len(t)} 字，超过一段标注该有的长度")
    if lines > max_lines:
        cp.err(where, f"在图上要排 {lines} 行（上限 {max_lines} 行）——"
                      f"「{t[:18]}…」会压到旁边的板或越过分区边")
    if width_px > max_width:
        cp.err(where, f"单行宽 {int(width_px)}px，超出可用的 {int(max_width)}px；"
                      f"标注不会自动换行，会直接压出分区")
    if size_px < 24:
        cp.warn("可读性", where, f"字号只有 {size_px:.0f}px，缩到半屏就看不见了")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blueprint")
    ap.add_argument("-o", "--out", default=None, help="copy_sheet.md path")
    ap.add_argument("--cell", type=int, default=None, help="override the blueprint's cell")
    ap.add_argument("--quiet", action="store_true", help="print counts only")
    args = ap.parse_args()

    bp = ac.load_blueprint(args.blueprint)
    cell = int(args.cell or bp["meta"]["canvas"]["cell"])
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    cp = Copy()

    zones = sorted(bp["zones"], key=lambda z: (int(z.get("row", 0)), int(z.get("col", 0))))
    chidx = ac.chars_by_id(bp)
    meta = bp["meta"]

    f_name = 62 * cell / 2048.0
    f_cap = 30 * cell / 2048.0
    f_ev = cell * 0.020

    # ---------------------------------------------------------------- title block
    for kind, text, size, maxw in (
            ("title", str(meta.get("title", "")), cell * 0.038, cell * 1.70 - cell * 0.060),
            ("subtitle", str(meta.get("subtitle", "")), cell * 0.0165, cell * 1.70 - cell * 0.060)):
        if not text:
            cp.err("标题栏", f"{kind} 是空的")
            continue
        font = ac.resolve_font(int(size))
        lines = ac.wrap_cjk(draw, text, font, maxw)
        w = max(ac.text_width(draw, ln, font) for ln in lines)
        check_text(cp, f"标题栏 {kind}", "caption", text, len(lines), 2, w, maxw, size)
        cp.records.append({"where": "标题栏", "kind": kind, "text": text, "size": size,
                           "lines": lines})

    # ---------------------------------------------------------------- zones
    for z in zones:
        zid = z["id"]
        x, y, w, h = ac.zone_rect(z, cell)
        if z.get("name") and not z.get("hide_name"):
            text = str(z["name"])
            font = ac.resolve_font(int(f_name))
            lines = ac.wrap_cjk(draw, text, font, w * 0.90 - 2 * f_name * 0.46)
            check_text(cp, f"{zid} 分区名", "name", text, len(lines), 1,
                       max((ac.text_width(draw, ln, font) for ln in lines), default=0),
                       w * 0.90, f_name)
            cp.records.append({"where": zid, "kind": "name", "text": text,
                               "size": f_name, "lines": lines})
        elif not z.get("hide_name"):
            cp.err(f"{zid} 分区名", "没有名字，也没有声明 hide_name")

        if z.get("caption"):
            text = str(z["caption"])
            font = ac.resolve_font(int(f_cap))
            maxw = w * 0.78 - 2 * f_name * 0.46
            lines = ac.wrap_cjk(draw, text, font, maxw)
            check_text(cp, f"{zid} 副题", "caption", text, len(lines), 3,
                       max((ac.text_width(draw, ln, font) for ln in lines), default=0),
                       maxw, f_cap)
            if text.strip() == str(z.get("name", "")).strip():
                cp.err(f"{zid} 副题", "和分区名一字不差——这一行没有给读者新信息")
            cp.records.append({"where": zid, "kind": "caption", "text": text,
                               "size": f_cap, "lines": lines})

        for i, lb in enumerate(z.get("labels") or []):
            text = str(lb.get("text", ""))
            if not text:
                cp.err(f"{zid} 标注#{i + 1}", "是空的")
                continue
            font = ac.resolve_font(int(float(lb.get("size", 40)) * cell / 2048.0))
            check_text(cp, f"{zid} 标注「{text[:10]}」", "label", text, 1, 1,
                       ac.text_width(draw, text, font), w * 0.92,
                       float(lb.get("size", 40)) * cell / 2048.0)
            cp.records.append({"where": zid, "kind": "label", "text": text,
                               "size": float(lb.get("size", 40)) * cell / 2048.0,
                               "lines": [text]})

    # ---------------------------------------------------------------- events
    for e in bp.get("events", []):
        z = next((zz for zz in zones if zz["id"] == e.get("zone")), None)
        if not z:
            continue
        text = str(e.get("label", ""))
        where = f"{e.get('id')} 事件"
        font = ac.resolve_font(int(f_ev))
        check_text(cp, where, "event", text, 1, 1, ac.text_width(draw, text, font),
                   ac.zone_rect(z, cell)[2] * 0.92, f_ev)
        cp.records.append({"where": e.get("zone"), "kind": "event", "text": text,
                           "size": f_ev, "lines": [text], "event": e.get("id")})
        ch = e.get("chapter")
        if ch is not None:
            ref = CHAPTER_REF.search(text)
            if ref and int(ref.group(1)) != int(ch):
                cp.err(where, f"标注写「第 {ref.group(1)} 回」，但 chapter 字段是 {ch}")

    # ---------------------------------------------------------------- names
    seen_names = {}
    for cid, ch in chidx.items():
        nm = str(ch.get("name", cid))
        seen_names.setdefault(nm, []).append(cid)
        if len(nm) > 8:
            cp.warn("人名", nm, f"{len(nm)} 字，名字板会挤到旁边")
        if re.search(r"[A-Za-z]{1,}$", nm) and not re.search(r"[\u4e00-\u9fff]", nm):
            cp.warn("人名", nm, "纯拉丁名在中文图里会跳出来，确认原文确实这么写")
    for nm, ids in seen_names.items():
        if len(ids) > 1:
            cp.err("人物", f"「{nm}」出现在多个 id 上：{', '.join(ids)}")

    # ---------------------------------------------------------------- duplicates
    zone_names = {}
    for z in zones:
        nm = str(z.get("name", "")).strip()
        if nm:
            zone_names.setdefault(nm, []).append(z["id"])
    for nm, zids in zone_names.items():
        if len(zids) > 1:
            cp.err("分区名", f"「{nm}」被 {', '.join(zids)} 共用——读者会以为同一格")

    texts = {}
    for r in cp.records:
        if r["kind"] in ("label", "event") and r["text"].strip():
            texts.setdefault(r["text"].strip(), []).append(r["where"])
    for t, wheres in texts.items():
        if len(wheres) > 1:
            cp.warn("重复", "、".join(wheres), f"同一句「{t[:16]}…」用了 {len(wheres)} 次")
    for z in zones:
        labels = [str(lb.get("text", "")).strip() for lb in (z.get("labels") or [])]
        for t in set(labels):
            if labels.count(t) > 1:
                cp.err(f"{z['id']} 标注", f"「{t}」在同一格重复了 {labels.count(t)} 次")

    # ---------------------------------------------------------------- coverage arithmetic
    cov = bp.get("coverage") or {}
    total = cov.get("chapters_total")
    covered = cov.get("chapters_covered") or []
    missing = cov.get("chapters_missing") or []
    if total:
        if covered and missing and len(covered) + len(missing) != int(total):
            cp.err("coverage", f"{len(covered)} 已覆盖 + {len(missing)} 省略 ≠ {total} 章——"
                               f"这个块会印在图上，数字对不上比不写更糟")
        if covered and not missing and len(covered) < int(total):
            cp.warn("coverage", "coverage", f"只列了 {len(covered)} 章，没有 chapters_missing，"
                                            f"图上会读成「全书都覆盖了」")
        bad = [c for c in list(covered) + list(missing) if not (1 <= int(c) <= int(total))]
        if bad:
            cp.err("coverage", f"章号超出 1..{total}: {bad[:5]}")
    else:
        cp.err("coverage", "没有 chapters_total，标题栏的覆盖率无法计算")

    # ---------------------------------------------------------------- years inside a zone
    for z in zones:
        evs = [e for e in bp.get("events", []) if e.get("zone") == z["id"]]
        seq = []
        for e in sorted(evs, key=lambda e: float(e.get("y", 0.5))):
            m = YEAR.search(str(e.get("label", "")))
            if m:
                seq.append((float(e.get("x", 0.5)), float(e.get("y", 0.5)), int(m.group(0))))
        # Only compare events in the same column: two dots side by side are not a sequence,
        # and treating them as one produced a backwards-time warning on every wide zone.
        for a, b in zip(seq, seq[1:]):
            if abs(a[0] - b[0]) > 0.2:
                continue
            if b[1] < a[1]:
                cp.warn("时间线", z["id"], f"从 y={a[1]:.2f} 到 y={b[1]:.2f}，"
                                           f"年份从 {a[2]} 退到 {b[2]}——读者会当成倒叙")

    # ---------------------------------------------------------------- wording tics
    caps = [str(z.get("caption", "")).strip() for z in zones if z.get("caption")]
    heads = {}
    for c in caps:
        if len(c) >= 2:
            heads.setdefault(c[:2], []).append(c[:10])
    for head, items in heads.items():
        if len(items) >= 3:
            cp.warn("开头重复", f"「{head}…」", f"{len(items)} 条副题同一个开头：{'、'.join(items[:3])}")
    # One aggregate, not one warning per event: forty lines saying the same thing is how a
    # report stops being read, and the count is the number that matters.
    no_anchor = []
    for e in bp.get("events", []):
        if e.get("chapter") is None:
            continue
        t = str(e.get("label", ""))
        if not CHAPTER_REF.search(t) and not YEAR.search(t) and str(e["chapter"]) not in t:
            no_anchor.append(f"{e.get('id')}「{t[:12]}」")
    if no_anchor:
        cp.warn("回查锚", "事件",
                f"{len(no_anchor)}/{len(bp.get('events', []))} 条标注既没有「第 N 回」也没有年份或"
                f"章号数字，读者无法回查原文：{', '.join(no_anchor[:5])}"
                + ("…" if len(no_anchor) > 5 else ""))

    # ---------------------------------------------------------------- sheet
    lines = []
    A = lines.append
    A(f"# 文案初审单 —《{meta.get('title', '')}》")
    A("")
    A(f"画风 `{meta.get('style_id', '?')}` · 网格 {bp['meta']['canvas']['cols']}×"
      f"{bp['meta']['canvas']['rows']} · 单元格 {cell}px · 成图 "
      f"{bp['meta']['canvas']['cols'] * cell}×{bp['meta']['canvas']['rows'] * cell}")
    A("")
    if meta.get("subtitle"):
        A(f"副标题：{meta['subtitle']}")
    A(f"章节覆盖：{len(covered)}/{total or '?'} 章 · 省略 {len(missing)} 章 · "
      f"T1 {len([c for c in bp.get('characters', []) if c.get('tier') == 'T1'])} · "
      f"T2 {len([e for e in bp.get('events', []) if e.get('tier') == 'T2'])}")
    A("")
    A("> 这一页是给读者看的字，按阅读顺序排（从左到右、从上到下）。请当成第一次看到它们。")
    A("")

    for z in zones:
        recs = [r for r in cp.records if r["where"] == z["id"]]
        if not recs:
            continue
        A(f"## {z['id']}　{z.get('name', '')}")
        A(f"`第 {int(z.get('row', 0)) + 1} 行 第 {int(z.get('col', 0)) + 1} 列`")
        A("")
        for r in recs:
            label = {"name": "分区名", "caption": "副题", "label": "标注",
                     "event": "事件", "title": "标题", "subtitle": "副标题"}.get(r["kind"], r["kind"])
            extra = f"，{len(r['lines'])} 行" if len(r["lines"]) > 1 else ""
            A(f"- **{label}**　{r['text']}　`{len(r['text'])} 字 · {r['size']:.0f}px{extra}`")
        A("")

    A("## 机器检查")
    A("")
    if cp.errors:
        A(f"**{len(cp.errors)} 个必须改的问题**")
        A("")
        for e in cp.errors:
            A(f"- {e}")
        A("")
    else:
        A("没有硬错误。")
        A("")
    if cp.warns:
        groups = {}
        for g, w in cp.warns:
            groups.setdefault(g, []).append(w)
        A(f"**{len(cp.warns)} 条提醒**（按类归并）")
        A("")
        for g, items in groups.items():
            A(f"- **{g}**（{len(items)}）：{items[0]}")
            for w in items[1:4]:
                A(f"  - {w}")
            if len(items) > 4:
                A(f"  - …另有 {len(items) - 4} 条")
        A("")

    sizes = sorted([(r["size"], r["text"]) for r in cp.records if r["text"]])
    if sizes:
        s, t = sizes[0]
        A(f"图上最小的字：{s:.0f}px —— 「{t[:20]}」，在 {bp['meta']['canvas']['cols'] * cell}px 宽的图里")
        A("")

    A("## 人工四问（机器答不了）")
    A("")
    A("1. 每个名字都在原文里出现过？逐条 grep，别凭印象——一个想当然的名字会印在图上两百年。")
    A("2. 每条事件的章号/年份都能回到原文？回查锚错了，读者顺着找会找到别人的段落。")
    A("3. 每句副题描述的是**这一格画的东西**，还是一句放到任何一格都成立的抒情？")
    A("4. 通读一遍：有没有两格其实是同一件事，或者某一格的文案在替画面下结论？")
    A("")

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.blueprint)),
                                   "copy_sheet.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"copy sheet  {out}")
    print(f"strings {len(cp.records)}   errors {len(cp.errors)}   warnings {len(cp.warns)}")
    if not args.quiet:
        for e in cp.errors[:20]:
            print("  ERR  " + e)
        if len(cp.errors) > 20:
            print(f"  … {len(cp.errors) - 20} more errors in the sheet")
    if cp.errors:
        sys.exit(2)
    print("Copy is clean enough to lay out. Read the sheet before Gate 2 — the four "
          "questions are the ones a script cannot answer.")


if __name__ == "__main__":
    main()
