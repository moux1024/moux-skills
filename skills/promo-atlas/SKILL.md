---
name: promo-atlas
display_name: "社媒推广图集"
display_name_zh: "社媒推广图集"
display_name_en: "Promo Atlas"
description: "Turns a launch brief into a social-media campaign set — one internal master board (persona × scenario matrix with a timeline band) plus per-platform deliverables: 小红书轮播, 小红书长图, 抖音竖版, 朋友圈方图, 微博横图, 电商主图. Cartoon art is generated per cell; the real product, logo, mascot, app screen, chart and every client-confirmed number are composited in by code; every word sits on its own plate; every platform's UI occlusion band is respected. Copy tone is agreed before a single caption is written (plain / warm / urgent / expert / witty, with a countable 煽情 budget), and a long image never exceeds 1:4. Every cell must add a sourced fact: lint_density.py blocks empty cells, facts-free rule cards and pages with too few information units. Works for physical goods and for 理财 / 保险 / 金融产品, where a risk disclosure band and prohibited-claim blocking are enforced. Use when the user wants 社媒推广图, 小红书轮播, 小红书长图, 长图推广, 新品上市总览, 人群场景矩阵图, 一张图讲清上市计划, 金融产品宣传图, 保险产品海报, 条款解读图, or a multi-channel campaign set."
description_zh: "上市简报 → 人群×场景矩阵主图 + 各渠道成图；先定基调再写文案，每格必须新增一条可溯源事实，长图不超过 1:4"
description_en: "Launch brief to a persona-by-scenario master board plus per-channel deliverables; tone agreed before copy, every cell gated on a sourced fact, long image capped at 1:4"
version: 1.2.1
allowed-tools: Read,Write,Edit,Bash,Glob,Grep,ViewImage
agent_created: true
---

# Promo Atlas

Turn one launch brief into **one** ultra-high-resolution campaign poster: 3–5 personas ×
4–6 scenarios, a timeline band on top, every cell a designed panel with its own caption
plate. The picture carries the meaning; text and product are laid in by code.

The skill is an **orchestrator, not a generator**. It does not imagine the product, the
logo, the mascot, the app screen or a single printed character. Those are files and
geometry.

It also does not ship one poster and call it a campaign. The master matrix is an internal
alignment artefact; what goes out is a **set** — a carousel where the platform allows pages,
a single frame where it does not, and a long image where the audience saves instead of
swiping. Each one sized, padded and cropped for where it will be read.

And it does not write a word until the tone is agreed. "平实" and "煽情" are two different
products to the person reading them, and only one of them can be the baseline.

## Non-negotiable rules

1. **Source or it doesn't print.** Every number, price, date, spec and claim on the canvas
   carries a `caption_source` pointing at a brief section (`brief:§3`), an asset id
   (`asset:pack-02`) or a written confirmation (`client-confirmed:2026-10-21`). A sentence
   that cannot be pointed back does not go on the image — this replaces advertising-law
   scanning, because "is it in the material" is a question a script can answer.
2. **AI draws place and people; code places product and writes words.** Three asset classes
   are never redrawn: logo, product shot, mascot turnaround sheet. An image model asked for
   a logo returns a plausible fake one, and a fake logo is not a style problem.
3. **The slot is geometry, not a wish.** Every product gets a rectangle in the blueprint,
   the zone prompt forbids objects inside it, and `stitch.py` pastes the real file there.
   Shadow is `hard_ellipse` / `hard_oblique` / `none` — a physically soft shadow belongs to
   another world's lighting and is the clearest tell that a photo was dropped into a drawing.
4. **One persona, one face.** Each character has one full-body shot in its home cell
   (column 1, `face_allowed: true`). Everywhere else in its row it appears only as back,
   side or hands (`face_allowed: false`). No avatar crops, no face repetition — 3–5 personas
   need 3–5 faces, not 30.
5. **Structure picks layout.** Persona rows × scenario columns, timeline band on top,
   persona strip on the left, coverage note at the bottom. Genre is not a determinant.
6. **Selection is capped.** 3–5 personas, 4–6 scenarios, ≤30 cells. Over cap → merge scenes,
   not squeeze cells. An empty cell is legal and must state why; a silent empty cell is not.
7. **Three gates before spending on tiles** — content list, skeleton with every target
   previewed, single-zone style proof — plus an asset/cast audit after generation. Do not
   batch-generate until all three pass.
