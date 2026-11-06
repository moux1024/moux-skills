#!/usr/bin/env bash
# promo-atlas smoke test
#
# Runs the whole pipeline end to end without spending a single image generation:
#   intake -> validate -> copy gate -> skeleton (+every target) -> fake tiles -> stitch -> audit
#
# Tiles are synthesized as flat grey squares. That is deliberate: this script tests
# plumbing (paths, exit codes, geometry, reflow), not picture quality. A grey tile that
# stitches proves the compositor runs; a beautiful one proves nothing about the code.
#
#   bash tests/smoke.sh          # run, clean up on success
#   KEEP=1 bash tests/smoke.sh   # keep the tmp build dir and print its path
#
# Exit 0 = every stage behaved as documented. Exit 1 = at least one mismatch.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(cd "$HERE/.." && pwd)"
S="$SKILL/scripts"
PY="${PYTHON:-python3}"
# 512 is the smallest cell that still lays out the disclosure band. At 320 the disclosure
# text overflows and stitch exits 1 — that is the layout being honest about a 320px page,
# not a bug, so the smoke test stays above it. Production runs at 2048.
CELL="${CELL:-512}"

if [ -n "${SMOKE_DIR:-}" ]; then
  TMP="$SMOKE_DIR"
  mkdir -p "$TMP"
else
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/promo_atlas_smoke.XXXXXX")"
fi

PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); printf '  ok    %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  FAIL  %s\n' "$1"; shift; for l in "$@"; do printf '        %s\n' "$l"; done; }
row() { printf '\n[%s] %s\n' "$1" "$2"; }

# run <expected-exit> <label> <command...>
run() {
  exp="$1"; label="$2"; shift 2
  out="$("$@" 2>&1)"
  got=$?
  if [ "$got" -eq "$exp" ]; then
    ok "$label  (exit $got)"
  else
    bad "$label  (expected exit $exp, got $got)" "$(printf '%s' "$out" | tail -6)"
  fi
}

# exists <path> <label>
exists() {
  if [ -e "$1" ]; then ok "$2"; else bad "$2" "missing: $1"; fi
}

printf 'promo-atlas smoke  |  python=%s  cell=%s\n  workdir=%s\n' "$PY" "$CELL" "$TMP"

########################################################################
row 1 "intake: physical demo"
########################################################################
run 0 "brief.py --demo" "$PY" "$S/brief.py" --demo -o "$TMP/demo"
for f in brief.json blueprint.json reports/brief_report.md; do
  exists "$TMP/demo/$f" "demo produced $f"
done

########################################################################
row 2 "intake: finance demo (undocumented flag, headline capability)"
########################################################################
run 0 "brief.py --demo-finance" "$PY" "$S/brief.py" --demo-finance -o "$TMP/fin"
cat_check="$("$PY" - "$TMP/fin/brief.json" <<'PY' 2>&1
import json, sys
b = json.load(open(sys.argv[1]))
print(b.get("category") or "")
PY
)"
if [ "$cat_check" = "finance" ]; then
  ok "finance demo carries category=finance"
else
  bad "finance demo carries category=finance" "got: '$cat_check'"
fi

########################################################################
row 3 "validate: the Step 0 command as written in SKILL.md"
########################################################################
run 0 "brief.py <brief.json> validate" "$PY" "$S/brief.py" "$TMP/demo/brief.json"
exists "$TMP/demo/blueprint.draft.json" "draft blueprint always emitted"
run 2 "brief.py --draft is gone (rejected, not silently ignored)" \
  "$PY" "$S/brief.py" "$TMP/demo/brief.json" --draft

########################################################################
row 4 "copy gate: real copy passes, TODO scaffold is refused"
########################################################################
run 0 "lint_copy.py passes the demo copy" \
  "$PY" "$S/lint_copy.py" "$TMP/demo/blueprint.json" -o "$TMP/demo/reports/copy_sheet.md"
exists "$TMP/demo/reports/copy_sheet.md" "copy sheet written"

