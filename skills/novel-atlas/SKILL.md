---
name: novel-atlas
description: Turns a full novel into one ultra-high-resolution atlas image that holds its timeline, cast and key events, by designing a blueprint of tiled zones and stitching locally composited tiles into a single picture. This skill should be used when the user wants a 小说全景图, 人物关系图, 剧情时间线大图, 世界观地图, 全书信息图, 人物谱, a one-image book summary, or asks to visualize an entire novel's structure without splitting it across pages. Triggers on a novel file (.txt/.md/.epub/.docx) plus a request for one big image containing the whole story.
version: 0.3.0
---

# Novel Atlas

Turn one novel into **one** ultra-high-resolution atlas image: timeline, cast and irreversible events, all inside a single canvas. Images carry the meaning; text is a thin annotation layer added locally. The output is deliberately tiled and visibly sectional — a designed map, not a seamless painting.

Never produce multiple images meant to be read in sequence. Information must not break across pages.

## Non-negotiable rules

1. **AI draws, code writes.** Generated tiles contain zero text. Every character name, event title, date and connector label is composited by `scripts/stitch.py`. Never ask an image model to render text, and never ship text that appeared inside a generated tile.
2. **One home, one full body.** A T1 character gets exactly one full-body depiction, in its home zone. Everywhere else the character appears only as an avatar cropped by code from that home tile. Regenerating the same character in another zone is forbidden by default. The crop is a **square box on the face**, and it must be large enough to survive the smallest place that character appears — both are verified by script before the batch runs, not discovered in the finished image.
3. **Structure picks layout, not genre.** Infer four structural features from the text, then compose layout primitives. Genre is a prior, never a determinant. See `references/layout-primitives.md`.
4. **Selection is tiered and capped.** T1 ≤ 12, T2 ≤ 40. Omission is allowed; silent omission is not — the blueprint must report coverage gaps to the user.
5. **Seams are designed, not faded.** Zones are separated by explicit dividers. No feathering: feathering two unrelated pictures only produces a dirty band.
6. **Three gates before spending on tiles** — content list, local skeleton, single-zone style proof — **plus a copy review before the content list and one calibration after the proof.** Do not generate the full tile set until all three gates pass and every T1 anchor reads `ok`.
7. **Ask for art style before designing.** No style given → ask. Never pick silently.
8. **Fidelity over comfort, symbol over rewrite.** If content triggers a generation policy, degrade to symbolic depiction (silhouette, shadow, negative space, prop) and label the substitution explicitly. Never let a model substitute a softened version of the text and present it as faithful.
9. **A body is not a person.** One identity may occupy several chassis over the story. Each chassis is its own character entry with its own portrait and its own `body` — but they must share one face model and declare `same_person_as`. Collapsing them into a single entry (or, worse, merging two different people into one) is a factual error the reader will catch instantly.
10. **Not every T1 has a face.** If the text says a character gave up the human form, they get `faceless: true` and a `prop`, never a portrait box. A portrait of a body the book says is not humanoid is an invention, and the anchor maths cannot save it.
11. **Every face must be somebody.** Each zone carries a `cast` whitelist with exact figure counts. A tile is not finished until a vision pass has listed every figure in it and matched them against that list; any readable face not on the list fails the run. See Step 8.5.
12. **Draw what the text describes, not what the genre implies.** If the book says the old man has a straight moustache, sits on a folding stool and holds a tablet, that is the picture — not "a wise elder in a cape". Prosthetics, interfaces, damage and asymmetry come from the text; the model invents plausible-looking generic cyberpunk otherwise, and generic is the one thing an atlas cannot be.
13. **Text hangs under the picture, on its own plate.** Every label is black on an opaque white plate, placed below the thing it names: a name under the portrait, an event label under its dot, a zone's name and caption in a plate under the panel. A scrim measured against arbitrary artwork is a legibility bet that is lost the first time somebody views the atlas at fit-to-screen — the plate is a guarantee, not a preference. If a label would land on the title block or on another plate, it moves (or takes the next side); nothing is nudged by a few pixels and shipped.
14. **Copy is reviewed before it is laid out.** The words are hand-written into the blueprint and every plate is measured from them, so a caption that is two characters too long is also a label that collides. Run `lint_copy.py`, fix its hard errors, then read the sheet once as a reader — names against the text, chapter numbers, whether each caption describes *this* panel — before Gate 2 fixes the geometry around sentences nobody checked.