8. **Reflow, never crop.** A channel derivative solves its own cell height and stacks its
   cells into the shape closest to the ratio. Cropping a 16:9 master into 9:16 removes heads
   and plates; letterboxing removes the point.
9. **Copy is toned, traced, voiced, then measured.** In that order — a line written against
   the wrong baseline has to be rewritten before it is worth measuring, and a layout measured
   against words nobody kept has to be measured again. `lint_copy.py` gates it: a missing
   `voice.tone` blocks; concrete-object coverage below **50% blocks** (that is not short copy,
   it is empty copy), **50–66% warns**; a 煽情词 over the agreed budget blocks on 平实 / 专业 /
   轻松 baselines and warns elsewhere. Procedure, the rewrite order and the plate-scale
   failures: Step 0.5, Step 3 and `references/copy-voice.md`.
10. **Verdicts bind to pixels.** The audit record stores each tile's hash, so a regenerated
    image cannot inherit an old approval, and a "pass" without one sentence describing what
    was on screen is refused as a rubber stamp.
11. **Faithful to the material, not comfortable.** If the client's own copy carries a risky
    absolute claim, print it and flag it — never rewrite it into something that looks legal.
    This skill does not certify compliance and must never say it did.
12. **Seams are designed.** Panels are separated by their own frames and paper margins. No
    feathering: feathering two unrelated pictures produces a dirty band, not a transition.
13. **The platform is a constraint, not a canvas.** 抖音右侧与底部、小红书下缘都有平台自己的
    控件压住画面，安全区是四边不对称的**留白**——字进那块区域就是塞到点赞键底下。留白大
    就改平台参数，不改版面。每页还必须能**单独截图活下来**：自带标题、页码、披露，不靠前一页
    才读懂；页数是平台能力，抖音没有轮播。尺寸、安全区、页数上限见
    `references/social-channels.md`，逐页预览见 Step 5。
14. **金融与保险不是"另一种商品"。** 它们多一条不可协商的要求：风险披露在画面内持续可见，
    且承诺收益/保本/预测收益类表述**即使来自客户素材也硬拦截**。实物走"忠实于素材"，
    金融走"披露 + 拦截"，两种策略不能合并成一种。无客户验证走 `--demo-finance`（Step 0）。
15. **基调先定，再写第一句。** 平实 / 温和 / 紧迫 / 专业 / 轻松，是**问出来的**，不是替客户
    猜的；连同人称、文案模式（叙述 / 规则解读）、煽情词预算、金句配额、一句语感样例一起
    写进 `brief.voice`。没有 `voice.tone` 的 brief 不放行，没有 `meta.voice` 的 blueprint
    不许过文案复审。「这句是不是太煽情」在事后无法达成一致，只能对着一份写下来的基线判断。
    问题清单见 Step 0.5，纪律见 `references/copy-voice.md` §0。
16. **长图是一条渠道，不是更长的轮播。** 主流信息流都支持点开一张长图看全，但它们不给
    你滑动，所以整件事要在一列注意力里说完。比例**不超过 1:4**（超过平台先压缩再没人看），
    人群必须**按块完整落下**（分栏数整除场景数），每块第一格自带人群条。长图不替代封面的
    职责：顶部第一屏要能独立说清这是什么，并且自带结论、关键数字与一行披露——信息流里
    多数人只看到这一块，截图转发出去的也只有这一块。
17. **信息密度是可量的，不是观感。** 一个文件存在不等于一格有内容：v1.1.1 用八张空白
   几何卡填满十二格，`stitch.py` 因为只看「文件在不在」报了 `placeholder: 0`，全部门禁
   通过。现在 `meta.key_facts[]` 是第 12 项采集，每个 `zone` 必须引用至少一条**别格没说过**
   的事实并声明 `tile_origin`；`lint_density.py` 逐格、逐页、按面积比三处核账，空白卡、
   复述过多的稿子和没有关键数字的封面都过不了。Gate 1 原样贴出 `density_sheet.md`。
