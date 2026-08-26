---
name: auto-code-generator
description: >
  规格驱动的自动代码实施编排器。用户提到“自动生成代码”“全流程实施”“一键实施变更”
  “按 spec 实施”“自动化开发管线”或希望从需求持续推进到验证、归档时使用。先识别项目已有的
  生命周期所有者和风险档位；有 OpenSpec、QEDA 或其他权威流程时服从其实时状态与指令，只提供
  场景组内 TDD、按场景组粒度调度、安全并行、审查和验证等阶段内能力，不建立第二套流程、
  状态账本或 Git 授权。
---

# 自动代码生成器 v4.6

## 定位

本 skill 将已经确认的需求持续推进到可验证结果。它是自适应编排器，不是凌驾于项目工作流之上的
第二套生命周期。项目的 AGENTS、schema、实时指令、任务状态和原生验证命令始终优先。

保留的工程骨架：规格追踪、阶段门禁、行为任务 TDD、依赖调度、安全并行、严重度审查、最终验证，
以及独立 Git 授权下的 Apply 内 checkpoint 和归档后最终 closeout。

## 前置输入

开始前尽量确认以下信息；可以从仓库证据推导的内容不要反复询问用户：

- 期望结果与明确排除项；
- 当前项目规则、权威生命周期和活动 change；
- 执行意图：`PLAN_ONLY` 或 `PLAN_AND_APPLY`；
- Git 权限：默认 `NONE`，只有用户明确要求提交时才是 `LOCAL_COMMIT`；提交模式默认
  `CLOSEOUT_ONCE`，只有用户明确要求“分批提交”“阶段性提交”或“做完一部分先提交”时才是
  `INCREMENTAL_CHECKPOINT`；
- 当前分支、HEAD、工作树和重要外部输入的基线；
- 项目原生构建、测试、集成或人工验证入口。

“实现”“实施”“修复”“自动生成代码”通常表示 `PLAN_AND_APPLY`；“规划”“出方案”“生成 spec”
表示 `PLAN_ONLY`。这项推断不能覆盖项目要求的人工确认，也不能推断 commit、push、PR 或部署权限。

## 铁律速查

| 规则 | 内容 | 违反后果 |
|---|---|---|
| R0 | 先识别生命周期所有者；已有权威流程时服从其 schema、状态、指令和工件图 | 双重流程产生冲突完成判定 |
| R1 | 用户请求和已确认决策定义授权边界；工件、审查意见和最佳实践不能自行扩权 | 顺手修复演变为未授权变更 |
| R2 | 只保留一个持久任务真相源；场景组只是临时调度视图，不复制任务状态 | checkbox、报告、任务组和消息互相矛盾 |
| R3 | 风险决定流程深度；数量只触发评审，不能自动拆 change 或自动升级权限 | 低风险任务过载，高风险任务漏审 |
| R4 | 实施前锁定目标与重要外部输入基线；基线漂移时展示差异并重新确认 | 旧计划被静默套到新代码上 |
| R5 | 行为场景在同一执行上下文完成 `RED → GREEN → REFACTOR`；不为文档或配置任务虚构 RED | TDD 被切碎交接，或产生无意义测试和虚假证据 |
| R6 | 先按场景内聚性和成本收益形成调度组，再按写入、契约、资源和测试隔离性决定组间并行 | 微任务过度委派，或多 Agent 覆盖改动和污染证据 |
| R7 | 协调者必须核对真实 diff、范围和测试后才能完成任务 | 仅凭 worker 摘要制造假完成 |
| R8 | 审查按严重度闭环，不以固定轮数作为质量指标 | 为凑轮数制造 churn 或被迫放行 |
| R9 | 最终验证使用项目原生命令或可重复方法；未执行项不得标记通过 | 通用 runner 成为第二证据权威 |
| R10 | OpenSpec、任务完成或归档都不授予 Git 权限；commit、push、PR、部署分别需要授权 | 自动化越过用户控制边界 |
| R11 | 单次变更只能提出规则更新建议；未经明确请求不得自动修改项目或全局 skills | 单样本被过拟合成永久规则 |
| R12 | tracker task 是持久状态/验收单元，worker 场景组是临时调度单元；两者不得强制一一对应 | 每个微任务启动 worker，重复上下文与测试成本吞噬收益 |
| R13 | 增量提交只接受完整验收、文件归属可分离的交付切片；提交不等于整个 change 完成或归档 | 未完成或混合改动被冻结进历史，最终审查遗漏已提交阶段 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 规则 |
|---|---|:---:|
| “项目有 OpenSpec，但这套九阶段更完整，再包一层更安全” | 两套工件、审查和完成结论会互相冲突 | R0 |
| “任务很多，自动拆成五个 change 并行最快” | change 边界涉及授权、回滚和独立价值，只能建议后由人确认 | R3 |
| “同一 DAG 层没有依赖，可以全部并行” | 两个任务仍可能写同一文件、manifest、migration 或公开契约 | R6 |
| “每个 task 一个全新 worker 最容易追踪” | 紧密相关的测试、实现和断言会重复加载上下文、fixture 和测试进程，且切断 TDD 闭环 | R12 |
| “都属于同一用户场景，全部交给一个 worker” | 独立审批、迁移、权限和回滚边界会扩大失败爆炸半径 | R6 |
| “worker 报告测试通过，可以直接勾选” | 摘要可能遗漏越界修改、失败测试或工作树重叠 | R7 |
| “五轮 review 比一轮更严格” | 轮数不证明覆盖度，最终状态和问题严重度才可审计 | R8 |
| “归档成功就顺便提交” | 归档只证明生命周期状态，不代表用户授权 Git mutation | R10 |
| “这次出现了新模式，自动写入项目 skill” | 一次成功不等于稳定通用规则 | R11 |
| “一个 task 通过了，马上把当前所有改动提交掉” | worker/task 结果不是自动提交边界；只有完整验收的交付切片及其准确文件集可提交 | R13 |
| “同一文件混合了已完成和未完成任务，用补丁暂存切一下即可” | 默认补丁暂存会削弱范围审计和恢复；混合未完成任务的文件应留到边界可分离后 | R13 |