## Workflow

### Step 0 — Normalize and index the source

```bash
python3 scripts/normalize.py <book.txt|.md|.epub|.docx> -o atlas_build/
```

Produces `atlas_build/book.txt`, `atlas_build/chapters.json`, and a chapter-check report: chapter count, length distribution, and flagged chapters (too short, too long, untitled, likely front matter).

**Stop and read the report before continuing.** Wrong segmentation means wrong timeline, wrong appearance rates, wrong layout. Fix it now — adjust `--chapter-regex`, or split a merged file by hand — and re-run. Never continue past a report whose flagged chapters are the real story chapters.

### Step 1 — Measure the book, then decide how to read it

```bash
python3 scripts/chunk.py atlas_build/chapters.json -o atlas_build/context
```

It prints the plan and writes `context_plan.json`: token estimate, how many context windows the book is worth, chunk size, chunk count, the digest budget each chunk gets, arc grouping, and a **mode**. Read the mode before reading anything else.

| mode | meaning | what you do |
|---|---|---|
| `single_pass` | the book fits one reliable read | read it whole; do not chunk |
| `two_pass` | chunks → assembly | extract per chunk, assemble once |
| `three_pass` | chunks → arc briefs → assembly | add the middle level |

The mode is not a preference. The window is not the budget either: reliable use is about half the advertised window, so a 200k model reads roughly 150k characters of Chinese, not 300k. `chunk.py` does that arithmetic and refuses to recommend a level the numbers do not support.

- **`single_pass`**: read `chapters.json` and `book.txt` in one pass. Do not chunk for safety — chunking injects merge noise and alias drift into a book that fits.
- **`two_pass` / `three_pass`**: extract per chunk, in parallel if the host supports subagents, with each chunk emitting the fixed digest schema — **facts only**, names copied verbatim, events carrying chapter numbers, two quotes. Compression should land near 2–3% of source; a plan implying 0.5% has replaced the book with a genre average.

**Never read a volume as a unit.** A volume is a narrative boundary, not a context boundary: in a 3.1M-character novel the smallest volume was 275k chars and the largest 944k, six times the read budget. Cut arcs by budget, then nudge to the nearest volume edge.

The two-pass rule is what makes the blueprint trustworthy: chunk extraction may run in parallel; **alias merging, event deduplication, timeline alignment and appearance statistics must not**. They need the whole book. And when two digests disagree, re-read the chapter — digests are derivatives, the source is canon.

Load `references/context-budget.md` whenever the mode is not `single_pass`, or when asked why a book needs splitting.

Infer the four structural features, then let `references/layout-primitives.md` select primitives.

### Step 2 — Score tiers with code, not impressions

```bash
python3 scripts/stats.py atlas_build/chapters.json aliases.json --out atlas_build/stats.json
```

`aliases.json` maps one canonical character to every name the text uses for them: `{"林冲": ["林冲", "林教头", "豹子头"]}`. The script returns per-character chapter hit rate plus first and last appearance.

Assign tiers by the numbers:

| Tier | Rule | Presentation in image | Cap |
|---|---|---|---|
| T1 | hit rate ≥ 15%, **or** ≥ 2 irreversible turning points | own home zone, one full body, own palette | ≤ 12 |
| T2 | causes an irreversible state change (death, identity revealed, bond broken, permanent relocation) | one point, one label, one connector | ≤ 40 |
| T3 | everything else | colour, texture, crowd silhouette only | uncapped |

