#!/usr/bin/env python3
"""Layout resolution and geometry checks.

One place decides where every rectangle is. `skeleton.py`, `stitch.py` and
`lint_copy.py` all import from here, so the preview cannot promise a caption more
room than the stitcher will give it — the classic way a poster build silently
breaks is two scripts each computing their own plate.
"""

import math
import os

import promo_common as pc

DEFAULT_META = {
    "grid": {"cols": 4, "rows": 3, "cell": 2048, "gutter_ratio": 0.016, "pad_ratio": 0.035},
    "layout": {"band": True, "header_ratio": 0.26, "footer_ratio": 0.135,
               "row_label_ratio": 0.42, "col_header_ratio": 0.20, "caption_ratio": 0.145},
    "style": "cartoon_flat",
    "label_plate": "white",
}

# Caption typography, as a fraction of cell. Kept here so capacity maths and the
# renderer agree on how many characters a plate can hold.
# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

# `safe` is the part of the frame the platform's own UI sits on top of: a like button
# on the right of a vertical video, a caption bar along the bottom of a note. Content
# inside it is content the viewer never sees, so the poster pads around it instead of
# printing a risk disclosure underneath a comment field.
PLATFORMS = {
    "xiaohongshu": {
        "label": "小红书", "ratio": "3:4", "px": (1242, 1656),
        "safe": {"top": 0.045, "right": 0.040, "bottom": 0.070, "left": 0.040},
        "max_pages": 18, "note": "底部标题栏与话题标签压住画面下缘",
    },
    # 长图 is its own channel, not a taller carousel page. Every mainstream feed lets the
    # reader open one tall image full-screen; what it does not give you is a swipe, so the
    # whole story has to hold in a single column of attention. Capped at 1:4 — past that
    # the platform downsamples it into a grey strip and the caption plates stop resolving.
    "xiaohongshu_long": {
        "label": "小红书长图", "ratio": "1:4", "px": (1242, 4968), "long": True,
        "safe": {"top": 0.030, "right": 0.035, "bottom": 0.045, "left": 0.035},
        "max_pages": 1, "note": "信息流先只露顶部 1/4，标题与结论必须在头一屏内读完",
    },
    "long_image": {
        "label": "通用长图", "ratio": "1:4", "px": (1242, 4968), "long": True,
        "safe": {"top": 0.030, "right": 0.035, "bottom": 0.045, "left": 0.035},
        "max_pages": 1, "note": "微博/公众号/私域通用；高度不超过宽度的 4 倍",
    },
    "douyin": {
        "label": "抖音 / 视频号", "ratio": "9:16", "px": (1080, 1920),
        "safe": {"top": 0.055, "right": 0.110, "bottom": 0.110, "left": 0.040},
        "max_pages": 1, "note": "右侧点赞/评论键与底部文案条遮挡面积最大",
    },
    "wechat_moments": {
        "label": "朋友圈", "ratio": "1:1", "px": (1080, 1080),
        "safe": {"top": 0.045, "right": 0.045, "bottom": 0.045, "left": 0.045},
        "max_pages": 9, "note": "九宫格里会被裁成 1:1 缩略图，标题必须在中央",
    },
    "weibo": {
        "label": "微博", "ratio": "16:9", "px": (1600, 900),
        "safe": {"top": 0.070, "right": 0.050, "bottom": 0.120, "left": 0.050},
        "max_pages": 9, "note": "信息流按宽度铺满，上下会被裁",
    },
    "official_account": {
        "label": "公众号头图", "ratio": "2.35:1", "px": (900, 383),
        "safe": {"top": 0.060, "right": 0.040, "bottom": 0.060, "left": 0.040},
        "max_pages": 1, "note": "只有 383px 高，字号必须按最小可读反推",
    },
    "taobao": {
        "label": "电商主图", "ratio": "1:1", "px": (800, 800),
        "safe": {"top": 0.040, "right": 0.040, "bottom": 0.040, "left": 0.040},
        "max_pages": 5, "note": "主图第一张带角标，右上一角会被覆盖",
    },
    "print_backdrop": {
        "label": "发布会背板", "ratio": "16:9", "px": (6000, 3375),
        "safe": {"top": 0.070, "right": 0.045, "bottom": 0.110, "left": 0.045},
        "max_pages": 1, "note": "远看三秒，标题要占画面高度 15% 以上",
    },
}

# Financial products carry obligations a physical product does not: a risk disclosure that
# must stay legible, a data cut-off date, an institution and a licence. These are not
# style choices and they do not shrink to fit.
FINANCE_CATEGORIES = ("finance", "insurance")

