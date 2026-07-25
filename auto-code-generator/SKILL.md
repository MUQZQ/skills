---
name: auto-code-generator
description: 强制 spec 驱动全流程自动化 — 从提案到归档再到自动提交，必须执行 TDD 红绿循环、Code Review 5 轮审查、真实数据验证，所有关卡必须通过才允许进入下一阶段
---

# 自动代码生成器 v3.0

## 概述

通用化的完整 spec 驱动全流程自动化 skill。**强制执行**从用户描述出发，依次经历 **探索 → 变更拆分 → 提案生成 → 一致性校验 → 代码实施（TDD+Code Review）→ 全流程校验（构建 + 测试 + 真实数据）→ 归档 → 最终报告 → 项目子 skills 更新** 九个 phase。

**核心原则**: 每个 Phase 结束时必须有明确的 GATE CHECK（关卡检查），任何一项失败立即阻断，禁止跳过。

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|:------:|
| R0 | TDD 红绿循环不可跳过 — 每个 task 实现后必须先写测试（红），再实现代码（绿），再重构 | 代码没有测试保护，退化风险不可控 |
| R1 | Code Review 不可跳过 — 每个变更完成后必须经过 5 轮审查，P0/P1 问题必须清零 | 安全漏洞或架构问题逃逸到生产 |
| R2 | Spec 一致性校验不可跳过 — 实施前必须校验 proposal ↔ design ↔ tasks 一致性 | 实现与设计偏差，后期返工成本巨大 |
| R3 | 全流程校验不可跳过 — 构建 + 单元测试 + 真实数据验证 + 任务完成度 + artifact 完成度 全部通过 | 未验证的代码进入归档，最终交付物质量无保障 |
| R4 | 归档后再提交不可跳过 — 必须先执行 `openspec-archive-change`，再执行 `git commit` | 提交顺序混乱，归档记录与 git 历史不一致 |
| R5 | 项目子 skills 更新不可跳过 — 执行后自动识别新模式并更新项目规则 | 新发现的模式未被记录，后续重复踩坑 |
| R6 | GATE CHECK 任一失败立即阻断，禁止跳过 | 带伤进入下一阶段，累计错误不可收拾 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 | 实际后果 |
|---------------------|---------|:------:|---------|
| "这个 task 很简单，直接写代码跳过测试" | 简单的代码也可能引入边界 bug | R0 | 退化未被发现，后续 Phase 可能因这个问题全线崩溃 |
| "一致性校验报了 2 个警告，不严重，继续实施" | GATE CHECK 没通过就是没通过，没有"不严重" | R2, R6 | 设计偏差在实施中放大，最终返工重写 |
| "构建失败了，但不影响核心逻辑，先归档再修复" | 构建失败意味着有编译错误或依赖问题 | R3, R6 | 归档了不可编译的代码，其他依赖此变更的任务全部受阻 |
| "真实数据验证跑不过，应该是测试数据问题而不是代码问题" | 99% 的情况下就是代码问题 | R3 | 上线后用真实数据暴露 bug，hotfix 成本远高于追查 |
| "5 轮 Code Review 太费时间，跑 2 轮没 P0 就够了" | P0 可能在第 3-5 轮审查中被不同角度发现 | R1 | 漏网的 P0 问题在归档后被发现，需要开新变更修复 |

## 参考文档索引

| 文档 | 用途 |
|------|------|
| `openspec-propose` skill | 生成 proposal.md + design.md + tasks.md |
| `code-review-before-commit` skill | 5 轮审查循环 + 用户确认 + git commit |
| `code-review` skill | 审查路由协调者，按文件类型分派子审查 |
| `openspec-archive-change` skill | 归档变更 + delta spec 同步 |

## 输出质量指标

