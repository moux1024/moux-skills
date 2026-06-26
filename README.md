# moux-skills

Personal AI agent skills designed for direct installation from GitHub.

This repository follows the common Git-based skill distribution convention:

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill
```

A skill is a directory that contains a `SKILL.md` file. The installer clones this repository, resolves the requested path, validates `SKILL.md`, and copies that directory into the local skill store.

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

