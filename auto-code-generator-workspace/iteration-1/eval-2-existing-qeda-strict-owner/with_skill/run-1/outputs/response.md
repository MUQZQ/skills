# v4 响应

- 明确 QEDA/OpenSpec 是唯一生命周期 owner，本 skill 仅提供 Apply 阶段内 TDD、安全并行、验收与验证。
- 实施前重新读取实时 status、Apply contract 与 Target/Source baseline；不重建规划。
- 每个 Strict 任务使用全新 bounded worker，assignment 包含 allowed writes、forbidden scope、focused tests 与返回合同。
- 并行检查写入、独占资源、公共契约、未落地依赖和测试证据归属五项条件。
- 协调者核验真实 diff 与聚焦测试后才更新唯一任务状态。
- 最终使用 test plan 的项目原生命令，结论限定为 VERIFIED/BLOCKED/INCOMPLETE；全程无 Git mutation。
- 第一个动作：读取实时状态并复验 baseline，一致后派发首个依赖就绪任务。

完整运行响应记录在本次 Codex 会话工具输出中；本文件保留用于 benchmark viewer 的关键原文语义。
