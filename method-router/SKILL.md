---
name: method-router
description: >
  方法论体系统一路由器。当用户请求涉及诊断分析、决策选型、设计规划、流程改进、
  风险评估、管理协作、时间管理、总结汇报等需要方法论框架辅助的任务时触发。作为所有方法论 Skill 的
  统一入口，自动分类问题类型并路由到最合适的框架（5W2H/5Whys/SCQA/Pre-mortem 等）。
  触发关键词：为什么、分析、排查、定位、选哪个、优先级、风险、管理、协作、分工、委派、责任、
  子 Agent、卡槽、DAG、有向无环图、依赖图、拓扑、关键路径、时间、截止、超时、排期、复盘、用什么框架。
  也适用于用户不确定该用哪个方法论时主动介入。不应在纯代码编写或简单查询任务中触发。
---

# method-router 方法论路由器

## 前置条件

- 用户请求涉及方法论可解决的问题（诊断/决策/设计/改进/风险/沟通）
- 子 Skill（5W2H 等）的 SKILL.md 已存在于 `skills/` 目录
- 无强制依赖，缺失子 Skill 时优雅降级为手动建议

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|:------:|
| **R0** | 用户显式指定 > 路由推荐。用户说"用 5W2H"则跳过路由器直接执行 | 无视用户意图，信任崩塌 |
| **R1** | 分类置信度 < 0.7 时必须降级为展示 Top 3 选项让用户选择，禁止猜测 | 方向性错误，分析全链路作废 |
| **R2** | 紧急场景（线上故障/用户投诉）跳过确认，直接路由到最短路径 | 延误黄金处理时间 |
| **R3** | 同类型 Skill 不重复运行。diagnose 场景 5W2H 和 5Whys 二选一 | 输出冗余，用户困惑 |
| **R4** | 所有路由决策必须输出 rationale，格式：`因为 {A}，选择 {B} 而非 {C}` | 黑盒决策无法改进 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 |
|---------------------|---------|:------:|
| "用户说分析一下，5W2H 和 5Whys 都挺合适，两个都跑吧" | 两份重叠报告 > 用户花额外时间判断哪个对 > 效率反而降低 | R3 |
| "confidence 只有 0.65，但我感觉应该是 5W2H" | 0.35 的误判概率 × 每次误判浪费 5 分钟 = 不可接受 | R1 |
| "线上故障了，让我先仔细分类再路由" | 每延迟 1 分钟损失成倍放大。直接 OODA，理由事后补充 | R2 |
| "用户没说是诊断还是决策，我自己判断就行" | "分析一下这个方案"可能是诊断（方案的问题）也可能是决策（A vs B）。语义歧义必须澄清 | R1 |
| "5W2H 的输出不是 JSON，没法传给 SCQA，跳过衔接吧" | 路由器职责之一就是格式适配。让纯文本可被下游消费 | — |

---

## 工作流总览

```
用户输入
    │
    ▼
Phase 0: 上下文感知 ──▶ 扫描可用 Skill + 项目上下文
    │                    ← 读取 references/method-mapping.yaml
    ▼
Phase 1: 意图分类 ──▶ type / urgency / domain / confidence
    │
    ├── confidence < 0.7 ──▶ 降级：展示 Top 3 + 理由 + 等待用户选择
    │
    ├── confidence ≥ 0.7
    │   └──▶
    │       ▼
    │   Phase 2: 方法路由 ──▶ 主 Skill + 辅助 Skill + 执行顺序 + rationale
    │       │
    │       ├── urgency=critical ──▶ 跳过确认，直接执行
    │       │
    │       └── urgency≠critical
    │           └──▶ 展示路由方案 → 用户确认/调整
    │               │
    │               ▼
    │           Phase 3: 链式执行 ──▶ 按顺序加载并执行各 Skill
    │               │
    │               │   每个 Skill 完成后：
    │               │   - 检查输出格式
    │               │   - 格式适配（如纯文本 → SCQA 模板）
    │               │   - 传递给下一个 Skill（如有）
    │               │   - 用户可中断/跳过/重跑
    │               │
    │               ▼
    │           Phase 4: 统一输出 ──▶ 汇总所有 Skill 输出 → SCQA 模板
    │               │
    │               ▼
    │           Phase 5: 反馈收集 ──▶ 路由日志 + 用户评分
```

---

## Phase 0: 上下文感知