## 工作流总览

```text
Detect & Route
  → Plan to Apply-ready
  → Apply with bounded scenario groups
      ↳ Apply 内 checkpoint（仅 INCREMENTAL_CHECKPOINT 授权且交付切片完整时，可重复）
  → Review & Verify final state
  → Achieve and archive
  → Final closeout only with separate authority
  → Report final state
```

连续推进，不在任务之间重复询问“是否继续”。只在项目规定的人类门禁、边界变化、基线漂移、
缺失关键证据、不可逆外部操作或无法自行解决的真实阻塞处暂停。

## Stage 1：Detect & Route

每次执行的第一个实质动作都是只读取证：读取项目规则、实时生命周期状态与指令、当前分支、HEAD、status
和相关 baseline。先不改文件、不更新任务状态、不执行 Git mutation；能从这些证据推导的内容不向用户重复确认。

### 1.1 识别生命周期所有者

按以下顺序读取并决定：

1. 仓库级 `AGENTS.md`、项目说明和当前用户指令；
2. 活动 change、schema、状态命令和实时 apply/archive 指令；
3. 现有任务跟踪与验证约定；
4. 没有项目权威流程时，才使用本 skill 的 fallback 结构。

| 检测结果 | 本 skill 的行为 |
|---|---|
| 项目有 QEDA/OpenSpec/其他权威生命周期 | 调用官方生命周期操作；不新增 phase、artifact、reviewer、ledger 或 Git 动作 |
| 项目只有既有任务/计划系统 | 以其任务状态为唯一真相源，本 skill 只编排实施与验证 |
| 项目没有权威流程 | 使用本文件的最小 fallback 计划，不创建额外持久文件，除非用户要求 |

每次执行都输出一句所有权决定：`因为 {证据}，由 {owner} 管理生命周期；本 skill 仅负责 {范围}`。

### 1.2 选择风险档位

| 档位 | 典型证据 | 最低控制 |
|---|---|---|
| Light | 根因已知、局部可逆、无公共契约/数据/安全/跨组件影响 | 聚焦计划、场景内 TDD、自审、聚焦验证 |
| Standard | 普通多文件功能或重构，无架构和高风险边界变化 | 完整规格追踪、测试计划、最终审查和项目原生验证 |
| Strict | 架构、公共契约、持久化数据/迁移、安全/权限/隐私/支付、并发一致性、跨组件或外部系统影响 | 项目要求的架构/独立评审、全新 bounded worker、独立整体验证 |

如果项目 schema 已经完成风险路由，直接使用其结果，不做第二次分类。风险事实不清且会改变档位时先取证；
仍不清楚则停止并说明缺失项，不靠“更严格总没错”替代授权决定。

### 1.3 锁定基线和权限

在规划前记录到项目指定工件或当前协调上下文中：

- Target baseline：滚动记录仓库根、当前分支、HEAD，以及 staged、tracked、untracked 工作树的准确状态摘要；
  只在协调者验收授权内的状态转换后更新，不能用“刷新基线”吞掉未知并发改动；
