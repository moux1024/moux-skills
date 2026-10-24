# Art styles

Ask for a style before designing. Offer this menu, never pick silently. Each entry states what it costs the reader — say that cost out loud when the user chooses.

Every style entry has three parts:

- **`style_block`** — paste verbatim at the top of every zone prompt, in English, because image models weight leading tokens most heavily. It must be byte-identical across all zones; drift here is the main cause of a canvas that looks like twelve different books.
- **Compensation** — applied in the prompt *and* enforced later by `stitch.py`. Prompt-level compensation is a request; script-level enforcement is a guarantee.
- **Cost** — the readability price, stated to the user before they commit.

## Shared rules

- **Contrast floor 4.5:1.** Every label's foreground against the pixels actually behind it. `stitch.py` samples the real backdrop, picks black or white text, then grows a scrim until the floor is met. When even a full scrim fails, the script raises the scrim opacity, thickens the outline, and records the failure in `stitch_report.json`. Never ship an unresolved failure.
- **Minimum avatar edge by style.** Below this, a cropped portrait loses its face and must be replaced by a symbol marker instead. Encoded per style in the table below, and mirrored in `style-metrics.json` for the scripts — `anchor.py` fails the run when the two disagree, so this stays a rule rather than a paragraph.

  This floor is also what sets how large a home character has to stand. The crop is roughly 1.3 head-heights, a head is roughly 1/7.5 of a standing body, so on a 2048 cell the required share of frame height is `floor × 7.5 / (2048 × 1.3)`. **25% clears the loosest styles on the menu (woodcut and lego, 90px); 40% clears the strictest (watercolour, 140px).** A character standing further back than that cannot hold a face later, whatever the prompt says — the fix is a closer composition, not more adjectives.
- **Never let style win over legibility in the label bands.** If a zone's background detail fights the text, the compensation wins.

## 1. `watercolor` — 水彩绘本

```
style_block: soft watercolor illustration, wet-on-wet washes, visible cold-press paper grain,
muted pigment with bleeding edges, gentle granulation, airy negative space, natural daylight,
picture-book sensibility, 19th-century travel journal palette
```

| Compensation | Value |
|---|---|
| Character outline | 1.5–2px contour in the character's darkest local colour, required on any figure that will be cropped |
| Label scrim | 32% ink-wash tint, softened edge |
| Background lift | +12% lightness in any region reserved for text |
| Saturation cap | 78% — washes above this read as plastic |
| Min avatar edge | 140px |

**Cost**: the weakest detail retention of the menu. Faces blur below 200px, so remote avatars must be larger and fewer, and T1 count should be pushed toward the low end (8–10).

## 2. `inkwash` — 水墨淡彩

```
style_block: Chinese ink wash painting, sumi-e brush economy, xuan paper texture,
graded ink from jet black to pale grey with sparse mineral pigment accents,
deliberate unpainted voids, high tonal contrast, no gradient shading
```

| Compensation | Value |
|---|---|
| Character outline | none — instead, force 焦墨 (dense black) on the silhouette edge |
| Label scrim | 26% cool grey, since voids are already bright |
| Void management | reserve voids as text fields rather than filling them |
| Saturation cap | one accent colour only, otherwise the ink reads muddy |
| Min avatar edge | 120px |

**Cost**: the void is the style's best feature and the layout's worst enemy. Enforce that every zone declares which void is a text field; an undeclared void will be read as a mistake, not as composition.

## 3. `impasto` — 厚涂写实

```
style_block: thick impasto oil painting, visible palette-knife strokes, dramatic chiaroscuro,
rich layered glazes, textured canvas, deep shadow with warm bounce light, classical figure painting
```

| Compensation | Value |
|---|---|
| Character outline | none needed — edges are already hard |
| Label scrim | 38% dark, because backgrounds are busy and mid-dark |
| Background desaturation | −20% behind label bands only |
| Min avatar edge | 100px |

**Cost**: the most forgiving style for likeness and the least forgiving for text. Busiest backgrounds of the menu; scrims will be visible. Best likeness retention, worst annotation elegance.

## 4. `cyberpunk_noir` — 暗调赛博

