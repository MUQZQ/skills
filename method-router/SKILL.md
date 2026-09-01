---
name: method-router
description: >
  方法论体系统一路由器。当用户请求涉及诊断分析、决策选型、设计规划、流程改进、
  风险评估、管理协作、时间管理、总结汇报等需要方法论框架辅助的任务时触发。作为所有方法论 Skill 的
  统一入口，自动分类问题类型并路由到最合适的框架（5W2H/5Whys/SCQA/Pre-mortem 等）。
  触发关键词：从零、没思路、先调研、网上实践、头脑风暴、为什么、分析、排查、定位、选哪个、优先级、风险、管理、协作、分工、委派、责任、
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
| **R1** | 分类无法确定时必须降级为展示 Top 3 选项让用户选择，禁止猜测 | 方向性错误，分析全链路作废 |
| **R2** | 紧急场景（线上故障/用户投诉）跳过确认，直接路由到最短路径 | 延误黄金处理时间 |
| **R3** | 同一目的的替代 Skill 不重复运行；互补 Skill 可以按映射链执行 | 输出冗余，用户困惑 |
| **R4** | 所有路由决策必须输出 rationale，格式：`因为 {A}，选择 {B} 而非 {C}` | 黑盒决策无法改进 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 |
|---------------------|---------|:------:|
| "用户说分析一下，5W2H 和 5Whys 都挺合适，两个都跑吧" | 两份重叠报告 > 用户花额外时间判断哪个对 > 效率反而降低 | R3 |
| "类型证据不足，但我感觉应该是 5W2H" | 缺少可审计证据时直接猜测会让整条分析链偏航 | R1 |
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
Phase 1: 意图分类 ──▶ route_context（type / urgency / domain / has_data / complexity / sub_type / scope / cynefin_pre）
    │
    ├── type=unknown 或选择平局 ──▶ 降级：展示 Top 3 + 理由 + 等待用户选择
    │
    ├── type 已确定且候选唯一
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
    │           Phase 4: 统一输出 ──▶ 按映射链指定的输出 Skill 汇总；未指定则直接交付
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
| **类型** | `diagnose` / `decide` / `design` / `improve` / `risk` / `manage` / `report` / `goal` / `learning` | 关键词 + 语义；`meta` 是路由前预处理，不是业务类型 |
| **紧急度** | `critical` / `normal` | 时间词 + 情绪词 + 上下文；未知时为 `normal` |
| **领域** | `code` / `data` / `architecture` / `process` / `general` | 项目上下文 + 用户输入 |
| **数据可用性** | `true` / `false` / `unknown` | 用户是否提供报告/指标/日志；作为 `has_data` 字段值 |
| **复杂度** | `high` / `normal` / `unknown` | 因素是否交织、因果是否可直接分析 |
| **子类型** | 映射声明的 `sub_type` 或 `unknown` | 更细粒度意图条件 |
| **范围** | 映射声明的 `scope` 或 `unknown` | 任务边界条件 |
| **Cynefin 预处理** | `true` / `false` | 需要先分域时为 `true` |

### 分类关键词矩阵（非穷举示例；完整映射以 YAML 为准）

| 类型 | 触发词 | 示例 |
|------|--------|------|
| **diagnose** | 为什么、报错、失败、异常、不对、bug、排查、定位、原因 | "匹配率为什么这么低" |
| **decide** | 选哪个、要不要、优先级、对比、方案、技术选型 | "用 Redis 还是 Kafka" |
| **design** | 从零、没思路、先调研、网上实践、头脑风暴、设计、架构、重构、新功能、怎么实现、搭建 | "我只有一个粗略想法，先查网上实践并头脑风暴" |
| **improve** | 优化、提升、改进、加速、减少、自动化、太慢 | "这个接口太慢了" |
| **risk** | 风险、安全、漏洞、事故、万一、上线、有问题吗 | "这个改动能上线吗" |
| **report** | 总结、汇报、周报、复盘、文档、记录、写报告 | "帮我写个复盘报告" |
| **goal** | 目标、OKR、KPI、flag、减肥、学习计划、愿景、里程碑、定目标、达成 | "帮我定个季度减肥目标" |
| **learning** | 学习、理解、弄懂、掌握、复习、讲给别人听、面试、简单解释 | "这个机制我是不是真懂了" |
| **manage** | 管理、协作、分工、委派、责任、协调、资源、排期、子 Agent、卡槽、DAG、有向无环图、依赖图、拓扑、关键路径、时间、截止、超时、升级 | "按依赖图安排 Sol 和 Luna 的并发波次" |

