---
name: code-review
description: 按用户明确请求或提交前已选审查模式执行代码审查，根据变更文件路由到对应子 skills 并汇总结果。不得仅因用户请求 commit 而自动开启；提交前模式选择由 code-review-before-commit 负责。
---

# Code Review (协调者)

## 启动边界

- 用户明确请求代码审查时启动。
- 提交流程只有在用户选择“快速”或“全量”后才启动；选择“不做”时不得启动。
- 不得把“用户请求 commit”本身当作自动触发条件。
- “快速”模式只执行单轮聚焦审查；“全量”模式才执行完整路由，并由 `code-review-before-commit` 管理循环。
- 独立审查请求若未指定深度，默认使用“全量”；用户明确要求快速审查时使用“快速”。

## 职责

代码审查的协调层，负责：
- 获取变更文件列表
- 分析文件路径 → 路由到条件触发审查
- 根据“快速 / 全量”配置审查深度
- 启动 explore agent 执行专项审查
- 汇总所有审查结果
- 按 P0/P1/P2 分类输出审查报告
- 记录问题到 review-issues.md

## 审查流程

### 1. 获取变更

先确定唯一审查范围：

- 提交前审查只使用 `git diff --cached --name-only` 和 `git diff --cached`，保证结论对应精确暂存快照。
- 独立审查按用户指定的 commit/range/diff；未指定时才检查当前工作树，并明确包含已暂存还是未暂存变更。
- 同一轮不得混用暂存与未暂存 diff。

```bash
# 提交前审查
git diff --cached --name-only
git diff --cached

# 独立工作树审查（仅在用户未指定范围时）
git diff --name-only
git diff
```

### 2. 路由决策

根据变更文件路径匹配子 skills：

| 变更路径 | 触发子 Skill | 执行方式 | 说明 |
|----------|-------------|---------|------|
| 任何包含 `*.py` 文件的变更 | `lang-python` | **Agent** | Python 语言 |
| 任何包含 `*.go` 文件的变更 | `lang-go` | **Agent** | Go 语言 |
| 任何包含 `*.js` 或 `*.mjs` 文件的变更 | `lang-js` | **Agent** | JavaScript 语言 |
| 任何包含 `*.ts` 或 `*.tsx` 文件的变更 | `lang-ts` | **Agent** | TypeScript 语言 |
| `web/` 或 `*.jsx` 或 `*.tsx` 文件的变更 | `lang-react` | **Agent** | React 前端 |
| 涉及 `openspec/changes/` 或 `*.md` 设计文档的变更 | `design` | **Agent** | 先进入设计领域，再按产物类型选择审查能力 |
| 涉及 `openspec/changes/` 的变更 | `openspec-docs` | **Agent** | OpenSpec 文档 |
| 涉及权限/角色/认证的变更 | `permissions-review` | **Agent** | 权限审查 |
| 任何包含 `*.yaml` / `*.yml` 文件的变更 | `yaml-format` | **Agent** | YAML 格式检查 |
| **数据管道/指标异常/匹配问题** | `deep-analysis` | **Agent** | 5W2H 深度根因分析（当匹配率低、转化率低、数据管道异常时激活） |
| **快速或全量审查** | `security-review` | **Agent** | 安全审查 |
| **全量审查；快速模式在“变更明确涉及架构设计或结构重构”时追加** | `solid-principles` | **Agent** | SOLID 原则 |
| **全量审查；快速模式在“变更明确涉及坏味道治理或结构重构”时追加** | `code-smells` | **Agent** | 代码坏味道 |
| **快速或全量审查** | `coding-standards` | **Agent** | 通用编码规范 |

**路由规则**：
- 快速模式：只执行一轮，由一个 Agent 合并应用匹配的语言/领域规则、`security-review` 和 `coding-standards`
- 快速模式追加 `solid-principles` 的唯一条件：变更明确涉及架构设计或结构重构
- 快速模式追加 `code-smells` 的唯一条件：变更明确涉及坏味道治理或结构重构
- 全量模式：所有匹配的专项 skill 与四项全局 skill 分别通过 Agent 执行
- 本仓 Skill 统一以规范 `skill_name` 路由，并通过根目录 `skill-domain-mapping.yaml` 解析实际路径
- 语言规则根据文件后缀匹配（含 `lang-` 前缀）
- 全量模式无条件执行安全、SOLID、代码坏味道和通用编码规范；快速模式无条件执行安全与通用编码规范
- 项目特定审查规则由目标项目提供；共享协调器不内置具体项目的测试层级、目录或门禁命令

### 3. 启动条件触发审查

全量模式对路由匹配的子 skill 并行启动 explore agent。快速模式将必要规则合并到一个 explore agent，只执行一轮：

```
Task:
  subagent_type: explore
  prompt: |
    请执行根注册表中 `{skill-name}` 对应路径的审查规则，检查以下变更：

    变更文件:
    {本轮唯一审查范围的文件列表；提交前必须为 git diff --cached --name-only 输出}

    变更内容:
    {本轮唯一审查范围的 diff；提交前必须为 git diff --cached 输出}

    请按照该子 skill 定义的触发条件、审查检查清单和代码示例进行审查，
    按 P0/P1/P2 优先级输出问题列表。
```

### 4. 执行全局审查