```
style_block: neo-noir cyberpunk, heavy shadow with neon rim light, wet reflective surfaces,
dense city texture, teal and magenta light sources, chromatic bloom, volumetric haze,
cinematic 35mm framing
```

| Compensation | Value |
|---|---|
| Character outline | neon rim light on the silhouette edge, required |
| Label treatment | emissive outline (2px glow) plus 55% dark block — this style cannot host plain text |
| Shadow lift | +15% lightness in shadow regions reserved for text |
| Saturation cap | none, but neon must not sit under a label |
| Min avatar edge | 110px |

**Cost**: labels look like UI elements, not annotations. If the user wants an elegant literary object, this is the wrong choice and should be said plainly.

## 5. `woodcut` — 木刻／铜版刻线

```
style_block: woodcut engraving, dense hatching and cross-hatching, high-contrast black line on
warm off-white ground, limited spot colour, carved texture, early-modern cartography feel
```

| Compensation | Value |
|---|---|
| Character outline | inherent in hatching |
| Label scrim | 20% paper tone, matching ground |
| Hatching density | ≤ 60% coverage in label bands |
| Min avatar edge | 90px |

**Cost**: the best style for an atlas, because the medium is already cartographic and annotation reads as part of the artefact. Weakest for colour-coded factions; distinguish factions by hatch direction, not hue.

## 6. `gouache_flat` — 扁平岩彩

```
style_block: flat gouache illustration, bold simple shapes, mineral pigment palette,
matte surface, minimal internal detail, strong silhouette design, screen-print flatness,
mid-century poster geometry
```

| Compensation | Value |
|---|---|
| Character outline | none — silhouette is the identity |
| Label scrim | 0% needed in flat fields; sample and place labels inside flat regions |
| Palette discipline | 6–8 colours total, one accent reserved for T1 characters only |
| Min avatar edge | 80px |

**Cost**: the strongest style for label legibility and the weakest for atmosphere. Silhouette must carry identity, so the five-dimension anchor's silhouette field becomes the load-bearing one — a flat figure with a generic outline is indistinguishable from every other flat figure.

## 7. `lego` — 乐高积木

```
style_block: LEGO minifigure diorama, every element built from glossy ABS plastic bricks,
visible studs on all horizontal surfaces, sharp mould seams and sprue nubs,
hard specular highlights from a single softbox key, saturated primary brick palette,
macro product photography, tilt-shift miniature scale, shallow depth of field
```

| Compensation | Value |
|---|---|
| Character identity | every T1 needs one **identifying part** — a hair mould, a mask, a helmet, a visor, a printed torso — and that part must sit inside `portrait.box`. A bare head is a background figure |
| Face | a `[FACE]` block is mandatory — a flat cylinder with five printed strokes and no nose, chosen from the grammar below. Without it the model supplies a modelled doll face, which quietly undoes the whole style |
| Label treatment | black plate bar at ≥70% opacity, white type, yellow circular numbers — the language of a LEGO instruction booklet. Plain white type dies on yellow faces and red bricks |
| Palette cap | 8–10 official brick colours, no gradients, no painted texture |
| Ground rule | every zone must show a studded baseplate as its floor plane — this is the style's spatial grammar, not decoration |
| Min avatar edge | 90px |

### Expression grammar — the one loss this style can partly buy back

A minifigure face is **five strokes** pad-printed on a flat cylinder: two brows, two eyes with pupils, one mouth. Nothing else is moulded. Every expression in the official line — including the whole cast of *The LEGO Movie* — is a recombination of those five strokes plus at most two character marks. Write the strokes, not the feeling.

