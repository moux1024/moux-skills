# blueprint.json — the contract every script reads

One file holds the whole poster: geometry, cast, assets, copy, coverage, targets. The
scripts execute it; they never invent. If a number is not here, it does not exist.

```
build/
  brief.json              # Step 0 intake (human-owned)
  blueprint.json          # this contract (human-owned, script-checked)
  assets/                 # client files: logo, product shots, mascot sheet
  tiles/                  # one image per zone, plus audit.json
  reports/                # brief_report.md, copy_sheet.md, assets.json, stitch_report.json
```

## Skeleton of the file

```jsonc
{
  "meta": {
    "category": "physical",              // physical | finance | insurance | service
    "compliance": "trace_only",          // strict | trace_only（金融默认 strict）
    "campaign": "轻氧 Pro 2 · 上市战役总览",
    "product": "轻氧 Pro 2 净饮机 / 轻氧滤芯 Pro",
    "launch_date": "2026-11-01",
    "grid":   { "cols": 4, "rows": 3, "cell": 2048, "gutter_ratio": 0.016, "pad_ratio": 0.035 },
    "layout": { "band": true, "header_ratio": 0.26, "footer_ratio": 0.135,
                "row_label_ratio": 0.42, "col_header_ratio": 0.20, "caption_ratio": 0.145 },
    "style": "cartoon_flat",
    "label_plate": "white",
    "voice": {                           // Step 0.5 的结论；缺 tone 即阻断复审
      "tone": "plain",                   // plain | warm | urgent | expert | witty
      "pov": "第三人称白描",              // 叙述人称
      "caption_mode": "rule",            // narrative 这一格发生了什么 / rule 这一步按哪条算
      "emotion_budget": 0,               // 每条 caption 允许的煽情词数
      "punch_quota": 1,                  // 全套图允许的金句数
      "sample": "医保卡从窗口推进去，又推回来",   // 语感样例，作者照着写
      "body": "平台发布正文……"           // 同一套预算也管这一段
    },
    "header": { "title": "...", "subtitle": "...", "meta_line": "上市 2026-11-01 · 电商主图" },
    "footer": { "note": "人群画像为受众模型示意，非真实个体。",
                "signoff": "信息确认：客户市场部 / 法务" },
    "disclosure": {                      // 金融/保险必填，其他品类可留空
      "lines": ["本产品不保本，收益随市场波动，投资者可能损失本金。",
                "过往业绩不代表未来表现，业绩比较基准不构成收益承诺。"],
      "institution": "示例基金管理有限公司",
      "license": "中国证监会核准 · 编号 000000",
      "risk_level": "R3 中风险",
      "data_asof": "2026-09-30"
    },
    "key_facts": [                       // 第 12 项采集；lint_density.py 的事实基线
      { "id": "f_01", "text": "疾病等待期 30 日", "kind": "number",
        "source": "client-confirmed:条款截图·等待期" },
      { "id": "f_02", "text": "医保补偿后按余额 80% 给付", "kind": "condition",
        "source": "client-confirmed:条款截图·给付" }
    ],
    "density_limits": {}                 // 可选，按稿覆盖 DENSITY_LIMITS
  },
  "columns": [ { "id": "s_01", "title": "夜归", "note": "玄关到厨房，灯只开了廊灯" } ],
  "rows":    [ { "id": "a_01", "persona": "a_01", "name": "林小满",
                 "line1": "29 岁 · 新媒体编辑", "line2": "加班到家，包还没放下就先灌一杯水" } ],
  "band":    { "phases": [ { "label": "预热", "date": "10.15 – 10.31", "note": "痛点铺底" } ] },
  "characters": [ { "id": "c_a_01", "persona": "a_01", "name": "林小满",
                    "home_zone": "z_r1c1", "species": "human", "design": "", "source": "brief:§2" } ],
  "assets":  [ { "id": "p_01", "kind": "product", "file": "assets/p_01.png", "note": "正面平视" } ],
  "zones":   [ { "id": "z_r1c1", "row": 1, "col": 1, "persona": "a_01", "scene": "s_01",
                 "kind": "home", "face_allowed": true,
                 "duty": "她刚进门，手已经伸向台面",
                 "cast": { "named": ["c_a_01"], "extras_max": 0 },
                 "slots": [ { "asset": "p_01", "box": [0.30, 0.44, 0.40, 0.40],
                              "surface": "kitchen_counter", "shadow": "hard_ellipse" } ],
                 "caption": "夜归的人先要一杯水",
                 "caption_source": "brief:§2",
                 "facts": ["f_01", "f_02"],   // 本格新增的事实 id，至少一条别格没用过
                 "tile_origin": "ai" }, ],    // ai | code_card | evidence | chart
  "targets": [ { "id": "main", "type": "full", "ratio": "auto" },
               { "id": "row_a_01", "type": "row", "rows": [1], "ratio": "9:16" },
               { "id": "col_s_01", "type": "col", "cols": [1], "ratio": "4:5" } ],
  "coverage": { "cells_total": 12, "cells_filled": 12, "cells_empty": 0, "note": "..." }
}
```