run 1 "lint_copy.py refuses blueprint.draft.json (all TODO)" \
  "$PY" "$S/lint_copy.py" "$TMP/demo/blueprint.draft.json" -o "$TMP/demo/reports/copy_draft.md"

########################################################################
row 4b "tone gate: no baseline agreed, no copy review"
########################################################################
# The failure this guards: a build went out reading 煽情 because nobody ever wrote down
# what the baseline was supposed to be. The gate is only real if a missing tone fails.
run 0 "demo brief carries voice.tone" "$PY" - "$TMP/demo/brief.json" <<'PY'
import json, sys
b = json.load(open(sys.argv[1]))
print(b.get("voice", {}).get("tone") or "MISSING")
sys.exit(0 if b.get("voice", {}).get("tone") else 1)
PY

"$PY" - "$TMP/demo/brief.json" "$TMP/demo/brief_novoice.json" <<'PY'
import json, sys
b = json.load(open(sys.argv[1]))
b.pop("voice", None)
json.dump(b, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 1 "brief.py refuses a brief with no voice.tone" \
  "$PY" "$S/brief.py" "$TMP/demo/brief_novoice.json"

"$PY" - "$TMP/demo/blueprint.json" "$TMP/demo/blueprint_novoice.json" <<'PY'
import json, sys
bp = json.load(open(sys.argv[1]))
bp["meta"].pop("voice", None)
json.dump(bp, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 1 "lint_copy.py refuses a blueprint with no voice" \
  "$PY" "$S/lint_copy.py" "$TMP/demo/blueprint_novoice.json" \
  -o "$TMP/demo/reports/copy_novoice.md"

# Rule mode is a different contract: every caption must apply a clause and point at the
# policy text. Narrative copy dropped into rule mode must fail, not pass quietly.
"$PY" - "$TMP/demo/blueprint.json" "$TMP/demo/blueprint_rule.json" <<'PY'
import json, sys
bp = json.load(open(sys.argv[1]))
bp["meta"]["voice"]["caption_mode"] = "rule"
json.dump(bp, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 1 "lint_copy.py refuses narrative copy in rule mode" \
  "$PY" "$S/lint_copy.py" "$TMP/demo/blueprint_rule.json" \
  -o "$TMP/demo/reports/copy_rule.md"

########################################################################
row 4c "density gate: a cell has to add a fact, not just exist"
########################################################################
run 0 "lint_density.py passes the demo build" \
  "$PY" "$S/lint_density.py" "$TMP/demo/blueprint.json" \
  -o "$TMP/demo/reports/density_sheet.md"
exists "$TMP/demo/reports/density_sheet.md" "density sheet written"

"$PY" - "$TMP/demo/blueprint.json" "$TMP/demo/blueprint_nofacts.json" <<'PY'
import json, sys
bp = json.load(open(sys.argv[1]))
bp["meta"]["key_facts"] = []
for z in bp["zones"]:
    z["facts"] = []
json.dump(bp, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 1 "lint_density.py refuses a build with no facts" \
  "$PY" "$S/lint_density.py" "$TMP/demo/blueprint_nofacts.json" \
  -o "$TMP/demo/reports/density_nofacts.md"

# The exact 1.1.1 failure: eight cells declared as cards, each with a PNG file and no
# facts on it. A file existing is not a cell saying something.
"$PY" - "$TMP/demo/blueprint.json" "$TMP/demo/blueprint_blankcards.json" <<'PY'
import json, sys
bp = json.load(open(sys.argv[1]))
for z in bp["zones"]:
    z["tile_origin"] = "code_card"
    z["facts"] = []
json.dump(bp, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 1 "lint_density.py refuses declared cards with no facts" \
  "$PY" "$S/lint_density.py" "$TMP/demo/blueprint_blankcards.json" \
  -o "$TMP/demo/reports/density_blankcards.md"

########################################################################
row 5 "gate 2: skeleton, every target previewed"
########################################################################
run 0 "skeleton.py --targets" \
  "$PY" "$S/skeleton.py" "$TMP/demo/blueprint.json" -o "$TMP/demo/skeleton.png" \
  --cell "$CELL" --targets
exists "$TMP/demo/skeleton.png" "skeleton.png rendered"

# The disclosure retry path in make_grid only fires when the band is genuinely too short
# (small cell or many disclosure lines). It was dead code with a TypeError inside, so it
# crashed exactly when it was needed. Assert the path runs, not just that happy paths do.
band_check="$("$PY" - "$TMP/fin/blueprint.json" "$S" <<PY 2>&1
import sys
sys.path.insert(0, "$S")
import promo_layout as pl
bp = pl.load(sys.argv[1])
g, _r, _c = pl.make_grid(bp, cell=320)
print("%d px band at cell 320" % g.footer_h)
PY
)"
if [ $? -eq 0 ]; then
  ok "make_grid survives a band that needs the disclosure retry — $band_check"
else
  bad "make_grid survives a band that needs the disclosure retry" "$band_check"
fi

targets="$(find "$TMP/demo" -maxdepth 1 -name 'skeleton_*.png' | wc -l | tr -d ' ')"
if [ "$targets" -ge 1 ]; then
  ok "per-target previews rendered ($targets file(s))"
else
  bad "per-target previews rendered" "no skeleton_<target>.png found"
fi

########################################################################
row 6 "stitch: full composite, then every channel"
########################################################################
tile_err="$("$PY" - "$TMP/demo/blueprint.json" "$TMP/demo/tiles" "$CELL" <<'PY' 2>&1
import json, os, sys
from PIL import Image
bp, tiles, cell = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = json.load(open(bp))
os.makedirs(tiles, exist_ok=True)
zones = data.get("zones") or []
for z in zones:
    Image.new("RGB", (cell, cell), (190, 190, 186)).save(os.path.join(tiles, z["id"] + ".png"))
print(len(zones))
PY
)"
if [ "$tile_err" -ge 1 ] 2>/dev/null; then
  ok "synthesized $tile_err fake tiles (plumbing only)"
  # The command exactly as SKILL.md Step 8 writes it: no --target at all. This used to fail
  # because the flag defaulted to the literal id "main", which no blueprint has.
  run 0 "stitch.py (documented form, no --target)" \
    "$PY" "$S/stitch.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" \
    -o "$TMP/demo/atlas.png" --cell "$CELL"
  exists "$TMP/demo/atlas.png" "atlas.png composited"
  run 2 "stitch.py --target nosuch exits 2 with the available ids" \
    "$PY" "$S/stitch.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" \
    -o /tmp/nosuch.png --cell "$CELL" --target nosuch
  run 0 "stitch.py --target all" \
    "$PY" "$S/stitch.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" \
    -o "$TMP/demo/atlas.png" --cell "$CELL" --target all
  exists "$TMP/demo/atlas_master.png" "master target written"
  exists "$TMP/demo/atlas_xiaohongshu_p01.png" "carousel page 01 written"

  exists "$TMP/demo/atlas_xiaohongshu_long.png" "long image written"
  # A long image fails in two silent ways: it gets taller than 1:4 (the platform then
  # compresses it into a grey strip) or its column count does not divide the scene count,
  # so a persona's cells split across a fold. Both are arithmetic — check them.
  long_check="$("$PY" - "$TMP/demo/stitch_report.json" "$TMP/demo/blueprint.json" <<'PY' 2>&1
import json, sys
rep = json.load(open(sys.argv[1]))
bp = json.load(open(sys.argv[2]))
ncols = int(bp["meta"]["grid"]["cols"])
t = next((x for x in rep["targets"] if x.get("mode") == "long"), None)
if not t:
    print("no long target in stitch_report"); sys.exit(1)
w, h = t["size"]
errs = []
if h / float(w) > 4.01:
    errs.append("1:%.2f exceeds 1:4" % (h / float(w)))
if t.get("shape") and ncols % t["shape"][0]:
    errs.append("%d columns do not divide %d scenes — persona blocks split" % (
        t["shape"][0], ncols))
if t.get("pad_pct", 0) > 18:
    errs.append("pad %.1f%% — the reflow did not fill the frame" % t["pad_pct"])
if errs:
    print("; ".join(errs)); sys.exit(1)
print("1:%.2f, %dx%d grid, pad %.1f%%" % (h / float(w), t["shape"][0], t["shape"][1],
                                          t["pad_pct"]))
PY
)"
  if [ $? -eq 0 ]; then
    ok "long image holds 1:4 and keeps persona blocks whole — $long_check"
  else
    bad "long image holds 1:4 and keeps persona blocks whole" "$long_check"
  fi
else
  bad "synthesized fake tiles" "$tile_err"
fi

########################################################################
row 6b "stitch: a flat grey tile is not information"
########################################################################
# The smoke tiles are deliberately flat grey. --strict-info is the pixel half of the
# density gate: without it, `placeholder` only counts missing FILES, which is how eight
# empty cards once produced a clean report.
run 0 "stitch.py without --strict-info still renders (plumbing)" \
  "$PY" "$S/stitch.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" \
  -o "$TMP/demo/atlas_nostrict.png" --cell "$CELL"
run 1 "stitch.py --strict-info refuses flat grey tiles" \
  "$PY" "$S/stitch.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" \
  -o "$TMP/demo/atlas_strict.png" --cell "$CELL" --strict-info
blank_check="$("$PY" - "$TMP/demo/stitch_report.json" <<'PY' 2>&1
import json, sys
r = json.load(open(sys.argv[1]))
n = sum(len(t.get("blank_tile") or []) for t in r["targets"])
print(n)
PY
)"
if [ "$blank_check" -ge 1 ] 2>/dev/null; then
  ok "stitch_report.json lists $blank_check blank tiles explicitly"
else
  bad "stitch_report.json lists blank tiles explicitly" "got: $blank_check"
fi

########################################################################
row 6c "rule cards: the fallback has to print facts, not paper"
########################################################################
run 0 "make_rule_card.py renders cards from key_facts" \
  "$PY" "$S/make_rule_card.py" "$TMP/demo/blueprint.json" \
  -d "$TMP/demo/cardtiles" --only z_r1c1,z_r1c2 --size 512
card_check="$("$PY" - "$TMP/demo/cardtiles/z_r1c1.png" "$S" <<'PY' 2>&1
import sys
sys.path.insert(0, sys.argv[2])
import stitch
print("blank" if stitch.tile_is_blank(sys.argv[1]) else "printed")
PY
)"
if [ "$card_check" = "printed" ]; then
  ok "a rule card is not a flat tile"