| 指标 | 目标值 | 检查方法 |
|------|--------|---------|
| TDD 循环完成率 | 100% (每个 task 必须经过红→绿→重构) | Phase 4 完成报告 |
| Code Review 通过率 | 100% (所有 P0/P1 清零) | Phase 4 Gate Check |
| 一致性校验通过率 | 100% (所有检查项均为 ✅) | Phase 3 Gate Check |
| 全流程校验通过率 | 100% (5 项检查全部通过) | Phase 5 Gate Check |
| 真实数据验证通过率 | 100% | Phase 5.3 |
| 并行加速比 | 实际并行数(最优组) | Phase 4 完成报告 |

## 完整流程

```
Phase 0  探索阶段（可选）       explore → explore-review (最多 3 次循环)
Phase 1  变更拆分（可选）       大需求拆分为多个变更，构建变更 DAG
Phase 2  提案生成 + 工件检视    openspec-propose → artifact-review
Phase 3  一致性校验            内置校验逻辑 + 跨变更一致性 [GATE]
Phase 4  代码实施 + TDD+Code Review  DAG 分组 → 多 Agent 并行 → TDD 红绿 → 5 轮审查 [GATE]
Phase 5  全流程校验            构建 + 单元测试 + 真实数据验证 + 任务 + artifact [GATE]
Phase 6  归档与提交            openspec-archive-change → git commit (全自动)
Phase 7  最终报告              所有变更的处理结果和偏差记录
Phase 8  项目子 skills 更新     识别新模式 → 生成更新建议 → 用户确认
```

## 无人值守运行

管线启动后自动执行，仅在以下情况中断等待用户输入：
- 需求不明确需要澄清（Phase 0）
- 拆解结果需要确认（Phase 1）
- critical 级别检视不通过需要决策（任何 Phase）
- 项目子 skills 更新建议确认（Phase 8）

**其他所有情况必须自动修复，禁止中断**。

---

## Phase 0: 探索阶段（可选）

**触发条件**:
- 需求描述模糊，需要进一步澄清
- 涉及多个模块，影响范围不明确
- 技术方案存在多种选择，需要评估

**流程**:
```
Phase 0 探索循环 (最多 3 次):
  1. 调用 explore subagent 分析需求背景、技术选型、潜在风险
  2. 调用 explore-reviewer 检视探索输出
  3. 若 verdict=PASS，退出循环，进入 Phase 1
  4. 若 NEEDS_CLARIFICATION，追加反馈后重新 explore
  5. 3 次上限后：使用最后一次方案，记录未解决问题，进入 Phase 1
```

**输出**:
- 需求澄清文档（可选）
- 技术可行性分析
- 是否需要正式变更的决策建议

---

## Phase 1: 变更拆分（可选）

**触发条件**:
- **自动判断**: 预估任务数 > 15，或影响模块数 > 3，或复杂度评分 > 0.7
- **用户显式指定**: 用户明确要求拆分

**拆分算法**:
```
1. 识别需求中的功能点（通过 NLP 或规则）
2. 按模块/工具组聚类功能点
3. 分析功能点间的依赖关系
4. 生成有向无环图 (DAG)
5. 拓扑排序得到有序变更列表
```

**输出格式**:
```json
{
  "changes": [
    {
      "name": "add-feature-core",
      "description": "实现核心功能",
      "dependencies": [],
      "estimated_tasks": 8
    },
    {
      "name": "add-feature-tools",
      "description": "创建 MCP 工具",
      "dependencies": ["add-feature-core"],
      "estimated_tasks": 6
    }
  ]
}
```

**约束**: 单次运行建议不超过 5 个变更，变更间按 DAG 并行执行。

---

## Phase 2: 提案生成 + 工件检视

调用 `openspec-propose` skill，从用户描述生成完整的 spec artifact 集合：

- **proposal.md** — 变更名称、目的、背景、预期效果
- **design.md** — 技术方案、架构设计、接口定义
- **tasks.md** — 按依赖顺序拆解的实施任务列表

**产出**: `openspec/changes/<change-name>/` 目录及所有 artifact 文件。

**执行**:
```
Skill: openspec-propose
输入：用户描述的需求
输出：proposal.md, design.md, tasks.md
```