- Change base：任务开始时的原始 HEAD，在整个 change 完成前保持不变，用于累计审查已提交检查点；
- Source：实质影响方案的外部仓库 revision，或非 Git 输入的版本/摘要；
- Execution intent：`PLAN_ONLY` 或 `PLAN_AND_APPLY`；
- Git authority：`NONE` 或用户明确授予的具体动作；Commit mode：`CLOSEOUT_ONCE` 或
  `INCREMENTAL_CHECKPOINT`。

不要另建 baseline ledger。规划前、Apply 前和 Achieve 前比较当前状态；预先存在的非流程改动、HEAD 或
外部输入变化时，输出 `BASELINE_CHANGED`、具体差异和受影响决定，等待重新确认。

## Stage 2：Plan to Apply-ready

### 2.1 跟随实时工件图

已有 schema 时：

1. 读取实时 status 和当前 artifact instruction；
2. 计算 Apply requirements 及其传递依赖闭包；
3. 按依赖顺序生成或更新一个工件；
4. 每次写入后重新读取 status；
5. 到 Apply-ready 为止，不把每个工件当成额外用户检查点。

不得硬编码所有项目都必须具有 proposal、design 和 tasks。项目 schema 可以合并、增加或条件省略工件。

没有权威流程时，最小 fallback 计划应在现有计划工具或当前对话中包含：

- 一个可观察结果与范围内/范围外；
- 可验证需求或场景；
- 必要设计决定及未采用方案；
- 按依赖排序、可独立验收的任务；
- 每个场景对应的项目原生验证方法；
- 风险、回滚和真实阻塞。

### 2.2 一致性门禁

进入 Apply 前检查：

- 需求/场景都有设计和验证路径；
- 设计决定都有实施任务，任务不超出授权范围；
- 任务依赖、允许写入范围和验收方式明确，且可映射到临时场景组；
- 所有阻塞决策已解决，Execution intent 允许实施；
- baseline 未漂移。

失败时只返回负责该事实的权威工件修正，不复制一份“校验报告”作为第二真相源。

### 2.3 任务粒度评审

创建或修正实施任务时，以“能否单独给出有意义验收证据”为下限，而不是按文件、函数、Agent 或 TDD
阶段机械拆分。不要把 RED、GREEN、REFACTOR、同一行为的测试与实现、或同一生成链的输入与刷新产物
规划成必须独立委派的微任务；将它们写成一个可观察行为 task 的步骤或验收项。

如果权威 tracker 已存在更细 task，不复制、不批量重写状态；保留其编号和验收要求，并在 Apply 时把
紧密相关项映射到同一临时场景组。只有任务本身缺少可判定结果、边界互相覆盖或依赖无法表达时，才通过
生命周期所有者的正式接口修正任务定义。

### 2.4 变更拆分评审

当存在可独立交付价值、独立回滚/迁移边界、可分别批准的设计、不同验证/部署责任，或基础能力与
多个下游迁移混合时，提出具名拆分建议。任务数、文件数、模块数和复杂度分数只能触发这项评审。

默认保持单一 change。只有用户明确确认子变更名称、独立结果、前置依赖、回滚和验证边界后，才通过
项目正常接口创建子变更；不得静默改 schema、伪造目录或自动并行多个 change。

### 2.5 维护视图投影

仅在生命周期声明维护架构投影视图（维护视图契约）并提供官方 init/check 脚本时处理；未声明时不得创建或
伪造投影、模板或第二套视图状态。Apply-ready 时按以下顺序初始化 change 投影：

| 状态 | 判定 | 动作 |
|---|---|---|
| A | 已有 change 投影且有效 | 复用并运行官方结构检查，不静默覆盖 |
| B | change 投影缺失，但存在有效当前维护视图 | 调用官方初始化器，以有效当前维护视图为种子生成 change 投影 |
| C | change 投影与当前维护视图都不存在，且 schema 有全项目模板 | 才按 schema 全项目模板初始化覆盖全项目的投影 |
| D | 当前维护视图已存在但损坏 | 必须 BLOCKED，不得降级为空白模板，上报官方生命周期修复 |

脚本只做确定性初始化与结构检查；Agent 做语义设计审查。结构有效不代表语义正确：结构检查通过不豁免语义审批。

实施中出现相对已批准 change 投影的语义偏差（如新增跨包运行时依赖）时，即使现有测试通过也必须暂停受影响
任务，刷新 change 投影并重新执行结构检查与语义审批，获批后才能继续。最终验证同时比较实际实现、已批准的
change 投影与 prospective current view，由官方生命周期负责同步与归档。

## Stage 3：Apply with bounded scenario groups

### 3.1 唯一任务状态

使用项目生命周期指定的 task tracker；若没有，则使用当前计划中的任务列表。它是唯一持久进度源。
恢复执行时重新读取 task 状态、Git diff 和聚焦测试，不根据历史 worker 消息推断完成度，不创建
`issues.md`、task brief、execution ledger 或第二份实施报告来维护状态。