**目的**：了解可用资源，避免路由到不存在的 Skill。

### 步骤

1. 扫描 `skills/` 目录，识别所有可用方法论 Skill；可用/缺失清单以 `references/method-mapping.yaml` 的 `skill_registry` 与 routes 引用为唯一事实源，不在此维护副本
2. 读取 `references/method-mapping.yaml` 获取完整映射规则
3. 如果映射文件不存在，使用内置默认映射表（Phase 1 中定义）

### 输出

```
== 路由器就绪 ==
可用 Skill: 运行时读取 `references/method-mapping.yaml` 的 `skill_registry`
缺失 Skill: 运行时校验映射引用与根注册表，不在本文维护静态清单
路由模式: 映射优先；仅对运行时确认不可用的 Skill 执行降级
```

---

## Phase 1: 意图分类

**目的**：判断用户问题属于哪个类型，为路由提供依据。

### 分类维度

| 维度 | 选项 | 判定依据 |
|------|------|---------|
| **类型** | `diagnose` / `decide` / `design` / `improve` / `risk` / `manage` / `report` | 关键词 + 语义 |
| **紧急度** | `critical` / `normal` / `planning` | 时间词 + 情绪词 + 上下文 |
| **领域** | `code` / `data` / `architecture` / `process` / `general` | 项目上下文 + 用户输入 |
| **数据可用性** | `has_data` / `no_data` | 用户是否提供报告/指标/日志 |

### 分类关键词矩阵（非穷举示例；完整映射以 YAML 为准）

| 类型 | 触发词 | 示例 |
|------|--------|------|
| **diagnose** | 为什么、报错、失败、异常、不对、bug、排查、定位、原因 | "匹配率为什么这么低" |
| **decide** | 选哪个、要不要、优先级、对比、方案、技术选型 | "用 Redis 还是 Kafka" |
| **design** | 设计、架构、重构、新功能、怎么实现、搭建 | "设计一个消息推送系统" |
| **improve** | 优化、提升、改进、加速、减少、自动化、太慢 | "这个接口太慢了" |
| **risk** | 风险、安全、漏洞、事故、万一、上线、有问题吗 | "这个改动能上线吗" |
| **report** | 总结、汇报、周报、复盘、文档、记录、写报告 | "帮我写个复盘报告" |
| **goal** | 目标、OKR、KPI、flag、减肥、学习计划、愿景、里程碑、定目标、达成 | "帮我定个季度减肥目标" |
| **learning** | 学习、理解、弄懂、掌握、复习、讲给别人听、面试、简单解释 | "这个机制我是不是真懂了" |
| **manage** | 管理、协作、分工、委派、责任、协调、资源、排期、子 Agent、卡槽、DAG、有向无环图、依赖图、拓扑、关键路径、时间、截止、超时、升级 | "按依赖图安排 Sol 和 Luna 的并发波次" |

### 分类置信度计算

```
confidence = 加权平均:
  - 关键词命中 (权重 0.4): 命中 ≥3 个关键词 → 0.9, 1-2 个 → 0.6, 0 个 → 0.3
  - 语义明确度 (权重 0.4): 问题描述长度 > 20 字 → 0.8, 10-20 字 → 0.6, < 10 字 → 0.3
  - 上下文一致性 (权重 0.2): 当前项目领域与推断类型匹配 → 1.0, 不匹配 → 0.5
```

### 降级输出格式（confidence < 0.7 时）

```markdown
🤔 不太确定你的问题属于哪种类型，以下是可能性最高的 3 个方向：

1. **诊断分析** (匹配度 45%) → 会用 5W2H 深度分析原因
2. **决策对比** (匹配度 30%) → 会用量化矩阵对比方案
3. **流程改进** (匹配度 15%) → 会用 PDCA 循环优化

你更倾向于哪个方向？（输入数字或直接描述）
```

---

## Phase 2: 方法路由

**目的**：根据分类结果，匹配最佳 Skill 和执行顺序。

### 主映射表