# A long image may be four times as tall as it is wide. Beyond that every feed compresses
# it and the plates turn to grey — the cap is a platform fact, not a preference.
LONG_MAX_ASPECT = 4.0

# Copy tone. Selected by the user in Step 0.5, recorded in brief.voice, enforced by
# lint_copy. `budget` is how many 煽情词 one caption may contain at that baseline.
TONE_MODES = {
    "plain":  {"label": "平实陈述", "budget": 0,
               "note": "只说发生了什么，不解释读者该有什么感受"},
    "warm":   {"label": "温和共情", "budget": 1,
               "note": "承认这件事烦，但不放大它"},
    "urgent": {"label": "紧迫提醒", "budget": 1,
               "note": "把截止日与后果说清楚，不靠情绪施压"},
    "expert": {"label": "专业说理", "budget": 0,
               "note": "给条款、给算法、给边界，形容词一律删"},
    "witty":  {"label": "轻松调侃", "budget": 0,
               "note": "玩笑开在场景上，不开在产品与用户身上"},
}

# What a caption is FOR. Two jobs, two grammars, and they are not interchangeable:
#   narrative — 这一格画了什么（消费品的场景矩阵用这个）
#   rule      — 这个场景下，条款怎么算（保险/理财的四格用这个）
# A rule caption that slips into storytelling reads as an ad; a narrative caption on an
# insurance page leaves the reader with a feeling and no number.
CAPTION_MODES = {
    "narrative": {"label": "场景叙述", "note": "画面里发生了什么"},
    "rule":      {"label": "规则解读", "note": "这一步产生什么费用、按哪条规则算"},
}

# ---------------------------------------------------------------------------
# Information density — v1.2.0
# ---------------------------------------------------------------------------
# A tile that exists is not a tile that says something. The 1.1.1 build shipped eight
# code-drawn cards with no words or numbers on them and stitch reported `placeholder: 0`,
# because `placeholder` only counted *missing files*. These four declarations are the
# contract lint_density.py, stitch.py and audit_assets.py all read.

INFO_ORIGINS = ("ai", "code_card", "evidence", "chart")

DENSITY_LIMITS = {
    "facts_per_zone": 1,          # every cell must add at least one new fact
    "units_per_page": 6,          # a carousel row / full page
    "units_cover": 3,             # the cover is the only page everyone sees
    "units_end": 4,               # evidence + disclosure closing page
    "min_info_area": 0.18,        # information-bearing rectangles / usable page area
    "max_repeat_ratio": 0.30,     # repeated facts stop counting as information
    # How much of a cell's image area is counted as information-bearing, by origin.
    # An illustration carries its facts on a plate inside the frame; a rule card *is*
    # the information. A cell with no declared facts contributes zero either way.
    "info_weight": {"ai": 0.25, "code_card": 1.0, "evidence": 1.0, "chart": 1.0},
}


def density_limits(bp):
    """Per-build overrides win; the defaults above are the agreed baseline (Step 0.5)."""
    d = dict(DENSITY_LIMITS)
    d.update((bp.get("meta", {}).get("density_limits") or {}))
    w = dict(DENSITY_LIMITS["info_weight"])
    w.update(d.get("info_weight") or {})
    d["info_weight"] = w
    return d


def facts_of(bp):
    return {f.get("id"): f for f in (bp.get("meta", {}).get("key_facts") or [])
            if isinstance(f, dict) and f.get("id")}


def zone_fact_ids(zone):
    return [x for x in (zone.get("facts") or []) if isinstance(x, str) and x.strip()]


def platform_spec(name):
    return PLATFORMS.get((name or "").strip(), {})


def voice_of(bp):
    """The tone contract, or {} when nobody filled it in. Step 0.5 exists because of {}.  """
    return (bp.get("meta", {}) or {}).get("voice") or {}


def tone_of(bp):
    """Resolved tone: the declared one, or the category default when it is missing."""
    v = voice_of(bp)
    tone = (v.get("tone") or "").strip()
    if tone in TONE_MODES:
        return tone
    return "plain" if is_financial(bp) else "warm"


def emotion_budget(bp):
    """How many 煽情词 a single caption may carry. Declared value wins over the preset."""
    v = voice_of(bp)
    if v.get("emotion_budget") is not None and str(v.get("emotion_budget")).strip() != "":
        try:
            return max(0, int(v["emotion_budget"]))
        except (TypeError, ValueError):
            pass
    return TONE_MODES[tone_of(bp)]["budget"]