else
  bad "a rule card is not a flat tile" "got: $card_check"
fi
run 1 "make_rule_card.py refuses a cell with no facts" \
  "$PY" "$S/make_rule_card.py" "$TMP/demo/blueprint_nofacts.json" \
  -d "$TMP/demo/cardtiles_empty" --only z_r1c1 --size 512

########################################################################
row 6d "stitch: delivery pages land on the platform's exact pixels"
########################################################################
# pad_to_ratio can only ADD borders. Before v1.2.1 one carousel shipped a 1242px cover
# beside 1256px inner pages and a 1259px long image — one upload, three resample passes.
# An explicit --cell is a probe and keeps native size; a delivery run has no --cell.
run 0 "stitch.py --target xiaohongshu in delivery form (no --cell)" \
  "$PY" "$S/stitch.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" \
  -o "$TMP/demo/px/atlas.png" --target xiaohongshu
px_check="$("$PY" - "$TMP/demo/px/stitch_report.json" "$S" <<'PY' 2>&1
import json, sys
sys.path.insert(0, sys.argv[2])
import stitch
from PIL import Image

rep = json.load(open(sys.argv[1]))
bound = [t for t in rep["targets"] if t.get("platform_px")]
errs = []
if not bound:
    errs.append("no platform-bound target in report")
