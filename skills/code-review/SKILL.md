---
name: code-review
description: 代码审查协调者：根据变更文件自动路由到对应子 skills，汇总审查结果
---

# Code Review (协调者)

## 职责

代码审查的协调层，负责：
- 获取变更文件列表
- 分析文件路径 → 路由到条件触发审查
- 执行全局审查（安全/SOLID/代码坏味道，始终应用）
- 启动 explore agent 执行专项审查
- 汇总所有审查结果
- 按 P0/P1/P2 分类输出审查报告
- 记录问题到 review-issues.md

## 审查流程

### 1. 获取变更

```bash
# 查看所有变更文件
git diff --name-only

# 查看变更内容
git diff

# 查看已暂存的变更
git diff --cached

# 查看未暂存的变更
git diff
```

### 2. 路由决策

根据变更文件路径匹配子 skills：

| 变更路径 | 触发子 Skill | 执行方式 | 说明 |
|----------|-------------|---------|------|
| `AI_Data/` 或 `skills/datasheet-*` 或 `config.yaml` | `code-review/project-datasheet-parse/SKILL.md` | **Agent** | DatasheetParse 项目 |
| `controller/` 或 `model/` 或 `middleware/` 或 `relay/` | `code-review/project-oneapi/SKILL.md` | **Agent** | One API 项目 |
| `src/pcb_mcp/` 或 `frontend/` 或 `tests/` 或 `AGENTS.md` 或 `pyproject.toml` | `code-review/project-pcb-mcp/SKILL.md` | **Agent** | PCB MCP 项目 |
| 任何包含 `*.py` 文件的变更 | `code-review/lang-python/SKILL.md` | **Agent** | Python 语言 |
| 任何包含 `*.go` 文件的变更 | `code-review/lang-go/SKILL.md` | **Agent** | Go 语言 |
| 任何包含 `*.js` 或 `*.mjs` 文件的变更 | `code-review/lang-js/SKILL.md` | **Agent** | JavaScript 语言 |
| 任何包含 `*.ts` 或 `*.tsx` 文件的变更 | `code-review/lang-ts/SKILL.md` | **Agent** | TypeScript 语言 |
| `web/` 或 `*.jsx` 或 `*.tsx` 文件的变更 | `code-review/lang-react/SKILL.md` | **Agent** | React 前端 |
| 涉及 `openspec/changes/` 或 `*.md` 设计文档的变更 | `design-review/SKILL.md` | **Agent** | 设计文档自动检视（P0/P1 循环修复） |
| 涉及 `openspec/changes/` 的变更 | `code-review/openspec-docs/SKILL.md` | **Agent** | OpenSpec 文档 |
| 涉及权限/角色/认证的变更 | `code-review/permissions-review/SKILL.md` | **Agent** | 权限审查 |
| 任何包含 `*.yaml` / `*.yml` 文件的变更 | `code-review/yaml-format/SKILL.md` | **Agent** | YAML 格式检查 |
| **数据管道/指标异常/匹配问题** | `code-review/deep-analysis/SKILL.md` | **Agent** | 5W2H 深度根因分析（当匹配率低、转化率低、数据管道异常时激活） |
| 任何代码审查 | `code-review/qeda-integration/SKILL.md` | **Agent** | QEDA 测试集成（始终应用） |
| **任何代码审查** | `code-review/security-review/SKILL.md` | **Agent** | 安全审查（始终应用） |
| **任何代码审查** | `code-review/solid-principles/SKILL.md` | **Agent** | SOLID 原则（始终应用） |
| **任何代码审查** | `code-review/code-smells/SKILL.md` | **Agent** | 代码坏味道（始终应用） |

**路由规则**：
- 所有子 skill 统一通过 Agent 执行（条件触发或始终触发）
- 项目规则根据文件路径匹配（含 `project-` 前缀）
- 语言规则根据文件后缀匹配（含 `lang-` 前缀）
- 安全/SOLID/坏味道无条件执行（始终启动 Agent 审查）