18. **rule 模式的画要能算，数字由代码印。** `caption_mode: rule` 把文案改成「这一步按哪条
   算」，画就必须给出算式、对照、区间、清单或条款原文，不能只剩 paperwork 与等待。
   `[FORBIDDEN] no invented numbers` 管的是模型编数字，不是禁数字：客户确认的数字走
   `[DATA-SLOT]`，由 `make_rule_card.py` 或 `slots: fact_plate` 印上去，仍带 `source`、仍要
   签字。插画数少于格数时用内置规则卡模板降级，不许临时画空白纸片。语法见
   `references/rule-visual.md`。
19. **交付尺寸是精确值，不是近似值。** `pad_to_ratio` 只会补边、不会缩小，所以 v1.2.0
   重出的稿子出现了「1242 的封面 + 1256 的内页 + 1259 的长图」：同一次上传被平台按三种
   倍率重采样，文字锐度各不相同。凡绑定平台的 target，出图后一律归一化到平台像素
   （宽取 `PLATFORMS[key].px[0]`，高由 ratio 反推，小红书 1242×1656、长图 1242×4968），
   `stitch_report.json` 记 `platform_px` / `size_exact` / `normalized_from`，不精确就失败。
   master 不归一化。显式 `--cell` 是预览探针，保留原生尺寸、不参与尺寸门禁。

## Workflow

### Step 0 — Intake before anything else

```bash
python3 scripts/brief.py --init -o build/              # 11-item intake form
python3 scripts/brief.py --demo -o build/              # filled demo build, physical goods
python3 scripts/brief.py --demo-finance -o build/      # filled demo build, 理财 / 保险
python3 scripts/brief.py build/brief.json              # validate → build/blueprint.draft.json
```

`--demo-finance` is the only way to exercise the disclosure band and the prohibited-claim
blocking without a client: it produces a `category: finance` brief with two risk lines, a
cut-off date and a fund app screen. Run it before claiming the financial path works.

Twelve items: ① 品类 (`physical` / `finance` / `insurance` / `service`) ② products (with asset
files — for a fund this is the app screen or the NAV chart) ③ 3–5 personas, each with a
**trigger moment** ④ 4–6 scenarios ⑤ launch rhythm ⑥ must-appear assets ⑦ forbidden claims
and competitor red lines ⑧ **platforms** (`xiaohongshu` / `xiaohongshu_long` / `long_image` /
`douyin` / `wechat_moments` / `weibo` / `official_account` / `taobao` / `print_backdrop`)
⑨ 披露要素（金融/保险：机构、资质、风险等级、数据截至日） ⑩ who signs off on facts
⑪ **基调** — Step 0.5，必须问出来，不许默认 ⑫ **key_facts** — 读者必须带走的可核验事实，
每条 `{id, text, kind, source}`，金融/保险的 `source` 必须 `client-confirmed:*`。

**Stop if 品类/产品/人群/场景 are incomplete.** A matrix cannot be built without them, and a guessed one
returns as a rework. `brief.py` exits non-zero, lists blocking gaps, and writes
`reports/brief_report.md` with a coverage grid showing which cells are still unwritten.
Missing `voice.tone` blocks too: a matrix built against a tone nobody agreed comes back as
a rewrite of all twelve plates. Missing `key_facts` also blocks: without a fact list there
is nothing to check a cell against, and twelve cells will say the same three things.

`blueprint.draft.json` is a scaffold, not a proposal: every `duty` and `caption` reads
`TODO` on purpose, `zones[].facts` is empty and `lint_copy.py` / `lint_density.py` will both
refuse it until a human writes them.

### Step 0.5 — 定基调：问，不要猜

写第一句 caption 之前，把这五个问题问出去，答案抄进 `brief.voice`。**不许**用"我先按平实
写、回头再调"代替提问——上一版就是这么做的：十二条单看都具体，标题、人群设定和正文却在
使劲，而管线里没有任何一步拦过它。

1. **这一次要什么语气？** 平实陈述 / 温和共情 / 紧迫提醒 / 专业说理 / 轻松调侃。金融与保险
   默认平实；客户要别的语气，就写明这句话是谁说的。
2. **谁在说话？** 第三人称白描（"她把挂号单捏在手里"）／第二人称对话（"你去挂一次号"）／
   第一人称自述（"我那天"）。人称不定，十二条各写各的。第一人称用于**虚构角色**是文案，
   用于**真人证言**是虚假广告。
3. **每条能接受几个煽情词？** 给一个数。plain / expert / 轻松必须是 **0**，温和与紧迫最多 1。
   `lint_copy.py` 会逐条点名，所以现在就要谈定，别等出图。