严格区分两个层级：

- **tracker task**：持久状态、依赖、授权范围和独立验收单元；保持项目原有编号与粒度；
- **worker 场景组**：本轮基于实时依赖临时计算的调度单元，可包含一个或多个 task，不落盘为第二状态源。

每个未完成 task 在一次调度周期中只能映射到一个场景组。组完成不等于 task 自动完成；协调者仍按
每个 task 的验收证据逐项更新权威 tracker。恢复、边界变化或失败重划时重新计算组，不迁移旧组状态。

### 3.2 场景组形成与成本收益门禁

先从“外部依赖已完成，或剩余依赖可完整纳入同组 `internal_order`”的 task 形成候选集，再按可观察
场景和执行内聚性分组。不得把组外未完成依赖偷渡进组。只有同时通过以下四个门禁才合组：

1. 服务同一可观察行为或验收场景，组合后产生完整价值；
2. 不存在下述任一强制拆分边界；
3. 至少存在一种实质内聚信号：共享局部写入/fixture/生成或测试上下文、存在无法产生独立价值的紧密
   组内顺序，或共用回滚/验证/故障归因边界；
4. 下述成本收益门禁为正。

任一门禁不满足或证据不清时保持独立组；协调者可以串行独立组，不以合组掩盖不确定性。

出现任一以下边界时保持独立场景组，即使 task 属于同一用户故事：

- 独立审批、发布、回滚、迁移、安全/权限风险或外部系统责任；
- 公共基础契约及其多个消费者：基础先独立成组，验收后消费者再分别调度；
- 组合后无法把 diff、测试或失败证据可靠归属到底层 task；
- 写入与验证可隔离，拆组能获得有意义并行，而不增加共享资源冲突。

只有“减少的重复上下文、环境准备和重复测试成本”收益必须大于“损失的并行度、失败爆炸半径、
协调和回滚成本”时才合组。任务数只用于提醒复核，不设置固定每组任务上限，也不为减少 worker 调用而
牺牲验收边界。Light 通常由协调者直接执行单 task 或单组；Standard 默认按场景组调度；Strict 对每个
独立场景组使用上下文全新、输入受限的 worker。

### 3.3 DAG 方法投影和安全并行

并行调度前完整读取并执行共享方法
`../../method-router/management-collaboration/references/dag-scheduling.md`。共享方法拥有节点/边校验、环检测、
图收缩、拓扑层、关键路径、`ready_queue`、完成事件驱动释放和失败后继隔离；本阶段只负责自动编码领域投影：

- 从权威 tracker 构建 `task DAG`，节点保持 tracker task 的正式依赖和验收身份；
- 把 3.2 已批准的内聚分组作为收缩映射，组内顺序写入 `internal_order`，跨组依赖形成临时`场景组 DAG`；
- 把下述五项隔离门禁实现为共享方法的 `eligible(node)`，只有依赖就绪且安全准入的组才能执行；
- 只有组内全部底层 task 和组级场景都经 3.6 的 Sol 验收满足，才产生一次场景组完成事件；worker 自报完成不能释放后继或改写权威状态。

DAG 调度的目标是缩短关键路径和总执行时长，同时控制上下文、冲突和失败恢复成本；不以填满卡槽或最大化并发数为目标。
运行时按完成事件驱动：Sol 验收整个场景组后立即更新后继入度，把新就绪且通过隔离门禁的组加入
`ready_queue`，有空闲卡槽就立即调度，不等待同一拓扑层全部结束。拓扑层只用于解释依赖结构和估算并行
机会，不是执行屏障，也不落盘为第二状态源。部分 task 合格不能释放依赖整个场景组的后继；先按 3.6
更新已合格 task，再从权威 tracker 重算 `task DAG`、场景组边界和 `ready_queue`。

场景组形成后，再决定组间并行。只有两个或更多候选组同时通过以下五项隔离门禁时才并行：

- 实际写入文件和生成输出不重叠；
- 不竞争共享独占资源；
- 不同时演进同一公共契约、migration、manifest 或依赖声明；
- 不消费另一个任务尚未落地的行为或接口；
- 聚焦测试和变更证据可以归属于各自场景组及其底层 task。

公共基础组必须先由协调者验收，消费者组才可进入 `ready_queue`。无法证明安全时串行执行场景组。出现意外
重叠时冻结该并发集合，保留所有已有改动，
由协调者检查组合状态后重新划分范围；不得覆盖、清理或自动回退用户及其他 worker 的改动。

### 3.4 Worker assignment