for t in bound:
    if t.get("size") != t.get("platform_px") or not t.get("size_exact"):
        errs.append("%s: %s != %s" % (t["id"], t.get("size"), t.get("platform_px")))
    if t.get("size") != [1242, 1656]:
        errs.append("%s: carousel page is not 1242x1656" % t["id"])
if len(bound) < 2:
    errs.append("expected a full carousel, got %d page(s)" % len(bound))

# Long target and master are not rendered here; check their contract directly.
if stitch.platform_px({"type": "long", "platform": "xiaohongshu_long",
                       "ratio": "1:4"}) != (1242, 4968):
    errs.append("long target does not resolve to 1242x4968")
if stitch.platform_px({"type": "full", "ratio": "auto"}) is not None:
    errs.append("master was given a platform size")
img = Image.new("RGB", (1259, 5036), (250, 248, 240))
out, native = stitch.normalize_to_platform(
    img, {"type": "long", "platform": "xiaohongshu_long", "ratio": "1:4"})
if out.size != (1242, 4968) or native != (1259, 5036):
    errs.append("normalize_to_platform did not land on 1242x4968")
if errs:
    print("; ".join(errs)); sys.exit(1)
print("%d carousel pages exact, long=1242x4968, master untouched" % len(bound))
PY
)"
if [ $? -eq 0 ]; then
  ok "platform pixel contract — $px_check"
