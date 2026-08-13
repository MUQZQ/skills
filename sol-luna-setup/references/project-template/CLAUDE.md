# Claude Code 多代理政策

- 主会话使用最强可用模型（领导层）：规划、审核、整合、兜底。
- 执行层调用 `.claude/agents/` 下稳定命名的 `luna-*` 角色；模型由 Sol-Luna 控制器选择。
- `mode=off` 时禁止调用 Luna；`model=flash|pro|auto` 分别选择 V4 Flash、V4 Pro 或按风险选择。
- 当前用户说“不用 Luna”“只用 Sol”或“Luna 用 Flash/Pro”时，覆盖项目和全局默认。
- 调用 Claude Code 时传完整模型 ID，并检查 JSON `modelUsage` 是否与请求一致。
- 失败或质量不达标立即 escalate 回主会话。
- commit / PR / 部署永远由主会话控制。