## Rules the scripts enforce

| field | rule | why |
|---|---|---|
| `grid.rows` / `grid.cols` | 必须等于 `rows` / `columns` 的长度，且 `zones` 数 = 乘积 | 缺一格就是缺一格，不给它编 |
| `zones[].row` / `col` | 1-based，落在网格内 | 0-based 混用会把整列错位 |
| `zones[].kind` | `home` 必须在第 1 列 | 定妆照是整行的锚 |
| `zones[].face_allowed` | `true` 必须配 `cast.named`；`false` 必须为空 | 空的 face 格会被模型用人脸填满 |
| `characters[].home_zone` | 必须存在，且该格 `face_allowed` | 一人只有一身 |
| `slots[].box` | `[x,y,w,h]` 归一化到**本格画面区**，不越界 | 归一化到整图会让 target 重排时飘走 |
| `slots[].shadow` | `hard_ellipse` / `hard_oblique` / `none` | 真实柔边投影会让贴图一眼假 |
| `slots[].surface` | 必填（桌面/货架/手掌/相框/橱窗/地台） | 产品不能浮空 |
| `caption` | 非空、非 TODO、≤ 板子容量 | 容量由 `caption_ratio` 反算，见 `copy_sheet.md` |
| `caption_source` | 非空；价格/日期/规格必须是 `client-confirmed:*` | 溯源比合法性更可执行 |
| `meta.voice.tone` | 必须是 `pl.TONE_MODES` 里的一个值 | 没有基线，"这句太煽情"只能事后吵 |
| `meta.voice.emotion_budget` | 与 tone 相容；plain/expert/witty 必须为 0 | 基线与预算打架，读者会认为不是同一篇东西 |
| `meta.voice.caption_mode` | `narrative` / `rule`；rule 模式下每条 caption 必须含规则要素且 source 为 `client-confirmed:*` | 四格讲规则还是讲故事，是两种产品 |
| `targets[].rows` / `cols` | 必须指向存在的行列 | 渠道切片不能指向空气 |
| `targets[].type == "long"` | `ratio` 的高度 ≤ 宽度 × 4 | 超过 1:4 平台会压成一条灰带 |
| `meta.key_facts` | 非空；每条有 `id` / `text` / `kind` / `source`；金融保险 `source` 必须 `client-confirmed:*` | 没有事实清单，「这格有没有信息」无从判断 |
| `zones[].facts` | ≥1 条 `key_facts` 的 id，且至少一条别格没用过 | 复述不计信息单元；复述率 >30% 阻断 |
| `zones[].tile_origin` | `ai` / `code_card` / `evidence` / `chart` | 声明图片从哪来，决定信息面积权重 |
| `code_card` / `evidence` / `chart` 格 | facts 里至少一条 `number` / `condition` / `boundary` / `evidence` | 空白几何卡硬拦 |
| 每个投放页 | cover ≥3、row / full ≥6、end ≥4 个新信息单元 | 4 格页只印 4 句就是「信息少」 |
| 信息面积比 | ≥18%（`meta.density_limits.min_info_area` 可覆盖） | 只算说明板 / 信息卡 / 证据贴图，不算标题页码与披露带 |

