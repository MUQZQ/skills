# v4 响应

- 生命周期：仓库无权威流程，使用最小 fallback 与当前用户指令，不创建 OpenSpec 工件或第二账本。
- 风险：Light；根因已知、单文件、局部可逆，无公共契约/数据/安全/跨组件影响。
- TDD：先写 UTC 边界聚焦失败测试，确认失败来自目标行为缺失，再最小 GREEN 与必要 REFACTOR。
- 验证：使用仓库实际的 npm/pnpm/vitest 等项目原生命令；未执行项不得标记通过。
- Git：用户明确不要提交，Git authority 为 NONE，不 stage/commit/push/PR/deploy。
- 第一个动作：记录当前基线，然后为 `src/date.ts` 写入有效 RED 测试。

完整运行响应记录在本次 Codex 会话工具输出中；本文件保留用于 benchmark viewer 的关键原文语义。