def caption_mode(bp):
    """`narrative` (what is happening) or `rule` (what the policy does at this step).

    Defaults to narrative, except that a financial product that says nothing gets a
    warning rather than a silent preference: an insurance 4-panel that tells a story is
    exactly the build that came back as "太煽情".
    """
    v = voice_of(bp)
    mode = (v.get("caption_mode") or "").strip()
    if mode in CAPTION_MODES:
        return mode
    return "narrative"


def is_financial(bp):
    return (bp.get("meta", {}).get("category") or "physical") in FINANCE_CATEGORIES


def apply_safe(build, safe):
    """Two-pass padding: measure the page, then keep the platform's UI out of it."""
    if not safe:
        return build(None)
    probe = build(None)
    ins = {
        "left": safe.get("left", 0) * probe.width,
        "right": safe.get("right", 0) * probe.width,
        "top": safe.get("top", 0) * probe.height,
        "bottom": safe.get("bottom", 0) * probe.height,
    }
    pads = {k: max(probe.pad, int(v * 1.05)) for k, v in ins.items()}
    return build(pads)


def safe_rect(grid, safe):
    """The inset rectangle the platform's UI does not cover, in page pixels."""
    if not safe:
        return (0, 0, grid.width, grid.height)
    l = int(safe.get("left", 0) * grid.width)
    r = int(safe.get("right", 0) * grid.width)
    t = int(safe.get("top", 0) * grid.height)
    b = int(safe.get("bottom", 0) * grid.height)
    return (l, t, max(1, grid.width - l - r), max(1, grid.height - t - b))


def disclosure_lines(bp):
    d = bp.get("meta", {}).get("disclosure") or {}
    return [l.strip() for l in (d.get("lines") or []) if l and l.strip()]


def footer_body(bp):
    """The text that will actually be printed in the bottom band."""
    lines = disclosure_lines(bp)
    if lines:
        return lines
    note = bp.get("meta", {}).get("footer", {}).get("note", "")
    return [note] if note else []


def disclosure_height_px(bp, width_px, cell):
    """Height the disclosure actually needs at this width, after wrapping.

    Counting lines is not enough: the same three sentences take four lines on a wide
    master and seven on a 9:16 slice, and a footer sized by the count silently eats the
    third one. This measures, then the caller sizes the band to fit.
    """
    lines = footer_body(bp)
    if not lines:
        return 0
    f = pc.load_font(max(10, int(cell * 0.023)), "regular")
    lh = pc.text_h("字测", f) * 1.38
    n = sum(len(pc.wrap_text(para, f, max(40, width_px))) for para in lines)
    d = bp["meta"].get("disclosure") or {}
    extra = lh if d.get("data_asof") or d.get("institution") else 0
    return int(n * lh + extra + cell * 0.026)


def disclosure_ratio(bp):
    """Footer height needed to print the disclosure at its minimum legible size."""
    lines = footer_body(bp)
    if not lines:
        return 0.0
    base = bp["meta"]["layout"].get("footer_ratio", 0.135)
    # One extra line for the data cut-off, which sits on its own baseline and is the line
    # most likely to be drawn on top of the body text by a footer that was sized for the
    # body alone.
    need = ((len(lines) + (1 if (bp["meta"].get("disclosure") or {}).get("data_asof") else 0))
            * 0.034) + 0.030
    return max(base, need)


CAPTION_FONT_RATIO = 0.050
CAPTION_PAD_X_RATIO = 0.022
CAPTION_PAD_Y_RATIO = 0.016
CAPTION_MAX_LINES = 2
CAPTION_MIN_FONT_FRACTION = 0.62  # below this the caption was too long, not the plate too small


def normalize(bp):
    """Fill every optional field so downstream code never branches on .get()."""
    meta = bp.setdefault("meta", {})
    for k, v in DEFAULT_META.items():
        if isinstance(v, dict):
            merged = dict(v)
            merged.update(meta.get(k, {}) or {})
            meta[k] = merged
        else:
            meta.setdefault(k, v)
    bp.setdefault("zones", [])
    bp.setdefault("characters", [])
    bp.setdefault("assets", [])
    bp.setdefault("columns", [])
    bp.setdefault("rows", [])
    bp.setdefault("targets", [])
    bp.setdefault("band", {"phases": []})
    bp.setdefault("coverage", {})
    meta.setdefault("key_facts", [])
    for z in bp["zones"]:
        z.setdefault("cast", {"named": [], "extras_max": 0})
        z.setdefault("slots", [])
        z.setdefault("face_allowed", z.get("kind") == "home")
        z.setdefault("caption_source", "")
        z.setdefault("kind", "scene")
        z.setdefault("duty", "")
        z.setdefault("caption", "")
        z.setdefault("facts", [])
        z.setdefault("tile_origin", None)
    for a in bp["assets"]:
        a.setdefault("kind", "product")
        a.setdefault("note", "")
    return bp


