# Context Budget

A novel is not one document to be read; it is one document to be read **three different ways**, and each way has its own length limit. Picking one number ("read the whole thing if it's under X") is how blueprints end up with confident claims about chapters nobody actually read.

## The window is not the budget

Two findings decide the arithmetic:

- **Effective context is 50–65% of the advertised window** (NVIDIA RULER, across 17 models). A model advertising 200k is reliable to roughly 100–130k tokens, and the deficit is not announced.
- **Accuracy degrades as input grows even when retrieval succeeds** (Chroma, *Context Rot*, 2025, 18 models). Fully-present information is still used worse in a long prompt than in a short one. Semantic tasks — "what did this change about him" — rot **earlier and steeper** than lexical ones.

So the working number is:

```
usable tokens = window × 0.5
usable chars  = usable tokens × chars_per_token        # Chinese ≈ 1.5 chars/token
```

A 200k window therefore reads about **150k characters** reliably. Not 300k. A 1M window reads about 500k — usable, but only if nothing in it is a needle you need to hit exactly.

`chars_per_token` is the one soft input. Chinese runs about 1–1.7 characters per token depending on the tokenizer's vocabulary; 1.5 is a deliberate middle. The number is exposed as `--chars-per-token`, and being wrong by 20% only shifts the chunk count by 20% — it never turns a `three_pass` book into a one-shot read, because the window multiple is an order of magnitude away.

`scripts/chunk.py` computes all of this from `chapters.json` and prints the numbers, so nobody has to do it in their head.

## Three readings, three budgets

| Reading | What it must produce | Budget | Why that number |
|---|---|---|---|
| **Whole-book pass** | the four structural features, the arc, the ending, how the twist was set up | ≤ usable chars (150k on a 200k window) | above this, mid-book detail is silently dropped |
| **Chunk extraction** | per chapter: who appeared, what changed irreversibly, two quotes | 15–25k chars (10–17k tokens) | small enough that recall is near-perfect, large enough to close a cause→act→consequence |
| **Assembly** | every digest in view, plus writing `blueprint.json` | ≤ 55% of usable | the blueprint itself needs room, and output competes with input |

Chunk size has hard floor and ceiling. Below ~8k chars you get "someone did something" with no consequence in the same block, and the digest loses causality. Above ~30k the model starts summarising the ends of its own chunk and skipping the middle.

## Work backwards from assembly

The constraint that actually binds is **not** how much the reader can read. It is how much digest the assembly call can hold:

```
chunks        = ceil(total_chars / chunk_chars)
digest_budget = assembly_budget / chunks          # chars allowed per chunk digest

digest_budget ≥ 600  and  total ≤ 4 × read budget   → two passes are enough
digest_budget < 500  or   total > 4 × read budget   → one more level: arc briefs
```

Two ceilings, two jobs. The digest floor keeps each chunk's digest informative; the 4× cap keeps the corpus comparable. Past roughly two dozen digests the assembly call stops comparing and starts skimming, and alias merging, event deduplication and timeline alignment are exactly the comparisons that die first — so a five-window book rolls up to arc briefs even when every digest could have had two thousand characters.

This is why chunk size is not taste. Make the chunks bigger and you make each digest richer but fewer; make them smaller and the digest corpus outgrows the assembly call. The digest has to hold events **with chapter numbers** and **quotes**, so below ~500 characters it becomes a plot-free blur.

`chunk.py` reports the verdict as `single_pass`, `two_pass` or `three_pass`, and never claims a mode that the arithmetic doesn't support.

## Never treat a volume as a reading unit

A volume is a *narrative* boundary, not a context boundary. Real numbers from a 3.1M-character, 1154-chapter web novel:

| Volume | chapters | chars | fits a 150k read? |
|---|---|---|---|
| 第一卷 | 1–80 | 275k | no |
| 第二卷 | 81–220 | 460k | no |
| 第三卷 | 221–357 | 453k | no |
| 第四卷 | 358–757 | 944k | no — 6× over |
| 第五卷 | 758–1000 | 537k | no |
| 第六卷 | 1001–1154 | 437k | no |

Every volume overruns the budget; the largest is six times it. "One call per volume" would read 944k characters into a 150k budget and produce a confident, invented summary of the second half. Arcs must be cut **by budget**, then nudged to the nearest volume edge — not the other way round.

## The digest contract

Fixed fields, hard length cap. Assembly compares 132 of these side by side; free-form prose cannot be compared, and each extra hundred characters of one digest is a hundred characters stolen from all the others.

```json
{
  "chunk": "k007",
  "chapters": [43, 49],
  "present": ["向山", "尤基"],
  "new_names": ["阿魂"],
  "events": [{"what": "…", "chapter": 46, "irreversible": true}],
  "state_changes": ["左手被换掉", "身份对尤基暴露"],
  "places": ["吾珥城", "垃圾场"],
  "quotes": [{"chapter": 45, "text": "…不超过 40 字…"}],
  "open_threads": ["电池的来源没有交代"],
  "function": "一句话：这一块在全书里干什么"
}
```

- `present` / `new_names` are copied **verbatim** from the text. Never transliterate, never translate, never normalise.
- `irreversible: true` is the only flag that matters — it is what T2 selection later counts.
- `quotes` are the anti-drift anchor. A digest compresses; a 40-character quote survives compression. Every `[BODY]` and `[FACE]` claim in the blueprint must trace to a quote or a chapter number.

## Four rules that keep a split pass honest

1. **Facts only, no scoring.** A chunk pass never ranks characters or picks turning points. Tiers come from `stats.py` over the whole book, because hit rate is a global property and a chunk cannot see it.
2. **Alias merging is global, single, and last.** Chunk passes emit names verbatim; `aliases.json` resolves them once, after every chunk is done. Merge inside a chunk pass and you get "松岛" and "松岛宏" as two characters with two faces.
3. **Disagreement escalates to the chapter, not to a vote.** When two digests conflict, re-read the chapter. Digests are derivatives; the source is canon.
4. **Keep the compression ratio honest.** Digests should land around 2–3% of source. If your plan implies 0.5%, the middle of the book has been replaced by a genre average.

## Cost, stated plainly

The 3.1M-character case: 132 chunk calls + 17 arc briefs + 1 assembly = **150 calls**, about 150× the one-shot path, and 82.5k characters of digest (2.7% of source) to carry the whole book. That is the honest price of a blueprint that can cite chapter 46 for a prosthetic. Do not pay it for a book that fits.

## When none of this applies

**≤ 150k characters: read the whole book in one pass and skip the split entirely.** Chunking a book that fits injects merge noise, alias drift and a compression loss, and buys nothing. The temptation to chunk "for safety" is the same mistake as generating small tiles and upscaling — it adds a lossy stage to a problem that did not need one.

`chunk.py` prints `single_pass` and writes a plan with no chunks; that is a pass, not a failure.
