# Sol-Luna 执行 Provider 适配

本文件描述 `auto-code-generator` 如何把场景组委派给共享 Sol-Luna provider。先解析当前
`auto-code-generator/SKILL.md` 的真实路径（consumer 入口可能是 Junction），以其父级 skills 权威目录为根，
再定位同级 `_providers/sol-luna`；不要假定 consumer skills root 本地存在 `_providers`。provider 无
`SKILL.md`，唯一用户入口是 `auto-code-generator`。
provider 只负责有界执行，不拥有生命周期、任务状态或 Git 授权。

## 选择门禁

- Luna 默认开启，未配置时按 `mode=auto` 选择本 provider。
- 当前任务中的显式选择优先：用户说“不用 Luna”“只用 Sol”时不调用；有效配置为 `mode=off` 时也不自动调用。
- 当前用户明确要求 Luna 时可单次覆盖有效 `off`。原生 runner 在调用 `spawn_agent` 前应用该选择；外部 runner
  仅在这种覆盖情形携带 `--user-triggered`，且不得写入项目或全局配置。该参数是受信任编排层的当前请求
  声明，不是本地调用者权限之外的安全凭据。

## 模型选择

- Sol 是当前主会话模型，不进入模型列表；Luna 候选由用户在 provider 的 `luna-models.json` 中按顺序维护。
- 初始第一项是 `gpt-5.6-luna`，第二项是享有套餐额度的 `gpt-5.3-codex-spark`；其余顺序由用户维护，
  provider 不自动发现、联网刷新或静默改写。
- 用户只说“这次用 Luna”时使用列表第一项；`auto` / `default` 也是第一项。用户点名模型时按 `id` 或
  `aliases` 选择；不存在时停止并展示 `models` 的结果，不静默替换。
- 只读列出候选：`python -X utf8 <provider>/scripts/sol_luna.py models`。
- `backend` 表示模型来源，`runner` 表示执行通道。`backend=codex` 条目的 runner 优先级固定为
  `native_spawn → codex_exec`；`backend=claude` 条目使用 `claude_code`。不得把 runner 写进用户模型列表，
  也不得持久化当前客户端的动态能力。
- 原生 allowlist 和权限能力只读取当前 `spawn_agent` 工具说明；不得从 `luna-models.json`、CLI 模型缓存
  或历史会话推断。所选 Codex **精确模型**位于当前会话暴露的原生 allowlist，且工具说明证明原生权限边界
  满足角色要求时，Sol 直接使用 `native_spawn`：调用原生 `spawn_agent`，显式传入
  `model=<provider_model>`、对应
  `reasoning_effort` 与 `fork_turns="none"`，并把六字段任务卡和角色边界直接放入 assignment。不得省略
  `model` 继承 Sol，也不得静默换模。
- 当精确模型不在原生 allowlist、当前宿主未提供原生子 Agent，或原生权限边界不能满足任务时，仅在启动前
  选择 `codex_exec`（`codex exec`），使用控制器执行同一模型：`python -X utf8 <provider>/scripts/sol_luna.py
  --project-root <project> run worker --model <id-or-alias> "<六字段任务卡>"`。有效 `off` 被当前用户明确覆盖时
  额外传 `--user-triggered`。若用户明确要求
  `native only`，则返回 `BLOCKED` 并展示当前原生模型，不得回退 CLI。
- `scripts/sol_luna.py run` 只实现外部 runner，不是原生分派入口；符合原生条件时 Sol 不调用该命令。
  回退只允许发生在任何 worker 尚未启动时。`spawn_agent` 返回 Agent 标识即视为已启动，后续失败必须升级给
  Sol 检查共享工作树；不得自动再跑 `codex_exec`，避免重复写入和重复测试。
- `backend=claude` 使用 `claude_code`，通过同一控制器执行；不在后端失败时静默换模。
- Claude 条目变化后运行 `configure-claude` 合并映射；Codex 条目不需要该步骤。之后运行对应模型的
  `smoke`。Codex 返回的 `command_only` 只证明请求参数，不能冒充服务端实际模型证明。

## 委派粒度

- 把一个**完整内聚场景组**压缩为 provider 的**六字段任务卡**（目标、允许范围、禁止范围、约束、
  预期输出、验证证据），交给一个 `luna-worker` 在同一次执行上下文内完成
  `RED → GREEN → REFACTOR`。
- **不得拆分 RED、GREEN、REFACTOR**：同一行为的失败测试、最小实现、断言和必要重构不得派给不同
  worker，也不得按阶段切成多次调用。
- **建议规则：充分利用可用卡槽。** 当同一波次有多个已通过依赖、写入、资源、契约和验证隔离门禁的独立
  场景组，且存在空闲子 Agent 卡槽时，Sol 应优先并行调度这些组，把自己集中在领导协调、依赖确认、证据
  回收、冲突处理和最终验收上。卡槽不足时按依赖波次排队；不得为了填满卡槽拆分内聚场景、TDD 循环、
  公共契约或共享资源，安全隔离证据不足时串行优先。
- **建议规则：任务不清晰先问 Sol。** Luna 对目标、上下文、范围、依赖、约束、验收证据或冲突存在疑问时，
  应立即暂停并向 Sol 提出具体问题；不得猜测、扩大授权或先修改文件。需要上下文或协调时返回
  `NEEDS_CONTEXT` / `NEEDS_COORDINATION`，由 Sol 补充决策后再调度。
- 进行角色分工、委派、卡槽调度、升级或协作复盘时，可先读取
  `method-router/management-collaboration/SKILL.md`，参考 RACI、委派任务卡、Kanban/WIP、时间盒和检查点；它是协调
  方法参考，不拥有项目生命周期、任务状态或 Git 权限。

## 返回与验收

- provider 只返回 `group_status`、逐 task 的 `task_results`、真实 diff、命令结果与证据；
  `auto-code-generator`（Sol）据此逐 task 核验并更新权威 tracker，不得整组一键完成。
- 两个后端统一使用 consumer 契约：组状态为 `DONE`、`DONE_WITH_CONCERNS`、`NEEDS_CONTEXT`、
  `NEEDS_COORDINATION`、`BLOCKED`；task 状态为 `SATISFIED`、`UNSATISFIED`、`BLOCKED`。完成态要求
  每个 task 都是 `SATISFIED`，逐 task 证据和组级验证不得为空。
- provider 不归档、不 commit、不 push、不建 PR、不部署。

## 降级

- 当完整内聚场景组压缩后超出 provider 的 prompt/结果限额，或无法在任务卡内保持语义时，
  **provider 不适用**：回退由 Sol 或项目原生执行直接完成该场景组，而不是切碎 TDD 来迁就 provider。
