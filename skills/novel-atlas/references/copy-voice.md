# Copy voice

The atlas is read in five to twenty characters at a time. A reader at fit-to-screen sees twelve zone names, twelve captions and forty event labels — that is the whole editorial voice of the book, and it arrives without a paragraph around it to carry the tone. Copy written by a model fails here in a specific, repeatable way: not dull, but *recognisable*. It sounds like an atlas, and every caption sounds like the same atlas.

This page is how the copy gets written so it does not. It assumes the `humanizer-zh` skill is installed (`~/.workbuddy/skills/humanizer-zh/`); that skill is the general edit pass, this page is what survives at plate scale.

## What you are writing

| surface | length | grammar | what it must do |
|---|---|---|---|
| `meta.subtitle` | ≤ 20 字, 1 line | one clause, no数字并置 | the whole book in one breath — the only line that is allowed to be a thesis |
| `zones[].name` | 3–12 字 | 地名 · 年代 | locate, never narrate |
| `zones[].caption` | 9–19 字, ≤ 3 lines | one statement, one subject | name what is *in this panel*, present tense |
| `events[].label` | ≤ 14 字 | noun phrase or short clause | name one irreversible event, with its anchor |
| `zones[].labels` | ≤ 17 字, single line | two halves split by a wide space | locate the thing, then say the one fact about it |

There is no room for a transition, an aside, a qualification, or a sentence whose job is to introduce the next sentence. Anything you write that needs a second sentence to make sense is the wrong sentence.

## The nine patterns that actually bite

`humanizer-zh` carries 31 patterns for prose. At this size most of them cannot fire — there is no room for stacked qualifiers, no room for a paragraph that repeats its own opening. These nine do fire, and they fire on every build:

| humanizer | what it looks like on a plate | fix |
|---|---|---|
| §1 假对比 | 「不是称号，是出走」 — the negation corrects nothing the reader believed | drop the negation, keep the fact: 「朋友把国家拿走了，他去做刺客」 |
| §3 格言与伪深度 | 「它被造出来，只为把侠义一次钓干」 — reads like a line from a review, not a fact about the frame | say the mechanism: 「造它的用途：替人行使侠义」 |
| §7 句式开头复读 | six of twelve captions start with 「他」 | change the **subject**, not the sentence: 「她的颅骨里长着他」 |
| §12 AI 高频词 | 史诗 / 宿命 / 齿轮 / 洪流 / 见证 — a novel atlas attracts these more than any dashboard | replace with the thing itself or cut |
| §13 意义拔高 | 「人类挖开了一样不属于自己的东西」 — "不属于自己" is a mood, the frame contains a ship | name the object and its size |
| §15 句尾拔高 | 「…，彰显了秩序的脆弱」 | delete the tail, the fact survives without it |
| §29 四字排比 | 波澜壮阔 / 暗流涌动 / 命运齿轮 | one concrete noun beats four balanced characters |
| §30 万能背景 | 「随着技术发展…」 in a caption | cut to the subject |
| §31 套话收尾 | 副标题以「，和他的二百年」收尾 — a number pair plus 和他的, the single most recognisable AI poster subtitles | end on an action or a noun, not on a symmetry |

## The four things this format does that prose does not

These are not in `humanizer-zh`, because they are not article problems. They are atlas problems, and `lint_copy.py` counts the first two.

**1. 模板开头.** Four captions opening 「一个…的…」 is not repetition of *information*, so a duplicate check never sees it. `lint_copy.py` groups captions by their first two characters and warns at three. Vary the subject: a person, a place, a number, a bare object, a verb.

**2. 顿号清单.** 「武馆、黑帮、游骑兵，和一个只剩大脑的老侠客」. Three nouns and a 和 is how a model fills a caption it has nothing to say about. If the three things matter, they are labels, not a sentence. Keep the 顿号 only when the list is itself the finding (「护法 / 旗主 / 使臣 / 圣姑」 — four ranks in one panel is a fact).

**3. 对偶副标题.** 「一个人的十二具躯壳，和他的二百年」. Two numbers, a comma, 和他的. It scans as profound and says nothing the title does not. A human writes one clause with a verb in it.

