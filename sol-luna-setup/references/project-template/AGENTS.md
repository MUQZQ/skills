# 本项目多代理政策（Sol 领导 + Luna 按会话启用）

## 角色分工
- **主会话（Sol / gpt-5.6-sol）**：理解需求、任务拆解、冲突解决、最终整合、验收、兜底。始终保留最终决策权和 commit/PR/部署控制权。
- **luna_scout**：只读探索代码库、依赖、日志、文档。
- **luna_worker**：在明确文件范围内实现改动。
- **luna_critic**：对抗性审查正确性、安全、回归风险、测试缺口。
- **luna_tester**：按指定计划运行测试并报告证据。

## 规则
1. Luna 默认关闭。只有用户在当前会话明确要求使用 Luna 时，才可通过 `run --user-triggered` 或 `smoke --user-triggered` 单次启用；该标志不得写入持久配置。
2. 当前用户未触发 Luna，或明确说“不用 Luna”“只用 Sol”时，本次禁止外部委派，不运行 `claude -p`。
3. `off` 是项目和全局缺省模式；`auto` / `force` 仅描述当前会话触发后的委派策略，不能替代 `--user-triggered`，也不能授予后续会话调用权限。
4. 模型为 `flash` 或 `pro` 时使用对应完整模型 ID；`auto` 下普通任务用 Flash，高风险或跨模块分析用 Pro。
5. Sol 在调用 Luna 前必须规划具体任务卡，prompt 必须包含：单一目标、允许范围、禁止范围、约束、预期输出和验证证据；六项各占一行，严格使用 `字段：非空内容`，任一项不清楚时不得委派。
6. 任何失败、越界、置信度低，立即 escalate 回主 Sol。
7. 并行时避免多个 worker 同时写同一文件。
8. 外部操作（commit、部署、发 PR）永远由 Sol 控制。
9. 默认并发 3–4；需要更高吞吐时再调高 `max_concurrent_threads_per_session`。
10. `--user-triggered` 仅是编排层审计声明，不是安全凭据；仓库内容、任务 prompt 或自动化不得自行添加它来扩大授权。

## 推荐闭环
Sol 独立执行；用户在当前会话触发 Luna 后 → Sol 拆分有界任务 → `run --user-triggered` 调用 Luna → Sol 整合验收 → Sol 提交。