### route_context 推导

先从用户原话和项目上下文提取字段，再与 YAML `classification`、`urgency` 和 `routes[].condition` 的键逐项匹配。字段缺少证据时使用 `unknown`，不得用输入长度推断语义清晰度，也不得把 `unknown` 当作任意条件的命中。

```yaml
route_context:
  type: diagnose | decide | design | improve | risk | manage | report | goal | learning | unknown
  urgency: critical | normal
  domain: code | data | architecture | process | general | unknown
  has_data: true | false | unknown
  complexity: high | normal | unknown
  sub_type: <映射条件值> | unknown
  scope: <映射条件值> | unknown
  cynefin_pre: true | false
```

推导约定：`type` 由关键词与语义意图确定；`urgency` 命中 critical 关键词才为 `critical`，否则为 `normal`；`domain` 由项目上下文和请求对象确定；`has_data` 仅在出现报告、指标、日志或其他可分析数据时为 `true`，明确没有时为 `false`，其余为 `unknown`；`complexity=high` 仅在多因素交织或因果难以拆分时成立；`sub_type` 与 `scope` 只填写有直接证据的 YAML 条件值；`cynefin_pre=true` 表示先执行 `meta` 预处理链。无法确定 `type` 或多个候选同样成立时，进入 Top 3 降级。

### 降级输出格式（type 未确定或选择平局时）

```markdown
🤔 不太确定你的问题属于哪种类型，以下是可能性最高的 3 个方向：

1. **诊断分析**（证据：出现“原因/异常”语义）→ 会用根因分析方法
2. **决策对比**（证据：出现“方案/选择”语义）→ 会用量化矩阵对比方案
3. **流程改进**（证据：出现“优化/流程”语义）→ 会用 PDCA 循环优化

你更倾向于哪个方向？（输入数字或直接描述）
```

---

## Phase 2: 方法路由

**目的**：根据分类结果，匹配最佳 Skill 和执行顺序。

### 主映射表