**4. 抒情替代陈述.** The caption slot is the easiest place in the world to write how the panel feels instead of what it shows. The test is in `blueprint-schema.md` already and it is the only test that matters: **would this caption fit any other panel in the atlas?** 如果放得进任何一格，它就没说这一格。

## How to rewrite one caption

1. **Write down the fact first**, out of `duty` and the zone's events — not out of the picture. 「手术后第十一天他站起来」.
2. **Pick the subject.** A human, a thing, a number. Not 「他」 by reflex — check whether the previous zone already started with it.
3. **Say it as a person would say it out loud**, then delete what the picture already says.
4. **Count the characters.** The rewrite may not be longer than the original by more than two — the plate is measured from the string, and a caption that grows past its budget does not become better copy, it becomes a collision.

If after four steps the original is still the better sentence, keep the original. Not every line is broken, and a pass that touches all twelve is a pass that touched something it should not have.

## What you may not change

Names, the book title, chapter numbers, years, quantities, and the direction of causation. `humanizer-zh` puts this first for prose; here it is stricter, because every one of those is also a **lookup anchor** — a reader follows 「第 821 回」 back to the passage. A rewrite that shortens a label by dropping its chapter number has traded a verified plate for a prettier one.

You may not add detail either. If the caption needs a fact you do not have, it is not a copy problem — go back to the digest.

## Worked: the twelve captions of one real build

| zone | before | after | what changed |
|---|---|---|---|
| z1 | 人类挖开了一样不属于自己的东西 | 观测网先到，六个人两年后才下去 | 抒情 → 两个日期对应的两个动作 |
| z2 | 一个女孩的病毒撕开了各国共守的秘密 | 病毒是她写的，他们以为抓到了一台机器 | 模板开头 → 具体误解 |
| z3 | 他把瘫痪的人重新造成第一个基准人 | 瘫痪的人躺上手术台，十一天后站起来 | 主语从施术者换成被动者，画面即事实 |
| z4 | 他离开自己的公司，去当刺客 | 朋友把国家拿走了，他去做刺客 | 「离开公司」是过程，「拿走国家」是原因 |
| z5 | 他死在这里；看着他死的十三个人成了诸王 | 十三个人看着他死，然后分了天下 | 分号双句 → 一个因果 |
| z6 | 同一份记忆，十一具躯壳 | 十一具躯壳，互相指认对方不是自己 | 对偶 → 书里那句原话 |
| z7 | 他没有身体，长在别人的颅骨里 | 她的颅骨里长着他 | 换主语，从句变成画面 |
| z8 | 一个以「重新诞生」为教义的教会 | 他们求的是复活，向山是唯一的证据 | 定义 → 他们真正想要的东西 |
| z9 | 一个男孩从垃圾堆里刨出一颗还能转动的头 | 废铁堆里刨出一颗还在转的头 | 去掉「一个」和无主语的长定语 |
| z10 | 武馆、黑帮、游骑兵，和一个只剩大脑的老侠客 | 五座三千米的楼，底下是武馆街 | 顿号清单 → 尺度 + 一个地名 |
| z11 | 一个不是人的武神，被吊在自己的机体里 | 他们造它替人行侠，它先抬起了自己的手 | 状态 → 这一格真正发生的事 |
| z12 | 比赛没打完，假身份刚被看穿 | 他混进了总部，擂台那场还没打完 | 双短句并列 → 一前一后的两个现场 |

Twelve rewrites, eight subjects changed, zero facts added. The subtitle went from 「一个人的十二具躯壳，和他的二百年」 to 「一个人的记忆，抄了自己十一次」: same two facts, no symmetry, and a verb a model would not reach for.

## Before you hand the sheet to a reader

1. 把十二句并排读一遍——有没有四句同一个开头，同一副腔调？
2. 每一句能放进另一格吗？能，就重写。
3. 有没有一句在替读者下结论（「彰显」「见证」「宿命」）？
4. 字数有没有涨？涨了就回去删，别指望排版让路。

`lint_copy.py` catches the countable part of this — template openings, the 顿号 list, the high-frequency words, the 随着 opening, the slogan tail. It cannot hear tone. The four questions above are the part that stays human.
