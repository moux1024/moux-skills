# Promo Atlas 1.2.1 — information density and delivery contracts

A delivery review asked why a finished campaign set carried so little usable information.
The pictures were not lazy: every gate had passed. That was the problem. The gates all
checked **"nothing is wrong"** (provenance, compliance, geometry, style, hash-bound audit)
and none of them checked **"something is said"**.

This note records what changed in the skill, why, and what was deliberately left alone.
It contains no campaign material, client copy or product terms.

## What went wrong

Eight of twelve cells were code-drawn blank paper cards. They passed because:

1. `stitch.py` counted a placeholder only when a tile **file was missing**. A file that
   existed but held no information reported `placeholder: 0`.
2. `audit_assets.py` judged three axes — intent, plausibility, taste. A picture of blank
   paper passes all three.
3. `lint_copy.py` checked tone, sourcing and length, never "what new fact does this cell
   add". `check_geometry` checked that a caption was non-empty, not that it was new.
4. `caption_mode: rule` had been introduced without a matching visual grammar. Together
   with a `no numbers` prompt rule, the compliant way to draw a rule became a blank slip.

A second, quieter mismatch surfaced during the rework: the density ledger counted four
cover facts while the fact plate printed three, because the plate was hard-capped at two
rows. The takeaway still claimed four numbers. Same failure class — **the ledger says a
thing the picture does not** — so it is now a hard gate too.

## 1.2.0 — make information measurable

- `meta.key_facts[]` becomes the 12th intake item. Each `zones[].facts[]` must reference
  at least one fact not already stated elsewhere, with a declared `tile_origin`
  (`ai` / `code_card` / `evidence` / `chart`). Every financial fact needs a
  `client-confirmed:*` source.
- New `lint_density.py` writes `density_sheet.md`: facts per zone, information units per
  page, repeat ratio, and the area ratio of rectangles that actually carry new facts
  (titles, page numbers, column headers, persona strips and disclosure bands do not count).
  A `code_card` / `evidence` / `chart` cell with no number / condition / boundary /
  evidence fact is refused.
- `stitch.py` splits `placeholder` into `missing`, `blank_tile` (file exists but pixels
  are empty) and `low_information` (declared card with no facts). `--strict-info` fails
  the build on either of the latter two.
- `audit_assets.py` gains a fourth `information` axis; an information card's `sentence`
  must name a number or a clause element.
- `rule-visual.md` defines six drawable structures (formula, comparison, flow branch,
  range, checklist, evidence card) and `[DATA-SLOT]`: the model draws the carrier, code
  prints client-confirmed numbers. `no numbers` becomes `no invented numbers`.
- `make_rule_card.py` is the official fallback when there are fewer illustrations than
  cells; it refuses to generate a card with no facts.
- Covers print a takeaway plus key numbers; the long image's `first_screen` carries the
  conclusion, key numbers and one short line of disclosure in the top quarter that a
  feed actually shows.

## 1.2.1 — the delivery contract is exact

- `pad_to_ratio()` only adds borders; it cannot shrink. One upload therefore shipped a
  `1242x1656` cover beside `1256x1675` inner pages and a `1259x5036` long image, so the
  platform resampled every page differently. New `platform_px()` /
  `normalize_to_platform()` take the width from the platform table, derive height from
  the ratio, and land every bound output on exact pixels. `stitch_report.json` records
  `platform_px`, `size_exact`, `normalized_from`; a mismatch fails the build. The internal
  master is untouched, and an explicit `--cell` stays a preview probe.
- The platform table's Xiaohongshu entry is corrected from `1242x1660` to `1242x1656`,
  which is what its own `3:4` ratio implies. `references/social-channels.md` is kept in
  parity.
- The cover fact band grows to fit its rows instead of dropping facts. `facts_declared`,
  `facts_printed` and `facts_clipped` are reported, and declared != printed fails.
- Removed a Pillow `getdata()` deprecation in the blank-tile detector.

## Validation

```
bash tests/smoke.sh   →  48 passed, 0 failed
```

Rows 4c (density), 6b (strict-info), 6c (rule cards), 6d (exact platform pixels) and 6e
(cover facts, with a long-Chinese positive case and an unresolvable-id negative case)
cover the regression. Docs/code parity still checks all nine platform entries.

On the reviewed build: 24 sourced facts, 24 references, 0 restatements, 46.9% information
area, every page above its information-unit floor, `missing=0 blank=0 no-facts=0`, and
`cover 4 declared / 4 printed / 0 clipped`.

## Boundaries

- The persona-by-scenario matrix itself is unchanged. A `rulebook` layout is a later
  phase, waiting on a real campaign before it is designed.
- No financial or insurance safeguard was relaxed: prohibited-claim blocking, the
  persistent disclosure band, source traceability, tone registration and the caption
  length cap all stand.
- The model still never invents a number. Client-confirmed numbers are printed by code
  and still require a source and a human sign-off.
- No campaign asset, client copy, product term or draft deliverable is stored in this
  repository. The reviewed build's outstanding compliance placeholders remain with the
  client's compliance team and are not filled by the skill.
