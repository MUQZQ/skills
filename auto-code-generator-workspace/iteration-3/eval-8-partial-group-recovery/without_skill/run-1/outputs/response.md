# 恢复决策（auto-code-generator v4.1 快照）

## 状态判定

旧版 assignment 以单个 task 为 worker 单元，只允许 worker 返回 `DONE`、`DONE_WITH_CONCERNS`、`NEEDS_CONTEXT`、`NEEDS_COORDINATION` 或 `BLOCKED`；它没有 `group_status` 与逐 task `task_result` 合同。因此这份“组级 DONE + 部分失败”返回不符合旧版合同，不能据此更新 tracker，按需要协调的异常返回处理。

协调者重新读取权威 tracker、共享工作树 diff 和聚焦测试，以真实证据而不是该摘要判断完成度。

## 逐 task 更新

- T1：检查完整 diff 是否在 T1 的 allowed writes 内、是否覆盖既有改动，并核验真实测试和任务验收。只有证据完整时才单独把 T1 更新为完成；否则仍未完成。
- T2：部分 diff 不能证明完成，且缺少 schema 决策，保持未完成。
- T3：依赖 T2，保持未完成。

不会把三项整体标为完成，也不会用 T1 的证据替代 T2/T3。

## 改动保留

保留完整 T1 diff 和部分 T2 diff，不覆盖、清理或自动回退共享工作树。协调者先核对这些改动与基线、allowed writes 和各任务范围；需要协调时在保留现场的前提下重划边界。

## 依赖与重新调度

先通过权威计划或 schema 所有者解决 T2 的缺失决策。决策明确后重新读取 tracker 和当前 diff，以一个输入受限的 T2 worker 恢复剩余实现；协调者验收并将 T2 更新为完成后，才调度独立的 T3 worker。T3 不得越过 T2。

旧版没有临时场景组及其重算语义，因此恢复仍按单 task assignment 串行进行；不会继承题面中无效的组级 `DONE`。
