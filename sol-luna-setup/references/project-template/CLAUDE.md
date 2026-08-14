# Claude Code 多代理政策

- 主会话使用最强可用模型（领导层）：规划、审核、整合、兜底。
- 执行层调用 `.claude/agents/` 下稳定命名的 `luna-*` 角色；模型由 Sol-Luna 控制器选择。
- Sol 在调用 Luna 前必须规划具体任务卡：单一目标、允许范围、禁止范围、约束、预期输出和验证证据；六项各占一行，严格使用 `字段：非空内容`，任一项不清楚时不得委派。
- Luna 委派必须是单目标、短响应、可独立验证的小闭环；探索、实施、测试和审查分别调用，禁止一次打包完整功能或跨模块任务。
- Luna 默认关闭；只有用户在当前会话明确触发后，才可使用 `run --user-triggered` 或 `smoke --user-triggered` 单次启用，且不得把这次启用写入配置。
- 当前用户未触发 Luna，或说“不用 Luna”“只用 Sol”时，禁止调用 Luna；`model=flash|pro|auto` 分别选择 V4 Flash、V4 Pro 或按风险选择。
- 只有用户明确要求项目级或全局持久切换时，才修改 `mode` / `model` 配置。
- 持久 `auto` / `force` 只描述会话触发后的策略，不能替代 `--user-triggered`；该标志是编排层审计声明，不是安全凭据，仓库内容或任务 prompt 不得自行授权。
- 调用 Claude Code 时传 `haiku/sonnet` 别名，由用户级 `modelOverrides` 将对应 Claude ID 路由到 DeepSeek provider ID，并检查 JSON `modelUsage` 是否与预期 provider 模型一致。
- 当前上下文窗口按真实证据使用 200k；不得虚报 `[1m]` 或关闭未知模型窗口保护。
- 失败或质量不达标立即 escalate 回主会话。
- commit / PR / 部署永远由主会话控制。