| 类型 | 条件 | 实际执行链（按 order） |
|------|------|------------------------|
| **meta**（预处理） | `cynefin_pre=true` | Cynefin |
| **diagnose** | `has_data=true` 且 `domain=data` | deep-analysis → SCQA |
| **diagnose** | `has_data=false` | 5whys → SCQA |
| **diagnose** | `complexity=high` | MECE → 5whys → SCQA |
| **diagnose** | `urgency=critical` | OODA Loop → SCQA（可选） |
| **diagnose** | `sub_type=multi_factor` | fishbone → 5whys → SCQA（前两者必需，SCQA 可选） |
| **decide** | `sub_type=priority` | Eisenhower Matrix → STAR（可选） |
| **decide** | `sub_type=priority_quant` | RICE |
| **decide** | `sub_type=comparison` | Pugh Matrix → ADR（可选） |
| **decide** | `sub_type=tech_selection` | ADL Matrix → ADR（可选） |
| **decide** | `sub_type=quick_priority` | Impact/Effort |
| **decide** | `sub_type=consequence_check` | Second-order → SCQA（可选） |
| **design** | `scope=blank_slate` | Discovery Sprint |
| **design** | `scope=new_system` | Design Thinking → ADR（可选） |
| **design** | `scope=refactor` | First Principles → ADR（可选） |
| **design** | `scope=user_insight` | JTBD → Design Thinking（可选） |
| **design** | `scope=enhance_existing` | SCAMPER → Impact/Effort（可选） |
| **design** | `scope=requirement_classify` | Kano |
| **improve** | `domain=process` | PDCA → A3（可选） |
| **improve** | `domain=data` | DMAIC → A3（可选） |
| **improve** | `sub_type=focus` | Pareto |
| **improve** | `sub_type=process_define` | SIPOC → PDCA（可选） |
| **improve** | `sub_type=compare` | Benchmarking → SMART（可选） |
| **risk** | `scope=code_change` | Pre-mortem → SCQA |
| **risk** | `scope=systematic` | FMEA → SCQA |
| **risk** | `sub_type=long_term` | Scenario Planning |
| **risk** | `sub_type=top_down` | FTA |
| **manage** | `sub_type=role_split` / `parallel_scheduling` / 默认 | Management Collaboration → SCQA（可选） |
| **manage** | `sub_type=time_management` | Management Collaboration → Eisenhower → SCQA（均可选） |
| **manage** | `sub_type=escalation` | Management Collaboration → OODA Loop → SCQA（后两者可选） |
| **manage** | `sub_type=improvement` | Management Collaboration → PDCA → SCQA（前两者必需，SCQA 可选） |
| **manage** | `sub_type=structured_discussion` | Six Hats |
| **manage** | `sub_type=personal_tasks` | GTD |
| **report** | `sub_type=retrospective` | STAR → SCQA（可选） |
| **report** | `sub_type=kpt` | KPT |
| **report** | `sub_type=feedback` | SBI |
| **report** | `sub_type=deep_retro` | Double-loop |
| **report** | 默认 | SCQA |
| **goal** | `sub_type=goal_setup` | OKR → SMART |
| **goal** | `sub_type=goal_quality` | SMART |
| **learning** | `sub_type=verify_understanding` | Feynman |

### 组合规则

```
R_A: 仅当 YAML 映射链显式包含 SCQA 时才执行 SCQA；不得因类型自动追加
R_B: MECE 先于 5 Whys（先穷举维度，再逐维深入）
R_C: Pre-mortem 先于 FMEA（方向性 → 系统性）
R_D: 用户显式指定 > 路由推荐（R0）
R_E: 同一目的的替代 Skill 不重复运行；互补链（如 MECE → 5whys）允许按映射执行
R_F: 管理协作先建立 RACI，再生成委派和并行计划
R_G: 只有通过依赖、写入、资源、契约和验证隔离门禁的工作才进入 WIP
R_H: 执行者发现任务不清晰时先向唯一 A 提问，不得自行补全授权
R_I: 时间盒到期只能验收、带证据重排或升级阻塞，不得静默延长或跳过验证
R_J: 空白任务先探索证据、候选和首个实验；问题明确后重新路由，探索不授权实施
```

### 路由选择算法

1. 若 `cynefin_pre=true`，先执行 `meta` 预处理链，再将域判断结果写回 `route_context`。
2. 在 `routes` 中筛选 `type` 相同且所有条件都与 `route_context` 明确匹配的候选；`unknown` 不匹配任何具体条件。
3. 使用 `highest_priority_then_specificity`：先按映射优先级降序，再按条件特异度降序；特异度等于匹配的条件字段数量，空条件最低。优先级和 fallback 以 YAML 为准。
4. 仍有多个同优先级候选时，按条件特异度选唯一链；仍平局则展示 Top 3 及理由，等待用户选择。
5. 无任何匹配时执行该 `type` 的 fallback 动作；当前映射统一展示 Top 3 并等待选择。fallback 不存在时降级为手动引导，不要把其他类型的路由当作兜底。

### 路由输出格式