有子 Agent 能力且项目允许时，每个 Strict 独立场景组使用上下文全新、输入受限的 worker。其他档位按
成本收益选择协调者直做或使用同一合同。worker 不拥有 task 状态、Git、归档或整个 change 的完成判定。

每次 assignment 直接在调用中包含：

```yaml
change: 当前 change 与 schema，或 fallback 计划标识
scenario_group: 本轮临时组标识
group_goal: 单一可观察结果，以及本组为什么应一起执行
tasks: 每个底层任务的编号、完整文字、依赖和独立验收标准
internal_order: 组内任务和 TDD 行为的必要顺序
completed_dependencies: 已由真实状态证明完成的依赖
authorized_behavior: 相关 requirement/scenario 与确认结果
required_decisions: 必须消费的设计、接口、数据或迁移决定
allowed_writes: 允许修改的准确范围
forbidden_scope: 排除项、相邻任务、Git 和生命周期状态
focused_tests: 组级命令及其覆盖的底层任务/场景
task_checkpoints: 每个 task 需要返回的 diff、测试和验收证据
group_acceptance: 组完成所需的组合场景证据
return_contract: group_status、逐 task 的 task_result 与证据、实际修改文件、命令结果、疑虑、协调事项
time_management:
  timebox: 本轮时间预算
  critical_path: 本组在场景组 DAG 中的关键路径信息
  checkpoints: 需要回报的中间检查点
  timeout_action: 时间盒到期后的验收、带证据重排或升级动作
```

`group_status` 只取：`DONE`（全部 task 与组级场景满足）、`DONE_WITH_CONCERNS`（全部满足但有非阻塞疑虑）、
`NEEDS_CONTEXT`、`NEEDS_COORDINATION`（含部分 task 满足、依赖或边界需重划）、`BLOCKED`。每个 `task_result`
只取 `SATISFIED`、`UNSATISFIED`、`BLOCKED` 并附证据；它只是验收建议，不拥有 tracker 状态。

### 3.5 场景组内 TDD

对可观察行为变更，在同一场景组和 worker 内执行完整闭环，不把 RED、GREEN、REFACTOR 或紧密相连的
测试/实现微任务拆给不同 worker：

1. RED：先添加并运行失败测试，确认失败来自目标行为尚未实现，而不是语法、fixture、环境或无关设置；
2. GREEN：编写最小实现，循环运行新增和直接影响的测试直到通过；
3. REFACTOR：只做当前任务必要整理；若改代码，复跑同一组测试。

纯文档、声明性配置、生成物刷新或不能合理形成行为测试的 task 按其验收方法执行，不虚构 RED。
Apply 阶段运行聚焦测试；最终全量或跨场景验证留给 Stage 4。

### 3.6 协调者逐任务验收

worker 返回后，协调者必须检查共享工作树中的：

- 实际 diff 与 allowed writes，以及每项改动到 task 的映射；
- 是否覆盖预先存在或其他任务的改动；
- 聚焦测试的真实命令和结果；
- 每个 task 的需求、设计决定、独立验收及组级场景是否满足；
- 是否出现新的依赖、边界变化或疑虑。

证据支持后才逐项更新底层任务状态；不得因组级 `DONE` 一键完成全部 task。部分 task 合格时只更新合格项，
失败项保留未完成并按当前 diff、依赖和风险重划恢复组；缺上下文就补最小上下文恢复 worker；需要协调就
重划边界；真实计划或授权问题才请求用户裁决。只要有依赖就绪任务就持续调度。

### 3.7 增量交付检查点

只有 Git authority 为 `LOCAL_COMMIT` 且 Commit mode 为 `INCREMENTAL_CHECKPOINT` 时，才在 DAG 执行中评估
阶段提交。用户说“分批提交”“阶段性提交”“做完一部分先提交”或明确要求避免最后一次提交过多文件，表示
授权当前任务产生多个本地提交；不推导 push、PR、部署或其他仓库权限。

每次 Sol 完成 3.6 验收后，按以下门禁形成一个完整验收的交付切片：

1. 切片包含一个或多个已满足的底层 task/场景组，提交后自身行为有效、可解释、可回退，不依赖未完成代码
   才能成立；单个 worker 返回、RED/GREEN 中间态或仅部分通过的场景组不合格；
2. 为下一次 commit 从实际 diff 重新计算准确的 `AUTHORIZED_COMMIT_SET`，其中每个文件的全部当前改动只属于
   该切片；排除
   预先存在、范围外、其他参与者以及混合未完成任务改动的文件，默认不使用补丁暂存绕过混合边界；
3. 对该切片执行项目规定的聚焦审查和必要验证，Critical/Important 清零；共享契约、manifest、生成链或
   测试证据不能独立归属时，继续累积到边界完整，不为减少文件数强行提交；
