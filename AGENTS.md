# Repository Guidelines

## Project Structure

This repository stores distributable agent skills, installed directly from GitHub. Current layout:

```text
skills/
  novel-atlas/                 # original skill: SKILL.md + scripts/ + references/
  promo-atlas/                 # original skill: SKILL.md + scripts/ + references/ + tests/
  xhs-story/                   # original skill: SKILL.md + scripts/ + references/
  a-share-core-stock-analysis/ # original skill: SKILL.md + agents/
  wechat-miniapp-dev/          # original skill: SKILL.md + references/ + README(_CN)
  humanizer-zh/                # vendored third-party skill — never edited here
  example-skill/               # minimal template
registry.json                  # one entry per skill, kept in sync
skills-lock.json               # skills this repo consumes from other repos
docs/                          # design notes (design.md, per-skill design docs)
tools/validate-skills.js       # pre-commit validator
```

Every skill is self-contained: supporting files (`scripts/`, `references/`, `agents/`, `tests/`) live inside the owning skill directory, and no skill imports from another. If a skill needs a subset of another one's material, copy the subset into its own `references/` — novel-atlas does exactly this with `references/copy-voice.md`, a plate-scale subset of humanizer-zh.

## Skill Requirements

`SKILL.md` starts with YAML frontmatter. The core keys (example trimmed from `skills/novel-atlas/SKILL.md`):

```yaml
---
name: novel-atlas
description: Turns a full novel into one ultra-high-resolution atlas image that holds its
  timeline, cast and key events, by designing a blueprint of tiled zones and stitching
  locally composited tiles into a single picture. Use when the user wants a 小说全景图,
  人物关系图, 剧情时间线大图, or provides a novel file (.txt/.md/.epub/.docx) and asks
  for one big image of the whole story.
version: 0.5.0
---
```

Conventions:

- Directory names and frontmatter `name` are lowercase kebab-case and identical (`skills/novel-atlas/` ↔ `name: novel-atlas`). `example-skill`'s `Example Skill` is a template-era exception; do not add more.
- `description` is the trigger surface, not a summary: what the skill does, when to reach for it, and the Chinese phrases users actually type (`小说全景图`, `做个小红书图文`). Trigger-rich beats brief — this is what a host uses to decide whether to load the skill. If the text contains `": "`, quote it or write it as a block scalar (`>-`) — an unquoted colon breaks YAML parsing, and the validator rejects it.
- `version` is bumped on every behavioural change, in the same commit as the change.
- Optional keys in use: `description_zh` / `description_en` (xhs-story), `allowed-tools` (humanizer-zh, kept as upstream wrote it).

Keep `SKILL.md` focused on routing, workflow and contracts; push long domain material into `references/` files loaded on demand. No build steps anywhere; runtime dependencies are declared inside the owning skill (novel-atlas: Python 3 + Pillow, in `scripts/requirements.txt`).

## Registry

Every skill has an entry in `registry.json`, updated in the same commit as the skill:

```json
{
  "id": "novel-atlas",
  "name": "Novel Atlas",
  "repo": "moux1024/moux-skills",
  "path": "skills/novel-atlas",
  "version": "0.5.0",
  "tags": ["novel", "visualization", "image", "infographic"]
}
```

- `version` must match the frontmatter. The validator does not check this — staying in sync is on the author.
- Registry `name` is the display title (Title Case); frontmatter `name` is the kebab-case id.
- Vendored skills additionally carry `upstream`, `license` and a `vendor` tag.

## Vendored skills

`humanizer-zh` is third-party work kept **unmodified**, so one clone reproduces a working setup. Do not edit vendored skills in this repo:

- Fixes belong upstream (`op7418/Humanizer-zh`).
- If a local change is unavoidable, record it in that skill's `CHANGELOG.md` so the divergence is visible.
- To reuse vendored material, copy the subset into the consuming skill's `references/` and say where it came from.

## Validation

Run before committing:

```bash
node tools/validate-skills.js
```

It checks that every `skills/<id>/SKILL.md` parses, carries `name` and `description`, that names are unique, that no frontmatter value contains an unquoted `": "` (which YAML parsers reject), and that every `registry.json` path points at a real skill directory. Version sync and description accuracy are not covered — verify those yourself.

## GitHub Install Compatibility

Skills install straight from this repo:

```bash
npx skills@latest add moux1024/moux-skills/skills/novel-atlas
npx skills@latest add moux1024/moux-skills   # repo-level discovery
```

A plain clone-and-copy of a skill directory must yield a working skill — keep each one self-contained.