def load(path):
    return normalize(pc.load_json(path))


def resolve_asset_paths(bp, base_dir):
    """Asset paths are written relative to the blueprint; make them absolute once."""
    for a in bp.get("assets", []):
        f = a.get("file", "")
        if f and not os.path.isabs(f):
            a["file"] = os.path.join(base_dir, f)
    return bp


class ZoneView:
    __slots__ = ("zone", "row", "col", "local_row", "local_col", "rect", "image_rect",
                 "caption_rect", "slots")

    def __init__(self, zone, row, col, local_row, local_col, rect, image_rect, caption_rect, slots):
        self.zone = zone
        self.row = row
        self.col = col
        self.local_row = local_row
        self.local_col = local_col
        self.rect = rect
        self.image_rect = image_rect
        self.caption_rect = caption_rect
        self.slots = slots

    @property
    def id(self):
        return self.zone["id"]

    @property
    def cell(self):
        return self.rect[2]


def make_grid(bp, rows=None, cols=None, cell=None, safe=None):
    """Build a Grid for the full atlas or a row/column subset.

    Returns (grid, row_map, col_map) where row_map[i_local] = blueprint row number (1-based).
    `safe` is the platform's occluded band; padding grows so nothing important sits under it.
    """
    gmeta = bp["meta"]["grid"]
    lay = bp["meta"]["layout"]
    row_map = rows if rows else list(range(1, int(gmeta["rows"]) + 1))
    col_map = cols if cols else list(range(1, int(gmeta["cols"]) + 1))
    ftr = max(lay.get("footer_ratio", 0.0), disclosure_ratio(bp))

    def build(pads, ftr_=None):  # noqa: D401
        return pc.Grid(
            cols=len(col_map), rows=len(row_map), cell=cell or gmeta.get("cell", 2048),
            gutter_ratio=gmeta.get("gutter_ratio", 0.016),
            pad_ratio=gmeta.get("pad_ratio", 0.035),
            row_label_ratio=lay.get("row_label_ratio", 0.0),
            header_ratio=lay.get("header_ratio", 0.0),
            footer_ratio=ftr_ if ftr_ is not None else ftr,
            band=lay.get("band", False) and rows is None,
            col_header_ratio=lay.get("col_header_ratio", 0.0),
            caption_ratio=lay.get("caption_ratio", 0.145),
            pads=pads,
        )

    g = apply_safe(build, safe)
    for _ in range(2):
        need = disclosure_height_px(bp, g.width - g.pad_l - g.pad_r, g.cell)
        if need <= g.footer_h:
            break
        ftr = max(ftr, need / float(g.cell))
        # `build` takes the footer as a keyword-only-ish second argument, so the padding
        # pass has to be wrapped. Calling apply_safe(build, safe, ftr) directly raised
        # TypeError the moment a small cell or a long disclosure actually needed the retry
        # — which is exactly the case the retry exists for.
        g = apply_safe(lambda pads, f=ftr: build(pads, f), safe)
    return g, row_map, col_map


def matrix_mapping(row_map, col_map):
    """(blueprint row, blueprint col) -> (local row, local col) for a matrix slice."""
    return {(r, c): (row_map.index(r), col_map.index(c)) for r in row_map for c in col_map}


def zone_views(bp, grid, mapping):
    assets = {a["id"]: a for a in bp.get("assets", [])}
    out = []
    for z in bp["zones"]:
        key = (int(z.get("row", 0)), int(z.get("col", 0)))
        if key not in mapping:
            continue
        lr, lc = mapping[key]
        slots = []
        for s in z.get("slots", []):
            a = assets.get(s.get("asset"))
            if not a:
                continue
            box = grid.to_px(s.get("box", [0, 0, 0, 0]), grid.zone_image_rect(lr, lc))
            slots.append({"spec": s, "asset": a, "abs": box})
        out.append(ZoneView(z, key[0], key[1], lr, lc, grid.zone_rect(lr, lc),
                            grid.zone_image_rect(lr, lc), grid.caption_rect(lr, lc), slots))
    return out


