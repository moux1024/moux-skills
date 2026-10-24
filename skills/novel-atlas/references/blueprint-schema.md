# Blueprint schema

The single file the scripts consume. Coordinates are **zone-local, normalised 0–1**, measured from the zone's top-left corner. Font sizes are stated **for a 2048px cell** and scaled at stitch time. The grid is rectangular: a zone occupies a whole number of cells.

```json
{
  "meta": {
    "title": "水浒传 · 全景",
    "subtitle": "一百单八将的聚与散",
    "style_id": "woodcut",
    "canvas": { "cols": 4, "rows": 3, "cell": 2048, "bleed": 0.08 }
  },
  "structure": {
    "time_continuity": "strong",
    "causal_chain": "long",
    "centrality": "ensemble",
    "info_asymmetry": "none"
  },
  "primitives": [
    { "id": "confrontation_board", "role": "primary", "weight": 0.62,
      "rationale": "梁山与朝廷的结构性对抗贯穿全书，第 71 回排座次与第 82 回招安是中线两端的支点" }
  ],
  "palette": { "bg": "#1b1a17", "ink": "#f2ece0", "accent": "#a63d2f", "muted": "#7a7167" },
  "characters": [
    {
      "id": "c_linchong", "name": "林冲", "tier": "T1",
      "aliases": ["林冲", "林教头", "豹子头"],
      "hit_rate": 0.42, "turning_points": 3,
      "home_zone": "z3",
      "anchor": {
        "face": "窄下颌、薄唇、眼窝深",
        "hair": "中分黑直发及肩",
        "mark": "左眉骨旧疤",
        "silhouette": "过膝深色斗篷，右肩单披",
        "palette": "藏青 + 赭红"
      },
      "body": "右臂自肘下为义肢，掌心嵌一枚可拆的窝心锤；颈侧一道旧接口疤；平时覆仿生表皮",
      "body_en": "right arm prosthetic from the elbow down, a detachable pommel weight set in the palm",
      "portrait": { "zone": "z3", "box": [0.32, 0.24, 0.17, 0.30] }
    }
  ],
  "events": [
    { "id": "e12", "label": "第10回 · 山神庙夜奔", "chapter": 10, "zone": "z3",
      "x": 0.62, "y": 0.58, "kind": "irreversible", "tier": "T2", "link": ["e09"] }
  ],
  "zones": [
    {
      "id": "z1", "name": "汴京 · 秩序", "col": 0, "row": 0, "w": 1, "h": 1,
      "duty": "展示禁军体制与林冲原本的位置：一个可以被碾碎的秩序",
      "primitive": "timeline_spine",
      "seam_reason": { "right": "城门洞", "bottom": "御街" },
      "adjacent": ["z2", "z5"],
      "tonal": "light",
      "caption": "禁军教头的日常",
      "characters": ["c_linchong"],
      "avatar_slots": [],
      "cast": { "named": [ {"character": "c_linchong", "figures": 1, "prominence": "full"} ],
                "extras_max": 2, "extras_note": "禁军巡卒，不给脸" },
      "labels": [
        { "text": "第一回 – 第十回", "x": 0.06, "y": 0.055, "size": 46, "anchor": "lt" }
      ],
      "prompt": "[STYLE BLOCK]... [ZONE DUTY]... [COMPOSITION]... [CONTINUITY] right edge: 城门洞的砖砌门框延续到画外… [COMPENSATION]... [FORBIDDEN] no text…"
    }
  ],
  "coverage": {
    "chapters_total": 120,
    "chapters_covered": [1, 2, 3],
    "chapters_missing": [58, 79],
    "turning_total": 14,
    "turning_covered": 13,
    "turning_missing": ["招安后军中哗变"],
    "demotions": [
      { "character": "c_zhangqing", "from": "T1", "to": "T2", "reason": "hit_rate 0.11，且未驱动转折" }
    ]
  }
}
```

## Field notes

**`meta.canvas`** — `cols × rows` is the grid. `cell` is the generation resolution, normally the model's maximum square size. Final canvas is `cols*cell × rows*cell`; there is no upscaling anywhere. Keep `cols*rows` between 6 and 16. `bleed` is the fraction cropped from each tile edge before compositing: generate tiles with the subject extending past the frame, then crop, so figures are not guillotined at the seam.