When a cap is exceeded, demote by lowest hit rate first and list the demotions in the gate report.

### Step 3 — Design the blueprint

Write `atlas_build/blueprint.json` following `references/blueprint-schema.md` exactly: structural features, primitives, grid geometry, zones with duty and seam reason, characters with five-dimension anchors, events, labels, coverage block.

Pick the art style from the preset menu in `references/art-styles.md` and apply that entry's readability compensation to every zone prompt.

Each zone prompt must be self-contained — it goes to an image model that sees nothing else:

```
[STYLE BLOCK — verbatim, first, highest weight]
[ZONE DUTY — what this zone must communicate, one sentence]
[SET — the same place rebuilt in the style's own material grammar (see below)]
[BODY — who is in this frame, and what their body is made of, taken from the text]
[FACE — how each named face is printed, in stroke geometry (object styles only)]
[CAST — exactly how many named figures, and the cap on faceless extras]
[COMPOSITION — subject placement, depth, negative space reserved for labels]
[CONTINUITY — what crosses each open edge, described explicitly]
[READABILITY COMPENSATION — copied from the style table]
[FORBIDDEN — no text, no letters, no numbers, no captions, no watermark,
            no unidentified faces, no invented bystanders]
```

Four of those blocks are what stop the model from drawing a generic scene with interchangeable people:

- **`[SET]`** is required whenever the style's medium is a *physical object* rather than a painting — bricks, clay, paper craft, miniatures. A style block saying "LEGO diorama" plus a zone duty saying "a rust-red plain at night" gets you a realistic desert with two toys dropped into it. The scene has to be re-described in the medium's own vocabulary: what is a baseplate, what is a slope piece, what is a flex-tube, what is a printed tile, what is simply not buildable and therefore absent. Name parts, not moods. Painting styles do not need this block; object styles are lost without it.
- **`[BODY]`** is the only place the prosthetics live. For each figure, name the specific hardware the text gives them — which hand was replaced and from whom, whether the cranium opens, what the eye does when it is angry, whether the skin is still skin. The text usually mentions body work sparsely and unevenly; when it is thin, individualise two or three features (one organ, one facial detail, one joint) rather than inventing a whole look. A body of text with no hardware in it will be drawn as a person in a coat. In an object style the same rule applies one level down: *this arm is a different batch, the clip at the shoulder is visible* beats *a prosthetic arm*.
- **`[FACE]`** is required for every style whose medium is an object with its own face grammar — bricks above all, but also wooden figures and moulded toys. State the expression as **print geometry**: brow strokes, eye shape, pupil position, mouth stroke, character marks. Never use muscle words ("furrowed", "clenched", "gritted") — the object has no muscles, and the model will resolve them into a sculpted human face. For bricks the hard constraint is that the head is a **flat cylinder with no nose**; a nose is the single clearest sign that the model quietly abandoned the medium.
- **`[CAST]`** states the exact number of named figures and forbids any other readable face. Image models fill halls with faces because faces are what halls contain; the only defence is to say "exactly two" and to audit the result.

**State the home character's share of the frame, in numbers.** For every T1 standing in this zone, the COMPOSITION line says how much of the picture they take: "full body, head to foot, occupying 60% of the image height, feet just above the bottom edge, standing at x ≈ 0.38". That sentence is what makes `portrait.box` predictable — the head lands where the prompt asked, and calibration then adjusts a known position instead of hunting for one.

Two caveats, both learned the hard way. First, **the percentage alone does not pin the head**: models anchor a figure by its feet and grow it upward, so "70% of frame height" silently pushes the crown into the top edge regardless of what you said the head should do. The reliable form is a pair of absolute endpoints — "feet at y 0.90, crown just below y 0.24" — plus one sentence reserving the band above it ("the top fifth is empty, no head, no hair, no prop"). Second, **the crown drifts, the feet do not**: budgets that assume a clean top margin fail on the first tile. Leave at least 4% clearance between the requested crown and the zone-title baseline, and settle the real box from the proof tile rather than from arithmetic.