else
  bad "platform pixel contract" "$px_check"
fi

########################################################################
row 6e "cover: every declared key number is actually printed"
########################################################################
# v1.2.0 capped the fact band at two rows. The density sheet counted four cover facts,
# the takeaway said 四个数字, and the picture showed three. Long Chinese clauses are the
# case that loses a fact; short demo text never would, which is why this needs its own row.
"$PY" - "$TMP/demo/blueprint.json" "$TMP/demo/blueprint_longfacts.json" <<'PY'
import json, sys
bp = json.load(open(sys.argv[1]))
long_facts = [
    {"id": "fc1", "text": "疾病等待期三十日内发生的门急诊费用不予给付",
     "kind": "condition", "source": "client-confirmed:条款截图·等待期"},
    {"id": "fc2", "text": "医保补偿后按剩余金额的百分之八十给付",
     "kind": "number", "source": "client-confirmed:条款截图·给付比例"},
    {"id": "fc3", "text": "告知有医保但未获补偿时按余额百分之四十给付",
     "kind": "number", "source": "client-confirmed:条款截图·给付比例"},
    {"id": "fc4", "text": "单次门急诊给付限额为人民币八百元整",
     "kind": "boundary", "source": "client-confirmed:条款截图·给付限额"},
]
bp["meta"]["key_facts"] = (bp["meta"].get("key_facts") or []) + long_facts
ids = [f["id"] for f in long_facts]
for t in bp["targets"]:
    if t.get("type") == "carousel":
        for p in t.get("pages") or []:
            if p.get("kind") == "cover":
                p["facts"] = ids
json.dump(bp, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 0 "stitch.py prints all four long cover facts" \
  "$PY" "$S/stitch.py" "$TMP/demo/blueprint_longfacts.json" -d "$TMP/demo/tiles" \
  -o "$TMP/demo/fx/atlas.png" --target xiaohongshu --cell "$CELL"
facts_check="$("$PY" - "$TMP/demo/fx/stitch_report.json" <<'PY' 2>&1
import json, sys
r = json.load(open(sys.argv[1]))
c = [t for t in r["targets"] if "facts_declared" in t]
if not c:
    print("no cover stats in report"); sys.exit(1)
t = c[0]
if t["facts_declared"] != 4 or t["facts_printed"] != 4 or t["facts_clipped"] != 0:
    print("declared=%s printed=%s clipped=%s" % (
        t["facts_declared"], t["facts_printed"], t["facts_clipped"])); sys.exit(1)
print("4 declared / 4 printed")
PY
)"
if [ $? -eq 0 ]; then
  ok "long cover facts are not clipped — $facts_check"