### 3. 启动条件触发审查

对路由匹配的子 skill（执行方式为 Agent），并行启动 explore agent：

```
Task:
  subagent_type: explore
  prompt: |
    请执行 `code-review/{subskill-name}/SKILL.md` 中的审查规则，检查以下变更：

    变更文件:
    {git diff --name-only 输出}

    变更内容:
    {git diff 输出}

    请按照该子 skill 定义的触发条件、审查检查清单和代码示例进行审查，
    按 P0/P1/P2 优先级输出问题列表。
```

### 4. 执行全局审查

协调者通过 Agent 执行安全审查、SOLID 原则、代码坏味道审查（这三项为始终触发）：

```
Task:
  subagent_type: explore
  prompt: |
    请执行 `code-review/{skill-name}/SKILL.md` 中的审查规则，检查以下变更：

    变更文件:
    {git diff --name-only 输出}

    变更内容:
    {git diff 输出}

    请按照该子 skill 定义的审查检查清单进行审查，
    按 P0/P1/P2 优先级输出问题列表。
```

### 5. 汇总结果

将所有子 skill 的审查结果合并，按以下优先级分类：

| 优先级 | 类型 | 说明 | 处理 |
|--------|------|------|------|
| P0 | 阻塞性问题 | 安全漏洞、功能错误、类型错误、架构违规 | **必须修复** |
| P1 | 重要问题 | 性能问题、设计不一致、测试缺失、代码质量 | **建议修复** |
| P2 | 改进建议 | 代码风格、注释、优化建议、重构 | 可选修复 |

### 6. 输出审查报告

格式示例：

```markdown
## Code Review 结果

### 📊 统计
- P0 问题：X 个
- P1 问题：Y 个
- P2 问题：Z 个

### 🚨 P0 问题 (必须修复)
1. **问题描述**
   - 文件：`file:line`
   - 问题：详细说明
   - 建议：修复建议

### ⚠️ P1 问题 (建议修复)
...

### 💡 P2 问题 (改进建议)
...

---
**下一步**: 请修复 P0 问题后重新审查。
```

## 问题记录

发现的问题记录到：

```
<project-root>/.opencode/skills/code-review/review-issues.md
```

### 记录模板

```markdown
# Code Review 问题记录

## Change: <change-name> (<date>)

### Round <N> - <date>

#### P0 - 阻塞

| # | 问题描述 | 文件 | 位置 | 建议修复 | 状态 |
|---|----------|------|------|----------|------|
| 1 | ... | file.go | L10 | 建议... | 🔴 |

#### P1 - 重要

| # | 问题描述 | 文件 | 位置 | 建议修复 | 状态 |
|---|----------|------|------|----------|------|
| 1 | ... | file.go | L10 | 建议... | 🔴 |

#### P2 - 建议

| # | 问题描述 | 文件 | 位置 | 建议 | 状态 |
|---|----------|------|------|------|------|
| 1 | ... | file.go | L10 | 建议... | 🔲 |

### 审查结论

P0 X/Y 已修复，P1 X/Y 已修复，P2 X/Y 已修复。

**保留问题**: 列出保留不修复的问题及原因

---
*最后更新：YYYY-MM-DD HH:mm*
```

### 状态标记

- ✅ 已修复
- 🔴 待修复
- 🔲 保留（P2 建议）
- ❌ 拒绝修复（需说明原因）
- ⏸️ 待用户处理

## 最佳实践

1. **及时审查**: 代码提交前或 PR 创建后立即审查
2. **优先级明确**: 清晰区分 P0/P1/P2 问题
3. **建设性反馈**: 提供具体的修复建议，说明原因
4. **记录问题**: 使用 review-issues.md 跟踪问题
5. **持续改进**: 根据审查结果更新代码规范
6. **引用专项文档**: 根据变更内容路由到对应子 skill
7. **尊重开发者**: 代码审查的目的是提高代码质量，不是找茬