| 类型 | 条件 | 主 Skill | 辅助 Skill | 输出 Skill |
|------|------|----------|-----------|-----------|
| **diagnose** | has_data=true | **5W2H** | — | SCQA |
| **diagnose** | has_data=false | **5 Whys** | — | SCQA |
| **diagnose** | complexity=high | **MECE** → 5 Whys | — | SCQA |
| **diagnose** | urgency=critical | **OODA Loop** | — | SCQA |
| **decide** | 任务优先级 | **Eisenhower Matrix** | — | STAR |
| **decide** | 多方案对比 | **Pugh Matrix** | — | ADR |
| **decide** | 技术选型 | **ADL Matrix** | — | ADR |
| **manage** | 角色分工、责任归属、委派 | **Management Collaboration** | — | SCQA |
| **manage** | 多 Agent 并行、卡槽和依赖波次 | **Management Collaboration** | — | SCQA |
| **manage** | 时间管理、截止、超时和进度检查点（`time_management`） | **Management Collaboration** → Timeboxing + Critical Path → Eisenhower | — | SCQA |
| **manage** | 阻塞升级、冲突协调 | **Management Collaboration** → OODA | — | SCQA |
| **manage** | 重复性协作低效 | **Management Collaboration** → PDCA | — | SCQA |
| **design** | 新功能/系统 | **Design Thinking** | — | ADR |
| **design** | 架构重构 | **First Principles** | — | ADR |
| **improve** | 流程优化 | **PDCA** | — | A3 |
| **improve** | 数据驱动 | **DMAIC** | — | A3 |
| **risk** | 代码变更 | **Pre-mortem** | — | SCQA |
| **risk** | 系统性评估 | **FMEA** | — | SCQA |
| **report** | 复盘总结 | **STAR** | — | SCQA |
| **report** | 通用报告 | **SCQA** | — | — |
| **diagnose** | 多因素混杂（multi_factor） | **鱼骨图（fishbone）** | 5Whys（收敛后深挖） | SCQA |
| **decide** | 快速优先级（quick_priority） | **Impact/Effort 矩阵** | — | — |
| **decide** | 后果推演（consequence_check） | **二阶思考** | — | SCQA |
| **manage** | 结构化讨论（structured_discussion） | **六顶思考帽** | — | SCQA |
| **improve** | 聚焦（focus） | **帕累托 80/20** | — | SCQA |
| **goal** | 目标框架（goal_setup） | **OKR** | SMART（校验层） | SCQA |
| **goal** | 目标校验（goal_quality） | **SMART** | — | — |
| **report** | 反馈（feedback） | **SBI** | — | — |
| **design** | 用户洞察（user_insight） | **JTBD** | Design Thinking | ADR |
| **design** | 存量改造（enhance_existing） | **SCAMPER** | Impact/Effort | — |
| **design** | 需求分类（requirement_classify） | **Kano** | — | — |
| **risk** | 长期不确定（long_term） | **情景规划** | — | SCQA |
| **risk** | 顶级失效（top_down） | **FTA 故障树** | FMEA（先广后深） | SCQA |
| **improve** | 流程定义（process_define） | **SIPOC** | PDCA | A3 |
| **improve** | 对标（compare） | **Benchmarking** | SMART | A3 |
| **learning** | 理解验证（verify_understanding） | **费曼技巧** | — | — |
| **manage** | 个人任务（personal_tasks） | **GTD** | Eisenhower | SCQA |
| **report** | 深度复盘（deep_retro） | **双环学习** | KPT/STAR（先事件后框架） | SCQA |

### 组合规则

```
R_A: diagnose 类 Skill 输出自动衔接 SCQA（统一报告格式）
R_B: MECE 先于 5 Whys（先穷举维度，再逐维深入）
R_C: Pre-mortem 先于 FMEA（方向性 → 系统性）
R_D: 用户显式指定 > 路由推荐（R0）
R_E: 同类型 Skill 不重复运行（R3）
R_F: 管理协作先建立 RACI，再生成委派和并行计划
R_G: 只有通过依赖、写入、资源、契约和验证隔离门禁的工作才进入 WIP
R_H: 执行者发现任务不清晰时先向唯一 A 提问，不得自行补全授权
R_I: 时间盒到期只能验收、带证据重排或升级阻塞，不得静默延长或跳过验证
```

### 路由输出格式

```markdown
## 🧭 路由决策

**问题类型**：诊断分析（置信度 85%）
**推荐框架**：5W2H → SCQA
**理由**：你提供了量化数据（匹配率 21.2%）和代码访问权限，
5W2H 比 5 Whys 更适合数据驱动的根因分析。
SCQA 将自动格式化最终报告。

**备选方案**：5 Whys（如果根因不明确需要进一步追问）

执行此方案？（输入 yes 确认，或选择备选方案）
```

