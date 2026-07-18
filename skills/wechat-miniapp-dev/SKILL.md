---
name: wechat-miniapp-dev
description: WeChat Mini Program development workflow for non-professional users. Use when the user wants to create, initialize, scaffold, iterate, check, document, upload, review, or release a WeChat Mini Program project.
version: 0.1.1
---

# WeChat Miniapp Dev

Help non-professional users create and iterate WeChat Mini Program projects without turning the work into heavy engineering governance.

## Operating Stance

Guide with natural-language questions. Ask only for information required by the current task, continue locally when safe, and request explicit confirmation before any risky external action.

Assume the user may not understand Git, AppID, WeChat Cloud Development, backend APIs, build commands, remote repository authorization, or Mini Program review requirements.

Treat Tencent's official WeChat Mini Program documentation as the source of truth for framework behavior, APIs, components, configuration, privacy, review, and release requirements. Do not rely on third-party tutorials when official docs cover the topic. When the task touches unfamiliar or version-sensitive Mini Program behavior, read `references/official-docs.md` and route to the linked official page before designing or changing code.

## Project Files

Maintain these files inside the target project:

```text
docs/ai/miniapp/
  profile.yaml
  required-info.md
  current-plan.md
  api.md
  data-model.md
  plans/
```

Create advanced workflow, CI/CD, release, or YAML requirement files only when the current task needs them.

## Workflow

1. Resolve the target project and determine whether the task is for a new or existing project.
   Completion criterion: the target directory and `project_mode: new | existing` are clear before editing.
2. Read or create `docs/ai/miniapp/profile.yaml`.
   Completion criterion: known project facts are captured without inventing AppID, cloud, repository, or secret values. When creating project docs from scratch, read `references/templates.md`.
3. Ask the minimum natural-language questions needed for the current task.
   Completion criterion: every unanswered item is either blocking, warning, or optional under the current task.
4. Check official WeChat documentation when the task depends on platform behavior, configuration, components, APIs, privacy, upload, review, or release rules.
   Completion criterion: official references consulted are recorded in `current-plan.md` under assumptions, risks, or implementation notes. Read `references/official-docs.md` for the documentation map.
5. Infer likely WeChat capabilities from the user request.
   Completion criterion: inferred capabilities are written to `current-plan.md`; persist them to `profile.yaml` only after user confirmation. For capability details, read `references/capability-matrix.md`.
6. Classify missing information.
   Completion criterion: blocking items stop the task, warning items proceed only after confirmation, and optional items do not block. For the policy, read `references/required-info-policy.md`.
7. Write `docs/ai/miniapp/current-plan.md` and archive a copy under `docs/ai/miniapp/plans/`.
   Completion criterion: the plan records scope, assumptions, missing information, inferred capabilities, risks, checks, and explicit confirmations.
8. Implement scoped code or documentation changes.
   Completion criterion: changes stay inside the resolved target project and match its framework.
9. Update `api.md` and `data-model.md` whenever APIs, cloud functions, collections, database fields, permissions, or self-hosted backend contracts change.
   Completion criterion: docs describe the current interface and data shape affected by the task.
10. Run available checks.
   Completion criterion: local structure, JSON/config sanity, package scripts, syntax checks, and relevant consistency checks have run where available; skipped checks have reasons.
11. End with changed files, checks run, skipped checks, risks, official docs consulted, and next manual actions.
    Completion criterion: the user can tell what changed and what still requires WeChat platform or credential access.

## New Projects

For `project_mode: new`:

- Do not require an existing AppID, Git repository, backend repo, API docs, test environment, or build command for local creation.
- Default to native WeChat Mini Program plus WeChat Cloud Development.
- Use the user's specified template when provided.
- Use a confirmed internal scaffold command when provided.
- Otherwise create a minimal local scaffold:

```text
project.config.json
app.json
app.js
app.wxss
sitemap.json
pages/index/
utils/
services/
cloudfunctions/
docs/ai/miniapp/
```

Never fake a real AppID, create online WeChat Cloud resources, deploy cloud functions, write secrets, upload trial versions, submit review, or release production by default.

## Existing Projects

For `project_mode: existing`:

- Resolve the project directory before editing.
- Respect the existing framework, including native, Taro, uni-app, or custom setups.
- Detect existing config, commands, and structure where possible.
- Ask for missing information only when the current task needs it.
- Do not migrate frameworks unless the user explicitly asks.

## Optional Local Form UI

A local wizard UI may be used when it helps collect missing information. It must be non-technical, hide YAML field names, read and write `docs/ai/miniapp/profile.yaml`, update `required-info.md`, preview changes before writing, and never store plaintext secrets in the repository.

Use user-level service configuration at:

```text
~/.codex/wechat-miniapp-dev/config.yaml
```

If the service cannot start, fall back to Markdown and YAML files.

## Coding Principles

For native Mini Program projects:

- Pages own display, page state, and event binding.
- Business calls go through `services/`.
- Pages should not scatter direct cloud database or cloud function logic.
- Components have clear inputs and outputs.
- Cloud functions have one clear responsibility, validate inputs, and return stable error codes.
- Sensitive configuration is not hardcoded.
- Shared styles are extracted instead of repeated.

For Taro, uni-app, or other frameworks, follow the existing project's conventions.

## Git And Release Safety

Read Git state automatically when relevant, but support users who do not use Git. Missing Git is a warning for local development, not a blocker.

Require explicit confirmation before creating or switching branches, staging files, committing, pushing, creating a remote repository, triggering CI/CD, uploading a trial version, submitting review, or releasing production.

For release tasks, generate a WeChat platform checklist instead of auto-publishing. For checklist contents, read `references/release-checklist.md`.
