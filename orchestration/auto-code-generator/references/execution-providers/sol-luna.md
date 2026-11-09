# Luna 原生执行适配

本文件描述 `auto-code-generator` 如何把完整场景组委派给 Luna。共享 provider 只保留执行契约与
`result-schema.json`，不拥有生命周期、任务状态或 Git 授权。

consumer 入口可能位于 Junction。调用方必须先解析当前 `auto-code-generator/SKILL.md` 的真实路径，
从该文件所在 Skill 目录按 `../..`（向上两级）定位权威 skills 根目录，再读取 `_providers/sol-luna/CONTRACT.md`
及其 `references/result-schema.json`；读取前确认文件存在，路径不符时报告定位失败，不猜测备用根。不得假定
consumer skills 根目录本身存在 `_providers`，也不得使用评测快照或历史副本作为 provider 权威源。

## 选择门禁

- Luna 默认开启，表示低成本执行档位，不绑定固定模型名。
- 档位绑定按宿主当前 `spawn_agent` 说明选择：优先使用宿主提供的低成本或快速模型（如该模型可用）；
  没有时在同一模型上使用较低的 `reasoning_effort`。只读当前能力说明，不维护候选模型清单或外部映射。
- 用户在当前任务明确说“不用 Luna”“只用 Sol”时不委派 Luna，不写持久配置；
  项目允许协调者实施才由 Sol 直接执行，项目强制独立 worker 时说明冲突，不自动内联。
- 模型、精力档位可用性和宿主实际能力面只读取当前 `spawn_agent` 工具说明，不从 CLI、缓存、配置文件或历史会话推断。
- 任务卡不是安全边界。任务需要只读工具白名单、路径沙箱或命令限制而宿主无法强制时，仅在项目允许协调者实施时由 Sol 直接执行；项目要求独立 worker 时保持 BLOCKED。
  不得把自然语言任务卡当作权限隔离证明。
- 档位可落实且宿主能力未超出用户与项目对当前任务的授权时调用 `spawn_agent`，显式传入所选模型或较低的
  `reasoning_effort`、`fork_turns="none"` 和六字段任务卡。
- 档位无法落实或宿主能力超出当前授权时，先核对项目降级规则：允许协调者实施才由 Sol 直接执行；
  强制独立 worker 时保持 BLOCKED，不调用外部通道、不调用外部 runner、不建立候选目录。用户关闭 Luna 也不豁免项目独立性要求。
- `spawn_agent` 返回 Agent 标识即代表已启动；之后失败时先检查 Agent 结果、共享工作树、diff 和测试证据，
  再由 Sol 补充上下文、重划边界或在项目允许时接管，不自动重跑。

## 委派粒度

- 把一个**完整内聚场景组**压缩为**六字段任务卡**：目标、允许范围、禁止范围、约束、预期输出、验证证据。
- assignment 的时间盒、关键路径、检查点和超时动作必须写入六字段任务卡的“约束”；返回结果包含结构化
  `time_management`。
- 测试顺序以 assignment 中的项目策略为准；不要求 TDD 的项目可先实现后补测试，不由 provider 增加 RED 门禁。
- 适用 TDD 时，同一个 `luna-worker` 完成 `RED → GREEN → REFACTOR`；不得拆分 RED、GREEN、REFACTOR。
- **充分利用可用卡槽**：只有多个场景组通过依赖、写入、资源、契约和验证隔离门禁时才并行；Sol 保留
  领导协调、依赖确认、证据回收、冲突处理和最终验收。不得为填槽拆分内聚场景，安全隔离证据不足时串行优先。
- **任务不清晰先问 Sol**：目标、上下文、范围、依赖、约束或验收证据不清时暂停，返回
  `NEEDS_CONTEXT` / `NEEDS_COORDINATION`，不得猜测或扩大范围。
- 完整场景组无法在任务卡内保真表达时 provider 不适用；保留项目完整任务书，允许协调者实施才由 Sol 直接执行，否则报告阻塞，不切碎 TDD。

## 返回与验收

- 原生 Luna 返回必须映射到共享 `result-schema.json`：组状态、逐 task 结果、真实 diff、验证证据和
  `time_management`。
- Sol 在更新 tracker 前逐项核对任务证据、实际 diff、验证结果与 assignment；不得凭组级 `DONE` 一键完成。
- 带 timebox 的结果不得使用 `N/A`；`TIMEBOX_EXPIRED + 完成验收` 必须对应 `DONE` / `DONE_WITH_CONCERNS`；
  带证据重排或升级阻塞不得对应完成态。
  带时间盒的返回须核对 assignment 一致性，不得静默延长或跳过验证。
- provider 不归档、不 commit、不 push、不建 PR、不部署。
- 项目要求的任务组边界、角色标记、独立上下文和原始执行记录不能被六字段任务卡或返回 schema 省略。
