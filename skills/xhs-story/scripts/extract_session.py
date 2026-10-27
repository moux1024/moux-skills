#!/usr/bin/env python3
"""Extract a readable timeline from a WorkBuddy session transcript (.jsonl).

The transcript is the highest-fidelity record of what actually happened:
every user turn, every assistant turn, every tool call with its arguments,
every tool result including failures. It is the *only* place where the real
friction lives -- the retries, the wrong turns, the moment the question
changed. A story written from memory will smooth all of that away.

A long session can hold a year of tool spam: one 11 MB transcript expands to
~450k characters, which will not fit in any context window. So there are
three ways to cut it down before reading:

    --brief        keep the shape, drop the noise (user full, assistant short,
                   tool calls collapsed, failures and decisions kept)
    --grep PAT     only the turns that mention something, plus one neighbour
    --max-chars N  hard ceiling, cut from the middle (keeps both ends)

Usage:
    python3 extract_session.py --latest
    python3 extract_session.py --list
    python3 extract_session.py --session <path.jsonl> --brief --out digest.md
    python3 extract_session.py --session <path.jsonl> --grep 报错
    python3 extract_session.py --latest --scan
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

PROJECTS = os.path.expanduser("~/.workbuddy/projects")

# ---------------------------------------------------------------- discovery

def project_slug(cwd):
    """WorkBuddy stores a project dir named by its cwd with / swapped for -."""
    return os.path.abspath(cwd).strip("/").replace("/", "-")


def project_dir(cwd=None):
    return os.path.join(PROJECTS, project_slug(cwd or os.getcwd()))


def find_latest(cwd=None):
    """Newest .jsonl in this project dir; fall back to newest anywhere."""
    d = project_dir(cwd)
    files = glob.glob(os.path.join(d, "*.jsonl"))
    if not files:
        files = glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def list_sessions(limit=20):
    files = glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))
    files.sort(key=os.path.getmtime, reverse=True)
    rows = []
    for f in files[:limit]:
        rows.append(
            "%s  %6.1f KB  %s  %s"
            % (
                datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M"),
                os.path.getsize(f) / 1024,
                os.path.basename(os.path.dirname(f)),
                f,
            )
        )
    return "\n".join(rows) if rows else "(no transcripts found)"


# ---------------------------------------------------------------- parsing

NOISE = re.compile(
    r"<system-reminder[\s\S]*?</system-reminder>"
    r"|<identity_context>[\s\S]*?</identity_context>"
    r"|<user_info>[\s\S]*?</user_info>",
    re.I,
)


def clean(text):
    text = NOISE.sub("", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def blocks(rec):
    """Yield (kind, payload) for one transcript record."""
    t = rec.get("type")

    if t == "message":
        role = rec.get("role")
        content = rec.get("content")
        if isinstance(content, str):
            yield ("text", (role, clean(content)))
            return
        for b in content or []:
            if not isinstance(b, dict):
                continue
            kind = b.get("type", "")
            if kind.endswith("_text") or kind == "text":
                yield ("text", (role, clean(b.get("text", ""))))
            elif kind == "image_blob_ref":
                yield ("note", "  [image attached]")

    elif t == "function_call":
        name = rec.get("name") or "?"
        args = rec.get("arguments") or ""
        yield ("call", (name, args))

    elif t == "function_call_result":
        name = rec.get("name") or "?"
        status = rec.get("status") or ""
        out = rec.get("output") or {}
        text = out.get("text", "") if isinstance(out, dict) else str(out)
        yield ("result", (name, status, text))


def clip(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n].rstrip() + " …"


def looks_failed(status, text):
    if status and status.lower() not in ("completed", "success", "ok"):
        return True
    low = (text or "").lower()
    return any(
        k in low
        for k in ("error:", "traceback", "failed", "command not found",
                  "no such file", "permission denied", "exit code 1", "exception")
    )


SIGNAL_MARKS = {
    "AskUserQuestion": "决策点（用户在此做了选择）",
    "Write": "写文件（产出）",
    "Edit": "改文件（迭代）",
    "Skill": "调技能",
}

DECISION_TOOLS = {"AskUserQuestion"}
WRITE_TOOLS = {"Write", "Edit"}


def parse(path):
    """Records -> list of turns, each carrying the tool events that followed it."""
    turns = []
    cur = None

    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        ts = rec.get("timestamp")

        for kind, payload in blocks(rec):
            if kind == "text":
                role, text = payload
                if not text or role not in ("user", "assistant"):
                    continue
                cur = {"role": role, "ts": ts, "text": text, "events": []}
                turns.append(cur)
            elif kind == "call":
                name, args = payload
                if cur is None:
                    cur = {"role": "assistant", "ts": ts, "text": "", "events": []}
                    turns.append(cur)
                cur["events"].append(
                    {"kind": "call", "name": name, "args": args, "ts": ts}
                )
            elif kind == "result":
                name, status, text = payload
                if cur is None:
                    continue
                cur["events"].append(
                    {"kind": "result", "name": name, "status": status,
                     "text": text, "ts": ts, "failed": looks_failed(status, text)}
                )
    return turns


# ---------------------------------------------------------------- render

def stats(turns):
    calls = sum(1 for t in turns for e in t["events"] if e["kind"] == "call")
    fails = sum(1 for t in turns for e in t["events"]
                if e["kind"] == "result" and e.get("failed"))
    asked = sum(1 for t in turns for e in t["events"]
                if e["kind"] == "call" and e["name"] in DECISION_TOOLS)
    writes = []
    for t in turns:
        for e in t["events"]:
            if e["kind"] == "call" and e["name"] in WRITE_TOOLS:
                try:
                    a = json.loads(e["args"])
                    p = a.get("file_path") or a.get("path")
                    if p and p not in writes:
                        writes.append(p)
                except Exception:
                    pass
    return dict(
        calls=calls, fails=fails, asked=asked, writes=writes,
        user=sum(1 for t in turns if t["role"] == "user"),
        assistant=sum(1 for t in turns if t["role"] == "assistant"),
    )


def header(path, turns, st):
    ts = [t["ts"] for t in turns if isinstance(t.get("ts"), (int, float))]
    dur = ""
    if ts:
        mins = (max(ts) - min(ts)) / 60000
        dur = "%d 分钟" % mins if mins < 120 else "%.1f 小时" % (mins / 60)

    out = [
        "# 会话时间线（原始素材）",
        "",
        "- 文件：`%s`" % path,
        "- 时间：%s → %s（%s）"
        % (
            datetime.fromtimestamp(min(ts) / 1000).strftime("%Y-%m-%d %H:%M") if ts else "?",
            datetime.fromtimestamp(max(ts) / 1000).strftime("%H:%M") if ts else "?",
            dur or "?",
        ),
        "- 回合：用户 %d / 助手 %d" % (st["user"], st["assistant"]),
        "- 工具调用：%d 次，其中失败或报错 %d 次" % (st["calls"], st["fails"]),
        "- 用户被问到选择：%d 次" % st["asked"],
        "- 落盘文件：%d 个" % len(st["writes"]),
    ]
    if st["writes"]:
        out.append("")
        out.append("**产出物**")
        for p in st["writes"][:20]:
            out.append("- `%s`" % p)

    if not st["fails"] and not st["asked"]:
        out += [
            "",
            "> ⚠ 这次会话没有失败、也没有把选择权交给用户，大概率一路顺风。",
            "> 也就是说它没有真正的「承」和「转」——别硬写起承转合，考虑清单体",
            "> （见 references/story-shapes.md 末节）。",
        ]
    else:
        out += [
            "",
            "> 读法：失败次数和「用户被问到选择」的次数，是判断这段素材有没有",
            "> 「承」和「转」的第一手证据。",
        ]

    out += ["", "---"]
    return "\n".join(out)


def render_turns(turns, brief=False, max_text=1400, max_result=420):
    out = []
    for i, t in enumerate(turns, 1):
        clock = ""
        if isinstance(t.get("ts"), (int, float)):
            clock = datetime.fromtimestamp(t["ts"] / 1000).strftime("%H:%M")
        who = "用户" if t["role"] == "user" else "助手"

        if brief:
            body = clip(t["text"], 900 if t["role"] == "user" else 240)
        else:
            body = clip(t["text"], max_text)

        calls = [e for e in t["events"] if e["kind"] == "call"]
        results = [e for e in t["events"] if e["kind"] == "result"]
        fails = [e for e in results if e.get("failed")]

        if body:
            out.append("\n### %d · %s %s\n\n%s" % (i, who, clock, body))

        if brief:
            # keep only what a story consumes: failures, decisions, writes
            kept = []
            if body and calls:
                kept.append("  - 本轮 %d 次工具调用" % len(calls))
            for e in fails:
                kept.append("  - ← ✗失败 %s %s" % (e["name"], clip(e["text"], 300)))
            for idx, e in enumerate(calls):
                if e["name"] in DECISION_TOOLS:
                    r = results[idx] if idx < len(results) else None
                    kept.append("  - ◆ 决策点 %s" % clip(r["text"] if r else e["args"], 260))
                elif e["name"] in WRITE_TOOLS:
                    try:
                        a = json.loads(e["args"])
                        p = a.get("file_path") or a.get("path") or ""
                        kept.append("  - ✎ %s %s" % (e["name"], clip(p, 120)))
                    except Exception:
                        pass
            if kept:
                out.extend(kept)
            continue

        for e in t["events"]:
            if e["kind"] == "call":
                note = SIGNAL_MARKS.get(e["name"], "")
                out.append("  - → `%s`%s %s"
                           % (e["name"], (" · " + note) if note else "", clip(e["args"], 160)))
            else:
                flag = "✗失败" if e.get("failed") else "✓"
                out.append("  - ← %s %s %s"
                           % (flag, e["name"], clip(e["text"], max_result)))
    return "\n".join(out)


def cut_middle(text, ceiling):
    """Keep both ends; the middle is where tool spam piles up."""
    if len(text) <= ceiling:
        return text
    head = int(ceiling * 0.62)
    tail = max(0, ceiling - head - 300)
    return (
        text[:head]
        + "\n\n[...中间省略 %d 字。用 --grep <关键词> 定位具体片段，或开 --brief 重跑...]\n\n"
        % (len(text) - head - tail)
        + (text[-tail:] if tail else "")
    )


def digest(path, brief=False, grep=None, max_text=1400, max_chars=None):
    turns = parse(path)
    st = stats(turns)

    note = ""
    if grep:
        pat = re.compile(re.escape(grep), re.I)
        keep = set()
        for i, t in enumerate(turns):
            hay = t["text"] + " " + " ".join(
                (e.get("args") or "") + " " + (e.get("text") or "") for e in t["events"]
            )
            if pat.search(hay):
                keep.update({i - 1, i, i + 1})
        picked = [t for i, t in enumerate(turns) if i in keep]
        note = "\n> 已按关键词 `%s` 过滤：%d / %d 轮命中（含前后各一轮）。\n" % (
            grep, len(picked), len(turns))
        turns = picked
    elif not brief and not max_chars:
        size = sum(len(t["text"]) for t in turns) + sum(
            len(e.get("args") or "") + len(e.get("text") or "")
            for t in turns for e in t["events"])
        if size > 120000:
            note = ("\n> ⚠ 原始素材约 %d 字，直接读会吃掉大量上下文。"
                    "建议加 `--brief` 先看骨架，再用 `--grep` 钻细节。\n" % size)

    text = header(path, turns, st) + note + "\n" + render_turns(
        turns, brief=brief, max_text=max_text)
    if max_chars:
        text = cut_middle(text, max_chars)
    return text


# ---------------------------------------------------------------- redaction

PATTERNS = [
    ("绝对路径", re.compile(r"(?:/(?:Users|home|Volumes|private|tmp)/[^\s\"'`）)]+)")),
    ("邮箱", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("疑似密钥", re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{20,})")),
    ("内网地址", re.compile(r"\b(?:10|127|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?")),
    ("手机号", re.compile(r"\b1[3-9]\d{9}\b")),
]


def scan(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    out = ["## 敏感项扫描", ""]
    any_hit = False

    for label, pat in PATTERNS:
        found = set()
        for m in pat.findall(raw):
            v = m.rstrip("\\,;:。、.）)]}\"'`")
            if v:
                found.add(v)
        if not found:
            continue
        any_hit = True
        found = sorted(found, key=len, reverse=True)

        if label == "绝对路径":
            # a hundred paths is unreadable; group by parent dir so the user can
            # approve a folder in one glance instead of reading every file
            groups = {}
            for v in found:
                parent = os.path.dirname(v) or v
                groups[parent] = groups.get(parent, 0) + 1
            out.append("**绝对路径**（%d 个，按目录归组）" % len(found))
            for parent, cnt in sorted(groups.items(), key=lambda x: -x[1])[:8]:
                out.append("- `%s/` — %d 个" % (parent, cnt))
            out.append("")
            continue

        out.append("**%s**（%d 项）" % (label, len(found)))
        for v in found[:10]:
            out.append("- `%s`" % v)
        if len(found) > 10:
            out.append("- …还有 %d 项" % (len(found) - 10))
        out.append("")

    if not any_hit:
        out.append("未发现需要脱敏的内容。")
    else:
        out.append("> 保守脱敏：路径统一替换为「我的电脑」，密钥/邮箱/手机号一律抹掉，")
        out.append("> 项目名与他人姓名默认保留。渲染前把上面这份清单给用户过一眼。")
    return "\n".join(out)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", help="path to a .jsonl transcript")
    ap.add_argument("--latest", action="store_true", help="newest session of this project")
    ap.add_argument("--cwd", help="workspace dir (default: current)")
    ap.add_argument("--list", action="store_true", help="list recent sessions and exit")
    ap.add_argument("--brief", action="store_true",
                    help="compact mode: user turns full, assistant turns short, "
                         "tool calls collapsed, failures/decisions/writes kept")
    ap.add_argument("--grep", help="only turns containing this text, plus one neighbour")
    ap.add_argument("--max-chars", type=int, help="hard ceiling; cuts from the middle")
    ap.add_argument("--scan", action="store_true", help="also scan for sensitive strings")
    ap.add_argument("--out", help="write to this file instead of stdout")
    ap.add_argument("--max-text", type=int, default=1400)
    args = ap.parse_args()

    if args.list:
        print(list_sessions())
        return

    path = args.session or (find_latest(args.cwd) if args.latest or not args.session else None)
    if not path or not os.path.exists(path):
        sys.exit("找不到会话文件。先跑 `--list` 看看有哪些。")

    text = digest(path, brief=args.brief, grep=args.grep,
                  max_text=args.max_text, max_chars=args.max_chars)
    if args.scan:
        text += "\n\n" + scan(path)

    if args.out:
        d = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(d, exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text)
        print("已写入 %s（%d 字）" % (args.out, len(text)))
    else:
        print(text)


if __name__ == "__main__":
    main()