def caption_capacity(cell, caption_rect=None):
    """How much copy the caption plate can hold, in characters and in lines."""
    w = caption_rect[2] if caption_rect else cell
    h = caption_rect[3] if caption_rect else int(cell * 0.145)
    font_size = max(10, int(cell * CAPTION_FONT_RATIO))
    pad_x = int(cell * CAPTION_PAD_X_RATIO)
    pad_y = int(cell * CAPTION_PAD_Y_RATIO)
    usable_w = max(10, w - 2 * pad_x)
    usable_h = max(10, h - 2 * pad_y)
    char_w = font_size * 1.02  # CJK glyph advance is ~1em; latin is narrower
    per_line = max(1, int(usable_w / char_w))
    lines_by_height = max(1, int(usable_h / (font_size * 1.28)))
    lines = min(CAPTION_MAX_LINES, lines_by_height)
    return {"font_size": font_size, "pad_x": pad_x, "pad_y": pad_y,
            "chars_per_line": per_line, "max_lines": lines,
            "max_chars": per_line * lines}


def _check_long(bp, target, problems, warnings):
    """A long image is legal only while it stays readable and keeps persona blocks whole."""
    tid = target.get("id")
    plat = platform_spec(target.get("platform"))
    ratio = pc.parse_ratio(target.get("ratio")) or pc.parse_ratio(plat.get("ratio"))
    if not ratio:
        problems.append("target %s: 长图必须给 ratio（如 1:4）或绑定到长图平台" % tid)
        return
    w, h = ratio
    if h / float(w) > LONG_MAX_ASPECT + 0.01:
        problems.append("target %s: %s 超过长图上限 1:%.0f，平台会压缩成一条灰带"
                        % (tid, target.get("ratio") or plat.get("ratio"), LONG_MAX_ASPECT))
    ncols = int(bp["meta"]["grid"].get("cols", 0) or 0)
    if ncols > 2:
        # The reflow only considers column counts that divide the scene count, so each
        # persona lands as a complete block. With a prime scene count there is no such
        # count between 2 and ncols, so the image degenerates into one narrow column.
        inner = [c for c in range(2, ncols) if ncols % c == 0]
        if not inner:
            warnings.append("target %s: %d 个场景没有 2～%d 之间的整数分栏（质数），长图会退化成"
                            "单列长条——删一格或加一格场景，别硬排" % (tid, ncols, ncols))
    if plat and not plat.get("long"):
        warnings.append("target %s: 平台 %s 不是长图通道，比例可能是自己拍的，"
                        "真机上先验一次再定稿" % (tid, plat.get("label")))
    if len(voice_missing(bp)):
        warnings.append("target %s: 还没有登记基调，长图的顺序会替你把语气定下来——"
                        "先做 Step 0.5" % tid)


def voice_missing(bp):
    """The fields Step 0.5 must produce. Empty means nobody asked the five questions."""
    v = voice_of(bp)
    need = []
    if (v.get("tone") or "").strip() not in TONE_MODES:
        need.append("tone")
    if not (v.get("pov") or "").strip():
        need.append("pov")
    if not (v.get("sample") or "").strip():
        need.append("sample")
    return need