## Coordinates

Everything is a ratio of `cell`, so the same blueprint renders at 2048 (delivery) and at
640 (skeleton preview) with identical proportions. A box is normalised **inside its own
zone's image area**, which is what keeps a product on its table when a target reflows
4 cells into a 2×2 stack.

## Targets

| type | cells | notes |
|---|---|---|
| `full` | all | with `ratio: "auto"` → the master (band, headers, row labels, footer) |
| `carousel` | per `pages` | 轮播；每页独立成图，自带页码与披露 |
| `full` + ratio | all | reflows into the shape closest to the ratio (e.g. 1:1 电商主图) |
| `long` | all | 长图：竖着一次读完，人群按块完整落下，比例不超过 1:4 |
| `row` | one row, all columns | 人群定向素材；9:16 时自动变 2×2 竖排 |
| `col` | one column, all rows | 卖点主题图；4:5 或 1:1 |
| `cell` | one cell | 单格放大的社媒图 |

Nothing is ever cropped from the master. A target solves its own cell height so the
channel ratio is met by layout, and only residuals under ~3% become letterbox.

### 长图（`type: "long"`）

```jsonc
{ "id": "xiaohongshu_long", "type": "long", "platform": "xiaohongshu_long", "ratio": "1:4" }
{ "id": "long_image", "type": "long", "platform": "long_image", "ratio": "1:4" }
```

和 `full` + ratio 的区别只有两条，但两条都是硬约束：

1. **分栏数必须整除场景数**。`flow_shape` 只在能整除数里选列数，所以一个人群的 4–6 格
   永远是一整块（4 格 → 2×2 一块）。否则第一个人的最后一格会挨着第二个人的第一格，
   读者分不清哪几格属于谁——这是长图最常见的错。
2. **每块的第一格要带人群条**。长图没有左侧人群栏，`render` 会在块的起始格画一个
   `name · line1` 的色条；没有它，四格同属一个人这件事只靠"上下相邻"暗示，一截图就丢。

1:4 上限由 `LONG_MAX_ASPECT` 强制。要更长的故事就分页，不要拉长——平台会先压缩，再没人看。

### Platform targets

```jsonc
{ "id": "xiaohongshu", "type": "carousel", "platform": "xiaohongshu", "ratio": "3:4" }
{ "id": "douyin", "type": "full", "platform": "douyin", "ratio": "9:16" }
```

`platform` 一次性带来三件事：**投放尺寸**（页面按该平台真实像素反解格子）、**安全区**
（四边不对称留白，文字不进 UI 覆盖带）、**页数上限**（超过即报错）。`ratio` 可省略，
省略时取平台默认。

自定义安全区（例如换了账号排版）：

```jsonc
{ "id": "douyin", "type": "full", "platform": "douyin",
  "safe": { "top": 0.055, "right": 0.11, "bottom": 0.11, "left": 0.04 } }
```

### Carousel pages

```jsonc
{ "id": "xiaohongshu", "type": "carousel", "platform": "xiaohongshu",
  "pages": [
    { "kind": "cover", "title": "工资到账那天，先分一笔出去", "hero": "z_r1c1",
      "takeaway": "90 天持有期，1,000 元起", "facts": ["f_01", "f_02", "f_03"] },
    { "kind": "row", "rows": [1] },
    { "kind": "row", "rows": [2] },
    { "kind": "row", "rows": [3] },
    { "kind": "end", "lines": ["起投 1,000 元 · 90 天持有期"],
      "facts": ["f_01", "f_04", "f_07", "f_09"] }
  ] }
```

`pages` 省略时自动生成：封面 + 每个人群一页 + 落版，但那样 cover / end 的 `facts` 为 0，
`lint_density.py` 会阻断——封面是唯一一定被看到的一页，不能只有标题和一张图。
`cover.facts` 指向 `meta.key_facts`，由 `stitch.py` 印成一行「关键数字」板；
`cover.takeaway` 是一句来自事实的结论。`end.facts` 同理，落版至少 4 条。
`cover.title`、`cover.takeaway`、`end.lines` 是仅有的可以直接写文案的地方，其余文案仍来自
`zones[].caption`。