### Skill 缺失降级

当主 Skill 不可用时：

```markdown
⚠️ 推荐框架【5 Whys】尚未安装，降级为手动引导：

我来手动执行 5 Whys 追问流程：
1. 第一个为什么：{问题现象} 为什么会发生？
   → 等待你的回答
2. 第二个为什么：{上一轮答案} 为什么会发生？
   → ...

或者选择已有 Skill 替代：
- 5W2H（更全面，含代码定位）
- 直接开始分析（我来根据经验判断）
```

---

## Phase 3: 链式执行

**目的**：按顺序执行 Skill 链，处理输出传递和中断。

### 执行规则

1. **顺序执行**：按 Phase 2 指定的顺序逐个加载并执行 Skill
2. **格式检查**：每个 Skill 完成后检查输出是否可被下游消费
3. **中断处理**：用户可随时输入 `stop`/`skip`/`retry` 控制流程
4. **错误恢复**：单个 Skill 失败不中断链，标注后继续

### Skill 调用方式

```
对于每个路由决策中的 Skill：
1. 加载该 Skill 的 SKILL.md 完整内容
2. 将上游 Skill 的输出作为额外上下文传入
3. 执行该 Skill 定义的工作流
4. 收集输出，进行格式适配
5. 传递给下一个 Skill（如有）
```

### 链式输出追踪

```
[1/2] 5W2H 深度分析 ──▶ ✅ 完成 (3.2s)
      ├── Phase 1-5 已执行
      └── 输出: 5 个根因 + 代码定位 + 修复方案

[2/2] SCQA 格式化 ──▶ ⏳ 执行中...
      ├── 输入: 5W2H 报告
      └── 生成: 情境→冲突→问题→答案 叙事报告
```

---

## Phase 4: 统一输出

**目的**：汇总所有 Skill 输出，用 SCQA 模板生成最终报告。

### 如果 SCQA Skill 可用

自动调用 SCQA Skill 格式化所有输出。

### 如果映射指定的输出 Skill 在运行时不可用

先根据根注册表解析并确认映射指定的输出 Skill。只有确认不可用时，才降级为 Markdown 决策记录
（背景 / 选项 / 决策 / 理由）或 A3 一页纸摘要（问题 / 现状 / 对策 / 效果）。

### 如果 SCQA Skill 不可用

使用内置 SCQA 模板：

```markdown
# {问题标题}

## 情境 (Situation)
{项目背景、当前状态}

## 冲突 (Complication)
{问题表现、量化数据、影响范围}

## 问题 (Question)
{核心需要解决什么问题}

## 答案 (Answer)
{根因链 + 修复方案 + 优先级 + 成本}

## 附录
- 路由决策日志：选择了 {Skill 链}，理由：{rationale}
- 执行耗时：{总时间}
- 跳过的 Skill：{如有}
```

---

## Phase 5: 反馈收集

**目的**：收集路由质量数据，持续优化映射规则。

### 路由日志格式

```yaml
route_log:
  timestamp: "2026-07-24T15:30:00"
  user_input: "匹配率为什么这么低"
  classification:
    type: diagnose
    confidence: 0.85
    urgency: normal
  route:
    skills: [5W2H, SCQA]
    rationale: "有量化数据，选 5W2H 而非 5Whys"
    user_confirmed: true
    user_adjusted: false
  execution:
    skills_completed: [5W2H]
    skills_failed: []
    skills_skipped: [SCQA]
    total_time_ms: 3200
```

### 用户反馈收集

```
✅ 本次分析完成！路由是否合适？
  [1] 很合适，框架选择正确
  [2] 还行，但可以试试其他框架
  [3] 不合适，我想用 {其他框架}
```

---

## 错误处理

