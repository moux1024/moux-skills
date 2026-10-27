#!/usr/bin/env python3
"""Render Xiaohongshu carousel pages: HTML -> PNG via headless Chrome.

Why HTML and not an image model: every Chinese character on these pages must be
a real, correctly-spelled character. Image models garble CJK glyphs, invent
strokes and drop characters. CSS sets type exactly, and re-shooting one page
after a one-word edit costs two seconds.

Why not PIL: precise kerning, line-height, gradients, and image overlays are
CSS's home turf. PIL can do it, but every template becomes arithmetic.

Usage:
    python3 render.py pages.json -o out/pages
    python3 render.py pages.json -o out/pages --sheet       # + contact sheet
    python3 render.py pages.json -o out/pages --only 1,3    # re-shoot pages 1 and 3
    python3 render.py --check                               # verify Chrome works

pages.json:
{
  "slug": "my-story",
  "theme": "paper",              // paper | ink | signal
  "font": "sans",                // sans | serif
  "accent": "#C2401F",           // optional, overrides theme accent
  "pages": [
    {"type": "cover", "kicker": "", "title": "...", "sub": "...", "bg": "cover.png"},
    {"type": "statement", "kicker": "起", "title": "...", "foot": "..."},
    {"type": "cards", "kicker": "承", "title": "...",
     "cards": [{"n": "01", "t": "...", "d": "..."}]},
    {"type": "ledger", "kicker": "转", "title": "...",
     "rows": [{"k": "外包报价", "v": "8000"}, {"k": "我花了", "v": "3 小时"}]},
    {"type": "quote", "kicker": "转", "text": "...", "by": "..."},
    {"type": "shot", "kicker": "合", "title": "...", "img": "shot.png", "cap": "..."},
    {"type": "end", "title": "...", "sub": "...", "cta": "..."}
  ]
}
"""

import argparse
import base64
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

W, H = 1242, 1660
PAD = 104

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]

THEMES = {
    # warm paper, ink text, vermilion accent -- the default for build logs
    "paper": dict(bg="#FBF8F2", ink="#1C1A17", sub="#6B6459", line="#DED6C6",
                  card="#FFFFFF", accent="#C2401F"),
    # dark ground, bone text -- for reflective / statement-heavy pieces
    "ink": dict(bg="#171614", ink="#F2EDE4", sub="#9A938A", line="#332F2A",
                card="#211F1C", accent="#E8A33D"),
    # cool grey with a hard accent -- for tool / data / process stories
    "signal": dict(bg="#F4F5F3", ink="#14171A", sub="#5F686E", line="#D3D8D6",
                   card="#FFFFFF", accent="#00A06B"),
}

FONT_SANS = '"PingFang SC","Hiragino Sans GB","STHeiti","Noto Sans SC",sans-serif'
FONT_SERIF = '"Songti SC","STSong","Songti TC","Noto Serif SC",serif'


# ------------------------------------------------------------------ helpers

def chrome_bin():
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def data_uri(path):
    """Inline an image so the file:// page needs no subresource permission."""
    if not path:
        return None
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(path, "rb") as fh:
        return "data:image/%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())


def units(s):
    """Approximate width in ems: CJK = 1em, latin = 0.55em."""
    n = 0.0
    for ch in s or "":
        n += 1.0 if ord(ch) > 0x2E80 else 0.55
    return n or 1.0


def fit(text, width, max_size, lines=1, min_size=26):
    """Largest font size at which `text` wraps into about `lines` lines."""
    size = width * lines / units(text)
    return int(max(min_size, min(max_size, size)))


def fit_block(text, width, max_size, lines=1, min_size=26):
    """Size for text that may carry explicit line breaks.

    With explicit breaks the block is only correct if the LONGEST authored line
    still fits on one line -- sizing by total length lets a long line wrap into
    an orphan glyph, which is the single most common way a card page dies.
    """
    text = text or ""
    segs = [s for s in text.split("\n") if s.strip()]
    if len(segs) > 1:
        return int(max(min_size, min(max_size, width / max(units(s) for s in segs))))
    return fit(text, width, max_size, lines=lines, min_size=min_size)


