#!/usr/bin/env python3
"""Copy review — traceability, then tone, then voice, then measurement.

Four passes, in this order, because they answer different questions:

  0. **Tone**   Was a baseline agreed at all (Step 0.5), and does each line stay inside the
                情绪预算 that came with it? A missing baseline is a hard error: "is this too
                煽情" cannot be settled after the fact, only against something written down.
  1. **Trace**  Can every printed sentence be pointed back at a brief section or an asset id?
                This is the whole合规 story of the skill: not "is it legal" but
                "is it in the material". A claim nobody can source never reaches a plate.
  2. **Voice**  Does it read like a person wrote it, or like a model filled a slot?
  3. **Measure** Does it fit the plate it will be printed on?

Run it before Gate 1. The geometry gets fixed around whatever text survives; reviewing
copy after the skeleton means measuring a skeleton against words nobody kept.

Usage
  python3 lint_copy.py build/blueprint.json -o build/reports/copy_sheet.md
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402

HALF_PUNCT = {",": "，", ".": "。", ";": "；", ":": "：", "!": "！", "?": "？",
              "(": "（", ")": "）"}
PLACEHOLDERS = ("TODO", "todo", "待定", "XXX", "占位", "TBD", "…待补")

# Informational only. The skill does not police advertising law; it reports what it sees
# and puts the liability where it belongs — with the person who signed off the material.
# Patterns, not words: 「晨起第一杯」 is a caption, 「销量第一」 is a claim. A bare word
# list flags both and trains the author to ignore the whole sheet.
AD_TERMS = [
    (r"最[佳好强优低高大小新]", "绝对化比较"),
    (r"第一(名|品牌|销量|款|家|大|个品牌)", "排名宣称"),
    (r"唯一|首个|首创|独家", "排他性宣称"),
    (r"国家级|世界级|顶级|顶尖", "级别宣称"),
    (r"100\s*%|百分百", "完全性宣称"),
    (r"根治|永久|彻底解决|无副作用|包治", "疗效/永久性宣称"),
]

# Facts that are never inferred. Volume alone is not one of them: 「装满 1.5 升」 is a
# use case, 「容量 1.5 升」 is a spec.
FACT_PATTERNS = [
    (r"[¥￥]\s*\d|\d+\s*元|\d+\s*折|到手价|活动价|原价", "价格"),
    (r"\d{4}\s*[.\-/年]\s*\d{1,2}|\d{1,2}\s*月\s*\d{1,2}\s*日", "日期"),
    (r"(容量|型号|功率|尺寸|重量|电压|噪音|保修|认证|编号|批次|标准)\s*[:：]?\s*[\w\d.]+", "规格"),
]

# A financial poster is not "faithful to the material" in the same way a kettle is.
# Printing a client's own 「年化 8%」 is an administrative penalty for the publisher, so
# these are hard errors even when the wording came from the client. Switch off with
# meta.compliance: "trace_only" if the material has already been cleared by counsel —
# it is a switch, not a default.
FINANCE_HARD = [
    (r"保本|保收益|保证收益|保底|稳赚|稳赚不赔|零风险|无风险|绝对安全|必赚", "承诺收益或保本"),
    (r"预期收益|预计收益|预期年化", "预测收益（只能用「业绩比较基准」）"),
    (r"确诊即赔|必然赔付|一定赔", "保险赔付承诺"),
    (r"我(买|投|赚)了|我靠它|亲测.{0,4}赚", "第一人称收益证言"),
]

# A percentage next to a return word is the single highest-risk string in the file.
YIELD_CONTEXT = r"收益|年化|回报|利率|利率|净值增长|业绩"
QUALIFIER = r"业绩比较基准|历史|过往|截至|模拟"


# --- plate-scale voice ------------------------------------------------------------
# At 12-18 characters a caption cannot recover from a slogan. These detectors exist
# because the failure is countable, not because a word is banned.

OBJECT_CHARS = set("杯瓶壶罐盒袋箱包盘碗筷勺锅刀叉桌椅床柜抽屉窗门灯镜框纸张笔本册账"
                   "票据单卡键屏幕机表镜头包袋巾帽衣衫鞋袜套盒袋篮车推冰箱炉台面墙地板货架"
                   "器历碗筷缸桶棒杆绳轮针线勺铲")
MEASURE_RE = r"[一二三四五六七八九十几两半]\s*(张|只|个|杯|瓶|本|支|把|条|件|台|块|片|袋|盒|双|行|格|张)"
ABSTRACT_WORDS = ("部分", "方式", "一切", "可能", "事情", "东西", "生活", "自己",
                  "状态", "空间", "价值", "意义", "未来", "选择")

COUPLET_PATTERNS = [
    (r"[^，]{2,6}之前，先[^，]{1,6}", "对偶：X 之前，先 Y"),
    (r"[^，]{2,6}在前，[^，]{2,6}在后", "对偶：X 在前，Y 在后"),
    (r"^先[^，]{1,6}，再[^，]{1,6}$", "对偶：先 X，再 Y"),
    (r"一次[^，]{1,4}，一次[^，]{1,4}", "对偶：一次 X，一次 Y"),
    (r"[^，]{2,6}是[^，]{1,4}，[^，]{2,6}是[^，]{1,4}", "对偶：A 是 X，B 是 Y"),
]
APHORISM = r"才是|不过是|终究|说到底|优先|最麻烦|不该|与其|不如|无非"


def has_object(text):
    """Does the line contain something you could photograph, or a number?"""
    if re.search(r"\d", text):
        return True
    if re.search(MEASURE_RE, text):
        return True
    return any(ch in OBJECT_CHARS for ch in text)


VOICE_PATTERNS = [
    ("格言腔", r"只为|才是|不过是|无非|终究|说到底"),
    ("拔高", r"见证|定义|重塑|开启|赋能|致|献给"),
    ("假对比", r"不是.{1,6}而是"),
    ("抒情替代陈述", r"仿佛|似乎|像是|好像|如同"),
    ("万能背景", r"在这个.{0,6}的时代|每一个.{0,4}的人"),
]

# --- tone: the baseline is a decision, and it is countable -------------------------
# Every one of these words tells the reader how to feel instead of what happened. One of
# them on a 12-caption poster is a choice; six of them is the whole piece asking to be
# pitied, and on a medical or insurance product that reads as manipulation.
EMOTION_WORDS = (
    "心酸", "崩溃", "绝望", "无助", "咬牙", "硬撑", "硬扛", "熬过", "熬到", "熬了",
    "眼泪", "掉泪", "哭了", "心疼", "不容易", "太难", "雪上加霜", "不敢想", "扎心",
    "揪心", "撑住", "扛住", "认命", "苦撑", "默默", "独自", "终于等到", "说不出口",
    "想哭", "忍不住", "顾不上自己", "把最好的留", "从来不说", "谁懂",
)
# The specific failure the last build made: pick the most painful version of a scene
# instead of the most common one. Pain + a small hour in one line is that tell.
MISERY_BODY = (r"发烧|烧到|高烧|咳嗽|住院|手术|抢救|输液|吊针|挂水|打针|化验单|病危|化疗|"
               r"确诊|疼痛|伤口")
MISERY_HOUR = (r"半夜|凌晨|深夜|通宵|雨夜|大年三十|拖了|拖着|拖到|忍了|半个月|一整夜|"
               r"连着几天")


def emotion_hits(text):
    return [w for w in EMOTION_WORDS if w in (text or "")]


# --- caption mode ------------------------------------------------------------------
# A `rule` caption is not a description, so "does it contain a photographable object" is
# the wrong question. The right one is: which clause is being applied at this step, and is
# it traceable? A rule that cannot be pointed at the policy text is a rule the writer
# invented on the canvas.
RULE_ELEMENTS = [
    (r"\d", "数字"),
    (r"免赔|限额|上限|给付比例|等待期|续保|补偿原则|不重复给付|按次|余额|基数|结算|社保|自付"
     r"|比例|费用|门诊|住院|药品", "条款要素"),
    (r"单次|每次|同一次|按次|届满|期间|年度", "计量单位"),
    (r"(?:不|仅|只|须|应|不得|不再|未)[^，。]{0,8}", "条件"),
]


def rule_elements(text):
    return [name for pat, name in RULE_ELEMENTS if re.search(pat, text or "")]


def misery_hits(text):
    body = re.search(MISERY_BODY, text or "")
    hour = re.search(MISERY_HOUR, text or "")
    return [body.group(0), hour.group(0)] if (body and hour) else []


def reader_strings(bp):
    """Every string a reader actually sees — not just the plates.

    A flat caption under a melodramatic page title still reads as melodrama, and a
    persona whose whole setup is "the worst night of her year" carries the tone for a
    row of otherwise sober cells. Reviewing only `zones[].caption` is how 煽情 survived
    the last review with zero flags.
    """
    out = []
    head = bp["meta"].get("header") or {}
    for k in ("title", "subtitle", "meta_line"):
        if head.get(k):
            out.append(("header.%s" % k, head[k]))
    for i, r in enumerate(bp.get("rows", [])):
        for k in ("name", "line1", "line2"):
            if r.get(k):
                out.append(("rows[%d].%s" % (i, k), r[k]))
    for c in bp.get("columns", []):
        if c.get("note"):
            out.append(("columns[%s].note" % c.get("id", "?"), c["note"]))
    for t in bp.get("targets", []):
        for j, pg in enumerate(t.get("pages") or []):
            for k in ("title", "subtitle", "eyebrow"):
                if pg.get(k):
                    out.append(("%s 第 %d 页 %s" % (t.get("id"), j + 1, k), pg[k]))
            for k, ln in enumerate(pg.get("lines") or []):
                out.append(("%s 第 %d 页 lines[%d]" % (t.get("id"), j + 1, k), ln))
    body = (pl.voice_of(bp).get("body") or "").strip()
    if body:
        out.append(("voice.body", body))
    return out


def tone_metrics(bp):
    """What the tone contract actually cost, in numbers, so a reviewer can see the drift."""
    voice = pl.voice_of(bp)
    tone = (voice.get("tone") or "").strip()
    budget = pl.emotion_budget(bp) if tone else 0
    written = [(z["id"], (z.get("caption") or "").strip()) for z in bp["zones"]
               if (z.get("caption") or "").strip()
               and not (z.get("caption") or "").startswith("TODO")]
    hits = [(zid, emotion_hits(t), t) for zid, t in written if emotion_hits(t)]
    punches = [zid for zid, t in written
               if re.search(APHORISM, t) or any(re.search(p, t) for p, _n in COUPLET_PATTERNS)]
    body = (voice.get("body") or "").strip()
    side = [(loc, emotion_hits(t), t) for loc, t in reader_strings(bp) if emotion_hits(t)]
    misery = [(loc, misery_hits(t), t) for loc, t in reader_strings(bp) if misery_hits(t)]
    for zid, t in written:
        if misery_hits(t):
            misery.append((zid, misery_hits(t), t))
    return {
        "tone": tone,
        "label": pl.TONE_MODES[tone]["label"] if tone in pl.TONE_MODES else "未定",
        "mode": pl.caption_mode(bp),
        "budget": budget,
        "written": len(written),
        "hits": hits,
        "hit_count": sum(len(h) for _z, h, _t in hits),
        "side_hits": side,
        "side_count": sum(len(h) for _l, h, _t in side),
        "misery": misery,
        "punches": punches,
        "punch_quota": voice.get("punch_quota", 1),
        "body": body,
        "body_hits": emotion_hits(body) if body else [],
        "pov": voice.get("pov", ""),
        "sample": voice.get("sample", ""),
    }


def lint(bp, grid):
    issues, warns = [], []
    cap = pl.caption_capacity(grid.cell, grid.caption_rect(0, 0))
    zones = bp["zones"]
    seen = {}

    # --- tone: first question of the sheet, because it outranks every other check ------
    voice = pl.voice_of(bp)
    tone = (voice.get("tone") or "").strip()
    budget = pl.emotion_budget(bp) if tone else 0
    mode = pl.caption_mode(bp)
    rule_mode = mode == "rule"
    if tone not in pl.TONE_MODES:
        issues.append("基调未登记：先做 Step 0.5 的五个问题（基调 / 人称 / 煽情预算 / 金句配额 / "
                      "语感样例），把结论写进 brief.voice。没有基线，『这句是不是太煽情』"
                      "只能靠事后吵")
    else:
        if not (voice.get("pov") or "").strip():
            warns.append("基调：人称未填——十二条会各写各的（第三人称白描 / 第二人称 / 第一人称）")
        if not (voice.get("sample") or "").strip():
            warns.append("基调：语感样例未填——作者没有可对照的一句，跑偏了也没人发现")
    if rule_mode and pl.is_financial(bp):
        warns.append("文案模式：规则解读。每条 caption 必须能指回条款原文，"
                     "写完自己念一遍：它是在讲这一步怎么算，还是在讲这个人多不容易")
    elif not rule_mode and pl.is_financial(bp):
        warns.append("文案模式：场景叙述。保险/理财的四格通常应写「这一步按哪条算」，"
                     "也就是 `caption_mode: \"rule\"`——叙述容易滑向讲故事")

    emotional_lines = []

    for z in zones:
        zid = z["id"]
        text = (z.get("caption") or "").strip()
        tag = "%s" % zid

        if not text:
            issues.append("%s: caption 为空" % tag)
            continue
        if text.startswith("TODO") or any(p in text for p in PLACEHOLDERS):
            issues.append("%s: caption 仍是占位文本「%s」" % (tag, text))
            continue

        src = (z.get("caption_source") or "").strip()
        if not src:
            issues.append("%s: 缺 caption_source——图上这句话是从哪来的" % tag)

        n = len(text)
        if n > cap["max_chars"]:
            issues.append("%s: %d 字超出板子容量 %d 字（%d 字/行 × %d 行）" % (
                tag, n, cap["max_chars"], cap["chars_per_line"], cap["max_lines"]))
        elif n > cap["max_chars"] * 0.92:
            warns.append("%s: %d 字，接近上限 %d，换行位置会很挤" % (tag, n, cap["max_chars"]))

        for half, full in HALF_PUNCT.items():
            # A decimal point between digits is not punctuation.
            esc = re.escape(half)
            if re.search(r"(?<!\d)" + esc + r"|" + esc + r"(?!\d)", text):
                warns.append("%s: 半角「%s」应改全角「%s」" % (tag, half, full))
        if text.count("（") != text.count("）"):
            issues.append("%s: 括号不配对" % tag)
        if re.search(r"[，。]{2,}", text):
            warns.append("%s: 标点重复" % tag)
        if text.count("、") >= 3:
            warns.append("%s: 顿号清单（%d 个顿号）——三个名词加一个「和」是填充，不是信息"
                         % (tag, text.count("、")))

        for name, pat in VOICE_PATTERNS:
            if re.search(pat, text):
                warns.append("%s: %s「%s」" % (tag, name, re.search(pat, text).group(0)))
        for pat, name in COUPLET_PATTERNS:
            if re.search(pat, text):
                warns.append("%s: %s「%s」——对偶说了标题已经说过的事" % (
                    tag, name, text))

        # Tone budget. A 煽情词 is not illegal and not always wrong: it is a withdrawal
        # from a budget the client agreed to, and over budget the piece stops being the
        # thing that was agreed.
        hits = emotion_hits(text)
        if hits:
            emotional_lines.append((tag, hits, text))
            if len(hits) > budget:
                msg = "%s: 煽情词 %d 处（%s），基线是「%s」、每条上限 %d" % (
                    tag, len(hits), "、".join(hits),
                    pl.TONE_MODES[tone]["label"] if tone in pl.TONE_MODES else "未定", budget)
                if tone in ("plain", "expert", "witty"):
                    issues.append(msg + "——删掉感受，只留发生了什么")
                else:
                    warns.append(msg + "——留一处最具体的，其余换成动作或物件")
        if re.search(MISERY_BODY, text) and re.search(MISERY_HOUR, text):
            pass  # 苦情取材 is tallied once, over every reader-facing string (tone_metrics)

        m = re.search(APHORISM, text)
        if m:
            warns.append("%s: 格言腔「%s」——这一格画的是什么，就写那个东西" % (tag, m.group(0)))
        for w in ABSTRACT_WORDS:
            if w in text:
                warns.append("%s: 抽象名词「%s」——换成一个能拍照的东西" % (tag, w))
                break
        if "，" not in text and "。" not in text and len(text) <= 9 and not rule_mode:
            warns.append("%s: 单短语无动作「%s」——加一个动词" % (tag, text))
        if not rule_mode and not has_object(text):
            warns.append("%s: 全句没有具体物件或数字「%s」" % (tag, text))
        if rule_mode:
            if not rule_elements(text):
                warns.append("%s: 这一格没有规则要素「%s」——读者读完不知道该按哪条算"
                             % (tag, text))
            # A rule statement is only as good as the clause behind it. Narrative copy can
            # point at the brief; a rule cannot, because the brief does not legislate.
            if "client" not in src:
                issues.append("%s: 规则解读没有指回条款（source=%r）——图上每一条规则都必须"
                              "能在客户条款里找到原文，否则就是替保险产品立规" % (tag, src))
        for pat, kind in AD_TERMS:
            m = re.search(pat, text)
            if m:
                warns.append("%s: %s「%s」——忠实于素材即照排，风险由签字方承担"
                             % (tag, kind, m.group(0)))

        if text in seen:
            issues.append("%s: 与 %s 的 caption 完全相同「%s」" % (tag, seen[text], text))
        else:
            seen[text] = tag

        # Money, dates and specs are the class of fact that is never inferred.
        for pat, kind in FACT_PATTERNS:
            m = re.search(pat, text)
            if m and "client" not in src:
                issues.append("%s: 出现%s「%s」，但 source 是「%s」——这类信息必须由客户书面确认"
                              % (tag, kind, m.group(0), src))

    # Template openings: count the first character, not the sentence.
    firsts = {}
    for z in zones:
        t = (z.get("caption") or "").strip()
        if t:
            firsts.setdefault(t[:1], []).append(z["id"])
    for ch, ids in firsts.items():
        if len(ids) >= 3:
            warns.append("模板开头：%d 条 caption 都以「%s」开头（%s）——换主语，不是换句子"
                         % (len(ids), ch, "、".join(ids)))
    twins = [z["id"] for z in zones
             if re.search(r"[，,]\s*和(他|她|它)的", z.get("caption") or "")]
    if len(twins) >= 2:
        warns.append("对偶副标题：%d 条用了「，和他的…」句式（%s）" % (len(twins), "、".join(twins)))

    # --- financial copy: hard blocks, regardless of where the wording came from ------
    cat = bp["meta"].get("category") or "physical"
    if cat in ("finance", "insurance") and bp["meta"].get("compliance") != "trace_only":
        for z in zones:
            t = (z.get("caption") or "").strip()
            if not t:
                continue
            for pat, kind in FINANCE_HARD:
                m = re.search(pat, t)
                if m:
                    issues.append("%s: %s「%s」——这类表述不能上图，即使来自客户素材"
                                  % (z["id"], kind, m.group(0)))
            if re.search(YIELD_CONTEXT, t) and re.search(r"\d+(\.\d+)?\s*%", t):
                if not re.search(QUALIFIER, t):
                    issues.append("%s: 收益数字「%s」没有限定语——必须写成「业绩比较基准」或"
                                  "「历史业绩」，并配数据截至日" % (z["id"], t))
        if cat == "insurance":
            warns.append("保险类：确认图上的保障范围、免责与等待期，与条款一致；"
                         "「保证续保」类表述需资质支撑")

    # --- aggregate: one countable health metric per caption mode ----------------------
    written = [z for z in zones if (z.get("caption") or "").strip()
               and not (z.get("caption") or "").startswith("TODO")]
    if rule_mode:
        # In rule mode the failure is not "no object", it is "no clause": a caption that
        # reads like a scene description has drifted back into storytelling.
        bare = [z["id"] for z in written if not rule_elements(z.get("caption") or "")]
        if bare:
            warns.append("规则要素缺失 %d/%d 条（%s）——这几格还是在讲画面，没讲规则"
                         % (len(bare), len(written), "、".join(bare)))
        numbered = [z for z in written if re.search(r"\d", z.get("caption") or "")]
        if written and len(numbered) < len(written) / 3.0:
            warns.append("带数字的规则只有 %d/%d 条——全篇都是「按规则计算」式表述时，"
                         "这页规则解读退化成科普散文" % (len(numbered), len(written)))
    else:
        concrete = [z["id"] for z in written if has_object(z.get("caption") or "")]
        cov = len(concrete) / float(len(written)) if written else 1.0
        if written and cov < 0.5:
            issues.append("具体物件覆盖率 %.0f%%（%d/%d）——一半以上的板子上没有一件东西，"
                          "这不是文案短，是文案空" % (cov * 100, len(concrete), len(written)))
        elif written and cov < 0.66:
            warns.append("具体物件覆盖率 %.0f%%（%d/%d），目标 ≥66%%" % (
                cov * 100, len(concrete), len(written)))

    # --- tone aggregate: one number the client can compare across drafts ---------------
    tm = tone_metrics(bp)
    if tm["tone"] in pl.TONE_MODES:
        if tm["hit_count"]:
            warns.append("基调实测：煽情词 %d 处 / %d 条（基线「%s」的上限是每条 %d）" % (
                tm["hit_count"], tm["written"], tm["label"], tm["budget"]))
        used = len(tm["punches"])
        quota = tm["punch_quota"]
        try:
            quota = int(quota)
        except (TypeError, ValueError):
            quota = 1
        if used > quota:
            warns.append("金句配额：%d 条在用力（%s），配额 %d——一张图只有一个重点，"
                         "每格都在用力等于没有重点" % (used, "、".join(tm["punches"]), quota))
        if tm["body_hits"] and len(tm["body_hits"]) > max(2, tm["budget"] * 2):
            warns.append("正文（voice.body）煽情词 %d 处（%s）——图和正文是同一篇东西，"
                         "图克制、正文煽情，读者会认为在演" % (
                             len(tm["body_hits"]), "、".join(tm["body_hits"])))

        # Tone is set by the loudest string on the page, not by the captions alone.
        for loc, hs, text in tm["side_hits"]:
            warns.append("%s: 煽情词「%s」——标题、人群设定、正文同样受基调管辖，"
                         "板子上克制、标题上使劲，读者只会记住后者" % (loc, "、".join(hs)))
        for loc, ms, text in tm["misery"]:
            msg = "%s: 苦情取材「%s / %s」——把最难的一版端上来，读者记住的是惨，不是产品；" \
                  "换成这个人最常见的那一次" % (loc, ms[0], ms[1])
            if tm["tone"] in ("plain", "expert"):
                issues.append(msg + "（%s 基调下不接受）" % tm["label"])
            else:
                warns.append(msg)

    # A content word repeated across most plates reads as a template even when every
    # sentence is fine alone. Punctuation and grammar particles are not evidence — counting
    # them buries the one real signal under ten false ones, and a report people learn to
    # ignore is worse than no report.
    FUNC_CHARS = set("的了在和一是有不这那人个我你他她它上下着还就都也又把被给对从到与及或"
                     "很再才更没可让做用里外中前后时年天日为以与而之其")
    PUNCT = set("，。、：；！？…—「」（）《》“”‘’,.;:!?")
    freq = {}
    for z in written:
        for ch in set((z.get("caption") or "")):
            # A space between 「800 元」 and what follows is layout, not a content word.
            # Digits are facts, not filler: 「100 / 800 / 30」 are three different numbers,
            # and counting their shared zero would bury the one real repetition.
            if ch in PUNCT or ch.isspace() or ch.isdigit() or ch in FUNC_CHARS:
                continue
            freq[ch] = freq.get(ch, 0) + 1
    hits = sorted(((c, n) for c, n in freq.items() if n >= 5), key=lambda kv: -kv[1])[:2]
    for ch, n in hits:
        warns.append("字频：『%s』出现在 %d 条 caption 里——这一行没有别的可说" % (ch, n))

    # Same opening across plates is the cheapest template tell to detect.
    opens = {}
    for z in written:
        t = (z.get("caption") or "").strip()
        if len(t) >= 2:
            opens.setdefault(t[:2], []).append(z["id"])
    for op, ids in opens.items():
        if len(ids) >= 3:
            warns.append("同构开头：%d 条以「%s」开头（%s）——换主语，不是换句式"
                         % (len(ids), op, "、".join(ids)))

    # Structural copy
    if not (bp["meta"].get("header", {}).get("title") or "").strip():
        issues.append("meta.header.title 为空——主图没有标题")
    foot = bp["meta"].get("footer", {})
    if not (foot.get("note") or "").strip():
        warns.append("footer.note 为空：主图缺少「画像为示意，非真实个体」类声明")
    if not (foot.get("signoff") or "").strip():
        warns.append("footer.signoff 为空：图上没有签字人")
    for i, c in enumerate(bp.get("columns", [])):
        if not (c.get("title") or "").strip():
            issues.append("columns[%d] 没有标题" % i)
    for i, r in enumerate(bp.get("rows", [])):
        if not (r.get("name") or "").strip():
            issues.append("rows[%d] 没有人群名" % i)
        if not (r.get("line2") or "").strip():
            warns.append("rows[%d] 缺 line2（触发时刻）——这一行会退化成一个人名标签" % i)

    # Timeline must run forwards; a band that jumps back reads as a typo.
    prev_val, prev_date = None, ""
    for ph in bp.get("band", {}).get("phases", []):
        d = ph.get("date", "")
        m = re.search(r"(\d{1,2})[.\-/](\d{1,2})", d)
        if m:
            val = (int(m.group(1)), int(m.group(2)))
            # A campaign that starts in November and ends in February is not running
            # backwards; it crossed the year. Only a small backward step is a typo.
            if prev_val:
                went_back = val < prev_val
                crossed_year = prev_val[0] - val[0] > 6
                if went_back and not crossed_year:
                    warns.append("时间轴倒流：%s 在 %s 之后" % (d, prev_date))
            prev_val, prev_date = val, d
        else:
            warns.append("时间轴日期读不出月/日：%s" % (d or ph.get("label", "?")))

    return issues, warns, cap


def sheet(bp, issues, warns, cap):
    tm = tone_metrics(bp)
    L = ["# 文案审核表", "",
         "板子容量：每行约 %d 字 × %d 行 = %d 字（字号 %dpx @ cell %d）" % (
             cap["chars_per_line"], cap["max_lines"], cap["max_chars"],
             cap["font_size"], bp["meta"]["grid"]["cell"]),
         "",
         "## 基调（Step 0.5 的结论，写第一句之前就该有）", "",
         "- 基线：**%s**（%s）· 人称：%s · 文案模式：**%s**（%s）" % (
             tm["label"], tm["tone"] or "未登记", tm["pov"] or "（未填）",
             pl.CAPTION_MODES[tm["mode"]]["label"], tm["mode"]),
         "- 煽情词预算：每条 ≤ %d；实测 **%d 处 / %d 条**（另有标题、人群设定、正文 %d 处）" % (
             tm["budget"], tm["hit_count"], tm["written"], tm["side_count"]),
         "- 苦情取材（病痛 + 深夜/拖延 同句）：**%d 处**" % len(tm["misery"]),
         "- 金句配额：%s；已用 %d 条" % (tm["punch_quota"], len(tm["punches"])),
         "- 语感样例：%s" % (tm["sample"] or "（未填——作者只能凭感觉）"),
         ""]
    all_hits = [(z, hs, t) for z, hs, t in tm["hits"]] + \
               [(loc, hs, t) for loc, hs, t in tm["side_hits"]]
    if all_hits:
        L.append("| 位置 | 煽情词 | caption / 原句 |")
        L.append("|---|---|---|")
        for loc, hs, text in all_hits:
            L.append("| %s | %s | %s |" % (loc, "、".join(hs),
                                           text.replace("|", "\\|").replace("\n", " / ")))
        L.append("")
    if tm["misery"]:
        L.append("| 位置 | 苦情取材 | 原句 |")
        L.append("|---|---|---|")
        for loc, ms, text in tm["misery"]:
            L.append("| %s | %s | %s |" % (loc, " + ".join(ms),
                                           text.replace("|", "\\|").replace("\n", " / ")))
        L.append("")
    L += ["| zone | 人群 | 场景 | caption | 字数 | source |", "|---|---|---|---|---|---|"]
    rows = {(r.get("id")): r for r in bp.get("rows", [])}
    cols = {c.get("id"): c for c in bp.get("columns", [])}
    for z in bp["zones"]:
        cap_t = (z.get("caption") or "").strip()
        L.append("| %s | %s | %s | %s | %d/%d | %s |" % (
            z["id"],
            (rows.get(z.get("persona"), {}) or {}).get("name", z.get("persona", "—")),
            (cols.get(z.get("scene"), {}) or {}).get("title", z.get("scene", "—")),
            cap_t.replace("|", "\\|") or "（空）",
            len(cap_t), cap["max_chars"],
            z.get("caption_source", "") or "**缺**"))
    written = [z for z in bp["zones"] if (z.get("caption") or "").strip()]
    if pl.caption_mode(bp) == "rule":
        bare = [z for z in written if not rule_elements(z.get("caption") or "")]
        numbered = [z for z in written if re.search(r"\d", z.get("caption") or "")]
        L += ["", "## 规则解读：可数指标", "",
              "- 规则要素覆盖率：**%d/%d**（每条都要有数字 / 条款要素 / 计量单位 / 条件之一）" % (
                  len(written) - len(bare), len(written)),
              "- 带数字的规则：**%d/%d**（目标 ≥ 1/3，低于就是「按规则计算」式散文）" % (
                  len(numbered), len(written)),
              "- 条条可溯源：规则类 caption 的 source 必须是 `client-confirmed:*`，"
              "因为 brief 不立法，条款才立法",
              "- 改写顺序：这一格产生什么费用 → 按哪条算 → 边界在哪（不赔的那半句）",
              "", "## 硬错误（必须改）", ""]
    else:
        concrete = [z for z in written if has_object(z.get("caption") or "")]
        L += ["", "## 说人话：可数指标", "",
              "- 具体物件覆盖率：**%d/%d（%.0f%%）**，目标 ≥ 66%%" % (
                  len(concrete), len(written),
                  (100.0 * len(concrete) / len(written)) if written else 100.0),
              "- 对偶 / 格言 / 抽象名词 / 无动作短语：见下方提醒逐条列出",
              "- 改写顺序：删判断句 → 换动作 → 补物件 → 压字数（最多比原句长两个字）",
              "", "## 硬错误（必须改）", ""]
    L += ["- %s" % i for i in issues] or ["- 无"]
    L += ["", "## 提醒（数字可数，自己判断）", ""]
    L += ["- %s" % w for w in warns] or ["- 无"]
    L += ["", "## 机器查不了的七件事，交付前自己答一遍", "",
          "1. 每个数字、价格、规格、日期，都能在客户素材里找到原文吗？找不到就删。",
          "2. 每条 caption 描述的是**这一格**，还是换成任何一格都成立？",
          "3. 十二条并排读：是不是有四条用同一种开头、同一种语气？",
          ("4. 这一格有没有滑回讲故事（谁在抱谁、谁更难受）？四格要讲的是**这一步按哪条算**。"
           if pl.caption_mode(bp) == "rule" else
           "4. 有没有哪一格在解释画面（「体现了…」），而不是在说一件具体的事？"),
          "5. 人群描述里有没有替客户下了「他们就是这样的人」的结论？改成「面向…的人群」。",
          "6. 图里生成出来的人，有没有配上第一人称证言、使用时长或效果数据？有就是虚假广告。",
          "7. 把这一页读给一个不懂这行的人听：他先知道发生了什么，还是先被吓到/被可怜到？"
          "后者说明基调已经跑过 Step 0.5 定下的那条线。"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="promo-atlas copy review")
    ap.add_argument("blueprint")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    bp_path = os.path.abspath(args.blueprint)
    base = os.path.dirname(bp_path)
    bp = pl.load(bp_path)
    grid, _r, _c = pl.make_grid(bp)

    issues, warns, cap = lint(bp, grid)
    tm = tone_metrics(bp)
    out = args.out or os.path.join(base, "reports", "copy_sheet.md")
    pc.ensure_dir(os.path.dirname(out))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(sheet(bp, issues, warns, cap))

    print("文案审核：硬错误 %d，提醒 %d   → %s" % (len(issues), len(warns), out))
    print("基调：%s · 煽情词 %d 处 / %d 条（上限 %d）· 苦情取材 %d 处 · 金句 %d 条（配额 %s）" % (
        tm["label"], tm["hit_count"], tm["written"], tm["budget"],
        len(tm["misery"]), len(tm["punches"]), tm["punch_quota"]))
    for i in issues:
        print("  ✗ %s" % i)
    for w in warns[:12]:
        print("  · %s" % w)
    if len(warns) > 12:
        print("  · …另有 %d 条，见 copy_sheet.md" % (len(warns) - 12))
    if issues:
        print("\n硬错误未清，不要进 Gate 1。文案改完再跑一次。", file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
