**决策（冻结快照 auto-code-generator v4.2，2026-08-14）**

快照中**不存在 Sol-Luna provider 选择规则**，只有 3.4 Worker assignment。因此"本会话明确要求 Luna"无法在快照内映射为 provider 选择——这是阻塞/降级点：按快照降级为 3.4 的 worker 语义，不补造 Sol/Luna 规则。

**委派粒度**
失败测试＋最小实现＋重构验收是同一可观察行为 task 的 RED→GREEN→REFACTOR 闭环（R5、2.3、3.5），共享 fixture 与写入范围，必须合成**单一场景组、单一 worker 同上下文**完成，不得拆成三个微委派（R12、R6）。任务卡压缩后能进 provider 限额，故不因限额拆组（若放不下才停止并返回拆分建议）。

**返回验收**
按 3.4 return_contract：`group_status`（DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/NEEDS_COORDINATION/BLOCKED）＋逐 `task_result`（SATISFIED/UNSATISFIED/BLOCKED）附证据。协调者（3.6）核对真实 diff、allowed_writes、聚焦测试后**逐项**更新权威 tracker；组 DONE ≠ task 自动完成（R7）。

**失败降级**
RED 因 fixture/环境失败→修复测试基础重立有效 RED，不宣称 TDD；部分合格→只更新合格 task，失败项保留未完成并按 diff/依赖/风险重划恢复组；组过大或部分失败→按独立验收/回滚/证据边界拆组。

**边界**
生命周期：权威 tracker 是唯一持久真相源（R2），本 skill 仅编排实施与验证。投影：worker 场景组是临时调度视图，不落盘（R12、3.1）。Git：默认 NONE，不提交（R10）。

**第一个实质动作**
Stage 1 Detect & Route 只读取证：项目规则、权威 tracker 实时状态、branch/HEAD/status/baseline，输出所有权决定；不改文件、不更新状态。

证据：skill=auto-code-generator v4.2；eval_id=11 version=old_skill。
