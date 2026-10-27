---
name: xhs-story
description: Turn a real "idea → shipped" process into a Xiaohongshu (小红书 / rednote) image carousel -- 7 pages at 1242x1660 plus a paste-ready caption -- structured as 起承转合. Reads WorkBuddy session transcripts to recover what actually happened (tool calls, failures, retries, the moment the question changed), and also accepts dictation or local documents as source material. All Chinese text is rendered by CSS + headless Chrome, never by an image model. Use when the user wants to post a session to 小红书, write a build log as social content, explain how an idea was shipped with WorkBuddy, or says 做个小红书图文.
description_zh: "把一个「想法→落地」的真实过程,按起承转合编排成小红书图文(7张3:4图 + 可直接粘贴的文案)"
description_en: "Turn a real build process into a 起承转合 Xiaohongshu image carousel with paste-ready caption"
version: 1.0.0
allowed-tools: Read,Write,Edit,Bash,Glob,Grep,ViewImage
---

# 小红书图文故事工坊

把一段「想法 → 落地」的真实过程，压成 7 张 3:4 竖图和一段能直接粘贴的文案。

小红书上这类内容九成是通稿：「我用 AI 做了个网站，效率提升 300%」。读者不傻，一眼过。能跑出来的只有一种：**有具体动作、有真实卡点、有一个说得清的反转**。这个 skill 的存在意义就是把这三样从真实素材里挖出来，而不是替用户编出来。

## 产出契约

```
./xhs-<slug>/
  storyboard.md      每页的文字 + 视觉指令 + 情绪落点（闸门用）
  pages.json         渲染输入，可手改后重拍
  pages/01.png …     成品，1242×1660
  caption.md         标题 + 正文 + 话题，可直接全选粘贴
  assets/            真截图 / AI 底图
  contact-sheet.png  七页拼版，一眼看整体节奏
```

---

## 四条铁律

**1. 中文一律代码渲染。** 图片模型写中文必然崩——错字、缺笔、乱码。所有可见文字走 `scripts/render.py`（CSS + headless Chrome），一个字节都不交给生成模型。需要 AI 生成的是**底图**，且必须是无字画面。

**2. 真转优先，允许降级，不许编造。**
判据很硬：素材里能不能**指认出**「哪一句提问变了、方案就变了」的时刻。能→认知反转；不能→降级为数字对比；再不能→换清单体。**永远不要加一句「我终于明白……」。** 读者对假顿悟的识别率极高，一句就废。

**3. 缺料不注水，文末认账。** 不做素材体检，不拦着用户，但素材不够时不许拿「效率提升 300%」填坑。体例照常走起承转合，在尾页加一句诚实的注脚：`目前跑到这一步` / `还没上线，但骨架通了`。

**4. 合那一页必须能验真。** 真做过网站就放真截图，做过文档就放打开的文件截图。**绝不用 AI 效果图冒充产出。** 这是全篇唯一无法伪造的证据。

---

## 素材分级

按保真度从高到低，每次交付都要在 storyboard.md 顶部标注这次用的是哪一级：

| 级 | 来源 | 能拿到什么 |
|---|---|---|
| **L1 可回溯** | 会话 transcript（`.jsonl`） | 每次工具调用、每个报错、每次被问到选择、真实时长 |
| **L2 上下文** | 当前对话记忆 | 主干，但长会话被压缩后细节会丢 |
| **L3 口述** | 用户补充 | 情绪落点、当时怎么想的 |
| **L4 文档** | 本地 md/代码/笔记 | 结论，通常没有过程 |

L1 的独家价值：**失败与反复**。这是「承」和「转」唯一的来源。读法是看两件事——工具报错了几次、用户被问到选择了几次。一项都没有的会话，通常是顺风局，故事要按无转折的方式重写。

---

## 流程

### Step 0 · 定素材

```bash
# 当前/最近一次会话
python3 scripts/extract_session.py --latest --out xhs-<slug>/source.md

# 历史会话：先列出来挑
python3 scripts/extract_session.py --list
python3 scripts/extract_session.py --session <path.jsonl> --out ...

# 顺带扫敏感项
python3 scripts/extract_session.py --latest --scan
```

脚本输出的是**时间线**不是文章：每轮对话、每次工具调用、每次失败、落盘文件清单、被问到选择的次数。读它，不要读原始 jsonl。

会话里出现过的图片存在 `~/.workbuddy/blobs/`，transcript 的 `image_blob_ref.blob_path` 里有绝对路径——需要「合」页的真截图时先去那里翻，比重新截一次更真。

用户只给了口述或文档（L3/L4）时跳过这步，但在 storyboard 里标注级别。

### Step 1 · 抽零件

从素材里抽四样东西，写成 storyboard.md 的开头。抽不出来就写「缺」，别硬凑：

```markdown
素材级别：L1 可回溯（会话 13:19–14:02，24 次工具调用，2 次失败，8 次被追问）

- 起：<一句具体的、带动作的原始诉求>
- 承：<撞到的坎，以及你当时的预期错在哪>
- 转：<类型 A/B/C + 证据原文，能指认是哪一句>
- 合：<看得见的产出 + 文件路径或截图路径>
```