**验证**: 确认三个文件都生成成功，任一文件缺失则失败并返回 Phase 1。

---

## Phase 3: 一致性校验（GATE）

在开始实施前，**必须**校验三个核心 artifact 之间的一致性。**任何一项失败立即阻断，禁止进入 Phase 4**。

### 3.1 运行状态检查

```bash
openspec status --change "<name>" --json
```

确认所有 `applyRequires` 类型 artifact 状态为 `done`。

**失败处理**: 若有 artifact 状态不是 `done`，返回 Phase 2 补充生成。

### 3.2 proposal ↔ design 一致性

- [ ] proposal.md 中的功能描述是否全部在 design.md 中有对应技术方案
- [ ] design.md 中的接口/组件/模型是否与 proposal.md 的功能范围一致（无遗漏、无超出）

**失败处理**: 任一检查失败，返回 Phase 2 补充 artifact。

### 3.3 design ↔ tasks 一致性

- [ ] design.md 中的每个设计点是否都对应 tasks.md 中的至少一个 task
- [ ] tasks.md 中的每个 task 是否都能在 design.md 中找到实现依据
- [ ] tasks.md 的排序是否符合依赖关系（先 model → handler/service → router → test）

**失败处理**: 任一检查失败，返回 Phase 2 补充 artifact。

### 3.4 任务原子性检查

- [ ] 每个 task 应该是独立的、可验证的最小实现单元
- [ ] 每个 task 对应明确的文件变更范围

**失败处理**: 任一检查失败，返回 Phase 2 拆分 task。

### 3.5 校验报告

```
== Phase 3 一致性校验报告 ==

| 检查项 | 状态 | 说明 |
|--------|------|------|
| artifact 状态 | ✅/❌ | 所有 applyRequires 为 done |
| proposal ↔ design | ✅/❌ | 功能范围一致 |
| design ↔ tasks | ✅/❌ | 设计点全部覆盖 |
| 任务原子性 | ✅/❌ | 每个 task 独立可验证 |

**结果**: 通过/失败
```

**通过条件**: 所有检查项均为 ✅

**失败处理**: 返回 Phase 2 补充 artifact，**禁止进入 Phase 4**。

---

## Phase 4: 代码实施 + TDD + Code Review（GATE）

引入 DAG 分组 + 多 Agent 并行机制，**每个 task 必须执行 TDD 红绿循环**，每组完成后**必须**执行 `code-review-before-commit` 5 轮审查。

### 4.1 加载 code-review 技能

每个 group 开始实施前，加载审查规则：
```
Skill: code-review
```

审查规则自动路由：
- `code-review/security-review` — 安全审查（始终应用）
- `code-review/solid-principles` — SOLID 原则（始终应用）
- `code-review/code-smells` — 代码坏味道（始终应用）
- `code-review/lang-*` — 语言规则（按文件类型）
- `code-review/project-*` — 项目规则（按项目特征）

### 4.2 DAG 分组与并行执行

#### 4.2.1 依赖分析

读取 `tasks.md`，自动分析 task 间的依赖关系，构建有向无环图（DAG）：

```
识别规则:
1. 标记为 `- [ ]` 的为待办 task
2. task 描述中包含"依赖"、"先完成"、"基于"等关键词
3. 常见依赖模式:
   - Model → Service → Handler → Router
   - DTO → Service
   - Interface → Implementation
   - Core → Extension
```

#### 4.2.2 分组策略

按 DAG 的拓扑排序将 task 分组：

```
Group 1: 无前置依赖的 task，可并行执行
Group 2: 依赖 Group 1 全部完成的 task，可并行执行
Group N: 依赖 Group N-1 全部完成的 task，可并行执行
```

**分组输出格式**:
```
== DAG 分组结果 ==

Group 1 (可并行：2 tasks):
  - [ ] 1. 创建 User 模型
  - [ ] 2. 创建 User DTO

Group 2 (依赖 Group 1):
  - [ ] 3. 实现 User Service

Group 3 (依赖 Group 2):
  - [ ] 4. 创建 User Handler
```