4. **全套允许几句金句？** 默认 1 句。每格都在用力等于没有重点。
5. **有没有一句"就是这个感觉"的样例？** 客户原话、竞品一句、你自己写的一句都行。没有样例，
   作者只能凭感觉写，这就是跑偏的定义。
6. **四格写故事，还是写规则？** `narrative`（这一格发生了什么）／`rule`（这一步按哪条算）。
   **保险与理财写 rule**：四格画的是挂号、缴费、取药、回家四个缴费节点，每格配的应该是
   这一步的算法与边界，不是人物的处境。写成了故事，四格就变成煽情的分镜。

```jsonc
"voice": { "tone": "plain", "pov": "第三人称白描", "caption_mode": "rule",
           "emotion_budget": 0, "punch_quota": 1, "banned_words": ["安心", "稳稳的幸福"],
           "sample": "单次免赔 100 元，给付上限 800 元，按余额 80%。",
           "body": "平台发布正文，同一套预算也管它" }
```

Gate 1 汇报时把这五个答案原样贴出来：客户看到自己选的那条基线，才会用同一把尺子看图。

### Step 1 — Write the cells

For each zone, in `blueprint.json`:

- `duty` — one sentence: what this panel must communicate. "她刚进门，手已经伸向台面",
  not "夜归场景". 在 rule 模式下，duty 保留**画面里正在发生什么**，caption 换成**这一步的规则**——
  两者分工，不要用 caption 去描述画。
- `caption` — the single line a reader sees, ≤ the plate's capacity (printed by
  `lint_copy.py`). Write it as a writer, then cut it as an editor. `caption_mode: "rule"`
  时它是一句规则：这一格产生什么费用、按哪条算、到哪为止，且必须能指回条款原文。
- `caption_source` — where that line comes from. Prices, dates and specs must be
  `client-confirmed:*`; in rule mode **every** caption must be `client-confirmed:*`.
- `slots` — which asset, where (`box` normalised **inside this cell**), on what `surface`.
- `facts` — ids of `meta.key_facts` this cell **adds**. At least one must not appear in any
  earlier cell; a restatement does not count as information. This is what the picture and
  the caption are both accountable to.
- `tile_origin` — `ai` / `code_card` / `evidence` / `chart`. A `code_card` with no
  number / condition / boundary / evidence fact is an empty card and is refused.

In `rule` mode, `duty` names the structure the reader should be able to compute with
(算式 / 对照 / 区间 / 清单 / 证据卡), not "a pile of blank paper". Load
`references/rule-visual.md` before writing it, and `references/blueprint-schema.md`
for the exact contract.

### Step 2 — Assets in, before any generation

```bash
python3 scripts/assets.py build/blueprint.json
```

Checks transparency (a white-background PNG is not a cut-out), corner alpha, minimum edge
per class, and whether the subject fills its canvas. Failures are blocking: the fix is a
better file from the client, never a generated substitute.

### Step 3 — Copy: voice first, then measurement

```bash
python3 scripts/lint_copy.py build/blueprint.json -o build/reports/copy_sheet.md
```

Three passes in one run, and the order matters:

1. **Tone** — `meta.voice` 有没有登记？每条 caption 的煽情词在不在 `emotion_budget` 里？
   标题、人群设定、正文（`voice.body`）也一起盘：板上克制、标题使劲，读者只记住后者。
   「病痛 + 深夜/拖延」同句算苦情取材，平实基线下列为硬错误。台账在 `copy_sheet.md` 顶部。
2. **Trace** — 没有 `caption_source` 的句子是硬错误。价格、日期、规格必须是 `client-confirmed`。
3. **Voice** — 脚本能数出来的，按 `caption_mode` 换口径：叙述模式数具体物件覆盖率
   （**<50% 阻断、<66% 警告**）；规则模式数**规则要素**（数字 / 条款要素 / 计量单位 / 条件），
   并要求每条 caption 的 source 是 `client-confirmed:*` —— 图上每一条规则都要能在条款里
   找到原文，否则就是替保险产品立规。两种模式都数对偶句、格言腔、抽象名词、同构开头、
   内容字复读。**它数不出好句子，只能数出坏句子的形状。** 真正的改写要在写的时候就完成：
   load `references/copy-voice.md`，叙述走"删判断 → 换动作 → 补物件 → 压字数"，
   规则走"这一步产生什么费用 → 按哪条算 → 边界在哪"。
