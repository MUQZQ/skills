# Luna 原生执行适配

本文件描述 `auto-code-generator` 如何把完整场景组委派给 Luna。共享 provider 只保留执行契约与
`result-schema.json`，不拥有生命周期、任务状态或 Git 授权。

consumer 入口可能位于 Junction。调用方必须先解析当前 `auto-code-generator/SKILL.md` 的真实路径，
从该文件所在 Skill 目录向上三级定位权威 skills 根目录，再读取同级 `_providers/sol-luna`；不得假定
consumer skills 根目录本身存在 `_providers`，也不得使用评测快照或历史副本作为 provider 权威源。

## 选择门禁

- Luna 默认开启，固定且唯一使用 `gpt-5.6-luna`。
- 用户在当前任务明确说“不用 Luna”“只用 Sol”时不委派，由 Sol 直接执行；不写持久配置。
- 模型可用性和宿主实际能力面只读取当前 `spawn_agent` 工具说明，不从 CLI、缓存、配置文件或历史会话推断。
- 任务卡不是安全边界。任务需要只读工具白名单、路径沙箱或命令限制而宿主无法强制时，由 Sol 直接执行；
  不得把自然语言任务卡当作权限隔离证明。
- 模型可用且宿主能力未超出用户与项目对当前任务的授权时调用 `spawn_agent`，显式传入 `model="gpt-5.6-luna"`、适合任务的
  `reasoning_effort`、`fork_turns="none"` 和六字段任务卡。
- `gpt-5.6-luna` 不可用或宿主能力超出当前授权时由 Sol 直接执行当前场景组；不换模、不调用外部 runner、不建立候选目录。
- `spawn_agent` 返回 Agent 标识即代表已启动；之后失败时先检查 Agent 结果、共享工作树、diff 和测试证据，
  再由 Sol 补充上下文、重划边界或接管，不自动重跑。

## 委派粒度

- 把一个**完整内聚场景组**压缩为**六字段任务卡**：目标、允许范围、禁止范围、约束、预期输出、验证证据。
- assignment 的时间盒、关键路径、检查点和超时动作必须写入六字段任务卡的“约束”；返回结果包含结构化
  `time_management`。
- 同一个 `luna-worker` 完成 `RED → GREEN → REFACTOR`；不得拆分 RED、GREEN、REFACTOR。
- **充分利用可用卡槽**：只有多个场景组通过依赖、写入、资源、契约和验证隔离门禁时才并行；Sol 保留
  领导协调、依赖确认、证据回收、冲突处理和最终验收。不得为填槽拆分内聚场景，安全隔离证据不足时串行优先。
- **任务不清晰先问 Sol**：目标、上下文、范围、依赖、约束或验收证据不清时暂停，返回
  `NEEDS_CONTEXT` / `NEEDS_COORDINATION`，不得猜测或扩大范围。
- 完整场景组无法在任务卡内保真表达时 provider 不适用，由 Sol 直接执行，不切碎 TDD。

## 返回与验收

- 原生 Luna 返回必须映射到共享 `result-schema.json`：组状态、逐 task 结果、真实 diff、验证证据和
  `time_management`。
- Sol 在更新 tracker 前逐项核对任务证据、实际 diff、验证结果与 assignment；不得凭组级 `DONE` 一键完成。
- 带 timebox 的结果不得使用 `N/A`。`TIMEBOX_EXPIRED + 完成验收` 才能对应完成态；带证据重排或升级阻塞
  不得对应完成态。
- provider 不归档、不 commit、不 push、不建 PR、不部署。