**`structure`** — the four features from `references/layout-primitives.md`. Mandatory; they are the audit trail for why the layout looks the way it does.

**`primitives`** — exactly one `"primary"` with `weight > 0.5`, at most two `"secondary"`. `rationale` is for the Gate 1 conversation, and it is not optional — a primitive without a reason is a decoration.

**`palette`** — four colours, used by the scripts for scrims, seams, markers, and the cartouche. `ink` is the annotation colour, not a background.

**`characters[]`** — every character that appears on the canvas, T1 or not.
- `tier`: `T1` | `T2` | `T3`. T1 gets a home zone and a portrait box; T2 gets event nodes only; T3 appears nowhere explicitly.
- `hit_rate` and `turning_points` come from `stats.py`, not from judgement. Keep them in the file — they are what makes the tier auditable.
- `home_zone`: where the one full-body depiction lives. A T1's portrait box must be inside this zone.
- `anchor`: five fields, all required. At least two must be silhouette-level, i.e. recognisable at 100px.
- `portrait.box`: `[x, y, w, h]` in home-zone fraction. **This is the crop rectangle for every remote avatar, and it is a head, not a figure.** Two requirements the scripts enforce: it must be square on the canvas (`w*zone_w == h*zone_h`, because the stitcher force-fits it into a circle), and its pixel side must clear both the style's minimum avatar edge and the largest size the character is drawn at anywhere else. Write an estimate at blueprint time, then settle it in Step 7 against the real tile — `anchor.py` prints the numbers and the corrections.
- `body`: the character's hardware, in the text's own terms — which limb was replaced and with what, whether the cranium opens, what the eye does, whether any skin is left. This is what goes into the zone prompt's `[BODY]` block. `body_en` is the same thing in the prompt's language; a Chinese `body` inside an English prompt gets obeyed inconsistently and sometimes renders as glyphs.
- `body` is per character, but a character's body changes with the era. When a zone shows them at a different age or in a different chassis, override it **on that zone's cast entry**, not here: `zones[].cast.named[].body`.
- `expression`: `{ "key", "print", "note" }`. `key` names the face from the style's expression grammar (`references/art-styles.md`; for bricks: `factory_smile`, `smirk`, `aghast`, `cry`, `unhinged`, `menace`, `deadpan`, `worry`, `stare`, `off`, `misregistered`, `blank`). `print` is the stroke-level description that goes verbatim into `[FACE]` — brows, eyes, pupils, mouth, marks — written as print geometry, never as muscle. `note` records the line of text that justifies it. A character whose expression cannot be traced to the text keeps `factory_smile`: the default head is a statement about them, not a missing value.
- `faceless`: `true` when the text says the character is not humanoid. Such a character gets **no** portrait box (`portrait: {box: null}`), a `prop_at: [x, y]` so the skeleton can mark where the object stands, and a `prop` description (`body`). Give them a face and you have invented a person.
- `same_person_as`: comma-separated ids of the character entries that are the same individual in a different chassis. Each keeps its own home zone and portrait; the field exists so the reader, and the reviewer, know the face is supposed to match and the body is not.

**`events[]`** — `kind`: `irreversible` (default for T2) or `event`. `link` references other event ids; lines are drawn between them, so only link events that a reader should connect. Labels carry the chapter number — the reader's anchor back to the text.

