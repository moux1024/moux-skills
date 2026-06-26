# WeChat Miniapp Dev Skill Design

## Conclusion

`wechat-miniapp-dev` is feasible as a long-term workflow skill for one-stop WeChat Mini Program creation and iteration.

The skill should target non-professional users. It should guide users with natural-language questions, create or update a lightweight project profile, implement code changes when enough context is available, maintain basic project documentation, and require explicit confirmation for risky actions such as creating remote repositories, pushing code, uploading trial versions, submitting review, or releasing production.

It should not be a heavy engineering governance system. The default path should help the user start locally first, then ask for more setup only when the current task truly needs it.

## Positioning

The skill owns the WeChat Mini Program workflow:

- Create new miniapp projects.
- Iterate existing miniapp projects.
- Distinguish new projects from existing projects.
- Default new projects to native WeChat Mini Program plus WeChat Cloud Development.
- Infer WeChat capabilities from user requirements.
- Keep a lightweight project profile and human-readable missing-info notes.
- Generate and archive implementation plans.
- Implement scoped code changes.
- Maintain API and data model docs.
- Run available checks.
- Produce release checklists.

The skill should not default to:

- Enterprise-grade project governance.
- Complex schema migration.
- CI/CD management.
- Test-account or reviewer-account matrices.
- Automatic online WeChat Cloud resource creation.
- Automatic review submission or production release.

## User Model

Assume the user may not understand:

- Git.
- AppID.
- WeChat Cloud Development.
- Backend APIs.
- Mini Program review requirements.
- Build commands.
- Remote repository authorization.

The interaction should therefore be a guide, not a technical form. Ask the fewest questions needed to proceed, then gradually collect more information as the current task requires it.

## Project Files

Default project-owned files:

```text
docs/ai/miniapp/
  profile.yaml
  required-info.md
  current-plan.md
  api.md
  data-model.md
  plans/
```

Advanced files are generated only when needed:

```text
docs/ai/miniapp/workflow.md
docs/ai/miniapp/required-info.yaml
CI/CD config docs
custom release docs
```

## Project Mode

The first initialization branch is always:

```yaml
project_mode: new | existing
```

For `new` projects:

- Do not require an existing AppID, Git repository, backend repo, API docs, test environment, or build command.
- Default to native WeChat Mini Program.
- Default to WeChat Cloud Development.
- Create a local project first.
- Treat AppID, cloud environment, GitHub/Gitee authorization, and upload permissions as action-specific requirements.

For `existing` projects:

- Resolve the target project directory.
- Respect the actual framework, such as native, Taro, or uni-app.
- Do not migrate frameworks unless explicitly requested.
- Detect existing config, commands, and structure where possible.
- Ask for missing information only when the current task needs it.

## Required Info Policy

Missing information is classified by current task:

```text
blocking: The current task cannot safely continue.
warning: The task can continue after user confirmation.
optional: The task can continue without confirmation.
```

Examples:

- Missing AppID is a warning for local project creation, but blocking for trial upload, review submission, and production release.
- Missing GitHub or Gitee authorization is optional for local development, but blocking for remote repo creation and push.
- Missing WeChat DevTools is a warning for ordinary code edits, but blocking for tasks that require preview or upload.
- Missing payment configuration is optional for static pages, but blocking for payment integration.

Warning items require user confirmation before continuing, and the risk should be recorded in `current-plan.md`.

## Natural-Language Intake

Use a minimal question set.

For a new project:

1. Is this a new project or an existing project?
2. What should the miniapp do?
3. What is the project name?
4. Do you already have a WeChat Mini Program AppID? If not, continue with a placeholder or test setup.
5. Where should the project be created locally?
6. Do you want a remote code repository now, or should we start locally?

For an existing project:

1. Is this a new project or an existing project?
2. Where is the project code?
3. What do you want to change?
4. Can the existing WeChat configuration be used?

## Local Form UI

A local form UI is allowed, but it is optional.

The UI service should:

- Be wizard-style and non-technical.
- Hide underlying YAML field names.
- Read and write the current project's `docs/ai/miniapp/profile.yaml`.
- Generate or update `docs/ai/miniapp/required-info.md`.
- Show a change preview before writing.
- Never write plaintext secrets into the project repository.
- Fall back to Markdown/YAML if the service cannot start.

The service configuration should be user-level, not project-level:

```text
~/.codex/wechat-miniapp-dev/config.yaml
```

The skill may use default service settings, then let user-level config override them.

## Capability Matrix

The skill should include a WeChat capability matrix and infer possible needs from user requirements, including:

- Login.
- Phone number authorization.
- Payment.
- Subscribe messages.
- Image upload.
- User-generated content.
- Content security.
- Location.
- Share.
- Cloud functions.
- Privacy and review requirements.

Inferred capabilities are written to the current plan first. They become long-term `profile.yaml` facts only after user confirmation.

## New Project Scaffold

For new projects:

1. Use the user's specified template if provided.
2. Use a confirmed internal scaffold command if provided.
3. Otherwise generate a minimal native WeChat Mini Program plus cloud development scaffold.

Default scaffold:

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

The skill should not:

- Fake a real AppID.
- Create online WeChat Cloud resources by default.
- Deploy cloud functions by default.
- Write secrets into the project.
- Upload a trial version by default.

## Development Workflow

Default flow:

