已按要求只读核查：`SKILL.md`（auto-code-generator v4.3）、`references/execution-providers/sol-luna.md`（provider 适配）、`_providers/sol-luna/CONTRACT.md`。以下直接回答 eval 5（eval_id=5，version=with_skill），不修改文件。

## 决策
- 权威流程：题设无项目生命周期，则以已有任务列表 T1–T3 为唯一真相源（SKILL 3.1）。
- 风险档位：公共契约 + 跨组件 → **Strict**（1.2）；默认单一 change，不拆子 change。
- 执行意图：PLAN_ONLY；Git 授权 NONE；provider 需本次会话显式同意 Luna，否则回退 Sol。

## 场景组划分
- G1 = {T1}：公共接口定义 + 契约测试。因「公共基础契约及其多个消费者」强制拆组，基础独立成组（3.2 边界）。
- G2 = {T2}：package-a 接入；G3 = {T3}：package-b 接入。写入与测试完全隔离，各自独立组。

## 依赖波次
- 波次 1：G1（T1）。G1 验收前 G2/G3 不得启动。
- 波次 2：G2 ∥ G3（前提：G1 被协调者逐 task 验收为 SATISFIED）。

## 并行条件（G2∥G3，3.3 五项全满足）
写文件不重叠（a/b 包）；不竞争共享独占资源；不同时演进公共契约（只消费已落地 T1）；不消费对方未落地接口；聚焦测试与 diff 可分别归属。题设「完全隔离」已满足；任一项无法证明则串行。

## 验收（3.6 + 4.2）
- G1：契约测试在同组完成 RED→GREEN→REFACTOR；协调者核对 diff 归属 T1 与真实测试结果，逐 task 更新为 SATISFIED 后放行波次 2。
- G2/G3：各自包聚焦测试通过、diff 归属各自 task；组级 DONE 不等于一键完成任务，逐 task 验收。
- Stage 4：最终审查 Critical/Important=0，项目原生全量验证通过才 VERIFIED。

## 失败恢复（错误表）
- G1 失败：T2/T3 不启动，修复后重验。
- G2 或 G3 失败：保留已验收 task 状态，失败项按当前 diff/依赖重划后单独重调度，不连累另一并行组。
- 意外重叠：冻结并发集，保留全部改动，协调者重划边界后串行恢复。
- RED 因环境/fixture 失败：先修测试基础再重建有效 RED，不宣称 TDD 完成。

## 暂停条件
权威流程/基线漂移（输出 BASELINE_CHANGED）、任务边界不明确、Critical/Important 未解决
