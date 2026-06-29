# 微信小程序开发 Skill

用于创建和迭代微信小程序项目的一站式工作流 Skill，重点是用自然语言引导用户完成本地开发、资料补全、文档维护和发布准备。

这个 Skill 面向非专业开发用户。默认先帮助用户在本地启动项目，只收集当前任务真正需要的信息，维护轻量项目文档，并在任何有风险的微信平台或 Git 操作前要求用户明确确认。

## 安装

```bash
npx skills@latest add moux1024/moux-skills/skills/wechat-miniapp-dev
```

## 适用场景

- 创建新的微信小程序项目。
- 迭代已有微信小程序项目。
- 脚手架生成原生小程序和微信云开发结构。
- 根据产品需求推断可能需要的微信能力。
- 更新小程序 API 和数据模型文档。
- 准备体验版上传、提审或正式发布清单。

## 默认项目文档

Skill 会在目标项目内维护轻量 AI 协作文档：

```text
docs/ai/miniapp/
  profile.yaml
  required-info.md
  current-plan.md
  api.md
  data-model.md
  plans/
```

这些文件用于记录项目事实、缺失信息、当前实现计划、API 契约、数据模型和历史计划归档。

## 行为方式

对于新项目，默认使用原生微信小程序加微信云开发。Skill 可以先创建本地脚手架，不要求用户一开始就提供真实 AppID、Git 仓库、后端仓库或微信开发者工具配置。

对于已有项目，Skill 会尊重当前项目的框架和结构，包括原生小程序、Taro、uni-app 或自定义工程。除非用户明确要求，否则不会迁移框架。

## 安全边界

以下操作必须先获得用户明确确认：

- 创建或切换 Git 分支。
- 暂存、提交或推送代码。
- 创建远程仓库。
- 触发 CI/CD。
- 上传体验版。
- 提交微信审核。
- 发布正式版本。

Skill 不会把明文密钥写入项目仓库，不会伪造真实 AppID，也不会默认创建线上微信云开发资源。

## 参考文件

辅助参考文件位于 `references/`：

- `capability-matrix.md`：微信能力推断。
- `required-info-policy.md`：缺失信息的 blocking、warning、optional 分类策略。
- `templates.md`：项目文档初始模板。
- `release-checklist.md`：微信上传、审核和发布检查清单。

