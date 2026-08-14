# Eval transcript

## 输入

一个跨三个 package 的功能已有任务：T1 定义公共接口并加契约测试，T2 在 package-a 接入，T3 在 package-b 接入。T2/T3 都依赖 T1，但彼此写入和测试完全隔离。请规划自动实施调度。评估模式：只输出场景组划分、依赖波次、并行条件、验收与失败恢复，不修改文件。

## 使用规则

- 版本：auto-code-generator v4.2（工作树新版）
- 核心依据：tracker task 与临时场景组分层；公共基础先独立验收；消费者仅在五项隔离条件成立时并行；协调者逐 task 验收。

## 输出

见 `outputs/response.md`。本次仅生成调度计划，没有修改被评估项目，也没有执行 Git mutation。