4. **Measure** — 字数对板子真实容量、半角标点、括号配对。

一个诚实的分工：脚本负责阻止**空句子**和**跑偏的语气**上线，人负责让句子**值得印**。第一版
十二条里九条没有一件东西，脚本会拦住它；但把「先稳住，再谈别的」改成「台灯下压着一张存单，
折了角」这件事，脚本做不了。

The sheet ends with seven questions a script cannot answer — read them.

### Step 3.5 — Density: what does the reader actually take away

```bash
python3 scripts/lint_density.py build/blueprint.json -o build/reports/density_sheet.md
```

Copy is toned and traced; this pass asks a different question. `lint_copy.py` can approve
twelve perfectly sourced sentences on twelve pictures that say nothing. `lint_density.py`
reads `meta.key_facts` and counts:

| check | default | why |
|---|---|---|
| 每格新增事实 | ≥ 1 | 空格子不给它编，也不许靠 caption 撑着 |
| 每个投放页新信息单元 | ≥ 6（封面 3 / 落版 4） | 4 格页只印 4 句就是「有效信息少」 |
| 事实复述率 | ≤ 30% | 同一条规则换个格子说一遍不是新信息 |
| 信息面积比 | ≥ 18% | 承载新事实的矩形太少，图上就是空 |
| `code_card` / `evidence` / `chart` | 至少一条数字/条件/边界/原文事实 | 空白几何卡硬拦 |

面积比只算说明板、信息卡与证据贴图；标题、页码、列标题、人群条、披露带是结构开销，
不算信息——把它们算进去，正是空海报看起来很满的原因。阈值集中在
`promo_layout.DENSITY_LIMITS`，可用 `meta.density_limits` 按稿覆盖。`--no-area` 只用于
管线连通性测试。

`density_sheet.md` 顶部是总账，后面是逐页增量、逐格新增事实与完整事实清单。Gate 1
要**原样贴出**，让人逐条核对来源。

### Step 4 — Gate 1: content list

Present in plain language: the matrix (which persona × scenario, what each cell says), the
persona definitions with their trigger moments, the timeline phases, the asset list with
which cells carry a product, the empty cells and why, `copy_sheet.md` and
`density_sheet.md` verbatim, **and a "读者拿走什么" table** (页 / 格 / 这一格新增了哪条事实 /
出处 / 是不是复述). Two sheets and no table is not a Gate 1: a matrix of well-sourced
sentences can still leave the reader with nothing. Get confirmation before drawing anything.

### Step 5 — Gate 2: skeleton, every target

```bash
python3 scripts/skeleton.py build/blueprint.json -o build/skeleton.png --targets
```

Flat diagram at zero cost: header, timeline spine, column headers, persona strips, every
cell with its `duty`, caption plates, asset slots, and the dashed **platform safe area**.

`--targets` renders every channel deliverable too — including **every carousel page
separately**, because a page that only works after the previous one dies the moment somebody
screenshots it. Each target prints its letterbox percentage; anything over 18% means the
layout does not fit that channel. A `long` target prints its 分栏 shape as well: check that
each persona's cells form one block and that the top first-screen already says what this is.

Exit non-zero lists geometric failures: caption over capacity, slot out of bounds, two
slots overlapping, a `face_allowed` cell with nobody in it, a home cell not in column 1.

### Step 6 — Gate 3: one zone, full resolution

Generate the most representative cell (usually the first home cell) at the model's maximum
square resolution, then:

```bash
python3 scripts/finalize.py gen/raw.png -o build/tiles/z_r1c1.png --cell 2048 \
    --wm 880,946,1024,1024
python3 scripts/stitch.py build/blueprint.json -d build/tiles -o build/proof.png \
    --allow-partial
```

Judge three things and stop: **does the style match the preset**, **is the slot still
empty**, **is the subject inside the central 60%** (a tall derivative will crop the sides).
Wrong style means fixing the style block and regenerating this one cell — never "continuing
and seeing".

### Step 7 — Generate the rest

One image per cell, `build/tiles/<zone_id>.png`, at max resolution. Every returned tile
goes through `finalize.py` for watermark removal and cell fit; it reports `upscaled` when a
tile is smaller than the cell, and an upscaled tile is a declared downgrade, not a habit.

