# WeChat Miniapp Dev

One-stop workflow skill for creating and iterating WeChat Mini Program projects with natural-language guidance.

This skill is designed for non-professional users. It helps start locally first, collect only the information needed for the current task, maintain lightweight project docs, and avoid risky WeChat or Git actions unless the user explicitly confirms them.

## Install

```bash
npx skills@latest add moux1024/moux-skills/skills/wechat-miniapp-dev
```

## Use When

- Creating a new WeChat Mini Program project.
- Iterating an existing Mini Program project.
- Scaffolding a native Mini Program with WeChat Cloud Development.
- Inferring required WeChat capabilities from product requirements.
- Updating Mini Program API and data model documentation.
- Preparing upload, review, or release checklists.

## Default Project Docs

The skill maintains lightweight AI collaboration files inside the target project:

```text
docs/ai/miniapp/
  profile.yaml
  required-info.md
  current-plan.md
  api.md
  data-model.md
  plans/
```

These files record project facts, missing information, implementation plans, API contracts, data models, and archived plans.

## Behavior

For new projects, the default path is native WeChat Mini Program plus WeChat Cloud Development. The skill can create a local scaffold without requiring a real AppID, Git repository, backend repository, or WeChat DevTools setup.

For existing projects, the skill respects the current framework and structure, including native Mini Program, Taro, uni-app, or custom setups. It does not migrate frameworks unless explicitly requested.

## Safety Boundaries

The skill requires explicit confirmation before:

- Creating or switching Git branches.
- Staging, committing, or pushing code.
- Creating a remote repository.
- Triggering CI/CD.
- Uploading a trial version.
- Submitting review.
- Releasing production.

It never writes plaintext secrets into the project repository, never fakes a real AppID, and does not create online WeChat Cloud resources by default.

## References

Supporting reference files live in `references/`:

- `capability-matrix.md`: WeChat capability inference.
- `required-info-policy.md`: Blocking, warning, and optional missing information.
- `templates.md`: Starting templates for project docs.
- `release-checklist.md`: WeChat upload, review, and release checklist.