4. 暂停会修改该切片文件或目标仓库 Git 状态的调度，把 `AUTHORIZED_COMMIT_SET` 交给“Git 与外部动作边界”
   的统一事务协议；使用 conventional commit 记录已完成结果，不使用 `WIP:` 表示已验收交付；
5. 统一事务成功后更新完整 Target baseline 并恢复 `ready_queue`；保留原始 Change base，确保 Stage 4 对累计
   提交和剩余改动做 whole-change 审查。事务失败时保持冻结并按统一错误状态恢复，不复制另一套 Git 规则。

阶段提交只减少安全工作树中的累计改动，不触发归档、不把整个 change 标记完成，也不替代 3.6 的验收或
完成事件；DAG 后继是否释放仍只由真实任务/场景组验收决定。没有合格文件集时继续实施或重划边界，不创建
空提交，不把未完成改动硬塞进本批次。

### 3.8 共享执行 provider 选择

默认可选用共享 Sol-Luna provider（`_providers/sol-luna`，无 `SKILL.md`；`auto-code-generator` 是唯一用户
入口）。有效配置为 `off`，或用户在当前任务明确说“不用 Luna”“只用 Sol”时不委派；当前用户明确要求
Luna 时可单次覆盖持久 `off`，但不得改写配置。选择与委派规则见
`references/execution-providers/sol-luna.md`。Codex 原生 runner 由 Sol 按以下顺序直接协调，不进入 Python
控制器：

1. 先应用当前任务的显式选择；“不用 Luna”“只用 Sol”优先关闭，其余情况默认按 `mode=auto` 选择；
2. 从用户模型列表解析精确模型，再从当前 `spawn_agent` 工具说明读取模型 allowlist 与权限能力；不得用 CLI
   缓存推断原生能力；
3. 精确模型和权限均匹配时，直接调用 `spawn_agent`，显式传入 `model`、`reasoning_effort`、
   `fork_turns="none"` 和六字段任务卡；
4. `spawn_agent` 返回 Agent 标识即记为已启动；此后失败只由 Sol 检查工作树并恢复，不得改走其他 runner；
5. 只有尚未启动且原生能力不匹配时，才调用 provider 控制器的外部 runner，以同一模型走受限 CLI 降级；
   用户要求 `native only` 时直接 `BLOCKED`。

模型 backend 与执行 runner 分离；不得静默换模或在已启动失败后重复执行。
把完整内聚场景组压缩为一个六字段任务卡；assignment 的 `time_management` 必须进入六字段任务卡的“约束”，
由同一个 `luna-worker` 完成 `RED → GREEN → REFACTOR`，不得
拆分 TDD；provider 不拥有生命周期、任务状态或 Git 授权；完整场景组无法在限额内保持语义时 provider
不适用，回退 Sol 或项目原生执行，不得切碎 TDD。

所有 runner 使用同一套 runner 无关的统一返回验收规则：原生和外部返回都必须映射到 provider 的
`result-schema.json`，由 Sol 在更新 tracker 前检查逐 task 证据、`time_management` 与 assignment 一致性。
带 timebox 的结果不得使用 `N/A`；时间盒到期只能选择“完成验收”“带证据重排”或“升级阻塞”，不能
静默延长或跳过验证。`TIMEBOX_EXPIRED + 完成验收` 必须对应 `DONE` / `DONE_WITH_CONCERNS`；重排或
升级动作不得对应完成态。结构不完整或语义矛盾时不得验收，返回补充上下文、重排或阻塞。

## Stage 4：Review & Verify final state

### 4.1 最终审查

针对从原始 Change base 到当前 HEAD 的累计提交，加上尚未提交的工作树 diff，而不是只看最后一个检查点或
为每个并行组固定跑 N 轮：

- 对照确认边界、需求/场景、设计、任务、测试计划和项目规则；
- 将问题分为当前变更相关或既有/范围外，再分为 Critical、Important、Minor；
- Critical 和 Important 必须在授权边界内解决；需要扩边界时先获得确认；
- Strict 使用一次上下文独立的 whole-change reviewer；不要叠加任务级独立 reviewer；
- 修复影响实现或验证后，重新审查受影响部分。

### 4.2 项目原生验证

只有当前最终审查不阻塞时才执行最终验证：

1. 按 test plan 将每个变更场景映射到项目原生命令或可重复方法；
2. 记录实际命令/方法、退出状态和关键结果；
3. 真实数据、迁移、权限、并发、外部系统或人工验证只在场景需要时执行；
4. 未执行或环境不可用的项目写 `PENDING`、`BLOCKED` 或 `N/A` 及原因，禁止伪造通过；
5. 相关代码、测试、配置、生成行为、spec 或 test plan 变化后，重跑受影响结果。