Prompt per cell follows `references/cartoon-style.md` — the block order is weight, and the
`[SLOT]` sentence is what keeps the table empty. In `rule` mode the `[DATA-SLOT]` sentence
keeps the number plate empty too: the model draws the surface, code prints the client's
figures (`references/rule-visual.md`).

When the brief pays for fewer illustrations than cells, this is a declared choice, not a
scramble. Mark those cells `tile_origin: code_card`, give each one its `facts`, then:

```bash
python3 scripts/make_rule_card.py build/blueprint.json -d build/tiles
```

It prints the caption plus up to three sourced facts on its own plate. It refuses a cell
with no facts rather than drawing a blank slip. Do not write a one-off geometry script —
that is exactly what produced the eight empty cards in v1.1.1.

### Step 8 — Audit, then stitch

```bash
python3 scripts/audit_assets.py build/blueprint.json -d build/tiles --init
python3 scripts/audit_assets.py build/blueprint.json -d build/tiles --sheet
```

Look at every tile (full frame, plus each dark corner brightened 2–3×) and fill
`build/tiles/audit.json` per cell: `figures` (who is in it), `slots` (`slot_clean`: did the
model draw something in the reserved area), `axes` (**intent / plausibility / taste /
information**), and `sentence` — one line about what is actually on screen. The fourth
axis exists because three style axes all pass on a picture of blank paper. For a
`code_card` / `evidence` / `chart` cell, `sentence` must name a number or a clause element;
"两张空白登记票据" is not evidence that anything was said.

The script refuses: a cell with no record, a record whose hash no longer matches, a readable
face with no character, a face in a cell designed to be faceless, an unjudged slot, an empty
sentence, an information card with no facts. **Fixing means regenerating that cell, not
editing the record.**

```bash
python3 scripts/stitch.py build/blueprint.json -d build/tiles -o build/atlas.png
python3 scripts/stitch.py build/blueprint.json -d build/tiles -o build/atlas.png --target all
python3 scripts/stitch.py build/blueprint.json -d build/tiles -o build/atlas.png --target all --strict-info
```

`--strict-info` fails the build when a tile **file exists but carries no information** —
blank pixels, or a declared card with no facts. Without it `stitch_report.json` still lists
`blank_tile` / `low_information` per target; a delivery should always be run with the flag.
Read that report for missing tiles, unresolved assets, letterbox percentages per target.
Ship nothing with a missing tile or an unaccounted blank one. On a cover, also read
`facts_declared` / `facts_printed`: the density ledger counts declared facts, so a number
that never made it onto the plate fails the build rather than quietly contradicting the
takeaway.

A delivery run **does not pass `--cell`**. Without it, every platform-bound output is
normalized to the channel's exact pixels before saving (rule 19); `platform_px`,
`size_exact` and `normalized_from` in the report are the proof. A reflow that only
letterboxes lands a few pixels off-width — check `size_exact` for every page, and treat
`false` as a failed build. `--cell` is for probes and previews: those keep their native
size and are not delivery artefacts.

### Step 9 — Deliver

The master (internal), and per platform: the carousel pages or the single frame or **the long
image**, at the platform's real pixel size, with the safe band respected. Then one paragraph:
what it says, which cells are empty and why, which claims came from the client's own material,
and who signed off the facts. State the tone that was agreed and whether the copy stayed inside
it. For a financial product, also state which pages carry the disclosure and confirm the
figures' cut-off date.

When the brief has a long image, deliver it **in addition to** the carousel, not instead: the
carousel is what people swipe through, the long image is what they save. Check its actual size
on a phone before shipping — a 1:4 file is ~5,000px tall and the top quarter is all the feed
shows until someone taps.

Attach `copy_sheet.md`, `density_sheet.md` and `reports/assets.json` — the answers to
"where did this number come from", "what did each page actually add" and "who decided it
should sound like this", three weeks from now.

## Environment

Python 3 + Pillow. A CJK font is required (PingFang, Hiragino Sans GB, Noto Sans CJK, or
msyh); the scripts fall back down that list.

```bash
python3 -m pip install pillow
```

No other dependency. `brief.py`, `assets.py`, `lint_copy.py` and `skeleton.py` run without
any generated image or network access.

### Smoke test

