#!/usr/bin/env python3
"""Step 0 — structured intake.

A commercial campaign almost never arrives as a clean brief. It arrives as a chat
thread, three slides and a sentence from the boss. This script is the gate that turns
that into `brief.json`, refuses to start when the matrix cannot be built, and emits a
draft blueprint whose gaps are visible instead of plausible.

Usage
  python3 brief.py --init  -o build/            # write an empty intake form
  python3 brief.py --demo  -o build/            # a filled demo build, physical goods
  python3 brief.py --demo-finance -o build/     # a filled demo build, financial product
  python3 brief.py build/brief.json             # validate, report, emit blueprint.draft.json

The draft blueprint is always emitted alongside the report: it is a scaffold with visible
holes, not an option a user has to remember to ask for. The old `--draft` flag was accepted
and ignored, which is worse than not existing.

Exit codes
  0  brief is complete enough to design from
  1  blocking gaps (products / personas / scenes / launch rhythm / sign-off)
  2  bad input file
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promo_common as pc  # noqa: E402
import promo_layout as pl  # noqa: E402

REQUIRED_BLOCKING = ("products", "personas", "scenes", "timeline", "signoff")


def empty_brief():
    return {
        "_note": "12 项采集。前 3 项（products / personas / scenes）缺任何一项，开工即返工；"
                 "voice 不填，文案复审阻断；key_facts 不填，信息密度门禁阻断。",
        "category": "physical",
        "_category_help": "physical 实物 / finance 理财 / insurance 保险 / service 服务。"
                          "金融与保险会启用强制风险披露与承诺收益类硬拦截。",
        "voice": {
            "tone": "",
            "pov": "",
            "caption_mode": "",
            "emotion_budget": None,
            "punch_quota": 1,
            "banned_words": [],
            "sample": "",
            "body": "",
            "_help": "Step 0.5 的结论，一条都不能替客户猜。tone 取 plain / warm / urgent / "
                     "expert / witty；pov 是叙述人称（第三人称白描 / 第二人称 / 第一人称自述）；"
                     "caption_mode 取 narrative（这一格发生了什么）/ rule（这一步按哪条算，"
                     "保险与理财用这个）；emotion_budget 是每条 caption 允许出现的煽情词数；"
                     "sample 是一句语感样例；body 是平台正文，同一套预算也管它",
        },
        "campaign": {
            "name": "",
            "product_lines": [],
            "launch_date": "",
            "platforms": [],
            "channels": [],
            "_help": "platforms 填平台 key：xiaohongshu / xiaohongshu_long / long_image / douyin / "
                     "wechat_moments / weibo / official_account / taobao / print_backdrop；"
                     "channels 是给人看的说明",
        },
        "disclosure": {
            "lines": [],
            "institution": "",
            "license": "",
            "risk_level": "",
            "data_asof": "",
            "_help": "金融/保险必填。lines 至少两条；理财要 risk_level（R1–R5）；"
                     "保险要 license；所有收益与费率都要 data_asof",
        },
        "products": [
            {"id": "p_01", "name": "", "model": "", "asset": "assets/p_01.png",
             "confirmed_by": "", "_help": "asset 必须是去底 PNG（带 alpha），由客户提供"}
        ],
        "personas": [
            {"id": "a_01", "name": "", "age": None, "job": "", "moment": "", "pain": "",
             "source": "", "_help": "moment = 她/他会在哪个具体时刻需要这个产品；source = 这画像从哪来（brief:§2 / client-confirmed:日期）"}
        ],
        "scenes": [
            {"id": "s_01", "title": "", "desc": "", "source": ""}
        ],
        "key_facts": [
            {"id": "f_01", "text": "", "kind": "number", "source": "",
             "_help": "第 12 项：本次投放读者必须带走的可核验事实（数字/期限/比例/条件/边界/原文）。"
                      "kind 取 number / condition / boundary / evidence / object / action；"
                      "金融与保险的 source 必须 client-confirmed:*。每个 zone 至少引用一条新事实，"
                      "没有它 lint_density.py 不放行"}
        ],
        "assets": [
            {"id": "logo", "kind": "logo", "file": "assets/logo.png", "note": ""},
            {"id": "mascot", "kind": "mascot", "file": "assets/mascot.png",
             "note": "官方三视图；无则留空并在 redlines 说明"}
        ],
        "timeline": {
            "phases": [
                {"label": "", "date": "", "note": ""}
            ],
            "_help": "至少 2 段，如 预热 10/15-10/31 / 发布 11/01 / 上市后 11/02-11/30"
        },
        "redlines": {
            "forbidden_claims": [],
            "competitor_rule": "",
            "asset_rules": "",
            "_help": "禁用表述、竞品红线、不得出现的元素（真实用户证言 / 竞品对比 / 未授权肖像）"
        },
        "signoff": {"name": "", "role": "", "date": "",
                    "_help": "签字人对图上全部数字、规格、价格、日期负责"},
        "style": {"preset": "cartoon_flat", "palette": "warm_paper", "note": ""},
    }


DEMO_BRIEF = {
    "voice": {
        "tone": "warm", "pov": "第三人称白描", "caption_mode": "narrative",
        "emotion_budget": 1, "punch_quota": 1,
        "banned_words": ["生活仪式感", "治愈"],
        "sample": "包挂在门后，手已经伸向台面",
        "body": "回家第一件事是找水喝。壶里剩半杯，凉的。净饮机放在台面上，接满一杯大概 "
                "八秒，水温能定在 45 度——冲奶粉那一档，不用再试温。",
    },
    "campaign": {
        "name": "轻氧 Pro 2 · 上市战役总览",
        "product_lines": ["轻氧 Pro 2 净饮机", "轻氧滤芯 Pro"],
        "launch_date": "2026-11-01",
        "platforms": ["xiaohongshu", "xiaohongshu_long", "douyin", "taobao"],
        "channels": ["小红书轮播", "小红书长图", "抖音竖屏", "电商主图"],
    },
    "products": [
        {"id": "p_01", "name": "轻氧 Pro 2 净饮机", "model": "QY-P2", "asset": "assets/p_01.png",
         "confirmed_by": "客户市场部 2026-10-20"},
        {"id": "p_02", "name": "轻氧滤芯 Pro", "model": "QY-F7", "asset": "assets/p_02.png",
         "confirmed_by": "客户市场部 2026-10-20"},
    ],
    "personas": [
        {"id": "a_01", "name": "林小满", "age": 29, "job": "新媒体编辑",
         "moment": "加班到家，包还没放下就先灌一杯水", "pain": "嫌烧水等太久，冷不下来",
         "source": "brief:§2"},
        {"id": "a_02", "name": "陈默", "age": 34, "job": "产品经理",
         "moment": "晚上十点健身房出来，要一次补足 1.5 升", "pain": "嫌杯子太小，来回接水",
         "source": "brief:§2"},
        {"id": "a_03", "name": "周雅", "age": 41, "job": "两个孩子的妈妈",
         "moment": "凌晨三点冲奶粉，水温要刚好 45 度", "pain": "试温试不准，孩子等得哭",
         "source": "brief:§2"},
    ],
    "scenes": [
        {"id": "s_01", "title": "夜归", "desc": "玄关到厨房，灯只开了廊灯", "source": "brief:§3"},
        {"id": "s_02", "title": "晨起", "desc": "窗边晨光，厨房台面刚醒", "source": "brief:§3"},
        {"id": "s_03", "title": "训练后", "desc": "健身房更衣区，毛巾搭在包上", "source": "brief:§3"},
        {"id": "s_04", "title": "冲奶台", "desc": "卧室角落的小桌，奶瓶和暖灯", "source": "brief:§3"},
    ],
    "assets": [
        {"id": "logo", "kind": "logo", "file": "assets/logo.png", "note": "深色版"},
        {"id": "p_01", "kind": "product", "file": "assets/p_01.png", "note": "正面平视"},
        {"id": "p_02", "kind": "product", "file": "assets/p_02.png", "note": "滤芯，可斜放 15 度内"},
    ],
    "timeline": {
        "phases": [
            {"label": "预热", "date": "10.15 – 10.31", "note": "人群痛点铺底，不露产品"},
            {"label": "发布", "date": "11.01", "note": "发布会当天，主图上线"},
            {"label": "上市后", "date": "11.02 – 11.30", "note": "场景扩散，渠道切片投放"},
        ]
    },
    "redlines": {
        "forbidden_claims": ["母婴适用", "医用级", "可直饮"],
        "competitor_rule": "不出现任何可识别的竞品外观与商标",
        "asset_rules": "不出现真实用户肖像；不出现捏造的用户评价",
    },
    "signoff": {"name": "客户市场部 / 法务", "role": "信息与表述确认", "date": "2026-10-22"},
    "style": {"preset": "cartoon_flat", "palette": "warm_paper",
              "note": "平涂卡通，线条粗 4px，阴影只做硬边"},
}

# Filled demo copy. Real builds get this from a human writer + references/copy-voice.md;
# the demo exists so the pipeline can be executed end to end without a client.
# Demo copy. These went through references/copy-voice.md: a judgement deleted, an action
# put back, one object per line, and nothing longer than the line it replaced. The first
# draft of these twelve had 9 of 12 without a single object and read like a slogan sheet —
# `lint_copy.py` scores that as 具体物件覆盖率 and refuses anything under 50%.
DEMO_CELLS = {
    ("a_01", "s_01"): ("包挂在门后，手已经伸向台面", "玄关灯还亮着，她把包挂在门后，手已经伸向台面。"),
    ("a_01", "s_02"): ("窗开着一条缝，玻璃杯放在台面上", "窗开着一条缝，台面上只有杯子和机器。"),
    ("a_01", "s_03"): ("毛巾搭在包上，壶里见了底", "毛巾搭在包上，水壶见了底。"),
    ("a_01", "s_04"): ("奶瓶排成一排，水温还得试", "卧室角落的小桌，奶瓶排成一排。"),
    ("a_02", "s_01"): ("电脑还开着，键盘边放着水瓶", "电脑还开着，水瓶放在键盘边。"),
    ("a_02", "s_02"): ("运动包立在门口，壶嘴露在侧袋", "运动包立在门口，水壶插在侧袋。"),
    ("a_02", "s_03"): ("长凳上摊着护腕和一只空瓶", "更衣区的长凳上摊着护腕和空瓶。"),
    ("a_02", "s_04"): ("台面只留一盏暖灯，水要 45 度", "台面只留一盏暖灯，水温要准。"),
    ("a_03", "s_01"): ("孩子睡了，客厅只剩待机灯", "客厅只剩电视的待机灯。"),
    ("a_03", "s_02"): ("餐桌上四只玻璃碗，高矮不同", "餐桌上四只容器排开。"),
    ("a_03", "s_03"): ("推车停在门口，壶挂在扶手上", "推车停在门口，水壶挂在扶手上。"),
    ("a_03", "s_04"): ("床头柜上放着奶瓶和小毛巾", "床头柜放着奶瓶和一条小毛巾。"),
}


DEMO_FINANCE_BRIEF = {
    "category": "finance",
    "voice": {
        "tone": "plain", "pov": "第三人称白描", "caption_mode": "narrative",
        "emotion_budget": 0, "punch_quota": 1,
        "banned_words": ["稳稳的幸福", "财富自由", "安心"],
        "sample": "手机在桌上震，人还没起身",
        "body": "90 天持有期，1,000 元起，R3 中风险。业绩比较基准 3.2%（年化）不构成收益"
                "承诺，过往业绩不代表未来表现，本金可能损失。",
    },
    "campaign": {
        "name": "稳盈债券 90 天 · 新发募集",
        "product_lines": ["稳盈债券 90 天持有期"],
        "launch_date": "2026-11-05",
        "platforms": ["xiaohongshu", "long_image", "douyin", "wechat_moments"],
        "channels": ["小红书轮播", "通用长图", "抖音竖屏", "朋友圈方图"],
    },
    "products": [
        {"id": "p_fund", "name": "稳盈债券 90 天持有期", "model": "WY-90",
         "asset": "assets/ui_buy.png", "confirmed_by": "客户合规部 2026-10-24"},
    ],
    "personas": [
        {"id": "a_01", "name": "许南", "age": 27, "job": "互联网运营",
         "moment": "发薪日当天，把工资里那笔闲钱挪出去", "pain": "活期利息低，又不敢碰股票",
         "source": "brief:§2"},
        {"id": "a_02", "name": "陈立", "age": 38, "job": "区域销售经理",
         "moment": "年终奖到账，先想稳一稳房贷月供", "pain": "钱一到账就被花掉",
         "source": "brief:§2"},
        {"id": "a_03", "name": "周慧", "age": 56, "job": "中学教师",
         "moment": "退休前三年，把存款分成几笔滚动", "pain": "怕期限太长，用钱取不出",
         "source": "brief:§2"},
    ],
    "scenes": [
        {"id": "s_01", "title": "发薪日", "desc": "工位上的手机，工资到账推送", "source": "brief:§3"},
        {"id": "s_02", "title": "奖金到账", "desc": "车里，手机架在出风口", "source": "brief:§3"},
        {"id": "s_03", "title": "月供之前", "desc": "餐桌，房贷账单摊在一边", "source": "brief:§3"},
        {"id": "s_04", "title": "退休规划", "desc": "书房，存单和计算器", "source": "brief:§3"},
    ],
    "assets": [
        {"id": "logo", "kind": "logo", "file": "assets/logo.png", "note": "深色版"},
        {"id": "ui_buy", "kind": "ui", "file": "assets/ui_buy.png", "note": "App 申购页，不可重绘"},
        {"id": "chart_nav", "kind": "chart", "file": "assets/chart_nav.png", "note": "净值曲线，数据截至 2026-09-30"},
    ],
    "timeline": {"phases": [
        {"label": "募集期", "date": "11.05 – 11.12", "note": "额度售完即止"},
        {"label": "成立", "date": "11.13", "note": "验资完成，进入封闭"},
        {"label": "开放", "date": "02.11", "note": "90 天持有期后可赎回"},
    ]},
    "redlines": {
        "forbidden_claims": ["保本", "稳赚", "预期收益", "零风险", "高收益"],
        "competitor_rule": "不与他人产品做收益对比；不使用排名类表述",
        "asset_rules": "不得出现真实用户证言；不得暗示刚性兑付",
    },
    "signoff": {"name": "客户合规部", "role": "表述与披露确认", "date": "2026-10-24"},
    "disclosure": {
        "lines": [
            "本产品不保本，收益随市场波动，投资者可能损失本金。",
            "过往业绩不代表未来表现，业绩比较基准不构成收益承诺。",
            "请阅读产品合同与招募说明书，选择与自身风险承受能力匹配的产品。",
        ],
        "institution": "示例基金管理有限公司",
        "license": "中国证监会核准 · 编号 000000",
        "risk_level": "R3 中风险",
        "data_asof": "2026-09-30",
    },
    "style": {"preset": "cartoon_flat", "palette": "warm_paper",
              "note": "平涂卡通；金融不画钞票雨、不画金币堆、不画上扬箭头"},
}

DEMO_CELLS_FIN = {
    ("a_01", "s_01"): ("推送响的时候，杯子还剩半杯水", "手机亮着工资到账的推送，桌上还有半杯咖啡。"),
    ("a_01", "s_02"): ("红灯还有90秒，手机架在出风口", "车里等红灯，手机架在出风口。"),
    ("a_01", "s_03"): ("账单摊开，笔停在月供那一行", "餐桌上摊着账单，笔停在数字上。"),
    ("a_01", "s_04"): ("台灯下压着一张存单，折了角", "书房的台灯下，存单折了一角。"),
    ("a_02", "s_01"): ("手机在桌上震，人还没起身", "工位上手机震动，人还没起身。"),
    ("a_02", "s_02"): ("方向盘还温着，导航在跳秒", "车里暖气开着，导航还在跳。"),
    ("a_02", "s_03"): ("桌垫下面压着这个月的账单", "账单压在杯垫下，只露出日期。"),
    ("a_02", "s_04"): ("计算器按到一半，数字停住", "计算器屏幕上是一串被按掉一半的数字。"),
    ("a_03", "s_01"): ("窗台上那只保温杯用了八年", "办公室窗台上放着老式保温杯。"),
    ("a_03", "s_02"): ("抽屉里三张存单，到期日不一样", "书桌抽屉里三张存单并排。"),
    ("a_03", "s_03"): ("日历上圈了三个月后的那天", "日历上圈出了三个月后的日期。"),
    ("a_03", "s_04"): ("本子上列了三笔钱，用途不同", "黄昏的光落在摊开的笔记本上。"),
}


# 第 12 项采集的 demo 样本：每格两条新事实，id 由 draft_blueprint 按 (persona, scene)
# 生成，所以 12 格有 24 条不重复的信息单元。Demo 的作用是让整条管线可跑通，不是让文案
# 值得印——它照样要过 lint_density.py 的逐格与逐页门槛。
DEMO_FACTS = {
    ("a_01", "s_01"): [("玄关到厨房 3 步", "object", "brief:§2"),
                       ("45 度恒温档", "number", "client-confirmed:2026-10-20")],
    ("a_01", "s_02"): [("接满一杯约 8 秒", "number", "client-confirmed:2026-10-20"),
                       ("玻璃杯放在台面上", "object", "brief:§3")],
    ("a_01", "s_03"): [("滤芯 Pro 单支 6 个月", "number", "client-confirmed:2026-10-20"),
                       ("水壶见了底", "object", "brief:§3")],
    ("a_01", "s_04"): [("45 度冲奶档不用试温", "condition", "brief:§3"),
                       ("奶瓶排成一排", "object", "brief:§3")],
    ("a_02", "s_01"): [("台面预留 28 cm", "number", "client-confirmed:2026-10-20"),
                       ("键盘边放着水瓶", "object", "brief:§3")],
    ("a_02", "s_02"): [("侧袋可放水壶", "condition", "brief:§3"),
                       ("壶嘴露在侧袋", "object", "brief:§3")],
    ("a_02", "s_03"): [("更衣区无插座", "condition", "brief:§3"),
                       ("长凳上摊着护腕和空瓶", "object", "brief:§3")],
    ("a_02", "s_04"): [("水温 45 度可直饮", "number", "client-confirmed:2026-10-20"),
                       ("台面只留一盏暖灯", "object", "brief:§3")],
    ("a_03", "s_01"): [("待机不取水", "condition", "brief:§3"),
                       ("客厅只剩待机灯", "object", "brief:§3")],
    ("a_03", "s_02"): [("四只容器高矮不同", "condition", "brief:§3"),
                       ("餐桌上四只玻璃碗", "object", "brief:§3")],
    ("a_03", "s_03"): [("扶手可挂水壶", "condition", "brief:§3"),
                       ("推车停在门口", "object", "brief:§3")],
    ("a_03", "s_04"): [("45 度档留给夜间", "number", "client-confirmed:2026-10-20"),
                       ("床头柜放着奶瓶", "object", "brief:§3")],
}

_DEMO_FIN_TEXTS = [
    ("起投 1,000 元", "number"), ("90 天持有期", "number"),
    ("R3 中风险", "condition"), ("业绩比较基准 3.2% 年化", "number"),
    ("募集期 11.05–11.12", "number"), ("成立日 11.13", "number"),
    ("开放日 02.11", "number"), ("数据截至 2026-09-30", "boundary"),
    ("本金可能损失", "boundary"), ("收益随市场波动", "condition"),
    ("业绩比较基准不构成收益承诺", "boundary"), ("过往业绩不代表未来表现", "boundary"),
    ("请阅读产品合同", "evidence"), ("请阅读招募说明书", "evidence"),
    ("需匹配风险承受能力", "condition"), ("不保本", "boundary"),
    ("90 天后方可赎回", "condition"), ("非同一次申请不合并计算", "condition"),
    ("净值曲线截至 09-30", "boundary"), ("申购页为官方截图", "evidence"),
    ("不与他人产品做收益对比", "boundary"), ("不使用排名类表述", "boundary"),
    ("无预期收益表述", "boundary"), ("不使用真实用户证言", "boundary"),
]
DEMO_FACTS_FIN = {}
for _i, (_pk, _sk) in enumerate(
        [(p, s) for p in ("a_01", "a_02", "a_03")
         for s in ("s_01", "s_02", "s_03", "s_04")]):
    DEMO_FACTS_FIN[(_pk, _sk)] = [
        {"text": t, "kind": k, "source": "client-confirmed:2026-10-24"}
        for t, k in _DEMO_FIN_TEXTS[_i * 2:_i * 2 + 2]]


def demo_fact_list(finance=False):
    """The twelfth intake item, in cell order: two new facts per demo cell."""
    table = DEMO_FACTS_FIN if finance else DEMO_FACTS
    out = []
    for p in ("a_01", "a_02", "a_03"):
        for s in ("s_01", "s_02", "s_03", "s_04"):
            for j, item in enumerate(table[(p, s)], 1):
                fid = "f_%s_%s_%d" % (p, s, j)
                if isinstance(item, dict):
                    out.append({"id": fid, **item})
                else:
                    text, kind, source = item
                    out.append({"id": fid, "text": text, "kind": kind, "source": source})
    return out


def build_demo_assets(out_dir, finance=False):
    """Draw placeholder asset PNGs so the demo pipeline has real files to composite."""
    from PIL import Image, ImageDraw
    adir = os.path.join(out_dir, "assets")
    pc.ensure_dir(adir)
    if finance:
        # An app screen and a NAV chart: the two things a fund actually has instead of a
        # pack shot. Both are screenshots — facts — and neither may be regenerated.
        ui = Image.new("RGBA", (900, 1600), (255, 255, 255, 255))
        d = ImageDraw.Draw(ui)
        d.rounded_rectangle([0, 0, 899, 1599], radius=48, fill=(250, 249, 246),
                            outline=(43, 38, 34), width=10)
        d.rounded_rectangle([60, 120, 840, 300], radius=24, fill=(238, 232, 220))
        d.rounded_rectangle([60, 340, 840, 520], radius=24, fill=(232, 240, 236))
        d.rounded_rectangle([60, 560, 840, 760], radius=24, fill=(240, 234, 226))
        d.rounded_rectangle([60, 1120, 840, 1260], radius=60, fill=(211, 84, 60))
        f = pc.load_font(64, "bold")
        d.text((96, 170), "申购 1,000 元起", font=f, fill=(43, 38, 34))
        f2 = pc.load_font(44, "regular")
        d.text((96, 380), "业绩比较基准 3.2%（年化）", font=f2, fill=(43, 38, 34))
        d.text((96, 600), "持有期 90 天 · R3 中风险", font=f2, fill=(43, 38, 34))
        d.text((300, 1160), "立即申购", font=f, fill=(255, 255, 255))
        ui.save(os.path.join(adir, "ui_buy.png"))

        ch = Image.new("RGBA", (1200, 700), (255, 255, 255, 255))
        d = ImageDraw.Draw(ch)
        d.rounded_rectangle([0, 0, 1199, 699], radius=24, fill=(252, 251, 248),
                            outline=(43, 38, 34), width=8)
        pts = [(80, 560), (240, 520), (400, 535), (560, 470), (720, 440), (880, 460),
               (1040, 390), (1150, 370)]
        d.line(pts, fill=(52, 106, 138), width=12, joint="curve")
        f3 = pc.load_font(40, "bold")
        d.text((80, 50), "净值走势（示意）", font=f3, fill=(43, 38, 34))
        ch.save(os.path.join(adir, "chart_nav.png"))
        specs = [("logo.png", (43, 38, 34), None, "稳盈", 520, 200)]
    else:
        specs = [
            ("p_01.png", (86, 78, 68), (198, 188, 172), "净饮机", 620, 900),
            ("p_02.png", (52, 106, 138), (176, 208, 224), "滤芯", 300, 620),
            ("logo.png", (43, 38, 34), None, "轻氧", 520, 200),
        ]
    for fname, ink, fill, label, w, h in specs:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        r = int(min(w, h) * 0.08)
        if fill:
            d.rounded_rectangle([6, 6, w - 6, h - 6], radius=r, fill=fill, outline=ink, width=8)
        font = pc.load_font(int(h * 0.16), "bold")
        tw = pc.text_w(label, font)
        d.text(((w - tw) / 2, h * 0.42), label, font=font, fill=ink)
        img.save(os.path.join(adir, fname))
    return adir


def draft_blueprint(brief, demo=False):
    personas = brief["personas"]
    scenes = brief["scenes"]
    products = {p["id"]: p for p in brief.get("products", [])}
    cols, rows = len(scenes), len(personas)

    fin = (brief.get("category") or "physical") in pl.FINANCE_CATEGORIES
    disc = brief.get("disclosure") or {}
    # The twelfth intake item travels with the blueprint. A draft written by a human has
    # holes in it on purpose; the demo fills them so the whole pipeline can be exercised.
    key_facts = [dict(f) for f in (brief.get("key_facts") or [])
                 if isinstance(f, dict) and f.get("id")]
    fact_ids = [f["id"] for f in key_facts]
    layout = {"band": True, "header_ratio": 0.26, "footer_ratio": 0.135,
              "row_label_ratio": 0.42, "col_header_ratio": 0.20,
              "caption_ratio": 0.145}
    if fin:
        # The disclosure band is sized from its own copy, not from taste.
        layout["footer_ratio"] = max(0.135, len([l for l in disc.get("lines", []) if l]) * 0.034 + 0.030)

    bp = {
        "meta": {
            "category": brief.get("category") or "physical",
            "compliance": "strict" if fin else "trace_only",
            "campaign": brief["campaign"]["name"],
            "product": " / ".join(p["name"] for p in brief.get("products", [])),
            "launch_date": brief["campaign"].get("launch_date", ""),
            "disclosure": disc,
            "grid": {"cols": cols, "rows": rows, "cell": 2048, "gutter_ratio": 0.016,
                     "pad_ratio": 0.035},
            "layout": layout,
            "style": brief.get("style", {}).get("preset", "cartoon_flat"),
            "label_plate": "white",
            "key_facts": key_facts,
            # The tone contract travels with the blueprint, not with the chat: a writer
            # three days later has to be able to read what baseline was agreed.
            "voice": brief.get("voice") or {},
            "header": {
                "title": brief["campaign"]["name"],
                "subtitle": "一张图看懂：谁在什么时候，为什么需要它",
                "meta_line": "上市 %s · %s" % (
                    brief["campaign"].get("launch_date", ""),
                    " / ".join(brief["campaign"].get("channels", [])) or "渠道待定"),
            },
            "footer": {
                "note": "人群画像为受众模型示意，非真实个体；产品与规格以官方发布为准。",
                "signoff": "信息确认：%s" % brief.get("signoff", {}).get("name", ""),
            },
        },
        "columns": [{"id": s["id"], "title": s["title"], "note": s.get("desc", "")}
                    for s in scenes],
        "rows": [{"id": p["id"], "persona": p["id"], "name": p["name"],
                  "line1": "%s 岁 · %s" % (p.get("age", "—"), p.get("job", "")),
                  "line2": p.get("moment", "")} for p in personas],
        "band": {"phases": brief.get("timeline", {}).get("phases", [])},
        "characters": [{"id": "c_%s" % p["id"], "persona": p["id"], "name": p["name"],
                        "home_zone": "z_r%dc1" % (i + 1),
                        "species": p.get("species", "human"),
                        "design": p.get("design", ""),
                        "source": p.get("source", "")}
                       for i, p in enumerate(personas)],
        "assets": [{"id": a["id"], "kind": a.get("kind", "product"), "file": a["file"],
                    "note": a.get("note", "")}
                   for a in brief.get("assets", []) if a.get("file")],
        "zones": [],
        "targets": [],
        "coverage": {},
    }

    for i, p in enumerate(personas):
        for j, s in enumerate(scenes):
            caption, duty = "", ""
            if demo:
                table = DEMO_CELLS_FIN if fin else DEMO_CELLS
                caption, duty = table.get((p["id"], s["id"]), ("", ""))
            zone = {
                "id": "z_r%dc%d" % (i + 1, j + 1),
                "row": i + 1, "col": j + 1,
                "persona": p["id"], "scene": s["id"],
                "kind": "home" if j == 0 else "scene",
                "duty": duty or "TODO: 这一格要说清什么（一句话，具体到动作或物件）",
                "face_allowed": j == 0,
                "cast": {"named": ["c_%s" % p["id"]] if j == 0 else [], "extras_max": 0},
                "slots": [],
                "caption": caption or "TODO",
                "caption_source": p.get("source", "") if demo else "",
            }
            if demo and fin and j == 0:
                # A phone showing the app is this product's "pack shot": real screenshot,
                # reserved slot, hard cartoon shadow. The model never draws the interface.
                zone["slots"].append({
                    "asset": "ui_buy", "box": [0.34, 0.38, 0.32, 0.44],
                    "surface": "table", "shadow": "hard_ellipse"})
            if demo and not fin and j in (0, 2) and products:
                pid = "p_01" if j == 0 else "p_02"
                zone["slots"].append({
                    "asset": pid, "box": [0.30, 0.44, 0.40, 0.40],
                    "surface": "kitchen_counter", "shadow": "hard_ellipse"})
            if demo:
                k = len(bp["zones"]) * 2
                zone["facts"] = fact_ids[k:k + 2]
                zone["tile_origin"] = "ai"
            else:
                # A draft is a scaffold: the writer assigns facts per cell by hand.
                # lint_density.py refuses it until every cell carries a new one.
                zone["facts"] = []
                zone["tile_origin"] = None
            bp["zones"].append(zone)

    # Targets come from the channels the brief names, not from a wish list. A platform
    # that accepts several pages gets a carousel; one that does not gets a single frame.
    targets = [{"id": "master", "type": "full", "ratio": "auto",
                "use": "内部对齐：矩阵全貌，不投放"}]
    for ch in (brief.get("campaign", {}).get("platforms") or ["xiaohongshu"]):
        spec = pl.platform_spec(ch)
        if not spec:
            continue
        if spec.get("long"):
            # A long image is one tall frame read top to bottom. It is not a carousel with
            # a taller page: there is no swipe, so every persona block has to be complete
            # inside the single column of attention. The feed only shows the top quarter:
            # that quarter has to carry the conclusion and one line of disclosure itself.
            targets.append({"id": ch, "type": "long", "platform": ch,
                            "ratio": spec["ratio"], "note": spec.get("label"),
                            "first_screen": {
                                "takeaway": (key_facts[0]["text"] if key_facts else ""),
                                "facts": fact_ids[:3], "disclosure": True}})
        elif spec.get("max_pages", 1) > 1:
            pages = [{"kind": "cover", "hero": "z_r1c1", "facts": fact_ids[:3],
                      "takeaway": (key_facts[0]["text"] if key_facts else "")}]
            for ri in range(1, rows + 1):
                pages.append({"kind": "row", "rows": [ri]})
            pages.append({"kind": "end", "facts": fact_ids[-4:],
                          "lines": [f["text"] for f in key_facts[-3:]]})
            targets.append({"id": ch, "type": "carousel", "platform": ch,
                            "ratio": spec["ratio"], "note": spec.get("label"),
                            "pages": pages})
            targets.append({"id": "%s_overview" % ch, "type": "full", "platform": ch,
                            "ratio": spec["ratio"],
                            "note": "一张图看懂，作为轮播的最后一张或收藏图"})
        else:
            targets.append({"id": ch, "type": "full", "platform": ch,
                            "ratio": spec["ratio"], "note": spec.get("label")})
    bp["targets"] = targets

    filled = sum(1 for z in bp["zones"] if z["caption"] and z["caption"] != "TODO")
    bp["coverage"] = {
        "cells_total": len(bp["zones"]),
        "cells_filled": filled,
        "cells_empty": len(bp["zones"]) - filled,
        "note": "空格需在 gate 1 逐格说明：此「人群 × 场景」组合为何不成立",
    }
    return bp


def validate(brief):
    problems, warnings = [], []
    cat = brief.get("category") or "physical"
    if cat not in ("physical", "finance", "insurance", "service"):
        problems.append("category: %r 不可识别（physical / finance / insurance / service）" % cat)

    for ch in brief.get("campaign", {}).get("platforms") or []:
        if not pl.platform_spec(ch):
            problems.append("campaign.platforms: 未知平台 %r，可用 %s" % (
                ch, " / ".join(sorted(pl.PLATFORMS))))

    # --- Step 0.5: the tone is asked, not inferred ----------------------------------
    # A campaign whose baseline was never agreed drifts to whatever the writer felt that
    # afternoon. On a medical or insurance product that drift reads as 煽情, which is the
    # one thing the category cannot afford.
    v = brief.get("voice") or {}
    tone = (v.get("tone") or "").strip()
    if not tone:
        problems.append("voice.tone: 未定基调。先做 Step 0.5 的五个问题（平实 / 温和 / 紧迫 / "
                        "专业 / 轻松），不许替客户默认")
    elif tone not in pl.TONE_MODES:
        problems.append("voice.tone: %r 不可识别，取 %s" % (tone, " / ".join(pl.TONE_MODES)))
    else:
        if v.get("emotion_budget") in (None, ""):
            warnings.append("voice.emotion_budget 未填：将按 %s 的预设 %d 执行" % (
                tone, pl.TONE_MODES[tone]["budget"]))
        elif tone in ("plain", "expert", "witty") and int(v["emotion_budget"]) > 0:
            warnings.append("voice.emotion_budget=%s 与 %r 基调冲突：这两种基线写煽情句，"
                            "读者会认为不是同一篇东西" % (v["emotion_budget"], tone))
        if not (v.get("sample") or "").strip():
            warnings.append("voice.sample 为空：没有语感样例，作者只能凭感觉写，"
                            "这正是上一版跑偏的方式")
        if not (v.get("pov") or "").strip():
            warnings.append("voice.pov 为空：不确定第三人称白描还是第二人称对话，"
                            "十二条会各写各的")
        if (brief.get("category") or "") in pl.FINANCE_CATEGORIES and tone != "plain":
            warnings.append("金融/保险类基调是 %r。合规上不禁止，但先确认客户品牌口径允许" % tone)

    # 文案模式：四格是讲故事，还是讲这一格的规则？保险与理财的答案是后者。
    cmode = (v.get("caption_mode") or "").strip()
    if cmode and cmode not in pl.CAPTION_MODES:
        problems.append("voice.caption_mode: %r 不可识别，取 %s" % (
            cmode, " / ".join(pl.CAPTION_MODES)))
    elif (brief.get("category") or "") in pl.FINANCE_CATEGORIES and cmode != "rule":
        warnings.append("voice.caption_mode 未定为 rule：金融/保险的四格画的是每个缴费节点，"
                        "文案该写「这一步按哪条算」，写成人物的故事就会滑回煽情")
    elif not cmode and brief.get("category") == "physical":
        warnings.append("voice.caption_mode 未填：默认按 narrative（这一格发生了什么）走")

    if cat in pl.FINANCE_CATEGORIES:
        d = brief.get("disclosure") or {}
        if len([l for l in d.get("lines", []) if l]) < 2:
            problems.append("disclosure.lines: 金融/保险至少两条风险披露")
        if not d.get("institution"):
            problems.append("disclosure.institution: 缺发行/销售机构")
        if not d.get("data_asof"):
            problems.append("disclosure.data_asof: 缺数据截至日")
        if cat == "finance" and not d.get("risk_level"):
            problems.append("disclosure.risk_level: 理财类必须有 R1–R5 风险等级")
        if cat == "insurance" and not d.get("license"):
            problems.append("disclosure.license: 保险类必须有机构/中介资质编号")
        if not brief.get("campaign", {}).get("platforms"):
            warnings.append("campaign.platforms 为空：金融类没有渠道就等于没有披露位")
    for p in brief.get("personas", []):
        if not p.get("name"):
            problems.append("personas: 有画像缺 name")
        if not p.get("moment"):
            problems.append("personas[%s]: 缺 moment（触发时刻）——没有它，这一行就只是一个标签"
                            % (p.get("id") or p.get("name")))
        if not p.get("source"):
            warnings.append("personas[%s]: 缺 source，无法溯源到 brief" % p.get("id"))

    if not brief.get("products"):
        problems.append("products: 为空。没有产品清单，asset_slot 就无处可贴")
    for p in brief.get("products", []):
        asset = p.get("asset", "")
        if not asset:
            problems.append("products[%s]: 缺 asset" % p.get("id"))
        elif not os.path.isfile(asset):
            problems.append("products[%s]: asset 文件不存在 %s" % (p.get("id"), asset))
        if not p.get("confirmed_by"):
            warnings.append("products[%s]: 缺 confirmed_by（谁确认这是这个型号的外观）" % p.get("id"))

    n_p, n_s = len(brief.get("personas", [])), len(brief.get("scenes", []))
    if not (3 <= n_p <= 5):
        problems.append("personas: 需要 3–5 段，当前 %d。少于 3 撑不起矩阵，多于 5 每格就只剩一个头"
                        % n_p)
    if not (4 <= n_s <= 6):
        problems.append("scenes: 需要 4–6 个，当前 %d。少于 4 讲不清使用面，多于 6 主图在背板上看不清"
                        % n_s)

    # Step 0 item 12. A matrix built without a fact list is how twelve cells end up
    # saying the same three things: there is nothing to check a cell against.
    kf = [f for f in (brief.get("key_facts") or [])
          if isinstance(f, dict) and (f.get("id") or "").strip()
          and (f.get("text") or "").strip()]
    if not kf:
        problems.append("key_facts（第 12 项）：为空。没有事实清单，信息密度门禁会阻断，"
                        "且这一稿没有可逐条核对的信息基线")
    else:
        if len(kf) < n_p * n_s:
            warnings.append("key_facts 只有 %d 条，矩阵 %d 格：逐格分配时必然出现复述，"
                            "lint_density.py 会按复述率判" % (len(kf), n_p * n_s))
        for f in kf:
            if not (f.get("source") or "").strip():
                problems.append("key_facts[%s]: 缺 source——事实指不回素材就不许上图" % f["id"])
            if cat in ("finance", "insurance") and not (
                    f.get("source") or "").startswith("client-confirmed:"):
                problems.append("key_facts[%s]: 金融/保险类事实的 source 必须 client-confirmed:*"
                                % f["id"])

    phases = brief.get("timeline", {}).get("phases", [])
    if len([x for x in phases if x.get("label")]) < 2:
        problems.append("timeline.phases: 至少 2 段（如 预热 / 发布 / 上市后）")
    if not brief.get("signoff", {}).get("name"):
        problems.append("signoff: 缺签字人。图上会有价格、日期、规格，没人签字就不能上图")

    if not brief.get("campaign", {}).get("channels"):
        warnings.append("campaign.channels: 未填主图落地渠道，targets 只能按默认比例出")
    if not brief.get("redlines", {}).get("forbidden_claims"):
        warnings.append("redlines.forbidden_claims: 未填禁用表述，文案审核将没有红线可依")
    if not any(a.get("kind") == "mascot" and a.get("file") for a in brief.get("assets", [])):
        warnings.append("assets: 无吉祥物三视图。若画面里有 IP 角色，必须补——模型会把它画可爱，这在品牌上算事故")
    return problems, warnings


def report_markdown(brief, problems, warnings, draft):
    L = ["# Brief 采集报告", ""]
    L.append("**战役**：%s  " % brief.get("campaign", {}).get("name", "（未填）"))
    L.append("**矩阵**：%d 人群 × %d 场景 = %d 格  " % (
        len(brief.get("personas", [])), len(brief.get("scenes", [])),
        len(brief.get("personas", [])) * len(brief.get("scenes", []))))
    L.append("**上市日期**：%s  " % brief.get("campaign", {}).get("launch_date", "（未填）"))
    L.append("**签字人**：%s" % brief.get("signoff", {}).get("name", "（未填）"))
    v = brief.get("voice") or {}
    tone = (v.get("tone") or "").strip()
    tm = pl.TONE_MODES.get(tone)
    L.append("**基调**：%s · %s · 每条 caption 煽情词上限 %s  · 金句配额 %s  " % (
        (tm["label"] if tm else "（未定）"),
        v.get("pov") or "（未填人称）",
        v.get("emotion_budget") if v.get("emotion_budget") not in (None, "") else
        (tm["budget"] if tm else "—"),
        v.get("punch_quota", "—")))
    cmode = (v.get("caption_mode") or "").strip()
    L.append("**文案模式**：%s  " % (
        pl.CAPTION_MODES[cmode]["label"] + "：" + pl.CAPTION_MODES[cmode]["note"]
        if cmode in pl.CAPTION_MODES else "（未填，默认场景叙述）"))
    L.append("**语感样例**：%s" % (v.get("sample") or "（未填——作者会凭感觉写）"))
    L += ["", "## 阻断项（必须补，否则不开工）", ""]
    L += ["- %s" % p for p in problems] or ["- 无"]
    L += ["", "## 提醒项（可以开工，但 gate 1 要说清）", ""]
    L += ["- %s" % w for w in warnings] or ["- 无"]

    L += ["", "## 矩阵覆盖", ""]
    personas = brief.get("personas", [])
    scenes = brief.get("scenes", [])
    L.append("| 人群 \\ 场景 | " + " | ".join(s.get("title", "?") for s in scenes) + " |")
    L.append("|" + "---|" * (len(scenes) + 1))
    cells = {(z["persona"], z["scene"]): z for z in draft["zones"]}
    for p in personas:
        row = ["**%s**" % p.get("name", "?")]
        for s in scenes:
            z = cells.get((p["id"], s["id"]))
            row.append("已写" if z and z["caption"] != "TODO" else "待写")
        L.append("| " + " | ".join(row) + " |")

    L += ["", "## 事实清单（第 12 项：读者要带走什么）", "",
          "| id | 类型 | 事实 | 来源 |", "|---|---|---|---|"]
    for f in (brief.get("key_facts") or []):
        if isinstance(f, dict) and (f.get("text") or "").strip():
            L.append("| %s | %s | %s | %s |" % (
                f.get("id", ""), f.get("kind", ""),
                f["text"].replace("|", "/"), (f.get("source") or "").replace("|", "/")))
    L += ["", "## 下一步", ""]
    L.append("1. 把每个 zone 的 `duty`（这一格要说清什么）和 `caption`（读者会读到的那一句）写进 blueprint。")
    L.append("2. `caption_source` 必须指回 brief 的章节或资产编号——指不回去的句子不许上图。")
    L.append("3. 给每个 zone 分配 `facts`（本表里未在其他格出现过的 id）并声明 `tile_origin`。")
    L.append("4. 跑 `lint_copy.py` 与 `lint_density.py`，两份台账原样贴进 Gate 1 给人确认。")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="promo-atlas step 0: structured intake")
    ap.add_argument("brief", nargs="?", help="path to brief.json")
    ap.add_argument("--init", action="store_true", help="write an empty intake form")
    ap.add_argument("--demo", action="store_true", help="write a filled demo build (physical)")
    ap.add_argument("-o", "--out", default="build", help="output directory")
    ap.add_argument("--demo-finance", action="store_true",
                    help="write a filled demo build for a financial product (social channels)")
    args = ap.parse_args()

    out = pc.ensure_dir(os.path.abspath(args.out))

    if args.init:
        path = os.path.join(out, "brief.json")
        pc.save_json(path, empty_brief())
        print("已写入空白采集表: %s" % path)
        print("12 项必填，其中 products / personas / scenes 缺任一项即阻断；"
              "voice.tone 未定也不放行（Step 0.5）；key_facts 为空，信息密度门禁不放行。")
        return 0

    if args.demo or args.demo_finance:
        data = dict(DEMO_FINANCE_BRIEF if args.demo_finance else DEMO_BRIEF)
        data["key_facts"] = demo_fact_list(finance=args.demo_finance)
        path = os.path.join(out, "brief.json")
        pc.save_json(path, data)
        build_demo_assets(out, finance=args.demo_finance)
        draft = draft_blueprint(data, demo=True)
        pc.save_json(os.path.join(out, "blueprint.json"), draft)
        pc.save_json(os.path.join(out, "brief.json"), data)
        problems, warnings = validate(_resolve(data, out))
        (pc.ensure_dir(os.path.join(out, "reports")))
        with open(os.path.join(out, "reports", "brief_report.md"), "w", encoding="utf-8") as fh:
            fh.write(report_markdown(data, problems, warnings, draft))
        print("demo 已生成: %s" % out)
        print("  brief.json / blueprint.json / assets/ / reports/brief_report.md")
        print("  阻断项 %d，提醒项 %d" % (len(problems), len(warnings)))
        return 1 if problems else 0

    if not args.brief:
        ap.print_help()
        return 2

    path = os.path.abspath(args.brief)
    if not os.path.isfile(path):
        print("找不到 %s" % path, file=sys.stderr)
        return 2
    base = os.path.dirname(path)
    brief = _resolve(pc.load_json(path), base)
    problems, warnings = validate(brief)

    draft = draft_blueprint(brief)
    pc.save_json(os.path.join(base, "blueprint.draft.json"), draft)
    pc.ensure_dir(os.path.join(base, "reports"))
    md = report_markdown(brief, problems, warnings, draft)
    with open(os.path.join(base, "reports", "brief_report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)

    print(md)
    return 1 if problems else 0


def _resolve(brief, base):
    """Make asset paths absolute relative to the brief file, so scripts run from anywhere."""
    for p in brief.get("products", []) + brief.get("assets", []):
        f = p.get("asset") or p.get("file")
        if f and not os.path.isabs(f):
            cand = os.path.join(base, f)
            if os.path.isfile(cand):
                if "asset" in p:
                    p["asset"] = cand
                else:
                    p["file"] = cand
    return brief


if __name__ == "__main__":
    sys.exit(main())