最终结论只能是：

- `VERIFIED`：必要检查全部通过，且无当前变更的 Critical/Important；
- `BLOCKED`：权限、策略、环境或外部依赖阻止完成；
- `INCOMPLETE`：实施、审查或验证仍有必要工作未完成。

不得用“真实数据 100%”“测试数量”或“审查轮数”代替按场景验证。

## Stage 5：Achieve, closeout and report

最终归档状态统一记录为 `archive=SUCCESS | N/A | FAILED`。项目生命周期存在官方归档/关闭操作时，只有
`VERIFIED` 才能调用，并且成功后记录 `archive=SUCCESS`；失败记录 `archive=FAILED`，保持活动 change 并恢复。
没有官方生命周期归档操作的 fallback 项目记录 `archive=N/A`，不得为满足流程发明归档目录或伪造结果。
归档前再次检查 baseline、最终审查、验证结论和任务状态；由生命周期所有者同步 spec 和移动 change。

归档状态确定后，若有对应 Git authority，先按“Git 与外部动作边界”执行最终 closeout；无 Git 授权或
`AUTHORIZED_COMMIT_SET` 为空时不创建 commit。closeout 成功、不适用或明确失败后，再输出简洁最终报告，
确保其中的 hash/status 是当前事实：

```text
结果：VERIFIED / BLOCKED / INCOMPLETE
生命周期所有者与风险档位：...
已完成结果与范围：...
关键变更文件：...
审查：Critical 0，Important 0，Minor N
验证：命令/方法、退出状态、关键结果
归档：位置或未归档原因
Git：未授权 / 无剩余授权内 diff / checkpoints [<hash>...] + closeout <hash|N/A> / 提交失败 <状态/原因>
范围外发现：仅列候选，不写入当前任务状态
```

报告是当前事实的展示，不是新的状态账本。Minor 和范围外发现可以报告，但不得把失败的必要测试或
未解决的 Critical/Important 降级成“遗留问题后继续归档”。

## Git 与外部动作边界

- 默认不 stage、不 commit、不 push、不创建 PR、不部署；
- `AUTHORIZED_COMMIT_SET` 始终表示“下一次 commit 的准确文件及内容集合”，每次提交前重新计算：增量模式
  从 3.7 已完整验收的切片得到，closeout 模式从最终已确认 diff 得到；两种模式都排除预先存在、范围外或
  其他参与者的改动；
- Commit mode 默认为 `CLOSEOUT_ONCE`；只有用户明确要求多个本地提交、分批提交或阶段性提交时才设置
  `INCREMENTAL_CHECKPOINT`，该授权仅在当前任务和目标仓库/分支有效；
- 紧邻暂存前重新读取 branch、HEAD 和 status，并与 Target baseline 比较；发生漂移时停止。当前分支是
  `main`/`master` 时停止提交，只有项目分支工作流或用户另行授权后才能创建或切换分支；
- 暂存前拒绝进行中的 merge/rebase/cherry-pick/revert（`MERGE_HEAD`、rebase state、`CHERRY_PICK_HEAD`、
  `REVERT_HEAD`）；普通本地 commit 授权不包含完成这些 Git 操作的权限；
- 从暂存开始到 commit/tree 核验完成，目标仓库的 Git index 和当前分支必须由协调者独占；其他 Agent、hook
  或流程造成的 HEAD/index 漂移都必须停止本次提交；
- 只暂存 `AUTHORIZED_COMMIT_SET` 中的明确路径，不改动预先存在的 staged 状态；暂存后必须检查
  `git diff --cached --name-status` 和 `git diff --cached`，文件集合或内容不完全匹配就停止提交；
- 提交前执行项目规定的审查与验证，并证明结果对应精确暂存快照；剩余工作树改动参与过的测试结果不能单独
  证明 staged tree 有效；不得 force push；
- 记录 `pre_commit_head` 和 `reviewed_tree = git write-tree`，紧邻 commit 前复核二者及完整 cached diff；
  提交后读取完整 parent 列表，验证新提交恰好一个 parent 且该 parent 等于 `pre_commit_head`，同时验证
  `HEAD^{tree}` 等于 `reviewed_tree`；任一不一致时报告 `COMMIT_TREE_MISMATCH` 并停止，不自动 amend、reset
  或 push；
- 一个 task、worker 返回、TDD transition 或 artifact 完成不会自动成为 commit 边界；
- `INCREMENTAL_CHECKPOINT` 按 3.7 的 `AUTHORIZED_COMMIT_SET` 提交完整验收切片，门禁是切片验收通过、
  切片必要审查/验证通过、准确暂存集、工作分支和独立 Git 授权；它不要求整个 change 已归档；
