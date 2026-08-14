# Eval 4 执行记录：新版

- 版本来源：`auto-code-generator/SKILL.md`，v4.2。
- 输入：eval id 4 的原始 prompt。
- 约束：仅输出调度计划，不修改被评估项目文件。
- 采用规则：tracker task 与 worker 场景组分层；场景内聚与成本收益门禁；组内连续 TDD；协调者逐 task 验收。
- 判断：T1/T2/T3 同一场景、同一写入边界、共享 fixture，且没有独立风险或回滚边界，因此形成一个临时场景组。
- 输出：`outputs/response.md`。