else
  bad "long cover facts are not clipped" "$facts_check"
fi

# An id that resolves to nothing must fail, not quietly disappear from the plate.
"$PY" - "$TMP/demo/blueprint_longfacts.json" "$TMP/demo/blueprint_badcover.json" <<'PY'
import json, sys
bp = json.load(open(sys.argv[1]))
for t in bp["targets"]:
    if t.get("type") == "carousel":
        for p in t.get("pages") or []:
            if p.get("kind") == "cover":
                p["facts"] = p["facts"] + ["f_does_not_exist"]
json.dump(bp, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PY
run 1 "stitch.py refuses a cover whose key number is not printed" \
  "$PY" "$S/stitch.py" "$TMP/demo/blueprint_badcover.json" -d "$TMP/demo/tiles" \
  -o "$TMP/demo/bad/atlas.png" --target xiaohongshu --cell "$CELL"

########################################################################
row 7 "audit scaffolding"
########################################################################
run 0 "audit_assets.py --init" \
  "$PY" "$S/audit_assets.py" "$TMP/demo/blueprint.json" -d "$TMP/demo/tiles" --init
exists "$TMP/demo/tiles/audit.json" "audit.json pending records written"
axis_check="$("$PY" - "$TMP/demo/tiles/audit.json" <<'PY' 2>&1
import json, sys
r = json.load(open(sys.argv[1]))
print(",".join(sorted(r[next(iter(r))]["axes"])))
PY
)"
if [ "$axis_check" = "information,intent,plausibility,taste" ]; then
  ok "audit has a fourth information axis"
else
  bad "audit has a fourth information axis" "got: $axis_check"
fi

########################################################################
row 8 "docs <-> code parity: the platform table is not allowed to drift"
########################################################################
# references/social-channels.md duplicates the pixel size and page cap that promo_layout
# owns. When they disagree nothing errors — the script renders at the code's numbers while
# a human signs off against the document's. Cheap to check, silent when wrong: check it.
parity_out="$("$PY" - "$SKILL/references/social-channels.md" "$S" <<'PY' 2>&1
import re, sys
md_path, scripts = sys.argv[1], sys.argv[2]
sys.path.insert(0, scripts)
import promo_layout as pl

md = open(md_path, encoding="utf-8").read()
errs, seen = [], set()

for line in md.splitlines():
    if not line.startswith("| `"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) < 5:
        continue
    key, size, pages = cells[0].strip("`"), cells[3], cells[4]
    spec = pl.PLATFORMS.get(key)
    if spec is None:
        errs.append("%s: in the table, missing from PLATFORMS" % key)
        continue
    seen.add(key)
    m = re.match(r"(\d+)\s*[x×]\s*(\d+)", size)
    if not m:
        errs.append("%s: unreadable size %r" % (key, size))
        continue
    if (int(m.group(1)), int(m.group(2))) != tuple(spec["px"]):
        errs.append("%s: doc says %s, code says %s" % (key, size, spec["px"]))
    if str(pages) != str(spec["max_pages"]):
        errs.append("%s: doc says %s pages, code says %s" % (key, pages, spec["max_pages"]))

for key in sorted(set(pl.PLATFORMS) - seen):
    errs.append("%s: in PLATFORMS, missing from the table" % key)

if errs:
    print("\n".join(errs))
    sys.exit(1)
print("%d platforms in parity" % len(seen))
PY
)"
if [ $? -eq 0 ]; then
  ok "platform table matches PLATFORMS — $parity_out"
else
  bad "platform table matches PLATFORMS" "$parity_out"
fi


########################################################################
printf '\n────────────────────────────────────────\n%d passed, %d failed\n' "$PASS" "$FAIL"

if [ "$FAIL" -eq 0 ] && [ -z "${KEEP:-}" ] && [ -z "${SMOKE_DIR:-}" ]; then
  rm -rf "$TMP"
else
  printf 'artifacts kept: %s\n' "$TMP"
fi

[ "$FAIL" -eq 0 ] || exit 1