#### 4.2.3 并行执行（每个 task 必须执行 TDD）

对每个 Group：

1. **启动多个 Agent**
   ```
   对 Group 中的每个 task:
     Task:
       subagent_type: general
       prompt: |
         请实施 tasks.md 中的 task N:
         {task 描述}
         
         设计依据：design.md 中的 {相关章节}
         
         **必须执行 TDD 红绿循环**:
         1. 先写测试（红 - 预期失败）
         2. 实现代码使测试通过（绿）
         3. 重构优化
         4. 全量测试验证
         
         请完成代码实现，包括:
         1. 创建/修改相关文件
         2. 添加必要的类型定义
         3. 实现核心逻辑
         4. 添加单元测试
   ```

2. **等待完成** — 所有并行 Agent 完成后，收集变更文件列表

3. **TDD 红绿循环验证（强制）**
   
   对每个 task 的实现，**必须**验证 TDD 循环：
   ```
   1. 运行现有测试（确保绿）
   2. 添加新测试（红 - 预期失败）
   3. 实现代码使测试通过（绿）
   4. 重构优化
   5. 全量测试验证
   ```
   
   **验证失败**: 返回 task 重新执行 TDD 循环。

4. **分组合并审查** — 调用 `code-review-before-commit` 进行 5 轮审查

#### 4.2.4 分组合并审查（强制 5 轮）

```
Skill: code-review-before-commit

输入:
  - 变更文件列表
  - tasks.md 中对应 task 编号

流程:
  1. 汇总本组所有变更
  2. 执行 5 轮 code review
  3. 修复所有 P0/P1 问题
  4. 标记 task 为 [x]
```

**审查循环**:
```
Round 1: 检查 → 发现问题 → 修复 → 重新审查
Round 2: 检查 → 发现问题 → 修复 → 重新审查
...
Round 5: 最终检查 → 残留 P2 记录（允许）

通过条件：无 P0/P1 问题
```

**失败处理**: 5 轮后仍有 P0/P1 问题，展示最终结果，用户决定是否继续。**禁止自动跳过**。

### 4.3 下一组执行

完成本组审查后，进入下一组的并行执行。重复 4.2 流程，直到所有 task 完成。

### 4.4 Phase 4 完成报告

```
## Phase 4 完成

**Change:** <change-name>
**并行组数:** N 组
**总 Task 数:** M 个
**最大并行数:** K 个（在最优组中）
**加速比:** ~Kx（相比串行）
**TDD 循环:** M/M task 完成
**Code Review:** N/N 组通过（P0/P1 问题清零）

**所有 task 已完成！进入 Phase 5 全流程校验。**
```

**通过条件**: 
- 所有 task 标记为 [x]
- 所有组 Code Review 通过（无 P0/P1 问题）
- TDD 循环全部完成

**失败处理**: 返回 Phase 4 重新实施失败的 task。

---

## Phase 5: 全流程校验（GATE）

在归档前，**必须**通过以下全部校验。**任何一项失败立即阻断，禁止进入 Phase 6**。

### 5.1 构建校验

```bash
# 根据项目类型选择构建命令
# Go: go build ./...
# Python: python -m py_compile 或 pytest --collect-only
# Node: npm run build
# 通用：make build
```

**要求**: 无编译错误

**失败处理**: 修复后重新构建，**禁止跳过**。

### 5.2 单元测试校验

```bash
# 根据项目类型选择测试命令
# Go: go test ./...
# Python: pytest
# Node: npm test
# 通用：make test
```

**要求**: 全部测试通过

**失败处理**: 修复后重新测试，**禁止跳过**。

### 5.3 真实数据验证（强制）

**针对涉及真实数据的变更，必须使用真实数据验证功能正常**。