| 环节 | 失败条件 | 处理方式 |
|------|---------|---------|
| Phase 0 | `method-mapping.yaml` 不存在 | 使用内置默认映射表，标注"使用默认规则" |
| Phase 0 | 无任何可用 Skill | 手动执行对应方法论流程，问题驱动而非 Skill 驱动 |
| Phase 1 | 用户输入 < 3 个字，无法分类 | 追问：你能再描述一下具体遇到了什么问题吗？ |
| Phase 1 | 关键词跨类型命中（diagnose + decide 各命中 3 个） | 优先选择命中更多关键词的类型；相等时降级为用户选择 |
| Phase 2 | 主 Skill 和备选都缺失 | 降级为手动引导执行方法论步骤 |
| Phase 3 | 子 Skill 加载超时（>30s） | 跳过该 Skill，标注 `⏱️ 超时`，继续链式执行 |
| Phase 3 | 子 Skill 输出格式无法解析 | 保留原始输出，标注 `⚠️ 格式异常`，跳过格式适配 |
| Phase 3 | 用户中断（输入 stop） | 保存已完成 Skill 的输出，不标记为错误 |
| Phase 4 | 所有 Skill 都失败 | 给出基于 Phase 1 分类的分析建议，标注"无 Skill 可用，仅概念指导" |

> **兜底原则**：router 的核心价值是"选择正确的方法"，而非"执行方法本身"。当 Skill 不可用时，router 仍应输出方法论建议和手动执行步骤，让用户可自行跟进。

---

## 方法论块总览（按功能块分组，英文（中文名））

> 39 个框架按 10 个功能块组织；映射权威仍以 `references/method-mapping.yaml` 为准

| 块 | 框架 |
|---|---|
| **问题分析** diagnose | 5whys（五个为什么）· deep-analysis（5W2H 深度分析）· mece（MECE 穷尽检查）· fishbone（鱼骨图）· ooda（OODA 快速闭环） |
| **目标管理** goal | okr（目标与关键结果）· smart（SMART 目标校验） |
| **决策评估** decide | eisenhower（艾森豪威尔矩阵）· rice（RICE 评分）· impact-effort（影响×努力矩阵）· pugh（普氏决策矩阵）· adl（ADL 生命周期矩阵）· second-order（二阶思考）· adr（架构决策记录） |
| **设计创新** design | design-thinking（设计思维）· first-principles（第一性原理）· jtbd（用户任务洞察）· scamper（SCAMPER 改造法）· kano（KANO 需求分类） |
| **流程改进** improve | pdca（戴明环）· dmaic（六西格玛）· pareto（帕累托 80/20）· sipoc（SIPOC 流程边界）· benchmarking（对标分析） |
| **风险管理** risk | pre-mortem（事前验尸）· fmea（失效模式分析）· fta（故障树分析）· scenario-planning（情景规划） |
| **汇报与反馈** report | scqa（金字塔叙事）· star（STAR 叙事）· kpt（KPT 复盘）· a3（一页纸报告）· sbi（SBI 反馈）· double-loop（双环学习） |
| **协作管理** manage | management-collaboration（管理与协作）· six-hats（六顶思考帽）· gtd（GTD 任务管理） |
| **学习验证** learning | feynman（费曼技巧） |
| **元认知** meta | cynefin（问题域分类） |

## 参考文档索引

| 文档 | 用途 |
|------|------|
| `references/method-mapping.yaml` | 完整的分类→框架映射配置 |
| `deep-analysis/SKILL.md` | 5W2H 深度分析 |
| `5whys/SKILL.md` | 5 Whys 根因追问 |
| `scqa/SKILL.md` | SCQA 叙事框架 |
| `pre-mortem/SKILL.md` | Pre-mortem 事前验尸 |
| `cynefin/SKILL.md` | Cynefin 问题域分类 |
| `ooda/SKILL.md` | OODA 快速闭环 |
| `first-principles/SKILL.md` | First Principles 第一性原理 |
| `eisenhower/SKILL.md` | Eisenhower 优先级矩阵 |
| `mece/SKILL.md` | MECE 结构化穷举检查 |
| `dmaic/SKILL.md` | DMAIC 六西格玛改进 |
| `fmea/SKILL.md` | FMEA 失效模式分析 |
| `star/SKILL.md` | STAR 结构化叙事 |
| `pdca-tuning/SKILL.md` | PDCA 流程改进 |
| `management-collaboration/SKILL.md` | RACI、委派任务卡、Kanban/WIP、时间盒和 Sol-Luna 协作 |

---

## 输出格式建议

- 路由决策以 Markdown 表格展示：类型 / 推荐框架 / 理由 / 备选
- 执行进度以步骤列表展示，标注状态图标（✅ ⏳ ❌ ⚠️）
- 最终报告无论入口统一使用 SCQA 模板
- 每次路由输出 rationale，格式固定：`因为 {A}，选择 {B} 而非 {C}`
