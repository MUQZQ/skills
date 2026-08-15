# Sol-Luna 执行 Provider 适配

本文件描述 `auto-code-generator` 如何把场景组委派给共享 Sol-Luna provider。先解析当前
`auto-code-generator/SKILL.md` 的真实路径（consumer 入口可能是 Junction），以其父级 skills 权威目录为根，
再定位同级 `_providers/sol-luna`；不要假定 consumer skills root 本地存在 `_providers`。provider 无
`SKILL.md`，唯一用户入口是 `auto-code-generator`。
provider 只负责有界执行，不拥有生命周期、任务状态或 Git 授权。

## 选择门禁

- 只有当前会话用户**显式同意**使用 Luna（点名 Luna 角色或明确说“这次用 Luna”）时，才选择本 provider。
- 持久 `mode=auto|force` 只描述触发后的委派策略，不能替代当前会话显式同意；未收到显式同意时不调用。
- 每次 `run` / `smoke` 都必须携带 `--user-triggered`，且不得写入项目或全局配置。

## 模型选择

- Sol 是当前主会话模型，不进入模型列表；Luna 候选由用户在 provider 的 `luna-models.json` 中按顺序维护。
- 初始第一项是 `gpt-5.6-luna`，第二项是享有套餐额度的 `gpt-5.3-codex-spark`；其余顺序由用户维护，
  provider 不自动发现、联网刷新或静默改写。
- 用户只说“这次用 Luna”时使用列表第一项；`auto` / `default` 也是第一项。用户点名模型时按 `id` 或
  `aliases` 选择；不存在时停止并展示 `models` 的结果，不静默替换。
- 只读列出候选：`python -X utf8 <provider>/scripts/sol_luna.py models`。
- 单次执行：`python -X utf8 <provider>/scripts/sol_luna.py --project-root <project> run worker
  --user-triggered --model <id-or-alias> "<六字段任务卡>"`。
- `backend=codex` 由同一控制器使用受限的临时 `codex exec`；`backend=claude` 使用 Claude Code。
  不使用原生 `spawn_agent`，也不在后端失败时静默换模。
- Claude 条目变化后运行 `configure-claude` 合并映射；Codex 条目不需要该步骤。之后由当前会话明确授权
  运行对应模型的 `smoke`。Codex 返回的 `command_only` 只证明请求参数，不能冒充服务端实际模型证明。

## 委派粒度

- 把一个**完整内聚场景组**压缩为 provider 的**六字段任务卡**（目标、允许范围、禁止范围、约束、
  预期输出、验证证据），交给一个 `luna-worker` 在同一次执行上下文内完成
  `RED → GREEN → REFACTOR`。
- **不得拆分 RED、GREEN、REFACTOR**：同一行为的失败测试、最小实现、断言和必要重构不得派给不同
  worker，也不得按阶段切成多次调用。

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