The number is not a matter of taste. The avatar crop is roughly 1.3× the head height, and a head is about 1/7.5 of a standing body, so the box side works out to `cell × share × 0.17`. At a 2048 cell that means a character occupying **40% of the frame height still clears the most demanding style on the menu (watercolour, 140px)**; 55–70% is comfortable. Below 40%, no prompt wording saves the face — either bring the character closer or accept that they cannot appear remotely.

Because of that arithmetic, a distant figure is not a smaller depiction of a character, it is a different design decision. Say so at Gate 1 rather than discovering it at stitch time.

Labels default to a **plate under the subject**, not an overlay on it: `meta.label_plate` is `"white"` unless a build deliberately opts into the older measured scrim (`"tone"`). Leave it alone. Pick `meta.zone_caption_side` (`"bottom"` by default) only if the bottom of every panel is unusable — and let the per-zone `caption_side` override handle the panels where the title block sits, rather than flipping the whole grid.

### Step 3.5 — Copy review (before Gate 1)

```bash
python3 scripts/lint_copy.py atlas_build/blueprint.json -o atlas_build/copy_sheet.md
```

The copy layer is the only part of the atlas written by hand, and it is what the reader actually reads. It is also what the layout is measured from, so its errors arrive twice: once as a wrong sentence, once as a broken plate.

The script checks what a machine can: every name that appears on the canvas (and every zone name) is present and unique; nothing is a placeholder; brackets balance and punctuation is not repeated or half-width; no two labels in a zone say the same thing; `coverage` arithmetic adds up (`covered + missing == total`) because that block is printed on the image; event labels that carry a chapter number agree with the `chapter` field; years inside one column do not run backwards; captions do not all open with the same two characters. It then measures every string against the geometry it will occupy and fails the ones that do not fit.

It cannot check whether a sentence is true. So the sheet ends with four questions and they are not rhetorical:

1. Does every name appear in the text, spelled the way the text spells it? Grep, do not remember.
2. Does every event's chapter number or year resolve to the passage it claims?
3. Does each caption describe **this** panel — or would it fit any panel in the atlas?
4. Read it straight through: do two zones describe the same moment, or does the copy explain the picture instead of naming it?

An atlas with a wrong name on it is worse than an atlas with one fewer label. Fix the copy here; Gate 2 then measures the fixed text. Do not skip to the skeleton because the copy "looks fine" — the whole point is that it looks fine to the person who wrote it.


### Step 4 — Gate 1: content list

Present in plain language: T1/T2 lists with hit rates, demotions, the event list, chosen primitives and the reasoning, and the coverage block naming which chapters and which turning points were omitted and why. Include `copy_sheet.md` — the exact words that will be printed, not a paraphrase of them.

Get confirmation before drawing anything.

### Step 5 — Gate 2: skeleton

```bash
python3 scripts/skeleton.py atlas_build/blueprint.json -o atlas_build/skeleton.png
```

Renders the blueprint as a local flat diagram: zone blocks, standing boxes, event dots, connectors, labels, grid. Zero generation cost, seconds to run.

Show it. The user judges density, balance, sight lines, dead space and label collisions here. It also verifies the coordinate system — a mistake found now costs nothing, the same mistake found after 12 tiles costs the run.

The script exits non-zero and lists problems when the grid has gaps or overlaps, a plate collides with another plate or with the title block, an event points at an unknown zone, a portrait box leaves its home zone, a portrait box is not square, or a remote avatar has no home portrait to crop from. Fix every item and re-run; do not hand a skeleton with reported problems to the user.

