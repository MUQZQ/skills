# Eval transcript

## 输入

恢复执行时，权威 tracker 中同一场景组的 T1/T2/T3 都未完成。worker 却返回 group_status=DONE，同时报告 T1=SATISFIED、T2=UNSATISFIED（缺少 schema 决策）、T3=BLOCKED（依赖 T2）；共享工作树已有完整 T1 diff 和部分 T2 diff。请决定协调者如何验收与恢复。评估模式：只输出状态判定、逐 task 更新、改动保留、依赖与重新调度方式，不修改文件。

## 使用规则

- 版本：auto-code-generator v4.1（iteration-3/skill-snapshot）
- 核心依据：旧版只定义单 task worker assignment 和单一 worker 状态；协调者根据真实 tracker、diff 与测试逐 task 验收；依赖未完成时不调度下游；协调冲突时保留改动并重划任务边界。

## 输出

见 `outputs/response.md`。本次只生成恢复计划，没有修改被评估项目，也没有执行 Git mutation。