### Step 2 · 定形状，写 storyboard

默认七页，四段配比见下表。**改哪页都比改文案贵**，所以文字在这一步就定死。

| # | 段 | 页型 | 任务 |
|---|---|---|---|
| 1 | — | `cover` | 结果前置 + 反常识。标题 ≤ 20 字 |
| 2 | 起 | `statement` | 痛点钉在一个具体动作上 |
| 3 | 承 | `cards` | 卡点是什么（2–3 条，每条一句话） |
| 4 | 承 | `statement` 或 `quote` | 你为什么卡住——预期错在哪 |
| 5 | 转 | `quote`（认知）或 `ledger`（数字） | 全篇唯一的峰值，只放一句话 |
| 6 | 合 | `shot` | 真截图 + 一句说明 |
| 7 | — | `end` | 一句可截图带走的话 + 诚实注脚 |

页型速查：

| 页型 | 必填 | 用途 |
|---|---|---|
| `cover` | `title` `sub` `kicker` `badge` `bg?` | 首图。`bg` 可放无字 AI 底图 |
| `statement` | `title`（可含 `\n` 手动断行） `foot` | 单句重击，大量留白 |
| `cards` | `title` `cards[{n,t,d}]` | 清单/卡点，2–4 张 |
| `ledger` | `title` `rows[{k,v}]` `foot` | 前后对比，数字给大字号 |
| `quote` | `text` `by` | 引语，认知反转专用 |
| `shot` | `title` `img` `cap` | 真截图，`img` 相对 storyboard 所在目录 |
| `end` | `title` `sub` `cta` | 收尾 |

主题三选一（`pages.json` 的 `theme`）：`paper` 暖纸底适合过程记录，`ink` 深底适合思辨，`signal` 冷灰适合工具/数据。**按内容调性选，不要随机。**

### Step 3 · 闸门

写完 storyboard.md **停下来**，把七页的文字连同「转」用的是 A/B/C 哪一级一起给用户看。

- 用户点头 → Step 4
- 用户说「直接出」/「不用给我看」→ 跳过
- 用户改文案 → 只改 storyboard 和 pages.json，不重拍图

### Step 4 · 渲染

```bash
python3 scripts/render.py xhs-<slug>/pages.json -o xhs-<slug>/pages --sheet
```

首行会打印成功张数与失败页号。`--sheet` 生成 `contact-sheet.png`，先看拼版再看单页——**节奏问题只能在拼版上看出来**（比如三页都是大段文字，或者两页都是清单）。

只改了某几页：

```bash
python3 scripts/render.py pages.json -o pages --only 3,5
```

渲染完**必须逐页看一遍**（至少看拼版 + 第 1 页 + 第 5 页）。文字溢出、孤字成行、字号过小，脚本不报警，眼睛才看得见。

改了文字就重拍，不要迁就旧图。

### Step 5 · 文案

写 `caption.md`，格式见 `references/voice.md`。三件事必须做到：

1. **标题 ≤ 20 字**，钩子在前 20 字内说完。
2. **正文前三行**是钩子，不是背景介绍。首屏只露三行。
3. **备选标题给 2 条**，用户发布前八成会想换。

写完过一遍 AI 味黑名单（`references/voice.md` 第三节）。出现两条以上直接重写。

### Step 6 · 交付

```bash
python3 scripts/render.py --check     # 确认 Chrome 可用
```

交付时报告四件事：产物路径、用的哪级素材、转的类型（A 认知 / B 数字 / C 关系）、脱敏替换清单。

用 `present_files` 把 `contact-sheet.png` 和 `pages/01.png` 放最前——用户第一眼要看的是整体和封面。

---

## 脱敏

默认保守：只换硬敏感项（绝对路径、邮箱、密钥、内网地址、他人姓名），保留项目名和工作内容。

**渲染前把替换清单给用户过一眼**，不要静默改。用户有权知道哪几个字被吃掉了。细则见 `references/voice.md` 第四节。

---

## 失败处理

| 情况 | 怎么办 |
|---|---|
| `render.py` 找不到 Chrome | 装 Chrome/Edge/Chromium；或改用 PIL 直绘并在交付里说明质感会降级 |
| 某页渲染失败 | 读脚本打印的 stderr；多半是 `pages.json` 的 JSON 语法或未知页型 |
| 文字溢出画面 | 缩短文字。**不要**靠调小字号硬塞，14px 字在小红书上等于没写 |
| 找不到真截图 | 用 `shot` 页的空态（虚线占位），在 caption 里说明「截图待补」；不要换 AI 效果图 |
| 素材是 L3/L4，没有过程 | 换清单体（`references/story-shapes.md` 末节），别硬套起承转合 |

---

## 参考

- `references/pages.example.json` — 七页骨架，复制改造比从零写快
- `references/story-shapes.md` — 起承转合怎么映射、真转的三级判据、降级路径、七种死法
- `references/voice.md` — 平台硬规范、违禁词、AI 味黑名单、脱敏细则、caption 格式