全量模式通过 Agent 执行安全审查、SOLID 原则、代码坏味道、通用编码规范审查。快速模式以安全审查与通用编码规范为基础，并在满足唯一条件时追加 SOLID 或代码坏味道规则；所有适用规则合并到单轮聚焦审查。所有名称均先通过根注册表解析，再加载对应规则：

```
Task:
  subagent_type: explore
  prompt: |
    请执行根注册表中 `{skill-name}` 对应路径的审查规则，检查以下变更：

    变更文件:
    {本轮唯一审查范围的文件列表；提交前必须为 git diff --cached --name-only 输出}

    变更内容:
    {本轮唯一审查范围的 diff；提交前必须为 git diff --cached 输出}

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

## 前置条件

- 审查目标非空：用户指定的 commit/range/diff 可解析，或当前工作树存在 `git diff` / `git diff --cached` 变更
- 所有审查子 skill 对应的 SKILL.md 文件可被正常读取
- 只在审查任务需要创建或切换分支时应用 `branch-manager` 的工作区清洁检查；只读历史 commit/range 审查和精确暂存快照审查不要求工作区清洁

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|:------:|
| R0 | 快速审查必须执行安全与通用编码规范；全量审查必须同时执行安全、SOLID、代码坏味道、通用编码规范四项全局审查 | 审查深度与用户选择不一致 |
| R1 | 语言规则必须根据文件后缀自动路由，不得手动选择 | 审查维度不完整，特定领域问题被忽略 |
| R2 | 快速模式使用一个聚焦 Agent；全量模式使用专项 Agent，协调者不得内联替代审查 | 审查上下文或成本偏离所选模式 |
| R3 | 审查结果必须按 P0/P1/P2 三级分类输出 | 优先级混乱，无法区分紧急和可选问题 |
| R4 | 发现问题必须记录到 `review-issues.md`，格式遵循记录模板 | 问题跟踪链断裂，重复审查无效 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 | 实际后果 |
|---------------------|---------|:------:|---------|
| "快速模式可以跳过安全审查" | 单行代码也可以引入 SQL 注入或密钥泄露 | R0 | 安全漏洞逃逸审查 |
| "这次改动都是 .py 文件，只用 lang-python 就够了" | 快速模式还要检查安全与通用规范；全量模式还要执行四项全局审查 | R1 | 全局审查维度被遗漏 |
| "子 skill 结果差不多，我直接汇总就行不用启动 Agent" | 子 skill 包含特定审查逻辑和检查清单 | R2 | 漏掉专项审查中的关键检查项 |
| "这个问题很小，标 P0 有点小题大做" | 小问题可能触发其他模块的连锁失败 | R3 | 实际严重程度被低估，修订优先级倒置 |

## 错误处理

| 环节 | 失败条件 | 处理方式 |
|------|---------|---------|
| 获取变更 | git 命令返回空或无权限 | 检查仓库状态，确认当前目录为 git 仓库 |
| 路由匹配 | 文件路径匹配到多个子 skill | 全部并行启动审查，去重汇总 |
| 路由匹配 | 文件路径未匹配到任何专项 skill | 按模式执行全局审查：快速=安全+通用规范，并继续评估 SOLID/坏味道的唯一追加条件；全量=安全+SOLID+坏味道+通用规范；同时警告路由盲区 |
| Agent 执行 | explore agent 超时或返回错误 | 重试 3 次；仍失败则将本轮标记为 `INCOMPLETE`，不得宣称通过。提交前审查必须停止提交，独立审查须显式报告缺失项 |
| 结果汇总 | 多个子 skill 对同一问题产生重复报告 | 按文件:行号去重，保留优先级最高的问题 |

## 参考文档索引

| 文档 | 用途 |
|------|------|
| `code-review/security-review/SKILL.md` | 安全审查：密钥管理、注入防护、XSS/CSRF |
| `code-review/solid-principles/SKILL.md` | SOLID 原则：SRP/OCP/LSP/ISP/DIP |
| `code-review/code-smells/SKILL.md` | 代码坏味道：长函数、重复代码、God Class |
| `code-review/lang-python/SKILL.md` | Python 编码规范 |
| `coding-standards/SKILL.md` | 跨语言通用编码规范（快速与全量审查均应用） |
| `code-review/lang-go/SKILL.md` | Go 编码规范 |
| `code-review/lang-js/SKILL.md` | JavaScript 编码规范 |
| `code-review/lang-ts/SKILL.md` | TypeScript 编码规范 |
| `code-review/lang-react/SKILL.md` | React 前端编码规范 |
| `code-review/yaml-format/SKILL.md` | YAML 格式检查 |
| `code-review/permissions-review/SKILL.md` | 权限审查 |
| `code-review/openspec-docs/SKILL.md` | OpenSpec 文档审查 |
| `code-review/review-issues.md` | 问题跟踪文件 |

## 最佳实践

1. **及时审查**: 代码提交前或 PR 创建后立即审查
2. **优先级明确**: 清晰区分 P0/P1/P2 问题
3. **建设性反馈**: 提供具体的修复建议，说明原因
4. **记录问题**: 使用 review-issues.md 跟踪问题
5. **持续改进**: 根据审查结果更新代码规范
6. **引用专项文档**: 根据变更内容路由到对应子 skill
7. **尊重开发者**: 代码审查的目的是提高代码质量，不是找茬