def check_geometry(bp):
    """Everything that can be judged without artwork. Returns (problems, warnings)."""
    problems, warnings = [], []
    gmeta = bp["meta"]["grid"]
    nrows, ncols = int(gmeta["rows"]), int(gmeta["cols"])
    grid, row_map, col_map = make_grid(bp)

    zones = bp["zones"]
    seen = set()
    asset_ids = {a["id"]: a for a in bp.get("assets", [])}
    chars = {c["id"]: c for c in bp.get("characters", [])}

    if len(zones) != nrows * ncols:
        missing = nrows * ncols - len(zones)
        (problems if missing > 0 else warnings).append(
            "网格 %d×%d=%d 格，blueprint 里 %d 个 zone%s" % (
                nrows, ncols, nrows * ncols, len(zones),
                "，缺 %d 格" % missing if missing > 0 else "（有重复格子）"))

    slot_usage = {}
    for z in zones:
        zid = z["id"]
        if zid in seen:
            problems.append("zone id 重复: %s" % zid)
        seen.add(zid)
        r, c = int(z.get("row", 0)), int(z.get("col", 0))
        if not (1 <= r <= nrows and 1 <= c <= ncols):
            problems.append("%s: row/col 越界 (r%d c%d)" % (zid, r, c))
            continue

        # A face in the frame without a declared character is exactly what the audit
        # step exists to catch; declaring the contradiction here is cheaper.
        if z.get("face_allowed") and not z["cast"]["named"]:
            problems.append("%s: face_allowed=true 但没有 cast.named——没有人的格子会被人脸填满" % zid)
        if not z.get("face_allowed") and z["cast"]["named"]:
            problems.append("%s: face_allowed=false 却声明了 cast——本行其余格只允许背影/侧影/手" % zid)
        for cid in z["cast"]["named"]:
            if cid not in chars:
                problems.append("%s: cast 里的 %s 不在 characters 里" % (zid, cid))
            elif chars[cid].get("home_zone") != zid and z.get("face_allowed"):
                warnings.append("%s: 有脸但不是 %s 的 home_zone（%s）——一人只有一身" % (
                    zid, cid, chars[cid].get("home_zone")))
        if int(z["cast"].get("extras_max", 0)) < 0:
            problems.append("%s: extras_max 不能为负" % zid)

        if z.get("kind") == "home" and c != 1:
            problems.append("%s: home 格必须在第 1 列（定妆照是整行的锚）" % zid)

        # Slots
        boxes = []
        for s in z.get("slots", []):
            aid = s.get("asset", "")
            if aid not in asset_ids:
                problems.append("%s: slot 指向不存在的资产 %s" % (zid, aid))
                continue
            box = s.get("box") or []
            if len(box) != 4:
                problems.append("%s: slot %s 的 box 必须是 [x,y,w,h]" % (zid, aid))
                continue
            x, y, w, h = box
            if min(x, y, w, h) < 0 or x + w > 1.001 or y + h > 1.001:
                problems.append("%s: slot %s 的 box 越出画面 (%.2f,%.2f,%.2f,%.2f)" % (
                    zid, aid, x, y, w, h))
            if w < 0.08 or h < 0.08:
                warnings.append("%s: slot %s 只占 %.0f%%×%.0f%%，贴上去会糊成一块" % (
                    zid, aid, w * 100, h * 100))
            shadow = s.get("shadow", "hard_ellipse")
            if shadow not in pc.SHADOW_MODES:
                problems.append("%s: shadow=%r 非法，只能是 %s（真实柔边投影会让产品一眼假）" % (
                    zid, shadow, "/".join(pc.SHADOW_MODES)))
            if not s.get("surface"):
                warnings.append("%s: slot %s 未声明 surface（承载面）——产品会浮在场景里" % (zid, aid))
            boxes.append((aid, x, y, x + w, y + h))
            slot_usage[aid] = slot_usage.get(aid, 0) + 1
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a1, x1, y1, X1, Y1 = boxes[i]
                a2, x2, y2, X2, Y2 = boxes[j]
                if x1 < X2 - 0.01 and x2 < X1 - 0.01 and y1 < Y2 - 0.01 and y2 < Y1 - 0.01:
                    problems.append("%s: %s 与 %s 的贴图位重叠" % (zid, a1, a2))

        # Caption fit
        cap = caption_capacity(grid.cell, grid.caption_rect(0, 0))
        text = (z.get("caption") or "").strip()
        if not text:
            problems.append("%s: 没有 caption——留空要说清楚为什么，不能什么都不写" % zid)
        elif text.startswith("TODO"):
            problems.append("%s: caption 仍是 TODO" % zid)
        else:
            n = len(text)
            if n > cap["max_chars"]:
                problems.append("%s: caption %d 字，板子只装得下 %d 字（%d 字/行 × %d 行）" % (
                    zid, n, cap["max_chars"], cap["chars_per_line"], cap["max_lines"]))
            if not (z.get("caption_source") or "").strip():
                problems.append("%s: caption 没有 caption_source——图上每一句都要能指回素材" % zid)
        if not (z.get("duty") or "").strip() or (z.get("duty") or "").startswith("TODO"):
            problems.append("%s: duty 未写。这一格到底要说清什么？" % zid)

    # Assets that never reach the canvas
    for aid, a in asset_ids.items():
        if a.get("kind") == "product" and not slot_usage.get(aid):
            warnings.append("产品 %s 没有任何 slot，不会出现在图上——要么加贴图位，要么在 gate 1 说明" % aid)

    # Characters must have a home
    for cid, ch in chars.items():
        hz = ch.get("home_zone")
        if hz not in seen:
            problems.append("character %s 的 home_zone %r 不存在" % (cid, hz))

    # Coverage arithmetic (printed on the image, so it must add up)
    cov = bp.get("coverage") or {}
    if cov:
        filled = sum(1 for z in zones if (z.get("caption") or "") and not z["caption"].startswith("TODO"))
        cov["cells_total"] = len(zones)
        cov["cells_filled"] = filled
        cov["cells_empty"] = len(zones) - filled

    # Targets
    for t in bp.get("targets", []):
        ttype = t.get("type", "full")
        if ttype in ("row", "col") and not (t.get("rows") or t.get("cols")):
            problems.append("target %s: %s 类型必须给 rows/cols" % (t.get("id"), ttype))
        for r in t.get("rows", []) or []:
            if r not in row_map:
                problems.append("target %s: 行 %s 不存在" % (t.get("id"), r))
        for c in t.get("cols", []) or []:
            if c not in col_map:
                problems.append("target %s: 列 %s 不存在" % (t.get("id"), c))

    if not bp.get("band", {}).get("phases"):
        warnings.append("没有时间轴带 phases——「上市」这件事就只能靠文案说，不能靠结构说")

    # --- financial products: disclosure is not optional and not stylistic -----------
    cat = bp["meta"].get("category") or "physical"
    if is_financial(bp):
        d = bp["meta"].get("disclosure") or {}
        lines = disclosure_lines(bp)
        if len(lines) < 2:
            problems.append("金融/保险类必须至少两条风险披露（如「收益不保证」+「过往业绩不代表未来表现」），当前 %d 条"
                            % len(lines))
        if not d.get("institution"):
            problems.append("缺 disclosure.institution（发行/销售机构全称）")
        if not d.get("data_asof"):
            problems.append("缺 disclosure.data_asof（收益率、费率等数据截至日）")
        if cat == "finance" and not d.get("risk_level"):
            problems.append("理财类必须有 disclosure.risk_level（R1–R5）")
        if cat == "insurance" and not d.get("license"):
            problems.append("保险类必须有 disclosure.license（机构/中介资质编号）")
        if len(lines) > 4:
            warnings.append("风险披露 %d 条，会把落版带压到画面高度的 20%% 以上——主图正文明年会被挤" % len(lines))

    # --- targets: platform, pages, occlusion --------------------------------------
    for t in bp.get("targets", []):
        tid = t.get("id")
        plat = platform_spec(t.get("platform"))
        if t.get("platform") and not plat:
            problems.append("target %s: 未知平台 %r，可用：%s" % (
                tid, t.get("platform"), " / ".join(sorted(PLATFORMS))))
        if t.get("type") == "carousel":
            pages = t.get("pages") or default_pages(bp)
            mp = plat.get("max_pages")
            if mp and len(pages) > mp:
                problems.append("target %s: %d 页超出平台上限 %d 页" % (tid, len(pages), mp))
            if pages and pages[0].get("kind") != "cover":
                warnings.append("target %s: 第一页不是 cover，信息流里会缺少封面" % tid)
            for i, pg in enumerate(pages):
                if pg.get("kind") == "row" and not pg.get("rows"):
                    problems.append("target %s 第 %d 页: row 页缺 rows" % (tid, i + 1))
        if t.get("type") == "long":
            _check_long(bp, t, problems, warnings)
        safe = t.get("safe") or plat.get("safe")
        if safe and plat:
            keep_w = 1 - safe.get("left", 0) - safe.get("right", 0)
            keep_h = 1 - safe.get("top", 0) - safe.get("bottom", 0)
            if keep_w < 0.62 or keep_h < 0.60:
                warnings.append("target %s（%s）：安全区只剩 %.0f%%×%.0f%%，画面可用面积吃紧，"
                                "把标题压到一半高度以内" % (tid, plat.get("label"), keep_w * 100,
                                                       keep_h * 100))

    return problems, warnings