1. Resolve the target project.
2. Determine `new` or `existing`.
3. Read or create `docs/ai/miniapp/profile.yaml`.
4. Ask the minimum natural-language questions needed for the task.
5. Infer WeChat capabilities from the requirement.
6. Classify missing information as blocking, warning, or optional.
7. Stop on blocking items and guide the user to fill missing information.
8. Continue on warning items only after user confirmation.
9. Write `current-plan.md` and archive a copy under `plans/`.
10. Implement scoped code changes.
11. Update `api.md` and `data-model.md` when APIs, cloud functions, or data structures change.
12. Run available checks.
13. Summarize changed files, checks, skipped checks, risks, and next manual actions.
14. Require confirmation before Git mutation, remote repo creation, push, trial upload, review submission, or production release.

## API And Data Docs

Maintain:

```text
docs/ai/miniapp/api.md
docs/ai/miniapp/data-model.md
```

For WeChat Cloud Development:

- `api.md` records cloud function names, purpose, inputs, outputs, and error codes.
- `data-model.md` records collections, fields, indexes, permissions, and sample data.

For self-hosted backends:

- `api.md` records REST, GraphQL, or RPC contracts.
- If OpenAPI exists, link to it and summarize changes.
- `data-model.md` records database or entity changes relevant to the miniapp.

## Coding Principles

Default native miniapp principles:

- Pages handle display, page state, and event binding.
- Business calls go through `services/`.
- Pages should not scatter direct cloud database or cloud function logic.
- Components should have clear inputs and outputs.
- Cloud functions should have one clear responsibility.
- Cloud functions should validate inputs and return stable error codes.
- Sensitive configuration should not be hardcoded.
- Shared style should be extracted instead of repeated.

For Taro, uni-app, or other frameworks:

- Respect the existing project.
- Require project-level workflow notes only when needed.
- Do not migrate frameworks unless requested.

## Git And Repository Policy

Support users who do not use Git.

- Local development can continue without Git.
- Missing Git is a warning, not a blocker.
- Remote repository creation is optional.
- GitHub, Gitee, or GitLab authorization is required only for remote repo creation, push, or CI/CD.

Require confirmation before:

- Creating or switching branches.
- Staging files.
- Committing.
- Pushing.
- Creating a remote repository.
- Triggering CI/CD.

## Release Policy

The skill models release flow, but does not execute release actions by default.

Require explicit confirmation before:

- Uploading a trial version.
- Submitting review.
- Releasing production.

At release time, generate a WeChat platform checklist:

- AppID is real and correct.
- Trial version uploaded successfully.
- Service category matches the app.
- User privacy protection guide is updated.
- Payment, phone, location, album, and other permission descriptions are complete where relevant.
- Subscribe message templates are configured where relevant.
- Review version description is ready.
- Any reviewer account or instructions are handled directly in the WeChat platform.

Do not keep a default test-account or reviewer-account matrix in the project profile.

## Checks

Run what is available:

- File structure checks.
- `app.json` and `project.config.json` sanity checks.
- npm scripts if present.
- Basic JavaScript/JSON syntax checks where reasonable.
- Cloud function and docs consistency checks.

Do not block ordinary code development just because WeChat DevTools or `miniprogram-ci` is unavailable. Those become blocking only for preview, upload, review, or release tasks that require them.

## SKILL.md Draft Outline

```markdown
---
name: wechat-miniapp-dev
description: One-stop WeChat Mini Program development workflow for non-professional users. Use for creating, initializing, iterating, checking, documenting, and preparing release of WeChat Mini Program projects.
---

# WeChat Miniapp Dev

## Purpose
Help non-professional users build and iterate WeChat Mini Program projects end to end.

## User Model
Assume the user may not understand Git, AppID, cloud development, backend APIs, or release review details.

## Core Behavior
Use natural-language guidance first. Ask the fewest questions needed to proceed. Store structured project facts in `docs/ai/miniapp/profile.yaml`.

## Project Resolution
Resolve the target project before editing. Support cwd project, workspace parent, new project path, and existing project path. Never edit, create branches, upload, or publish before target project is clear.

## Project Mode
Always determine `new` or `existing` during initialization.

## Default Choices
For new projects, default to native WeChat Mini Program and WeChat Cloud Development.

## Required Info Policy
Classify missing information as blocking, warning, or optional based on current task and action.

## Form UI
If information is missing, optionally launch the local wizard UI. If unavailable, fall back to Markdown/YAML.

## Capability Inference
Infer WeChat capabilities from user requirements. Confirm before persisting long-term capability choices.

## Development Workflow
Plan, archive, implement, update docs, run available checks, summarize.

## API And Data Docs
Maintain `api.md` and `data-model.md` whenever cloud functions, APIs, or data structures change.

## Git And Release Safety
Read Git state automatically. Confirm before Git mutation, remote repo creation, push, trial upload, review submission, or production release.

## Publishing
Generate WeChat platform operation checklist. Do not auto-submit review or publish by default.

## Checks
Run available local checks. Do not block ordinary development solely because WeChat DevTools or miniprogram-ci is unavailable.

## Output
End with changed files, checks run, skipped checks with reasons, risks, and next manual actions.
```

## Proposed Skill File List

```text
skills/wechat-miniapp-dev/
  SKILL.md
  references/
    workflow.md
    project-resolution.md
    new-project-flow.md
    existing-project-flow.md
    required-info-policy.md
    capability-matrix.yaml
    profile-template.yaml
    plan-template.md
    api-template.md
    data-model-template.md
    form-service-contract.md
    coding-principles-native.md
    release-checklist.md
```