- 用户只要求“一个本地 commit”或未明确要求分批时使用 `CLOSEOUT_ONCE`，只创建一个 closeout commit；
- closeout commit 的统一门禁是 `VERIFIED + archive SUCCESS/N/A + 独立 Git 授权`；官方归档存在时必须
  `archive=SUCCESS`，fallback 无归档操作时允许 `archive=N/A`。提交后报告 hash 和 status；
- `INCREMENTAL_CHECKPOINT` 表示“零到多个 checkpoint + 一个最终 closeout”：Stage 4 修复、Stage 5 归档或
  其他剩余授权内 diff 在上述 closeout 门禁通过后形成最终 closeout；若没有剩余 diff，不创建空 commit，
  只报告已有 checkpoint hashes；
- 每次增量提交后更新完整 Target baseline，但保留原始 Change base；最终审查和验证必须覆盖 Change base
  以来的全部 checkpoint commits 与剩余 diff；
- push、PR 和部署各自需要明确授权，不能从 commit 权限推导。

## 错误与恢复

| 场景 | 处理 |
|---|---|
| 权威流程或 schema 不明确 | 读取项目配置和实时状态；仍不明确则报告缺失证据并停止 |
| baseline 漂移 | 输出 `BASELINE_CHANGED` 和差异，等待重新确认 |
| 任务边界不明确 | 在权威计划中修正；需要新结果时先确认扩边界 |
| RED 因环境或 fixture 失败 | 修复测试基础后重新建立有效 RED，不宣称 TDD 完成 |
| worker 越界或并行重叠 | 冻结相关任务，保留改动，协调者重划边界后串行恢复 |
| 场景组过大或部分失败 | 按独立验收、回滚与证据边界拆组；只保留已验收 task 状态，未完成项重新调度 |
| 连续根因假设失败 | 稳定复现并重新检查设计、任务粒度和授权，禁止叠加猜测性修复 |
| Critical/Important 未解决 | 返回 Apply；不能自动跳过、归档或提交 |
| 验证环境不可用 | 结论写 `BLOCKED` 或 `INCOMPLETE`，不得标记通过 |
| 归档失败 | 保持活动 change，按官方错误恢复，不手工移动目录 |
| 无 Git 授权 | 完成到归档和报告即停止，提供提交建议但不执行 |
| 增量切片混合未完成/他人改动 | 排除混合文件并继续实施或重划边界；不补丁暂存、不创建空提交 |
| 存在进行中的 merge/rebase/cherry-pick/revert | 停止普通 commit；不得替用户完成或中止该 Git 操作 |
| commit 前 HEAD/index 漂移 | 停止提交并重新取证；不得沿用旧 `reviewed_tree` |
| commit tree 与 `reviewed_tree` 不同 | 返回 `COMMIT_TREE_MISMATCH`，保留现场并停止；不自动改写历史或 push |

## 输出质量指标

| 指标 | 目标 | 检查方法 |
|---|---|---|
| 生命周期唯一性 | 1 个 owner、1 个任务真相源、1 个最终结论 | 检查是否新增平行 phase/ledger/verdict |
| 调度可追踪 | 每个本轮 task 恰好映射到一个临时场景组，组完成后逐项验收 | 检查 assignment 与 tracker 更新 |
| 调度收益 | 合组节省的上下文/准备/测试成本大于并行、失败、协调和回滚成本 | 记录分组理由与反例边界 |
| 并行效率 | 无不必要的拓扑层屏障；安全后继在验收后立即进入 ready queue | 检查完成事件、卡槽释放和调度日志 |
| 范围可追踪 | 每个改动可追溯到已确认场景或必要实现细节 | 对照 diff 与规格/任务 |
| TDD 有效性 | 所有适用行为任务有有效 RED、GREEN、必要 REFACTOR | 检查失败原因和聚焦命令 |
| 并行安全 | 并行场景组满足五项隔离条件 | 检查写入、契约、资源和测试归属 |
| 审查闭环 | 当前变更 Critical/Important 为 0 | 读取最终审查 |
| 验证真实性 | 每项必要验证有实际命令/方法、状态和关键结果 | 读取最终验证 |
| Git 授权 | 每个 Git/外部动作都有对应明确授权 | 对照用户指令和动作日志 |

## 规则更新

如果本次执行暴露出可复用模式，只在最终报告中给出“候选规则、证据、适用边界和反例”。只有用户另行
明确要求更新 skill/AGENTS/项目规则时，才进入对应维护流程并通过其评估；本阶段不自动写规则。

---

*版本：4.6*
*最后更新：2026-08-18*
*变更：新增授权式增量交付检查点，在完整验收切片后分批提交并保留累计 whole-change 审查。*
