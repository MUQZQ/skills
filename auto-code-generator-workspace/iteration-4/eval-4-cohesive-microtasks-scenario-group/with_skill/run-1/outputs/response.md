结论：由现有任务系统持有生命周期与唯一任务真相源，本 skill 仅编排实施（SKILL.md v4.3 §1.1/§3.1）。执行意图为 PLAN_ONLY，不修改文件、不提交。

**task 与 worker 调度单元的区别**：T1/T2/T3 是权威 tracker 的持久任务，也是逐项验收单元；场景组是临时 worker 调度单元，不落盘、不复制任务状态（§3.1、R12）。

**分组决定**：T1、T2、T3 合成 **1 个临时场景组**。§3.2 依据：服务同一可观察行为（登录锁定计数+审计事件）、共享认证模块写入与同一 fixture、整场景跑通才有价值；不存在独立审批/回滚/迁移/权限/外部系统等强制拆分边界；成本收益为正（省去重复上下文、fixture 与测试进程），无并行损失。单组执行，不并行。

**组内顺序**：同一 worker 内按 T1→T2→T3 执行；T1 先建立有效 RED（确认失败源于目标行为），T2 写最小计数器实现 GREEN，T3 补审计断言，必要时 REFACTOR 后复跑聚焦测试；不把 RED/GREEN/REFACTOR 拆给不同 worker（§3.5、R5）。

**验收与状态更新**：worker 只返回 group_status、逐 task 的 task_result、真实 diff 与命令证据；Sol 核对 diff、允许写入范围和测试命令结果后，**逐项更新** T1/T2/T3，不整组一键完成；部分合格只更新合格项（§3.4/§3.6）。

**边界与暂停条件**：写入限认证模块与共享 fixture；禁止越界改动及 Git/生命周期状态变更。暂停于：baseline 漂移（输出 BASELINE_CHANGED）、RED 因 fixture/环境失败、关键决策缺失、Critical/Important 未解；无 Git 授权则不提交。若本会话显式启用 Sol-Luna provider，用六字段任务卡承载完整组、不拆 TDD，超限回退 Sol（references/execution-providers/sol-luna.md、_providers/sol-luna/CONTRACT.md）。

**第一个实质动作**：只读取证——读权威 tracker 中 T1/T2/T3 状态、认证模块与 fixture 现状、branch/HEAD/status 基线，确认唯一真相源后再调度（Stage 1）。
