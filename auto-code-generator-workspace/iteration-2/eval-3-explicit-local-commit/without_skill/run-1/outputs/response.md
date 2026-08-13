# v4 响应

- 权限：识别 LOCAL_COMMIT，只授权本地提交；push、PR、部署均越界。
- 生命周期：服从仓库现有 QEDA/OpenSpec；不建立第二流程或状态源。
- 门禁：Apply-ready → bounded task 实施 → 最终严重度审查 → 项目原生验证 → VERIFIED → 官方归档 → closeout commit。
- 分支：不在 main/master 提交，不 force push；提交前核对准确暂存范围。
- 审查：Critical/Important 清零，不固定五轮。
- 第一个动作：读取现有 change 的实时 status、execution intent 与 baseline，然后编辑首个 dependency-ready 任务。
- 独立 reviewer 发现 P1：closeout commit 前的 baseline 与 staged diff 复核应从原则升级为明确门禁。

完整运行响应记录在本次 Codex 会话工具输出中；本文件保留用于 benchmark viewer 的关键原文语义。
