# Repository Guidelines

## Project Structure

This repository stores distributable agent skills. Place each skill under `skills/<skill-id>/` and make `SKILL.md` the canonical entrypoint. Keep optional files such as `scripts/`, `references/`, `prompts/`, and `templates/` inside the owning skill directory.

Repository-level metadata belongs in `registry.json`. General design notes belong in `docs/`.

## Skill Requirements

Every skill must include YAML frontmatter in `SKILL.md` with at least:

- `name`
- `description`

Use lowercase kebab-case for directory names. Keep `SKILL.md` focused on routing, workflow, and contracts. Move long examples or domain rules into `references/`.

## Validation

Run the validator before committing:

```bash
node tools/validate-skills.js
```

The validator checks skill discovery, required metadata, duplicate names, and registry path validity.

## GitHub Install Compatibility

Design skills so a CLI can install them with:

```bash
npx skills@latest add owner/repo/skills/<skill-id>
```

Do not require build steps for basic installation. If scripts need dependencies, document them inside the owning skill.

