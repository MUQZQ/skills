# Claude Code 多代理政策

- 主会话使用最强可用模型（领导层）：规划、审核、整合、兜底。
- 执行层调用 `.claude/agents/` 下稳定命名的 `luna-*` 角色；模型由 Sol-Luna 控制器选择。
- Luna 委派必须是单目标、短响应、可独立验证的小闭环；探索、实施、测试和审查分别调用，禁止一次打包完整功能或跨模块任务。
- `mode=off` 时禁止调用 Luna；`model=flash|pro|auto` 分别选择 V4 Flash、V4 Pro 或按风险选择。
- 当前用户说“不用 Luna”“只用 Sol”或“Luna 用 Flash/Pro”时，覆盖项目和全局默认。
- 调用 Claude Code 时传 `haiku/sonnet` 别名，由用户级 `modelOverrides` 将对应 Claude ID 路由到 DeepSeek provider ID，并检查 JSON `modelUsage` 是否与预期 provider 模型一致。
- 当前上下文窗口按真实证据使用 200k；不得虚报 `[1m]` 或关闭未知模型窗口保护。
- 失败或质量不达标立即 escalate 回主会话。
- commit / PR / 部署永远由主会话控制。