```bash
# 示例：datasheet_mcp 真实数据验证
uv run python -c "
from datasheet_mcp.tools.utils.compare import convert
import yaml

# 使用真实数据测试
temp_dir = 'C:/Users/xxx/sandbox/temp/DEVICE_NAME/temp'
temp_files = [f for f in os.listdir(temp_dir) if f.endswith('_temp.yaml')]

success_count = 0
for f in temp_files:
    result = convert(os.path.join(temp_dir, f), output_path, 'yaml')
    if result.get('success'):
        with open(output_path, 'r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict):
            success_count += 1

assert success_count == len(temp_files), f'真实数据验证失败：{success_count}/{len(temp_files)}'
"
```

**要求**: 真实数据验证 100% 通过

**失败处理**: 修复后重新验证，**禁止跳过**。

### 5.4 任务完成度校验

检查 `tasks.md`:
- 所有 task 均为 `- [x]`（无 `- [ ]` 遗留）
- 若有未完成任务，返回 Phase 4 补充实施

**失败处理**: 返回 Phase 4 补充实施。

### 5.5 Artifact 完成度校验

```bash
openspec status --change "<name>" --json
```

**要求**: 所有 artifact 状态为 `done`

**失败处理**: 返回 Phase 2 补充生成。

### 5.6 校验报告

```
== Phase 5 全流程校验报告 ==

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 构建 | ✅/❌ | 无编译错误 |
| 单元测试 | ✅/❌ | 全部通过 |
| 真实数据验证 | ✅/❌ | 100% 通过 |
| 任务完成度 | ✅/❌ | X/Y tasks 完成 |
| Artifact | ✅/❌ | 所有 artifact done |

**结果**: 通过/失败
```

**通过条件**: 所有检查项均为 ✅

**失败处理**: 修复后重新执行全部校验，**禁止进入 Phase 6**。

---

## Phase 6: 归档与提交（强制顺序）

**强制顺序**: 先归档，后提交。违反顺序禁止提交。

### 6.1 执行 openspec-archive-change

```
Skill: openspec-archive-change

输入：change-name

流程:
  1. 检查 artifact 完成状态
  2. 检查 tasks.md 完成状态
  3. 检查 delta spec 同步状态
  4. 执行归档操作
```

**归档输出**:
```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs
```

**失败处理**: 任一检查失败，返回对应 Phase 修复。

### 6.2 执行 git commit

归档完成后，执行 git 提交：

#### 6.2.1 查看变更状态

```bash
git status
git diff --cached
```

#### 6.2.2 暂存变更

```bash
git add <changed-files>
```

**注意**: 绝不要将 `review-issues.md` 加入暂存区。

#### 6.2.3 生成提交信息

遵循 conventional commit 格式:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**类型建议**:
- `feat`: 新功能
- `fix`: 修复 bug
- `refactor`: 重构
- `chore`: 构建/工具变更
- `docs`: 文档更新
- `test`: 测试相关

#### 6.2.4 用户确认

展示提交信息供用户确认:
```
== 提交预览 ==

提交信息:
  feat(sch-mcp): expand toolset with 40+ tools

变更文件:
  M  src/sch_mcp/sch_client.py
  A  src/sch_mcp/tools/auth.py
  A  src/sch_mcp/tools/schematic.py
  ...

是否继续提交？[Y/n]
```

#### 6.2.5 执行提交

```bash
git commit -m "<message>"
```

#### 6.2.6 完成摘要

```
## 自动代码生成完成

**Change:** <change-name>
**归档位置:** openspec/changes/archive/YYYY-MM-DD-<name>/
**提交:** <commit-hash>
**提交信息:** <message>

=== 流程统计 ===
- Phase 2 提案生成：✓
- Phase 3 一致性校验：✓
- Phase 4 代码实施：✓ (N 组，M tasks, 最大并行 K)
- Phase 5 全流程校验：✓
- Phase 6 归档：✓
- Phase 6 自动提交：✓
```

---

## Phase 7: 最终报告

所有变更完成后，生成最终报告：

### 7.1 变更统计