def flow_shape(n, target_aspect, header_ratio=0.105, footer_ratio=0.055, block=None):
    """Pick the cols×rows shape whose natural aspect is closest to the channel's.

    This is the whole point of "reflow, not crop". A 4-cell row is a wide strip; forced
    into 9:16 it either gets cropped (heads and plates lost) or letterboxed (79% paper).
    Wrapped into 2×2 it is a vertical poster that happens to contain the same four cells.

    `block` is how many cells form one indivisible group (one persona's scenes). A long
    image stacks those groups vertically, so the column count is only allowed to divide
    `block` — otherwise persona 1's last scene sits next to persona 2's first, and the
    reader cannot tell which four cells belong together.
    """
    best = None
    for c in range(1, n + 1):
        if block and block % c:
            continue
        r = -(-n // c)
        probe = pc.Grid(cols=c, rows=r, cell=1000, gutter_ratio=0.016, pad_ratio=0.03,
                        header_ratio=header_ratio, footer_ratio=footer_ratio)
        aspect = probe.width / probe.height
        empty = c * r - n
        score = abs(math.log(aspect / target_aspect)) + 0.05 * empty
        if best is None or score < best[0]:
            best = (score, c, r)
    if best is None:
        return 1, n
    return best[1], best[2]


def target_cells(bp, target):
    """The (row, col) cells a target contains, in reading order."""
    gmeta = bp["meta"]["grid"]
    nrows, ncols = int(gmeta["rows"]), int(gmeta["cols"])
    ttype = target.get("type", "full")
    if ttype == "cell":
        return [(target["rows"][0], target["cols"][0])]
    if ttype == "row":
        return [(r, c) for r in target.get("rows") or [] for c in range(1, ncols + 1)]
    if ttype == "col":
        return [(r, c) for c in target.get("cols") or [] for r in range(1, nrows + 1)]
    return [(r, c) for r in range(1, nrows + 1) for c in range(1, ncols + 1)]


def default_pages(bp):
    pages = [{"kind": "cover"}]
    for i in range(1, int(bp["meta"]["grid"]["rows"]) + 1):
        pages.append({"kind": "row", "rows": [i]})
    pages.append({"kind": "end"})
    return pages


def flow_plan(bp, target, cell=None, block_cols=None):
    """Grid + mapping + padding for one standalone page (no band, no row-label strip)."""
    cells = target_cells(bp, target)
    ratio = pc.parse_ratio(target.get("ratio"))
    plat = platform_spec(target.get("platform"))
    ratio = ratio or pc.parse_ratio(plat.get("ratio"))
    aspect = (ratio[0] / ratio[1]) if ratio else 1.3
    safe = target.get("safe") or plat.get("safe")
    cell_px = cell or bp["meta"]["grid"].get("cell", 2048)
    cols, rows = flow_shape(len(cells), aspect, 0.105, 0.055, block=block_cols)
    gmeta = bp["meta"]["grid"]
    cap_ratio = bp["meta"]["layout"].get("caption_ratio", 0.145)
    ftr = max(0.055, disclosure_ratio(bp))

    def build(hdr, ftr_, k=1.0):
        def b(pads):
            return pc.Grid(cols=cols, rows=rows, cell=cell_px, cell_h=int(cell_px * k),
                           gutter_ratio=gmeta.get("gutter_ratio", 0.016),
                           pad_ratio=gmeta.get("pad_ratio", 0.035),
                           header_ratio=hdr, footer_ratio=ftr_, band=False,
                           col_header_ratio=0.0, caption_ratio=cap_ratio, pads=pads)
        return b

    hdr, k = (0.16 if block_cols else 0.105), 1.0
    g1 = apply_safe(build(hdr, ftr, k), safe)
    if ratio and abs(g1.width / g1.height - aspect) > 0.02:
        # Solve the cell height that fills the channel instead of padding paper into it.
        # Bounded: a square tile can only be cover-cropped so far before the subject loses
        # its sides (see [CROP SAFETY] in references/cartoon-style.md). A long image is
        # allowed taller cells because it is read in a vertical scroll, not glanced at.
        k_hi = 2.2 if block_cols else 1.55
        need_h = g1.width / aspect
        k = (need_h - (g1.height - rows * cell_px)) / float(rows * cell_px)
        k = max(0.66, min(k_hi, k))
        g1 = apply_safe(build(hdr, ftr, k), safe)
    need = ((g1.width / aspect) - g1.height) / cell_px
    if need > 0.02:
        hdr = min(0.30, max(0.10, hdr + need * 0.7))
        ftr = min(0.16, max(ftr, ftr + need * 0.3))
    grid = apply_safe(build(hdr, ftr, k), safe)
    for _ in range(2):
        need_px = disclosure_height_px(bp, grid.width - grid.pad_l - grid.pad_r, grid.cell)
        if need_px <= grid.footer_h:
            break
        ftr = min(0.34, need_px / float(grid.cell))
        grid = apply_safe(build(hdr, ftr, k), safe)
    pad = 0.0
    if ratio:
        cur = grid.width / grid.height
        tgt = ratio[0] / ratio[1]
        if tgt > cur:
            pad = (tgt * grid.height - grid.width) / (tgt * grid.height)
        else:
            pad = (grid.width / tgt - grid.height) / (grid.width / tgt)
    return grid, {key: (i // cols, i % cols) for i, key in enumerate(cells)}, pad, len(cells)
