# Sol-Luna 共享 Provider 契约

## 定位

本目录是 `auto-code-generator` 的轻量执行契约，不是用户触发 skill：无 `SKILL.md`、无模型控制器。
`auto-code-generator` 是唯一用户入口，Sol 负责规划、协调、证据验收和最终决策。

## Luna 执行档位

- Luna 默认开启，表示低成本执行档位，不绑定固定模型名。
- 档位绑定只按宿主当前 `spawn_agent` 能力：优先使用宿主提供的低成本或快速模型；没有时在同一模型上
  使用较低的 `reasoning_effort`。
- 委派只通过宿主 `spawn_agent`；显式传入所选模型或较低的精力档位、`fork_turns="none"` 和输入受限的任务卡。
- 任务卡不是安全边界。任务要求只读工具白名单、路径沙箱或命令限制而宿主无法强制时，仅项目允许协调者实施时由 Sol 直接执行；否则保持 BLOCKED。
  不得把任务卡当作机器可执行的权限隔离。
- 不维护候选模型清单、别名、其他后端、外部 CLI 回退或 provider 映射。
- 用户在当前任务明确说“不用 Luna”“只用 Sol”时，不委派 Luna 且不写持久配置；项目强制独立 worker 时报告冲突，不自动内联。
- 当前工具无法落实该档位，或宿主能力超出用户与项目对当前任务的授权时，仅项目允许协调者实施时由 Sol 直接执行；
  强制独立 worker 时保持 BLOCKED，不调用外部通道。
- `spawn_agent` 返回 Agent 标识后不自动重跑；Sol 先检查共享工作树、diff、测试和 Agent 结果再恢复。

## 任务与结果

- 委派任务卡固定六项：目标、允许范围、禁止范围、约束、预期输出、验证证据；任一项不清楚则不委派。
- 一个完整内聚场景组由同一 Luna 完成，禁止拆分 `RED → GREEN → REFACTOR`。
- `references/result-schema.json` 是统一返回契约。Sol 核对逐 task 证据、实际 diff、验证和
  `time_management` 后，才更新权威 tracker。
- provider 不覆盖项目的任务组、独立上下文、角色标记和执行记录要求；
  不拥有生命周期、任务状态或 Git 授权；不归档、不 commit、不 push、不建 PR、不部署。

## 管理资产

- `CONTRACT.md`：单一路径、任务和授权边界；
- `references/result-schema.json`：Luna 结构化返回契约。
