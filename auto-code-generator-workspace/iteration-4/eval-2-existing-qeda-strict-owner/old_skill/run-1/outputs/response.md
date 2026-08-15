已读取冻结快照 `SKILL.md`（v4.2，2026-08-14）。以下为对评测 prompt 的直接回答。

---

**决策（R0）**：QEDA 是权威生命周期所有者，本 skill 仅负责阶段内能力——场景组内 TDD、按组调度、安全并行、审查验证；不新增 phase、ledger、Git 动作。执行意图已锁定 `PLAN_AND_APPLY`，Git 权限默认 `NONE`（R10）。

**第一个实质动作（只读取证）**：调用 QEDA 官方 status/artifact 指令，读取剩余 tasks、依赖、允许写入范围、验收标准与项目原生验证命令；Apply 前复核 Target/Source baseline 与 branch/HEAD/status 是否漂移（R4）。接管不据历史消息推断完成度，重读 tracker/diff/聚焦测试（3.1）。prompt 文本未含允许/禁止范围、预期输出、验证证据——须从 QEDA tracker 取证；若 tracker 同样缺失，停止并返回缺失项，不猜测、不扩权（R1、Sol 前置）。

**分派（R2/R6/R12）**：QEDA tracker 为唯一持久真相源。先取"依赖已完成或可整组 internal_order"的 task 为候选，按可观察场景内聚分组，过四门禁：同一可观察行为、无强制拆分边界、有内聚信号、成本收益为正；公共基础契约组先验收、消费者组下一波。tracker task 与 worker 场景组不强一一对应；Strict 用上下文全新受限 worker，其余按成本收益直做或同合同。

**并行（3.3）**：仅当候选组同时满足写入不重叠、不争独占资源、不共演契约/migration、不消费未落地接口、测试证据可归属才并行；否则串行；意外重叠即冻结、保留改动、重划边界。

**审查验证（R7/R8/R9）**：协调者逐 task 核对真实 diff、allowed_writes、聚焦测试命令与结果，逐项更新 tracker，不信组级 DONE 一键完成。最终按严重度 whole-change 审查（Critical/Important 清零），用项目原生命令逐场景验证，结论仅 `VERIFIED/BLOCKED/INCOMPLETE`；仅 VERIFIED 才调 QEDA 归档，不 commit/push/deploy（R10）。

**暂停条件**：baseline 漂移（`BASELINE_CHANGED`）、tracker 缺验收/范围/验证证据、Critical/Important 授权内无法解决、QEDA 规定人工门禁。

**版本证据**：v4.2；R0/R1/R2/R4/R6/R7/R8/R9/R10/R12；eval_id=2 version=old_sk
