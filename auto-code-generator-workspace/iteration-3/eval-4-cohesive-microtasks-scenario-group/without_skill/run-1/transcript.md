# Eval 4 执行记录：旧版快照

- 版本来源：`auto-code-generator-workspace/iteration-3/skill-snapshot/SKILL.md`，快照内容标记 v4.1。
- 输入：与新版完全相同的 eval id 4 原始 prompt。
- 约束：仅输出调度计划，不修改被评估项目文件。
- 采用规则：唯一任务状态；依赖与安全并行；单 task worker assignment；任务本地 TDD；协调者验收。
- 判断：认证场景按 Strict 处理；共享模块和 fixture 使三个任务不能并行。旧版合同没有多 task 场景组，因此按 T1、T2、T3 三个 bounded worker 串行调度。
- 输出：`outputs/response.md`。
