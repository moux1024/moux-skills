# moux-skills

[English](README.md) | [简体中文](README_CN.md)

Personal AI agent skills designed for direct installation from GitHub.

This repository follows the common Git-based skill distribution convention:

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill
```

A skill is a directory that contains a `SKILL.md` file. The installer clones this repository, resolves the requested path, validates `SKILL.md`, and copies that directory into the local skill store.

## Skills

| Skill | What it does |
|---|---|
| [novel-atlas](skills/novel-atlas/) | Turns a full novel into one ultra-high-resolution atlas image: timeline, cast and irreversible events on a single tiled canvas, composited locally. |
| [promo-atlas](skills/promo-atlas/) | Turns a launch brief into a persona-by-scenario master board plus per-channel deliverables (Xiaohongshu, Douyin, WeChat, Weibo), with compliance gating. |
| [xhs-story](skills/xhs-story/) | Turns a real "idea → shipped" process into a 7-page Xiaohongshu carousel plus a paste-ready caption, structured as 起承转合. |
| [a-share-core-stock-analysis](skills/a-share-core-stock-analysis/) | Reads institutional behavior on A-share core holdings through market regime, ETF flows, relative strength, chip distribution and national-team cost zones. |
| [wechat-miniapp-dev](skills/wechat-miniapp-dev/) | One-stop WeChat Mini Program workflow for non-professional users: scaffold, iterate, document, check, release. |
| [humanizer-zh](skills/humanizer-zh/) | Edits Chinese prose to strip filler and template phrasing while keeping the author's voice. Third-party, kept unmodified (see below). |
| [example-skill](skills/example-skill/) | Minimal template demonstrating the repository structure. |

Install any of them by path: `npx skills@latest add moux1024/moux-skills/skills/<skill-id>`.

## Layout

```text
skills/
  example-skill/
    SKILL.md
    scripts/
registry.json
tools/
  validate-skills.js
```

## Vendored Skills

Some skills here are third-party work kept **unmodified**, so that one clone reproduces a working setup. They are marked in `registry.json` with `upstream`, `license` and the `vendor` tag, and they ship with their own `LICENSE`:

| Skill | Upstream | License |
|---|---|---|
| `humanizer-zh` | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | MIT |

Vendored skills are not edited here. Fixes belong upstream; if a local change is unavoidable, record it in that skill's `CHANGELOG.md` so the divergence is visible.

## Skill Contract

Each skill directory must contain:

- `SKILL.md`
- YAML frontmatter with `name` and `description`
- Any supporting scripts, prompts, templates, or references needed by that skill

Example:

```md
---
name: Example Skill
description: Demonstrates the repository structure for GitHub-installed skills.
version: 0.1.0
---

# Example Skill

Use this skill when...
```

## Install Patterns

Install one skill by path:

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill
```

Install from a tag or commit if supported by the CLI:

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill@v0.1.0
```

Install all skills in the repository if the CLI supports repository-level discovery:

```bash
npx skills@latest add moux1024/moux-skills
```

## Validate

```bash
node tools/validate-skills.js
```

The validator scans `skills/**/SKILL.md`, checks required metadata, and verifies that `registry.json` points at real skill directories.