```
== 最终报告 ==

**变更名称:** <change-name>
**总耗时:** X 小时 Y 分钟
**变更文件数:** N 个
**代码行数:** +A -B
**测试覆盖:** X%
**Code Review:** N 轮通过
**真实数据验证:** 通过/失败
```

### 7.2 遗留问题

若有遗留问题，记录到 `issues.md`：

```markdown
## 遗留问题

| # | 问题描述 | 优先级 | 状态 | 后续计划 |
|---|----------|--------|------|----------|
| 1 | xxx 测试失败 | P1 | 跳过 | 待修复 |
```

### 7.3 经验总结

记录本次变更的经验教训，用于优化项目规则。

---

## Phase 8: 项目子 skills 更新

执行后自动识别新模式并更新项目规则：

### 8.1 识别新模式

分析本次变更：
- 新增的代码模式
- 新的测试模式
- 新的架构模式
- 新的工具使用模式

### 8.2 生成更新建议

为相关 project-* 或 lang-* skill 生成更新建议：

```
## 建议更新：project-xxx

**新增模式:**
- xxx 模式（本次变更首次出现）

**建议:**
- 将 xxx 添加到项目规则
- 更新 xxx 检查点
```

### 8.3 用户确认

展示更新建议，用户确认后应用。

---

## 与相关 Skill 的集成

| Phase | 调用 Skill | 说明 |
|-------|-----------|------|
| 1 | `openspec-propose` | 生成 proposal.md + design.md + tasks.md |
| 2 | 内置校验逻辑 | 使用 `openspec status --json` 和文件内容校验 |
| 3 | `openspec-apply-change` | 按 tasks.md 逐个实施（Agent 并行） |
| 3 | `code-review-before-commit` | 每组实施后 5 轮审查循环 |
| 3 | `code-review` | code-review-before-commit 内部自动路由 |
| 4 | 内置校验逻辑 | 构建 + 测试 + 任务完成度 + artifact 完成度 |
| 4 | `qeda-test-guard` 或类似 | 真实数据验证（如有） |
| 5 | `openspec-archive-change` | 归档变更 + delta spec 同步 |
| 6 | 内置 git 逻辑 | conventional commit 提交 |

---

## 通用化说明

- 不再绑定特定语言或框架
- 代码风格通过 `code-review` 动态路由到 `lang-*` 子 skill（Go/Python/React 等）
- 项目约定通过 `code-review` 动态路由到 `project-*` 子 skill
- 术语通用化：Handler/Service（替代 Controller）、Model（替代 struct）、DTO（通用）
- 所有 language-specific 和 project-specific 规则在 code-review-before-commit 阶段动态加载

---

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| Task 不明确 | 暂停，请求用户澄清 |
| 实施中发现设计问题 | 暂停，建议更新 design.md/tasks.md |
| 构建/测试失败 | 修复后重试，不进入下一阶段 |
| TDD 红绿循环失败 | 重新执行 TDD，不跳过 |
| Code Review 5 轮后仍有 P0/P1 | 展示最终结果，用户决定是否继续 |
| 真实数据验证失败 | 修复后重新验证，不跳过 |
| 归档时 artifact 未完成 | 警告用户，确认后继续或返回修复 |
| 并行 task 文件冲突 | 暂停，手动合并冲突后重试 |
| Task 依赖无法推断 | 标记为手动分组，用户确认后继续 |
| 并行 Agent 部分失败 | 重试失败的 Agent，其他继续 |
| 个别功能问题 | 可跳过，记录到遗留问题列表 |

---

## 遗留问题处理

对于暂时无法解决的问题：

```markdown
## 遗留问题

| # | 问题描述 | 优先级 | 状态 | 后续计划 |
|---|----------|--------|------|----------|
| 1 | xxx 测试失败 | P1 | 跳过 | 待修复 |
```

记录到 `openspec/changes/<name>/issues.md`，不影响归档和提交。

---

*版本：3.0*
*最后更新：2026-07-08*
*变更：强化强制关卡 — 增加 TDD 红绿循环、真实数据验证、GATE CHECK 阻断机制*