```bash
bash tests/smoke.sh          # 48 assertions, ~25 s: intake → tone → copy → density → skeleton → stitch → px → cover facts → audit
KEEP=1 bash tests/smoke.sh   # keep the temp build dir and print its path
```

Run it after touching any script. It synthesizes flat grey tiles on purpose: it tests
plumbing — paths, exit codes, geometry, channel reflow, the tone / caption-mode gate, the long-image cap —
not picture quality. Keep `CELL` at 512 or above; below that the disclosure band genuinely
cannot fit a page and stitch correctly fails.

## References

- `references/blueprint-schema.md` — the exact JSON contract, coordinate system, target
  types (including `long`), the tone contract, and the field rules the scripts enforce.
  Load when writing or debugging a blueprint.
- `references/cartoon-style.md` — style presets, the prompt block order, the `[SLOT]`
  sentence, cast rules for face vs figure cells, crop safety, the six failures the model
  repeats, and what a financial product may not depict. Load before writing any zone prompt.
- `references/copy-voice.md` — §0 the tone register (five questions, five baselines, the
  煽情 blacklist and the 苦情取材 failure), then plate-scale copy: the six failures that only
  exist at 12–18 characters, the countable metric (concrete-object coverage: below 50% blocks,
  below 66% warns), the rewrite order, and a worked rewrite of twelve real captions. Load
  before writing any caption.
- `references/social-channels.md` — platform sizes, safe areas and what eats them, page
  limits, carousel page structure, and per-channel copy length. Load when choosing targets or
  when a delivery looks empty.
- `references/rule-visual.md` — v1.2. Rule-mode visual grammar (算式 / 对照 / 区间 / 清单 /
  证据卡), the `[DATA-SLOT]` contract, what a financial picture may and may not print, and
  the `tile_origin` table. Load before writing any `duty` in `rule` mode.

Scripts: `promo_common.py` (geometry, plates, asset paste, shadow) · `promo_layout.py`
(layout resolution, geometry checks, `DENSITY_LIMITS`, target reflow) · `brief.py` (Step 0
intake, 12 items) · `assets.py` (asset gate) · `lint_copy.py` (copy review) ·
`lint_density.py` (Step 3.5 information gate, `density_sheet.md`) ·
`make_rule_card.py` (code-drawn rule cards from `key_facts`) · `skeleton.py` (Gate 2) ·
`finalize.py` (tile intake) · `audit_assets.py` (four-axis cast/slot/tile audit) ·
`stitch.py` (render, one code path for skeleton and delivery, `--strict-info`) ·
`references/social-channels.md` table mirrored in `promo_layout.PLATFORMS`.

## Provenance

The build discipline — three gates, geometry-first blueprint, code-composited text, tiered
cast with caps, hash-bound review — is taken from `novel-atlas`. Three things were removed
because a campaign has no book to read (`normalize.py`, `chunk.py`, `stats.py`, `anchor.py`
avatar crops) and four were added because a campaign has a client: the intake gate, the
asset slot, the traceability check, and channel reflow.

## 变更记录

**1.2.1** — 1.2.0 返工重出后逐张核对交付尺寸，发现同一次上传里封面 `1242×1656`、
内页 `1256×1675`、长图 `1259×5036`。根因是 `pad_to_ratio` 只会补边不会缩小，而
`PLATFORMS["xiaohongshu"].px` 写的是 `1242×1660`，与自己的 `3:4` 相差 4px。

- **平台像素归一化**（规则 19 / `stitch.py: platform_px` / `normalize_to_platform`）：
  宽取平台表，高由 ratio 反推，出图后一次 LANCZOS 落到精确像素；`stitch_report.json`
  增 `platform_px` / `size_exact` / `normalized_from`，不精确即 `exit 1`。master 不动，
  显式 `--cell` 的预览探针不参与。
- **平台表与文档对齐**：小红书 `1242×1660` → `1242×1656`，`social-channels.md` 同步，
  docs↔code parity 检查继续覆盖。
- **封面关键数字不再被静默裁掉**：`_draw_fact_band` 原写死「最多两行」，4 条中文事实
  只印出 3 条，而 `takeaway` 还写着「四个数字」、`density_sheet.md` 还记着 `4/3 ok`。
  现在事实板按实际行数长高（hero 让出高度），`stitch_report.json` 记
  `facts_declared` / `facts_printed` / `facts_clipped`，声明数 ≠ 印出数直接失败。
  这类「台账说有、画面没有」的脱节与 1.1.1 的空白卡同源，所以按硬门禁处理。
