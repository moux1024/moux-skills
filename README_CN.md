# moux-skills

[English](README.md) | 简体中文

个人 AI agent 技能集合，设计为可直接从 GitHub 安装。

本仓库遵循通用的基于 Git 的技能分发约定：

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill
```

一个技能（skill）就是一个包含 `SKILL.md` 文件的目录。安装器会克隆本仓库、解析请求的路径、校验 `SKILL.md`，然后把该目录复制到本地技能库。

## 目录结构

```text
skills/
  example-skill/
    SKILL.md
    scripts/
registry.json
tools/
  validate-skills.js
```

## 第三方引入的技能（Vendored）

仓库中的部分技能是第三方作品，**原样保留、不做修改**，这样一次克隆即可完整复现可用的环境。它们在 `registry.json` 中以 `upstream`、`license` 和 `vendor` 标签标注，并自带各自的 `LICENSE`：

| 技能 | 上游仓库 | 许可证 |
|---|---|---|
| `humanizer-zh` | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | MIT |

Vendored 技能不在本仓库中修改：修复应提交到上游；如确需本地改动，请在该技能的 `CHANGELOG.md` 中记录，让分歧保持可见。

## 技能约定

每个技能目录必须包含：

- `SKILL.md`
- 带 `name` 和 `description` 的 YAML frontmatter
- 该技能所需的其他脚本、提示词、模板或参考文档

示例：

```md
---
name: Example Skill
description: Demonstrates the repository structure for GitHub-installed skills.
version: 0.1.0
---

# Example Skill

Use this skill when...
```

## 安装方式

按路径安装单个技能：

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill
```

如果 CLI 支持，可以从标签或 commit 安装指定版本：

```bash
npx skills@latest add moux1024/moux-skills/skills/example-skill@v0.1.0
```

如果 CLI 支持仓库级发现，可以一次安装仓库中的全部技能：

```bash
npx skills@latest add moux1024/moux-skills
```

## 校验

```bash
node tools/validate-skills.js
```

校验器会扫描 `skills/**/SKILL.md`，检查必需的元数据，并验证 `registry.json` 指向的都是真实存在的技能目录。

更详细的仓库结构、frontmatter 写法与 vendored 技能策略，见 [AGENTS.md](AGENTS.md)。