The preview draws the annotation layer the way the stitcher will: white plates with black text, a caption plate under each panel, event labels below their dots. Plates and caption blocks are measured at the atlas's **real** cell and scaled to the preview, not measured at preview scale — the same text wrapped at 420px breaks in different places and produces boxes that are off by a few percent, which is enough to invent one collision and hide another. The title block's footprint is drawn as a dashed box: it is painted last, so anything inside it is lost, and a caption whose bottom corner falls under it flips to the top of its panel (the stitcher prints a warning naming the zone). Write `caption_side: "top"` on that zone to make the flip deliberate.

Because every plate is opaque now, a collision is two sentences painted over each other rather than a faint smear — the check is worth reading properly rather than skimming.

The two portrait checks are geometry only — they can be made without artwork, which is why they belong here rather than after the style proof. A tall box is almost always a standing figure mistaken for a head; `anchor.py --write-back` squares it, or write a square by hand.

### Step 6 — Gate 3: style proof

Generate **one** zone at full resolution — the most representative one, usually the opening or the emotional centrepiece. Stitch it with `--allow-partial` so absent tiles do not block the proof, show it, confirm art style, palette, brushwork and likeness before any batch generation.

Wrong style means fixing the style block and regenerating that single zone. Never proceed on a hope.

This gate decides one thing: does the picture look like the book. Do not also try to settle crop coordinates here — that is the next step, and judging both at once makes each of them harder.

For an object-medium style, ask three more questions before approving it, because "I don't like this face" and "this is not this material" feel identical at first glance and only one of them is fixable by a prompt adjective:

- Is the head a flat-topped cylinder, or has a skull grown under the plastic?
- Are the eyes solid black dots, or did white of the eye appear?
- Is there a nose?

Any "no" means the medium was abandoned, not that the style missed. Fix the `[FACE]` block and re-roll this one zone — approving it because the rest of the frame is right is how a dozen tiles inherit a doll face.

### Step 7 — Anchor calibration

```bash
python3 scripts/anchor.py atlas_build/blueprint.json -t atlas_build/tiles -o atlas_build/anchors
```

Every remote avatar in the atlas is one crop of one home tile. A wrong box does not damage one zone, it damages every zone that character appears in — so it is settled while it is still one tile, not after twelve.

The contact sheet shows, per T1: the home tile with the crop rectangle on it, the crop as it will actually be pasted (circular, square-fitted), and the numbers — crop size, the largest size this character is drawn elsewhere, the style's minimum edge.

Look at it and answer one question: **is the red rectangle on the face?** A box can be arithmetically perfect and still frame a shoulder. The numbers in `blueprint.json` are hand-written, not derived; change them and re-run until every row reads `ok`. Re-running costs seconds.

When the box is in the wrong *place* — not merely too small — do not guess again from the contact sheet. Bake a grid onto the home tile and read the head's four edges off it:

```bash
python3 scripts/measure.py atlas_build/tiles/z4_3_0.png
python3 scripts/measure.py atlas_build/tiles/z4_3_0.png --box 0.4755,0.156,0.165,0.165
```

The grid is labelled in the same normalized 0–1 space as `portrait.box`, so what you read is what you write. The `--box` mode renders candidates as the circular avatars they will become, at `demand_px`, and prints each crop's mean luminance — a crop can frame the head perfectly and still be too dark to read at 204px. Two blind rounds put a box on a console; one gridded read puts it on the face.

`--write-back` squares any non-square box and re-verifies from the corrected file. Use it when a box was written as a standing figure rather than a head. Then look at the sheet again: squared is not the same as on the face.

Exit 2 means one of: the box leaves its home zone, the box is not square, the crop is under the style's minimum avatar edge, or the crop is smaller than the largest place the character is drawn elsewhere. The last two are the same shortage of pixel, and there are only two cures — give the character a bigger share of the home tile, or stop showing them away from home. Neither is a script fix.