- **清理** `tile_is_blank()` 的 Pillow `getdata` 弃用告警，改用 `tobytes()` 切像素。
- 冒烟新增 row 6d（尺寸契约）与 6e（封面事实不截断，含长中文正例与无效 id 反例），
  43 → 48 项。
- 未动：信息密度门禁、rule 视觉语法、金融/保险硬拦截与披露带、溯源与基调登记、
  caption 字数上限、矩阵结构（阶段三 `rulebook` 仍待真实投放后再定）。

**1.2.0** — 一次交付复审问「这张图为什么有效信息那么少」。答案是所有门禁都在查
「不出错」，没有一条在查「说了什么」：十二格里八格是代码画的空白纸片，`stitch.py`
因为文件存在报 `placeholder: 0`，逐格审计三轴全 pass，最终 5 页轮播只有 12 句短规则。

- **信息密度门禁**（规则 17 / 第 12 项采集 / `meta.key_facts` / `zones[].facts` /
  `tile_origin` / `lint_density.py` / `density_sheet.md`）。逐格、逐页、按面积比三处核账；
  空白卡、复述、没有关键数字的封面都阻断。Gate 1 增加「读者拿走什么」表。
- **`placeholder` 不再等于「有文件」**（`stitch.py`）：拆成 `missing` / `blank_tile` /
  `low_information`，新增 `--strict-info`；`audit_assets.py` 加第四轴 `information`，
  信息卡的画面描述必须点名数字或条款要素。
- **rule 模式补视觉语法**（规则 18 / `rule-visual.md` / `[DATA-SLOT]`）。1.1.1 把文案
  改成规则解读却没改「画什么」，于是合规画法退化成空白纸片。现在 `no invented numbers`
  管模型编数字，客户确认的数字由代码印；插画数少于格数时走内置 `make_rule_card.py`。
- **首屏与封面真的带信息**：封面印 `pages[].facts` 的关键数字与 `takeaway`；长图
  `first_screen` 把结论、三条数字和一行披露放进信息流只露出的顶部 1/4。
- 未动：矩阵结构本身（`rulebook` 版式仍在阶段三，待一次真实投放后再定）、
  收益承诺硬拦截、溯源与基调登记、caption 字数上限。

**1.1.1** — 一次真实复审把「基调」这条规则又推进了一层：

- **文案模式**（`voice.caption_mode`：`narrative` / `rule`）。四格漫画画的是四个缴费节点，
  每格配的应该是这一步怎么算，不是人物多不容易。`rule` 模式下 lint 换口径：不数具体物件，
  数规则要素（数字 / 条款要素 / 计量单位 / 条件），并要求每条 caption 都
  `client-confirmed:*`——图上每条规则都要能在条款里找到原文。保险与理财不写 rule 只提醒，
  写错（叙述文案放进 rule 模式）直接阻断。

**1.1.0** — 两次真实投放暴露的问题，各补一条硬规则：

- **基调**（规则 15 / Step 0.5 / `voice` 合同 / `lint_copy` 基调台账）。上一版门急诊医疗险
  的稿子十二条 caption 具体物件覆盖率 100%、脚本零硬错误，客户仍判定"太煽情"：三个普通人
  都被安排在最惨的一晚，标题和正文在求同情，而管线里没有任何一步问过基调。现在
  `brief.voice.tone` 缺失即阻断，caption 超预算按基线判定阻断/提醒，标题、人群设定、正文
  一并盘账，`病痛 + 深夜/拖延` 同句列为苦情取材。
- **长图**（规则 16 / `xiaohongshu_long` 与 `long_image` / `type: "long"`）。比例上限 1:4
  由 `LONG_MAX_ASPECT` 强制；分栏只能取场景数的约数，人群按块完整落下；每块第一格带人群
  色条。上一版把 3:4 轮播当成了唯一形态，而读者实际是在长图上收藏和转发的。
- **修掉 `make_grid` 的披露重试分支**（`apply_safe(build, safe, ftr)` → `TypeError`）。
  那段代码只在版面真的装不下披露时才执行，所以一直没被触发；小格子或长披露一出现就崩。

**1.0.2** — 首版：三闸门、资产槽位、溯源、渠道重排、金融披露带。
