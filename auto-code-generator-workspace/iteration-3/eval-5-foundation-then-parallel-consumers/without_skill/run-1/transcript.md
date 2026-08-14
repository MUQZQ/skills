# Eval transcript

## 输入

一个跨三个 package 的功能已有任务：T1 定义公共接口并加契约测试，T2 在 package-a 接入，T3 在 package-b 接入。T2/T3 都依赖 T1，但彼此写入和测试完全隔离。请规划自动实施调度。评估模式：只输出场景组划分、依赖波次、并行条件、验收与失败恢复，不修改文件。

## 使用规则

- 版本：auto-code-generator v4.1（iteration-3/skill-snapshot 旧版）
- 核心依据：以 task 为直接调度单元；依赖就绪后再调度；仅在五项隔离条件成立时并行；协调者按 task 验收。

## 输出

见 `outputs/response.md`。旧版没有定义独立于 task 的场景组，因此输出如实采用 task 级 bounded worker，没有补入新版的场景组状态语义。
