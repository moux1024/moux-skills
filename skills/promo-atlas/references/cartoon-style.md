# Cartoon style — presets, prompt blocks, and the rules that keep it from going generic

The image model draws place, people, animals and light. It does not draw the product, the
logo, the mascot, or any text. Those arrive as files and are composited by code.

## Presets

| preset | medium | line | shadow | reads at 25% zoom | notes |
|---|---|---|---|---|---|
| `cartoon_flat` | 平涂色块 + 均匀描边 | 4–6px @2048, 深色但非纯黑 | 硬边椭圆或斜投影，无渐变 | 好 | 默认。印刷/背板/电商通用 |
| `paper_cut` | 纸片层叠，边缘有纸厚 | 无描边，靠投影分层 | 每层一层硬投影，方向一致 | 中 | 需要 `[SET]` 用纸的语汇重写场景 |
| `clay_toy` | 黏土/软陶质感，圆润体积 | 无描边，靠明暗 | 柔和但有明确接触阴影 | 中 | 产品贴图最易融合，也最容易显得廉价 |

`cartoon_flat` is the default because it survives both viewing distances this poster is
built for: a 3m backboard and a 800px product listing.

**Readability compensation** — copy the relevant line into every zone prompt:

- `cartoon_flat`: "flat fills only, one dark outline of even weight, no gradients inside
  shapes, no rendered texture, at most three values per object"
- `paper_cut`: "every element is a cut paper piece with a visible paper edge, layered
  with a single hard shadow direction, no smooth blending anywhere"
- `clay_toy`: "matte clay surface, visible thumb marks, soft but directional contact
  shadow, no glossy highlights, no metal reflections"

## The prompt block, verbatim order

A zone prompt goes to a model that sees nothing else. Order is weight.

```
[STYLE]        — the preset block, first, copied verbatim
[DUTY]         — the one thing this panel must communicate, one sentence
[SET]          — the place, in the preset's own material vocabulary
[CAST]         — exactly how many figures, and what kind (face / figure / none)
[BODY]         — for a face cell: build, clothing, one specific object in hand
[FACE]         — "the face is drawn, eyes are two dots with brows, mouth a single stroke"
[SLOT]         — the reserved area: what surface it is, and that it stays empty
[DATA-SLOT]    — rule mode only: the number plate stays blank too; code prints the
                 client's figures there after the tile is accepted
[COMPOSITION]  — subject placement, and the band left for the caption plate
[CROP SAFETY]  — the centre 60% holds everything that matters
[FORBIDDEN]    — no text, no letters, no invented numbers, no logo, no product,
                 no watermark, no extra faces, no invented bystanders
```

`no invented numbers` is not the same as `no numbers`. v1.1.1 printed the latter and the
only compliant picture left was a blank slip; `rule` mode then had nothing to illustrate.
The model may not *supply* a figure, but a figure supplied by the client is a fact and
belongs on the image. See `rule-visual.md` for the `[DATA-SLOT]` contract.

### `[SLOT]` is the block that protects the product

Every `asset_slot` in the blueprint becomes one sentence:

> *"A bare wooden countertop occupies the lower third, empty and evenly lit; nothing
> stands on it, no bottle, no cup, no appliance — the space is reserved."*

Without that sentence the model fills the table, and the pasted product lands on top of
drawn objects. This is the single most common failure in this skill, and it is a prompt
problem, not a compositing problem.

**Allowed surfaces** (`slots[].surface`): `table` `counter` `shelf` `display_plinth`
`palm` `frame_window` `shop_window` `floor_mat` `open_palm_of_hand`. Anything else and
the shadow has nowhere to attach.

### `[CROP SAFETY]` exists because cells are not always square

A 9:16 target stretches cells to as much as 1.55× height, and the artwork is generated
square and cover-cropped — up to 35% of the width is cut. Every prompt must therefore say:

> *"Everything that matters sits inside the central 60% of the width; the outer 20% on
> each side carries only background."*

## Casting: face cells vs figure cells

| cell | `face_allowed` | what may appear | why |
|---|---|---|---|
| home (column 1) | `true` | one named character, full body, face drawn | 一人一身，定妆照只有一张 |
| all other cells | `false` | back view, side silhouette, hands, a shoulder — **no readable face** | 脸不出现，就没有"长得不一样"的问题 |

This is the cheapest consistency guarantee in the whole build: 3–5 personas need 3–5
faces, not 12–30. The audit step fails a figure cell that contains a readable face, so the
rule is enforced against the pixels rather than against good intentions.

**Animals.** A mascot or an animal persona is a character with a written personality —
`species`, and one habit in `design` ("总是把杯子推到自己这边"). It is not decoration. An
animal that exists only to be cute will be drawn as a sticker, and a sticker cannot carry
a row of the matrix.

## What the model gets wrong, every time

| symptom | cause | fix |
|---|---|---|
| 一张桌面上出现了画好的杯子，产品贴上去后两个杯子 | `[SLOT]` 没写或太软 | 在 `[SLOT]` 里点名禁止具体物件，不只是"空" |
| 平涂风里出现渐变和高光 | `[STYLE]` 被后面的描述冲淡 | 把 readability compensation 放在 prompt 末尾再写一遍 |
| 每格的人长得都不一样 | 在 figure 格里给了脸 | 删掉脸，只留背影/手 |
| 场景里多出三四个路人 | 没有 `[CAST]` 数量上限 | "exactly one figure, no other person visible" |
| 产品被模型"预演"了一遍 | 提示词里写了产品名 | 提示词里不出现产品名，只出现承载面 |
| 竖版切片里人被切掉半个身子 | 没有 crop safety | 主体收进中央 60% 宽度 |

## Five questions before a tile is accepted

1. 这一格画的是 `duty` 说的那件事，还是"同题材的随便一张"？
2. 画面里每一张能辨认的脸，都是 `cast` 里有的人吗？
3. 贴图位那块区域，模型有没有自己画东西进去？
4. 如果这一格会被裁成 1:1.55，主体还在吗？
5. 风格、光向、材质，和样张那一格是同一套吗？


## Financial and insurance products

A fund has no pack shot, and the things that stand in for one are **screenshots**: the app
purchase screen, the NAV chart, the policy summary. They are `kind: "ui"` / `"chart"` in the
asset list, they are pasted as rectangles with a frame and no shadow, and the model never
draws them.

What the model must not draw, in this category more than any other:

| 禁止 | 为什么 |
|---|---|
| 钞票雨、金币堆、钱包装满 | 让读者以为收益是赠品 |
| 一路上扬的箭头 / 火箭 / 陡峭曲线 | 暗示只涨不跌，属于收益预测 |
| 老人独自在家数钱、孩子举着存钱罐 | 用弱势人群暗示刚兑 |
| 模型自己编出数字的纸片、报表、屏幕 | 模型会编出不存在的数据，而数字只能来自客户；客户确认的数字由 `[DATA-SLOT]` 代码印上，不在此禁 |

The cartoon style is still allowed to be warm — a person at a desk at night, a phone face
up on a table, a calendar with one date circled. That is the whole visual language of this
category: **the ordinary moment when the decision gets made**, not the payout after it.

For insurance, the same rule with one addition: never depict a medical event, a diagnosis,
or a payout scene. Show the paperwork, the conversation, the wait — not the claim.

That is a ban on **events**, not on information. A rule-mode insurance cell is allowed —
expected — to be an 算式 / 对照 / 区间 / 条款原文卡 with the client's own figures on it.
The whole visual grammar is in `rule-visual.md`; a cell that shows paperwork and nothing
else is the v1.1.1 failure, not the compliant answer.