If a home tile is regenerated later, the boxes inside it go stale — they point at pixels that no longer exist, and nothing in the blueprint looks wrong. The script fingerprints each home tile and reports `[stale]` on the next run, so re-run it after any regeneration rather than relying on memory.

Keep the sheet next to the build. It is the answer to "why does this person look different here", three weeks later.

### Step 8 — Generate the remaining tiles

One image per grid cell, saved as `atlas_build/tiles/<zone_id>_<col>_<row>.png`. A zone spanning several cells emits one tile per cell, each with the zone prompt plus that cell's positional role and which of its edges continue into a neighbour.

Generate at the model's maximum square resolution (typically ~2048). Never generate small and upscale — ultra-high resolution comes from few large tiles, not from resampling.

Every returned image still carries a watermark, and image-to-image tops out near 1024 while the batch is 2048. Put both through one script instead of a hand-written paste:

```bash
python3 scripts/finalize.py gen/raw.png -o tiles/z9_0_2.png --cell 2048 \
    --wm 880,946,1024,1024 --stamp z9
```

`--wm` fills the stamp by continuing the vertical gradient found just above it, column by column. Cloning clean artwork from beside the stamp looks fine in theory and fails on screen: the floor is a gradient, so the clone sits one tone off and reads as a rectangle. `--stamp` writes the source size and an `upscaled` flag into `cast_audit.json`, so a half-resolution tile is declared in the record rather than hidden in a habit.

**Put the camera inside the scene.** Object-medium styles invite the model to photograph a diorama from outside, which leaves a dark surround and a visible baseplate corner — and once the tile is stitched, that surround reads as an inset picture floating in the atlas. Say where the camera stands and that the scene runs off every edge: *"the camera stands inside the ruins at eye height; the wall runs off the top and left edges, the floor runs off the bottom edge — no dollhouse, no cutaway, no bird's-eye view, no visible baseplate corner, no dark border."* Three tiles were re-rolled for this in one run; the sentence is cheaper than the re-roll.

### Step 8.5 — Cast audit (before stitching anything)

The model does not know the cast. Left alone it will put a face in every alcove, a bystander behind every figure, and a crowd wherever there is room — and every one of those faces is a character the book never wrote, which the reader will try to place. Counting faces is a reading task, so the audit is written by looking; the script only keeps the record honest.

```bash
python3 scripts/audit_cast.py atlas_build/blueprint.json -d atlas_build/tiles --init   # register tiles
python3 scripts/audit_cast.py atlas_build/blueprint.json -d atlas_build/tiles          # verify
```

For each tile, look at it — full frame, plus each dark corner brightened 2–3×, because the model hides people in shadow — and write `atlas_build/tiles/cast_audit.json`:

```json
{ "z7": { "tile": "tiles/z7_2_1.png", "sha256": "…", "verdict": "pass",
  "figures": [
    { "character": "c_jeanne", "prominence": "face",   "note": "…" },
    { "character": "c_liu",    "prominence": "face",   "note": "…" },
    { "character": null,       "prominence": "figure", "note": "远处人影" } ],
  "reviewer_note": "四角提亮 2.6× 复核无人影",
  "fix": "…" } }
```

`prominence` is `face` (a face a reader could recognise and try to name), `figure` (a body with no readable face), or `prop` (an object standing in for a non-humanoid character). The script fails the run when:

- a tile has no entry, or the tile's hash changed after the entry was written (a regenerated image cannot inherit an old verdict);
- a `face` has no character id — this is the whole point of the step;
- a figure id is not in that zone's `cast.named`;
- faceless extras exceed `cast.extras_max`;
- a character declared as `prop` was drawn as a person.

Fixing an audit failure means regenerating with a stronger `[FORBIDDEN]` line, or cropping the extra figure out — not editing the audit until it passes. When a tile passes, the watermark is removed and the *new* hash is re-registered, because a stale hash is a lie about which image was approved.

### Step 9 — Stitch, label, deliver

