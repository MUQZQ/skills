# Eval transcript

## 输入

恢复执行时，权威 tracker 中同一场景组的 T1/T2/T3 都未完成。worker 却返回 group_status=DONE，同时报告 T1=SATISFIED、T2=UNSATISFIED（缺少 schema 决策）、T3=BLOCKED（依赖 T2）；共享工作树已有完整 T1 diff 和部分 T2 diff。请决定协调者如何验收与恢复。评估模式：只输出状态判定、逐 task 更新、改动保留、依赖与重新调度方式，不修改文件。

## 使用规则

- 版本：auto-code-generator v4.2（工作树新版）
- 核心依据：`DONE` 必须满足全部 task 与组级场景；逐 task 结果只是验收建议；协调者核对真实状态与 diff 后逐项更新；部分失败保留改动并按实时依赖重新计算场景组。

## 输出

见 `outputs/response.md`。本次只生成恢复计划，没有修改被评估项目，也没有执行 Git mutation。