| Key | Gloss | Brows | Eyes | Mouth | Source |
|---|---|---|---|---|---|
| `factory_smile` | 出厂笑脸 | two flat arcs, set wide | round dots, pupil centred with one catchlight pixel | single upward C-stroke, closed | 1978 classic head; Emmet's resting face |
| `smirk` | 歪嘴笑 | one brow lifted higher than the other | one eye narrowed to a half-round | short C-stroke pulled up on one side only | Emmet's lopsided grin; CMF smirk heads |
| `aghast` | 惊恐 | both lifted, inner ends high | enlarged to ovals, pupils shrunk | tall narrow oval, pure black interior | Emmet's terror head |
| `cry` | 怒吼 | inner ends pressed down into a V | squeezed to narrow slits | wide rectangle with one white tooth bar across it | Pirates 1989 — the first open mouths |
| `unhinged` | 失焦 | none, or one flat line | solid black, no pupil, no catchlight | D-shaped open mouth with a red tongue block | Benny |
| `menace` | 阴冷 | inner ends down, outer ends up | long narrow eyes, pupils toward the inner corner | one dead-flat horizontal line, corners unmoved | Lord Business |
| `deadpan` | 公事公办 | two short flat strokes | small square dots | one horizontal line | Biznis Kitty, "all business" |
| `worry` | 忧虑 | inner ends raised, classic 八字 | round dots sitting slightly high | shallow downturned arc | the old-man head |
| `stare` | 直视 | level, thin, wide apart | centred pupils, no catchlight, no blink line | horizontal line, held | — |
| `off` | 关机 | flat and low | two downward-curved closed-eye lines | horizontal line | death / power-down heads |
| `misregistered` | 错版 | brow and mouth strokes offset from the eye axis by about one stud | normal | normal | pad-print registration error, used deliberately |

**Character marks** (max two per face): freckle dots, one tear under one eye, a scar across a brow, stubble hatching along the jaw only, pad-printed circuitry, an oil smudge.

Five rules make the difference between a LEGO face and a doll head:

1. **Flat cylinder, no nose.** No modelled cheeks, no brow ridge, no chin. If a nose appears the figure becomes a doll wearing a brick body — this is by far the largest anthropomorphism leak in the style, and the one to check first on any finished tile. The companion tell is the eye: a printed minifig eye is **one solid black dot with no white of the eye, no eyelid, no iris ring**. As soon as sclera appears, the model has switched to portrait rendering and the nose will follow.
2. **Five strokes plus two marks.** More than that reads as a portrait, which the mould cannot physically hold.
3. **Write geometry, never muscle.** "Inner ends of the brows pressed into a V" — not "furrowed brow". "Eye reduced to a narrow slit" — not "squinting". A minifig has no muscles to move.
4. **The face is a separate part from the body.** Exploit the double-sided head as a *contradiction device*: the body performs something catastrophic while the printed face keeps its factory expression. Reserve `factory_smile` for exactly that, and for characters whose smile never reaches their eyes — the print grammar says this natively, because on a minifig the mouth genuinely is printed on and the eyes genuinely cannot join in.
5. **Reuse is correct, not lazy.** Real minifigures share heads across a whole theme. Six or seven distinct expressions across a full cast is the medium's natural economy, and the repetition reads as *standard issue* — which is what a novel about manufactured people usually wants anyway.

```
[FACE] faces are pad-printed on a flat cylindrical head: no nose, no cheek volume,
no sculpted brow, no shading on the face plane — five strokes only (two brows, two
eyes, one mouth) plus at most two character marks.
Jeanne: level thin brows set wide, small centred pupils, one horizontal line for the
mouth — a stare held too long, nothing on the face reacts.
Tumour-Xiang Shan: grey brows both raised at the inner ends, two round eye dots sitting
high, one shallow downturned arc — worry that never resolves.
```

**Cost**: this style gives up personhood by design, and the grammar above buys back only its *typology*. You get "afraid"; you never get "afraid of becoming his father". Six expressions cannot distinguish 约格莫夫's obsession from 向山's patience — that argument still has to be made by pose, prop and composition, and the face can only confirm the category. Brutality is neutralised for free: a character being disassembled and rebuilt reads as *assembly*, not *dismemberment* — the discomfort goes down and so does the weight. Say both halves out loud; users who want this style usually want the first and have not thought about the second.

**Where it earns its place**: stories about replaceable bodies. A brick is a part, a minifigure is a chassis, and a mismatched brick is an unlicensed implant — the medium's own grammar already argues the book's thesis, so the prompt does not have to.

## Adding a style outside the menu

Allowed, but with an explicit procedure: derive the compensation row **before** generating anything, write it into the blueprint, and validate it at Gate 3. Unknown styles get one tile of proof, not faith. If the derived compensation cannot reach 4.5:1 after two scrim adjustments, tell the user the style is not viable for an annotated atlas and offer the nearest menu entry.
