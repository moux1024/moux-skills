# Rule visuals — what the picture does when the caption states a rule

`caption_mode: rule` landed in v1.1.1. It changed the words: a cell no longer describes
what is happening, it says how this step is calculated. Nothing changed in the picture
contract, so a clause-explainer build drew twelve pictures of blank paper and waited.
The copy and the image stopped talking to each other.

This file is the missing half. Read it before writing any `duty` in rule mode, and before
accepting a tile as a rule card.

## The one change to `duty`

| | narrative mode | rule mode |
|---|---|---|
| `duty` says | 这一格画了什么：她刚进门，手伸向台面 | **读者看完这一格应能说出什么**：医保结算后余额按 80% 算 |
| `caption` says | 画面里的一件东西 + 一个动作 | 这一步产生什么费用、按哪条算、到哪为止 |
| 画负责 | 让那一刻可认 | 让那条规则**可算** |

`duty` 在 rule 模式下不是分镜说明，是这一格的信息目标。写「桌面摊开一叠空白纸页」是
不可验收的：画出来了也没人能判断它对不对。写「能看出 800 元是上限、100 元是免赔」才
能验收。

## Six structures a rule cell can use

Pick one per cell and name it in `duty`. Two neighbouring cells should not use the same
one — that is the visual version of 同构开头复读。

| structure | 画什么 | 适合的条款 | 验收问句 |
|---|---|---|---|
| `算式` | 费用项 → 扣减 → 比例 → 上限，四个可数的框 | 80% / 40% / 免赔 / 限额 | 读者能自己算一遍吗 |
| `对照` | 左右两列，同一笔费用的两种走法 | 已获医保补偿 vs 未获补偿 | 两列差异是不是只有那个条件 |
| `流程分支` | 一个入口，两个带条件的出口 | 等待期 / 无等待期情形 | 每个出口都写了触发条件吗 |
| `区间` | 一条时间轴，圈出 30 日 / 60 日 / 1 年 | 等待期、重新投保、保险期间 | 起止点有数字吗 |
| `清单` | 并列 2–3 个勾选项，每项一个条件 | 一次就诊的认定、合理且必要 | 每项换成别的产品还成立吗 |
| `证据卡` | 条款原文截图 + 一处高亮，其余留白 | 免责、不保证续保、补偿原则 | 截图是不是客户原文件 |

**金融与保险优先用「算式 / 对照 / 区间」。** 它们是唯一能同时做到「讲了规则」和
「没有暗示收益」的三种。流程分支要小心：画成人物在两条路上犹豫，就又变成煽情分镜了。

## `[DATA-SLOT]` — numbers arrive as files and geometry, not as imagination

`[FORBIDDEN]` 里的 `no numbers` 从来不是说画面上不能出现数字，是说**模型不能编数字**。
v1.1.1 把它读成了前者，于是合规的唯一解法变成「什么都不印」。

正确分工：

1. 模型只画承载面（表格、卡片、票面、屏幕边框），照 `cartoon-style.md` 的 `[SLOT]`
   句式把数字区域留空。
2. 数字、单位、条款原文由代码从 `meta.key_facts` 印上去，或直接由
   `scripts/make_rule_card.py` 整张生成。它们带 `source`，且只能是
   `client-confirmed:*`。
3. 模型提示词里**不出现产品名、不出现任何数字**；出现一次，它就有机会自己补一个。

在 blueprint 里，这仍是 `slots` 机制，只是 `asset.kind` 新增 `fact_plate`：

```jsonc
"slots": [{ "asset": "f_calc_80", "box": [0.18, 0.30, 0.64, 0.42],
            "surface": "table", "shadow": "none" }]
```

`shadow: none` 是刻意的：数字板是印在纸上的，不是放在纸上的物体，硬投影会让读者以为
那是一张贴上去的照片。

### 合规边界不因此放松

| 允许画 | 仍然禁止 |
|---|---|
| 客户条款里的数字、费率、期限、比例 | 模型生成的任何数字、报表、屏幕读数 |
| 条件分支、边界线、勾选项 | 一路上扬的箭头、火箭、陡峭曲线 |
| 条款原文截图（未改字，可标注出处） | 钞票雨、金币堆、钱包装满 |
| 医疗流程里的票据、窗口、等待 | 诊疗、诊断、赔付场景、钱币 |
| 「不保本」「不保证续保」等免责原文 | 保本 / 保收益 / 确诊即赔 / 全额报销 |

数字印上去不改变它的性质：它仍是客户素材，仍要 `caption_source` 与 `key_facts[].source`，
仍要签字人确认。这一步不替任何人做合规判断。

## When there are fewer illustrations than cells

`tile_origin` 是合同的一部分，不是备注：

| value | 谁来画 | 要求 |
|---|---|---|
| `ai` | 图像模型 | `[SLOT]` / `[CROP SAFETY]` 齐全，`facts` 仍要声明 |
| `code_card` | `make_rule_card.py` | 至少一条 number/condition/boundary/evidence 类事实 |
| `evidence` | 客户截图 / 条款裁切 | 不可重绘、不可改字，`source` 指到原文件 |
| `chart` | 客户图表文件 | 数据截至日必须出现在同一页 |

「只出 4 张插画」是一个正常选择，不是要偷偷糊过 8 格。做法是给那 8 格标
`tile_origin: code_card`、补 `facts`，跑 `make_rule_card.py`。**不允许**自己写一个画空白
纸片的临时脚本——`lint_density.py` 会拦，`stitch.py --strict-info` 也会拦。

## Five questions before accepting a rule tile

1. 遮住 caption，只看画：能说出这一格按哪条算吗？
2. 画上的每个数字，都能指回 `meta.key_facts` 里的哪一条？
3. 这一格的结构，和它上下左右那格是同一个吗？
4. 有没有任何一个数字是模型画的？
5. 换成竞品的条款，这张卡还成立吗？成立就说明它没写这条规则。

## In the pipeline

Step 1 写 `duty` 时定结构 → Step 2 资产门禁（截图类）→ Step 3 文案 → Step 3.5
`lint_density.py` 验证 facts → Step 6 Gate 3 样张要验的是「数字有没有被印出来」而不只是
「风格对不对」→ Step 8 逐格审计的 `information` 轴要看画面描述里有没有数字或条款要素。
