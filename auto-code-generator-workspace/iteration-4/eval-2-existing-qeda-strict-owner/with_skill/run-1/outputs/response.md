**决策与生命周期服从**
- 所有者判定：QEDA（`qeda-subagent-driven-sdd` 活动 change）。依 SKILL.md v4.3 §1.1/R0，服从其 schema、实时 status 与 artifact 指令；本 skill 仅负责场景组内 TDD、按场景组调度、安全并行与审查验证，不建第二套 phase/账本/结论。
- 已锁 `PLAN_AND_APPLY` 与 Target/Source baseline。但本次为评估模式：**只输出接管方案，不写文件、不更新 tracker、不 Git mutation**（R10，Git 默认 NONE）。未收到本会话显式 Luna 同意，不调 sol-luna provider，由 Sol 直做或项目原生执行（sol-luna.md 选择门禁、CONTRACT.md）。

**第一个实质动作（只读）**
- 重读 QEDA 实时 status、当前 artifact instruction、权威 tracker 剩余 tasks、当前 branch/HEAD/status，与已锁基线比对（R4/§3.1）。漂移即输出 `BASELINE_CHANGED` 并暂停；不凭历史 worker 消息推断完成度。

**分派与并行**
- 以 tracker tasks 为唯一真相源，按 §3.2 四门禁成临时场景组（同可观察行为、无强制拆分边界、有内聚信号、成本收益为正）。强制独立边界：独立审批/回滚/迁移/安全或公共契约及其消费者。
- 组间并行仅在 §3.3 五条件全满足：写入不重叠、无共享独占资源、不同时改公共契约/migration/manifest、不消费未落地行为、测试证据可归属；否则串行。公共基础组先验收，消费者下一波。
- worker 用 §3.4 完整 assignment 字段（tasks/internal_order/allowed_writes/forbidden_scope/focused_tests/return_contract），同组内完整 RED→GREEN→REFACTOR（R5，不拆 TDD）。协调者逐 task 核验真实 diff、范围与测试后才更新 tracker（R7/§3.6），不整组一键完成。

**审查验证**
- 对整 change diff 审查，分 Critical/Important/Minor；C/I 在授权边界内清零（R8/§4.1）。用项目原生命令验证，未执行项标 `PENDING/BLOCKED`，不伪造通过（R9/§4.2）。结论仅 `VERIFIED/BLOCKED/INCOMPLETE`；`VERIFIED` 才归档，归档≠Git 授权（R10）。

**暂停条件**
- baseline 漂移、QEDA 人工
