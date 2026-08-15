**eval_id=8，version=old_skill。依据：auto-code-generator v4.2 快照（最后更新 2026-08-14）。**

**状态判定**
组级 `group_status=DONE` 无效，不可采信。3.4 定义 `DONE` 为“全部 task 与组级场景满足”，但 worker 自报 T2=UNSATISFIED、T3=BLOCKED，自相矛盾；且 3.4 明确 `task_result` “只是验收建议，不拥有 tracker 状态”。按 R2、3.1，权威 tracker 是唯一持久真相源，T1/T2/T3 均维持未完成，不得因组级 DONE 一键完成全部 task（3.6）。

**逐 task 验收与更新**
- T1：按 R7、3.6 核对工作树真实 diff、allowed_writes 映射、聚焦测试命令与结果；证据支持且无越界，才在权威 tracker 将 T1 更新为完成。只更新合格项。
- T2：UNSATISFIED（缺 schema 决策），保留未完成；属 `required_decisions` 缺失，部分 T2 diff 保留。
- T3：BLOCKED（依赖 T2），保留未完成，等 T2 落地后再调度。

**改动保留**
T1 完整 diff 与部分 T2 diff 全部保留，不覆盖、不清理、不回退；重划时不迁移旧组状态（3.1）。

**依赖与重新调度**
重划场景组：T1 独立组验收；T2 单独组补最小上下文（required_decisions=schema 决策）后恢复 worker；T3 依赖 T2，待 T2 完成后入下一波，或与 T2 同组按 `internal_order` 串行。schema 决策优先从权威工件/仓库证据推导（1.1、3.1），推导不出则暂停请求裁决。

**边界与暂停条件**
schema 决策无法从现有权威工件推导、需人工裁决时暂停；发现 T1/T2 diff 越界、覆盖他人改动或并行重叠时冻结相关任务、保留改动、重划后串行恢复（错误与恢复表）；baseline 漂移输出 `BASELINE_CHANGED` 等待重新确认。

**第一个实质动作**
只读取证：重新读取权威 tracker 实时状态、`git diff`/`git status` 核对 T1/T2 diff 范围与越界、聚焦测试真实命令结果；不更新状态、不改文件、不执行 Git mutation；输出所有权决定并判定组级 DONE 无效。