```bash
python3 scripts/stitch.py atlas_build/blueprint.json -d atlas_build/tiles -o atlas_build/atlas.png
```

The script composites tiles on the grid, crops bleed, unifies global colour temperature, draws seam dividers, crops and pastes home portraits as remote avatars, draws every text element on a white plate, draws the title block and coverage note, and writes `atlas_build/stitch_report.json`.

The annotation layer is one system, not a pile of labels:

| element | where it goes | why |
|---|---|---|
| zone caption | a plate under the panel, name line + caption | a caption belongs under the picture; it is the first thing read and the last thing legible when a dark scrim sits on artwork |
| portrait / avatar name | centred under the box or the circle | a name above a head collides with the caption plate and covers the crown |
| event label | under the dot, centred | the dot marks the point; text above it covers the thing the dot points at |
| free label | under its declared point (`anchor: cb`) | same rule, same plate |

Each of those falls back to another side only when the preferred one is blocked by the panel edge, the caption plate or the title block — below, then above, right, left, and `label_side` on an event can put one of those first for a dense cluster. The dot never moves, so a leader line still points at something.

Black on white is 18:1 by construction, so the 4.5:1 floor stops being a fight and starts being a check that the plate was actually painted. It still applies to the title block: secondary lines are pushed darker until they clear the floor, and every line's measured ratio lands in `report.cartouche`. `meta.label_plate: "tone"` restores the old measured-scrim behaviour for a build that was drawn around it; do not reach for it to make an image look calmer — cut a label instead.

The title block is painted **after** the labels, so a label placed where it sits is sliced in half by its edge. Every overlap is named in `report.warnings` — `label under the cartouche: '…' at [x,y]`, and `label collision: '…' vs '…'` for two labels that landed on each other. The fix is to move that label in the blueprint — the event's `x`/`y`, or the zone label — never to nudge the block. Moving the label by hand keeps its marker dot and connector line together; the stitcher must not silently shift text, or a leader line ends up pointing at nothing.

Read the report. Fix and re-stitch any contrast failure, missing tile, unresolved avatar or label-under-cartouche warning — do not ship it.

Deliver the final image with a short note: what it contains, which chapters are missing, and where content had to be symbolized.

## Environment

Scripts need Python 3 and Pillow. If `import PIL` fails:

```bash
python3 -m pip install pillow
```

`normalize.py` reads `.txt`/`.md` natively and `.docx`/`.epub` through the standard library only — no extra parser dependencies.

## References

- `references/context-budget.md` — how long is too long: effective context, the three reading budgets, the digest contract and the arithmetic that picks the chunk size. Load when the book is over ~150k characters.
- `references/layout-primitives.md` — structural features, primitive vocabulary, adjacency rules, two worked derivations. Load when designing the layout.
- `references/blueprint-schema.md` — the exact JSON contract consumed by the scripts. Load when writing or debugging a blueprint.
- `references/art-styles.md` — preset style menu with readability compensation tables and prompt language. Load when asking about or applying art style.
- `references/style-metrics.json` — the machine-readable avatar size floor per style, read by `anchor.py`. When you change a `Min avatar edge` in `art-styles.md`, change it here too; the script reports any drift between the two as a failure rather than trusting either.

Scripts: `normalize.py` (Step 0) · `chunk.py` (Step 1 reading plan) · `stats.py` (Step 2) · `lint_copy.py` (Step 3.5 copy review) · `skeleton.py` (Gate 2) · `measure.py` (Step 7 measurement) · `anchor.py` (Step 7) · `finalize.py` (Step 8 tile intake) · `audit_cast.py` (Step 8.5) · `stitch.py` (Step 9). `atlas_common.py` holds the geometry all of them share — the label plate, the caption block and the title-block footprint above all: `text_box()`, `zone_caption_geometry()`, `cartouche_rect()`. If two scripts disagree about where something is, the bug is that one of them has its own copy.