**`zones[]`**
- `col`/`row`/`w`/`h`: cell rectangle. Zones must tile the canvas exactly, no gaps, no overlaps. `skeleton.py` fails on both.
- `duty`: one sentence. If it needs two, the zone is doing two jobs and should be split. **Internal only** — it appears in the skeleton so the reviewer can judge intent, never on the finished image.
- `caption`: optional, **reader-facing**. One short line under the zone name. This is the only editorial text a viewer sees besides labels, so keep it concrete.
- `tonal`: `light` | `dark` | `mid`. Drives the annotation plate direction for the whole zone — a light zone gets dark text on a light plate, a dark zone the reverse. Declaring it is what makes the label layer look drawn rather than accidental; when it is missing the stitcher picks per label and the result looks random. If the declared tone cannot reach 4.5:1, the stitcher inverts that one label and records a warning.
- `hide_name`: optional `true` to suppress the zone name (for zones that are pure atmosphere).
- `seam_reason`: `left`/`right`/`top`/`bottom` → the physical thing the seam is. Only these edges get a divider drawn. An edge with no reason is an edge that should not exist.
- `characters`: T1 home characters standing in this zone.
- `cast`: the whitelist for this zone, and the only authority on who may be drawn in it.
  ```json
  "cast": { "named": [ {"character": "c_jeanne", "figures": 1, "prominence": "full"},
                       {"character": "c_liu",    "figures": 1, "prominence": "full"} ],
            "extras_max": 0,
            "extras_note": "" }
  ```
  `prominence` is `full`, `mid`, or `prop` (an object standing in for a non-humanoid character — it is counted separately and never as a figure). `extras_max` caps **faceless** background figures; `extras_note` says what they are allowed to be. Every id in `characters` and `avatar_slots` must appear in `cast.named`, and `skeleton.py` fails when one does not — the whitelist has to be the same list the artwork is audited against, or the audit is theatre. A face outside this list fails Step 8.5.
- `avatar_slots`: remote appearances. `size` is a fraction of the zone's shorter side. These are cropped from the home tile — they are never generated.
- `labels`: `anchor` is `lt` (left-top), `ct` (centre-top) or `lm` (left-middle). `size` for a 2048 cell; the stitcher scales it. **Labels must sit below y ≈ 0.16**, the band reserved for the zone name and caption — `skeleton.py` reports a collision otherwise.
- `prompt`: the full self-contained zone prompt, in the five-part order given in SKILL.md.

**`coverage`** — the honesty block. `chapters_covered` may be omitted if `chapters_total` and `chapters_missing` are both given. Whatever is omitted must appear in a `*_missing` array, and the cartouche prints it on the final image.

## Hard rules the scripts enforce

| Rule | Enforced by | Failure mode if ignored |
|---|---|---|
| Zones tile the grid exactly | `skeleton.py` | Gaps become black bands; overlaps paste twice |
| Every event's zone exists | `skeleton.py` | Dot silently dropped |
| Every T1 has `portrait.box` | `skeleton.py` warns, `stitch.py` degrades | Remote avatars become symbols |
| `portrait.box` stays inside its home zone | `skeleton.py` | Crop reads the neighbouring zone's pixels |
| `portrait.box` is square on the canvas | `skeleton.py`, `anchor.py` | Face arrives squashed into the circle |
| Crop side ≥ the style's min avatar edge | `anchor.py` | Face is gone at display size |
| Crop side ≥ the largest remote display size | `anchor.py` | Upscaled blur, worse than a symbol |
| Labels do not overlap | `skeleton.py` | Unreadable stacked text |
| Label contrast ≥ 4.5:1 | `stitch.py` | Label unreadable on busy art |
| Every home / avatar id is in `cast.named` | `skeleton.py` | The cast list and the picture describe different zones |
| A faceless character has no portrait.box | `skeleton.py` | A human face is invented for a non-human body |
| Every tile has an audit newer than the tile | `audit_cast.py` | A regenerated image inherits a stale pass |
| No readable face outside `cast.named` | `audit_cast.py` | The atlas names somebody the book never wrote |
| Every expected tile exists | `stitch.py` | Hatched placeholder in the final image |

Both scripts exit non-zero on failure. Treat non-zero as "not done", not as a warning.

## Common authoring mistakes

- **Portrait box set from the skeleton.** The skeleton has no artwork; a box that passes geometry can still frame a shoulder. Square it at Gate 2, then put it on the face in Step 7 using the contact sheet.
- **A standing figure written as a portrait box.** `[0.3, 0.26, 0.18, 0.34]` describes a body. The avatar is cut from the head alone — roughly the top quarter — and the stitcher will squash whatever it is given into a circle.
- **Zone duty written as a title.** "第 3 区" is not a duty. A duty says what the reader should conclude from that region.
- **Seam reasons invented to satisfy the validator.** A seam with a fake reason is worse than no seam — it draws a divider across a continuous scene.
- **`cell` lowered to fit a bigger grid.** Shrinking cells to add zones defeats the whole resolution argument. Cut zones instead.
- **Coverage left empty.** An empty coverage block reads as "we checked everything", which is never true.
