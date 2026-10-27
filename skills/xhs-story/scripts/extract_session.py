#!/usr/bin/env python3
"""Extract a readable timeline from a WorkBuddy session transcript (.jsonl).

The transcript is the highest-fidelity record of what actually happened:
every user turn, every assistant turn, every tool call with its arguments,
every tool result including failures. It is the *only* place where the real
friction lives -- the retries, the wrong turns, the moment the question
changed. A story written from memory will smooth all of that away.

Usage:
    python3 extract_session.py --latest                 # newest session of cwd's project
    python3 extract_session.py --session <path.jsonl>
    python3 extract_session.py --list                   # recent sessions across projects
    python3 extract_session.py --latest --scan          # sensitive-item scan too
    python3 extract_session.py --latest --out digest.md
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


def list_sessions(limit=15):
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


def digest(path, max_text=1400, max_result=420):
    recs = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            continue

    t0 = t1 = None
    turns = {"user": 0, "assistant": 0}
    calls = 0
    fails = 0
    written = []
    asked = 0
    body = []
    step = 0

    for rec in recs:
        ts = rec.get("timestamp")
        if isinstance(ts, (int, float)):
            t0 = ts if t0 is None else min(t0, ts)
            t1 = ts if t1 is None else max(t1, ts)

        for kind, payload in blocks(rec):
            if kind == "text":
                role, text = payload
                if not text or role not in ("user", "assistant"):
                    continue
                turns[role] += 1
                step += 1
                clock = ""
                if isinstance(ts, (int, float)):
                    clock = datetime.fromtimestamp(ts / 1000).strftime("%H:%M")
                who = "用户" if role == "user" else "助手"
                body.append("\n### %d · %s %s\n\n%s" % (step, who, clock, clip(text, max_text)))

            elif kind == "call":
                name, args = payload
                calls += 1
                if name == "AskUserQuestion":
                    asked += 1
                if name in ("Write", "Edit"):
                    try:
                        a = json.loads(args)
                        p = a.get("file_path") or a.get("path")
                        if p:
                            written.append(p)
                    except Exception:
                        pass
                note = SIGNAL_MARKS.get(name, "")
                body.append(
                    "  - → `%s`%s %s" % (name, (" · " + note) if note else "", clip(args, 160))
                )

            elif kind == "result":
                name, status, text = payload
                bad = looks_failed(status, text)
                if bad:
                    fails += 1
                flag = "✗失败" if bad else "✓"
                body.append("  - ← %s %s %s" % (flag, name, clip(text, max_result if bad else max_result // 2)))

    dur = ""
    if t0 and t1:
        mins = (t1 - t0) / 60000
        dur = "%d 分钟" % mins if mins < 120 else "%.1f 小时" % (mins / 60)

    seen = []
    for p in written:
        if p not in seen:
            seen.append(p)

    head = [
        "# 会话时间线（原始素材）",
        "",
        "- 文件：`%s`" % path,
        "- 时间：%s → %s（%s）"
        % (
            datetime.fromtimestamp(t0 / 1000).strftime("%Y-%m-%d %H:%M") if t0 else "?",
            datetime.fromtimestamp(t1 / 1000).strftime("%H:%M") if t1 else "?",
            dur or "?",
        ),
        "- 回合：用户 %d / 助手 %d" % (turns["user"], turns["assistant"]),
        "- 工具调用：%d 次，其中失败或报错 %d 次" % (calls, fails),
        "- 用户被问到选择：%d 次" % asked,
        "- 落盘文件：%d 个" % len(seen),
    ]
    if seen:
        head.append("")
        head.append("**产出物**")
        for p in seen[:20]:
            head.append("- `%s`" % p)
    head += [
        "",
        "> 读法：失败次数和「用户被问到选择」的次数，是判断这段素材有没有「承」和「转」的第一手证据。",
        "> 一次都没失败、也没被问过的会话，通常没有转折，故事要按「顺风局」的方式重写。",
        "",
        "---",
    ]
    return "\n".join(head) + "\n" + "\n".join(body) + "\n"


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
            # 116 paths is unreadable; group by parent dir so the user can
            # approve a folder in one glance instead of reading every file.
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

    text = digest(path, max_text=args.max_text)
    if args.scan:
        text += "\n\n" + scan(path)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text)
        print("已写入 %s（%d 字）" % (args.out, len(text)))
    else:
        print(text)


if __name__ == "__main__":
    main()