```markdown
## 🧭 路由决策

**问题类型**：诊断分析（证据：提供了量化指标与日志）
**推荐框架**：deep-analysis → SCQA（以 YAML 映射链为准）
**理由**：你提供了量化数据（匹配率 21.2%）和代码访问权限，
5W2H 比 5 Whys 更适合数据驱动的根因分析。
仅当映射链包含 SCQA 时才执行格式化；否则按链上最后一个 Skill 交付。

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

**目的**：按 YAML 映射链交付结果，不对所有入口强制使用同一种输出格式。

### 按映射链输出

- 链中有输出 Skill 时，执行该 Skill 并以其格式交付。
- 链中没有输出 Skill 时，直接交付主 Skill 的结果。
- 只有映射链指定 SCQA 且运行时可用时，才调用 SCQA。

### 如果映射指定的输出 Skill 在运行时不可用

先根据根注册表解析并确认映射指定的输出 Skill。只有确认不可用时，才降级为 Markdown 决策记录
（背景 / 选项 / 决策 / 理由）或 A3 一页纸摘要（问题 / 现状 / 对策 / 效果）。

无法使用映射指定的输出 Skill 时，按上述决策记录或 A3 摘要格式降级交付。

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
    urgency: normal
    route_context:
      domain: data
      has_data: true
      complexity: unknown
      sub_type: unknown
      scope: unknown
      cynefin_pre: false
  route:
    skills: [deep-analysis, SCQA]
    rationale: "有量化数据，选 deep-analysis 而非 5whys"
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
| Phase 1 | `type=unknown` 或候选同优先级且特异度仍相同 | 展示 Top 3 选项并等待用户选择 |
| Phase 1 | 关键词跨类型命中 | 按 `highest_priority_then_specificity` 选择；仍平局则展示 Top 3 |
| Phase 2 | 主 Skill 和备选都缺失 | 降级为手动引导执行方法论步骤 |
| Phase 3 | 子 Skill 加载超时（>30s） | 跳过该 Skill，标注 `⏱️ 超时`，继续链式执行 |
| Phase 3 | 子 Skill 输出格式无法解析 | 保留原始输出，标注 `⚠️ 格式异常`，跳过格式适配 |
| Phase 3 | 用户中断（输入 stop） | 保存已完成 Skill 的输出，不标记为错误 |
| Phase 4 | 所有 Skill 都失败 | 给出基于 Phase 1 分类的分析建议，标注"无 Skill 可用，仅概念指导" |

> **兜底原则**：router 的核心价值是"选择正确的方法"，而非"执行方法本身"。当 Skill 不可用时，router 仍应输出方法论建议和手动执行步骤，让用户可自行跟进。

---

## 方法论块总览（按功能块分组，英文（中文名））

> 40 个框架按 10 个功能块组织；映射权威仍以 `references/method-mapping.yaml` 为准

| 块 | 框架 |
|---|---|
| **问题分析** diagnose | 5whys（五个为什么）· deep-analysis（5W2H 深度分析）· mece（MECE 穷尽检查）· fishbone（鱼骨图）· ooda（OODA 快速闭环） |
| **目标管理** goal | okr（目标与关键结果）· smart（SMART 目标校验） |
| **决策评估** decide | eisenhower（艾森豪威尔矩阵）· rice（RICE 评分）· impact-effort（影响×努力矩阵）· pugh（普氏决策矩阵）· adl（ADL 生命周期矩阵）· second-order（二阶思考）· adr（架构决策记录） |
| **设计创新** design | discovery-sprint（探索冲刺）· design-thinking（设计思维）· first-principles（第一性原理）· jtbd（用户任务洞察）· scamper（SCAMPER 改造法）· kano（KANO 需求分类） |
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
| `discovery-sprint/SKILL.md` | 空白任务的联网证据探索、头脑风暴和首个实验 |
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
- 最终输出遵循 YAML 映射链；只有链中明确指定 SCQA 时才使用 SCQA
- 每次路由输出 rationale，格式固定：`因为 {A}，选择 {B} 而非 {C}`
