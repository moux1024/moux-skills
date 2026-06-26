# Design

This repository is optimized for direct GitHub installation through a CLI such as:

```bash
npx skills@latest add owner/repo/skills/<skill-id>
```

The CLI is expected to:

1. Resolve `owner/repo/path`.
2. Clone `https://github.com/owner/repo.git` into a temporary directory.
3. Locate `SKILL.md` at the requested path or discover all `**/SKILL.md` files.
4. Validate metadata.
5. Copy each skill directory into the local skill store.

## Boundaries

This repository contains skill source files only. It does not need to be an npm package because the install target is a directory, not a Node executable.

## Versioning

Use Git tags for release points:

```bash
git tag v0.1.0
git push origin v0.1.0
```

An installer can also record the commit SHA used during installation.

## Future Registry

`registry.json` is intentionally simple so it can later back a search command:

```bash
npx skills@latest search video
npx skills@latest install example-skill
```