长图的第一屏另有一份合同：

```jsonc
{ "id": "xiaohongshu_long", "type": "long", "platform": "xiaohongshu_long",
  "ratio": "1:4",
  "first_screen": { "takeaway": "疾病等待期 30 日", "facts": ["f_01", "f_02", "f_03"],
                    "disclosure": true } }
```

`first_screen` 的三项分别进标题区的结论行、关键数字与一行短披露。信息流只露顶部 1/4，
截图转发也只有这一块；把披露全押在图片最底部，等于首屏截图里一句披露都没有。

## 信息密度合同

`lint_density.py` 在 Gate 1 之前跑，输出 `reports/density_sheet.md`。三个口径：

1. **信息单元** = 一条 `meta.key_facts` 里的新事实。同一 `id` 第二次出现算复述，不计入。
2. **信息面积比** = 承载新事实的矩形（说明板 + 信息卡 + 证据贴图）/ 页面面积，按
   `tile_origin` 加权（`ai` 0.25，其余 1.0）。标题、页码、列标题、人群条、披露带不算。
3. **逐页增量** = 该页所有格子里的新事实数，按 cover / row / full / end 分别比对门槛。

`make_rule_card.py` 只读 `tile_origin: code_card` 的格子，把 `facts` 里的 text / kind /
source 印成规则卡；没有 facts 的格子它直接拒绝生成。这套字段让「插画比格子少」成为
一个可审查的降级，而不是八个没有内容的文件。

## Tone contract

`meta.voice` 是 Step 0.5 的产出，和几何信息一样是合同的一部分。`lint_copy.py` 对它做三件事：

| 检查 | 判定 |
|---|---|
| `tone` 缺失或不在 `TONE_MODES` | **阻断**——没有基线就没有"太煽情"这件事 |
| caption 煽情词 > `emotion_budget` | plain / expert / witty → **阻断**；其余 → 提醒 |
| rule 模式下 caption 无规则要素 | 提醒（这一格还在讲画面，没讲规则） |
| rule 模式下 caption 的 source 不是 `client-confirmed` | **阻断**——图上每条规则都要能在条款里找到原文 |
| 标题、人群设定、正文里的煽情词 | 提醒（同样计入台账） |
| 病痛词 + 深夜/拖延 同句（苦情取材） | plain / expert → **阻断**；其余 → 提醒 |
| 金句数 > `punch_quota` | 提醒 |

煽情词表在 `lint_copy.EMOTION_WORDS`（心酸/崩溃/咬牙/硬撑/心疼/不容易…约 30 个），
苦情取材是 `MISERY_BODY × MISERY_HOUR` 的交叉。两张表都只数得清"形状"，数不出"好坏"：
它们负责拦住上一版那种"十二条平淡、标题和人群设定在使劲"的走偏，不负责替你写句子。

`copy_sheet.md` 顶部会出一段基调台账：基线、人称、预算、实测煽情词数、苦情取材清单、
金句用量。改稿时对着这一块看，比读十二条 caption 更快发现跑偏。

## Financial categories

`category` 为 `finance` / `insurance` 时，脚本额外强制：

| 字段 | 要求 | 缺失后果 |
|---|---|---|
| `disclosure.lines` | ≥ 2 条 | 阻断 |
| `disclosure.institution` | 发行/销售机构全称 | 阻断 |
| `disclosure.data_asof` | 收益率与费率的截止日 | 阻断 |
| `disclosure.risk_level` | 理财 R1–R5 | 阻断（仅 finance） |
| `disclosure.license` | 机构/中介资质编号 | 阻断（仅 insurance） |

并且 `lint_copy.py` 会硬拦截：保本/保收益/稳赚/零风险/预期收益/确诊即赔/第一人称收益
证言；收益百分比若不带「业绩比较基准 / 历史 / 截至」限定语，同样阻断。确已过法务的素材
可用 `meta.compliance: "trace_only"` 关闭，这是开关，不是默认。