def esc(s):
    return (str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def nl2br(s):
    return esc(s).replace("\n", "<br>")


# ------------------------------------------------------------------ page shells

def shell(body, css_vars, extra_css=""):
    return """<!doctype html><html><head><meta charset="utf-8">
<style>
  *{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
  html,body{width:%(w)dpx;height:%(h)dpx;overflow:hidden}
  body{%(vars)s
    font-family:var(--font);color:var(--ink);background:var(--bg)}
  .stage{position:relative;width:%(w)dpx;height:%(h)dpx;padding:%(pad)dpx;
         display:flex;flex-direction:column}
  .kicker{font-size:26px;letter-spacing:.34em;color:var(--accent);
          font-weight:600;text-transform:uppercase}
  .rule{height:1px;background:var(--line);width:100%%}
  .pno{position:absolute;right:%(pad)dpx;bottom:56px;font-size:22px;
       color:var(--sub);letter-spacing:.16em}
  %(extra)s
</style></head><body><div class="stage">%(body)s</div></body></html>""" % dict(
        w=W, h=H, pad=PAD, vars=css_vars, body=body, extra=extra_css)


def theme_vars(t, font):
    fam = FONT_SERIF if font == "serif" else FONT_SANS
    return ("--bg:%s;--ink:%s;--sub:%s;--line:%s;--card:%s;--accent:%s;--font:%s;"
            % (t["bg"], t["ink"], t["sub"], t["line"], t["card"], t["accent"], fam))


# ------------------------------------------------------------------ templates

def t_cover(p, n, total):
    inner_w = W - PAD * 2
    bg = data_uri(p.get("bg"))
    title = p.get("title", "")
    size = fit_block(title, inner_w, 150, lines=2, min_size=54)
    sub = p.get("sub", "")
    bgs = ""
    if bg:
        bgs = (""".stage{background-image:
                    linear-gradient(180deg,rgba(0,0,0,.18),rgba(0,0,0,.62)),url('%s');
                    background-size:cover;background-position:center}
                 .kicker,.h1,.sub{color:#fff}
                 .kicker{color:rgba(255,255,255,.82)}""" % bg)
    body = """
      <div class="kicker">%s</div>
      <div style="flex:1;display:flex;align-items:center">
        <div class="h1" style="font-size:%dpx;line-height:1.14;font-weight:700;
             letter-spacing:-.015em;width:100%%">%s</div>
      </div>
      <div class="sub" style="font-size:33px;line-height:1.58;color:%s">%s</div>
      <div style="height:30px"></div>
      <div class="rule" style="opacity:.55"></div>
      <div style="display:flex;justify-content:space-between;margin-top:26px;
           font-size:23px;color:%s;letter-spacing:.1em">
        <span>%s</span><span>%02d / %02d</span>
      </div>""" % (
        esc(p.get("kicker", "")), size, esc(title),
        "rgba(255,255,255,.8)" if bg else "var(--sub)", nl2br(sub),
        "rgba(255,255,255,.6)" if bg else "var(--sub)",
        esc(p.get("badge", "")), n, total,
    )
    return shell(body, "", bgs)


def t_statement(p, n, total):
    inner_w = W - PAD * 2
    title = p.get("title", "")
    size = fit_block(title, inner_w, 116, lines=3, min_size=44)
    body = """
      <div class="kicker">%s</div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center">
        <div style="width:64px;height:5px;background:var(--accent);margin-bottom:52px"></div>
        <div style="font-size:%dpx;line-height:1.34;font-weight:600;
             letter-spacing:-.01em">%s</div>
      </div>
      <div style="font-size:27px;color:var(--sub);line-height:1.6">%s</div>
      <div class="pno">%02d</div>""" % (
        esc(p.get("kicker", "")), size, nl2br(title), nl2br(p.get("foot", "")), n)
    return shell(body, "", "")


def t_cards(p, n, total):
    inner_w = W - PAD * 2
    cards = p.get("cards", [])[:4]
    title = p.get("title", "")
    tsize = fit_block(title, inner_w, 76, lines=2, min_size=40)
    rows = []
    for c in cards:
        dsize = 29
        rows.append("""
        <div style="background:var(--card);border:1px solid var(--line);
             border-radius:22px;padding:38px 40px;margin-bottom:24px;
             box-shadow:0 2px 0 rgba(0,0,0,.02)">
          <div style="display:flex;align-items:baseline;gap:22px">
            <span style="font-size:26px;font-weight:700;color:var(--accent);
                  letter-spacing:.06em;font-variant-numeric:tabular-nums">%s</span>
            <span style="font-size:40px;font-weight:650;line-height:1.3">%s</span>
          </div>
          %s
        </div>""" % (
            esc(c.get("n", "")), esc(c.get("t", "")),
            ('<div style="font-size:%dpx;line-height:1.62;color:var(--sub);'
             'margin-top:14px;padding-left:52px">%s</div>'
             % (dsize, nl2br(c.get("d", "")))) if c.get("d") else "",
        ))
    body = """
      <div class="kicker" style="margin-bottom:30px">%s</div>
      <div style="font-size:%dpx;font-weight:700;line-height:1.24;
           margin-bottom:44px;letter-spacing:-.01em">%s</div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center">
        %s
      </div>
      <div class="pno">%02d</div>""" % (
        esc(p.get("kicker", "")), tsize, nl2br(title), "".join(rows), n)
    return shell(body, "", "")


def t_ledger(p, n, total):
    inner_w = W - PAD * 2
    title = p.get("title", "")
    tsize = fit_block(title, inner_w, 84, lines=2, min_size=40)
    rows = []
    items = p.get("rows", [])[:4]
    for i, r in enumerate(items):
        rows.append("""
        <div style="display:flex;align-items:baseline;justify-content:space-between;
             gap:40px;padding:38px 0;border-bottom:1px solid var(--line)">
          <span style="font-size:30px;color:var(--sub);letter-spacing:.04em;
                flex:0 0 32%%;max-width:32%%">%s</span>
          <span style="font-size:%dpx;font-weight:700;letter-spacing:-.02em;
                font-variant-numeric:tabular-nums;text-align:right;
                flex:1 1 auto;color:%s">%s</span>
        </div>""" % (
            esc(r.get("k", "")),
            fit(str(r.get("v", "")), inner_w * 0.58, 92, lines=1),
            "var(--accent)" if i % 2 else "var(--ink)",
            esc(r.get("v", "")),
        ))
    body = """
      <div class="kicker" style="margin-bottom:30px">%s</div>
      <div style="font-size:%dpx;font-weight:700;line-height:1.26;
           margin-bottom:26px;letter-spacing:-.01em">%s</div>
      <div>%s</div>
      <div style="flex:1"></div>
      <div style="font-size:26px;color:var(--sub);line-height:1.6">%s</div>
      <div class="pno">%02d</div>""" % (
        esc(p.get("kicker", "")), tsize, nl2br(title), "".join(rows),
        nl2br(p.get("foot", "")), n)
    return shell(body, "", "")


def t_quote(p, n, total):
    inner_w = W - PAD * 2
    text = p.get("text") or p.get("title", "")
    size = fit_block(text, inner_w, 104, lines=3, min_size=44)
    body = """
      <div class="kicker">%s</div>
      <div style="flex:1;display:flex;align-items:center">
        <div>
          <div style="font-size:120px;line-height:.7;color:var(--accent);
               font-family:%s;margin-bottom:30px">“</div>
          <div style="font-size:%dpx;line-height:1.42;font-weight:600;
               letter-spacing:-.01em">%s</div>
        </div>
      </div>
      <div style="font-size:27px;color:var(--sub)">%s</div>
      <div class="pno">%02d</div>""" % (
        esc(p.get("kicker", "")), FONT_SERIF, size, nl2br(text),
        esc(p.get("by", "")), n)
    return shell(body, "", "")


def t_shot(p, n, total):
    inner_w = W - PAD * 2
    title = p.get("title", "")
    tsize = fit_block(title, inner_w, 66, lines=2, min_size=38)
    img = data_uri(p.get("img"))
    if img:
        frame = ('<div style="border-radius:20px;overflow:hidden;'
                 'border:1px solid var(--line);background:var(--card);flex:1;'
                 'display:flex;align-items:center;justify-content:center">'
                 '<img src="%s" style="max-width:100%%;max-height:100%%;'
                 'object-fit:contain;display:block"></div>' % img)
    else:
        frame = ('<div style="flex:1;border:2px dashed var(--line);border-radius:20px;'
                 'display:flex;align-items:center;justify-content:center;'
                 'color:var(--sub);font-size:28px">（真截图占位）</div>')
    body = """
      <div class="kicker" style="margin-bottom:28px">%s</div>
      <div style="font-size:%dpx;font-weight:700;line-height:1.24;
           margin-bottom:38px;letter-spacing:-.01em">%s</div>
      %s
      <div style="font-size:27px;color:var(--sub);line-height:1.55;
           margin-top:34px;min-height:44px">%s</div>
      <div class="pno">%02d</div>""" % (
        esc(p.get("kicker", "")), tsize, nl2br(title), frame,
        nl2br(p.get("cap", "")), n)
    return shell(body, "", "")


def t_end(p, n, total):
    inner_w = W - PAD * 2
    title = p.get("title", "")
    size = fit_block(title, inner_w, 104, lines=2, min_size=44)
    body = """
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center">
        <div style="font-size:%dpx;font-weight:700;line-height:1.3;
             letter-spacing:-.01em;margin-bottom:40px">%s</div>
        <div style="width:64px;height:5px;background:var(--accent);
             margin-bottom:40px"></div>
        <div style="font-size:32px;line-height:1.66;color:var(--sub)">%s</div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:flex-end">
        <div style="font-size:26px;color:var(--sub);letter-spacing:.06em">%s</div>
        <div style="font-size:24px;color:var(--sub)">%02d / %02d</div>
      </div>""" % (
        size, nl2br(title), nl2br(p.get("sub", "")),
        esc(p.get("cta", "")), n, total)
    return shell(body, "", "")


TEMPLATES = {
    "cover": t_cover,
    "statement": t_statement,
    "cards": t_cards,
    "ledger": t_ledger,
    "quote": t_quote,
    "shot": t_shot,
    "end": t_end,
}


# ------------------------------------------------------------------ render

def build_html(spec, theme, font):
    pages = spec.get("pages", [])
    total = len(pages)
    out = []
    for i, p in enumerate(pages, 1):
        kind = p.get("type", "statement")
        if kind not in TEMPLATES:
            raise SystemExit("未知页型：%s（可用：%s）" % (kind, ", ".join(TEMPLATES)))
        html = TEMPLATES[kind](p, i, total)
        html = html.replace("<style>", "<style>:root{%s}" % theme_vars(theme, font), 1)
        out.append(html)
    return out


def shoot(browser, html, png, tmpdir, idx):
    f = os.path.join(tmpdir, "p%02d.html" % idx)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(html)
    cmd = [
        browser, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--hide-scrollbars", "--force-device-scale-factor=1",
        "--window-size=%d,%d" % (W, H),
        "--virtual-time-budget=3000",
        "--screenshot=" + png,
        "file://" + f,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(png), r.stderr[-400:]


def sheet(pngs, out_path):
    try:
        from PIL import Image
    except ImportError:
        return False
    thumbs = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        im.thumbnail((310, 414))
        thumbs.append(im)
    if not thumbs:
        return False
    gap = 12
    w = sum(t.width for t in thumbs) + gap * (len(thumbs) + 1)
    h = max(t.height for t in thumbs) + gap * 2
    canvas = Image.new("RGB", (w, h), (240, 238, 233))
    x = gap
    for t in thumbs:
        canvas.paste(t, (x, gap))
        x += t.width + gap
    canvas.save(out_path)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?", help="pages.json")
    ap.add_argument("-o", "--out", default="pages", help="output dir for PNGs")
    ap.add_argument("--sheet", action="store_true", help="also write contact sheet")
    ap.add_argument("--only", help="comma separated page numbers to re-shoot")
    ap.add_argument("--check", action="store_true", help="verify Chrome is usable")
    args = ap.parse_args()

    browser = chrome_bin()
    if not browser:
        sys.exit("找不到 Chrome / Edge / Chromium。先装 Chrome，或改用 PIL 兜底渲染。")
    if args.check:
        print("Chrome: %s" % browser)
        return

    if not args.spec:
        sys.exit("需要一个 pages.json")

    spec = json.load(open(args.spec, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(args.spec))

    # resolve relative image paths against the spec file, not the cwd
    for p in spec.get("pages", []):
        for key in ("bg", "img"):
            v = p.get(key)
            if v and not os.path.isabs(v):
                p[key] = os.path.join(base, v)

    theme = dict(THEMES.get(spec.get("theme", "paper"), THEMES["paper"]))
    if spec.get("accent"):
        theme["accent"] = spec["accent"]

    htmls = build_html(spec, theme, spec.get("font", "sans"))
    os.makedirs(args.out, exist_ok=True)
    pngs = []

    only = None
    if args.only:
        only = {int(x) for x in args.only.split(",") if x.strip().isdigit()}

    tmpdir = tempfile.mkdtemp(prefix="xhs-")
    ok, fail = 0, []
    try:
        for i, html in enumerate(htmls, 1):
            png = os.path.join(args.out, "%02d.png" % i)
            pngs.append(png)
            if only and i not in only:
                continue
            done, err = shoot(browser, html, png, tmpdir, i)
            if done:
                ok += 1
            else:
                fail.append((i, err))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("渲染完成：%d/%d 张 → %s" % (ok, len(htmls), args.out))
    for i, err in fail:
        print("  第 %d 张失败：%s" % (i, err))

    if args.sheet:
        s = os.path.join(os.path.dirname(os.path.abspath(args.out)), "contact-sheet.png")
        if sheet([p for p in pngs if os.path.exists(p)], s):
            print("预览拼版：%s" % s)

    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
