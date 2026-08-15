版本依据：`auto-code-generator` v4.2 快照（`...iteration-4\skill-snapshot\SKILL.md`，2026-08-14），核心规则 R12、R6、R5，Stage 3.1–3.6。

**决策：合组。** T1/T2/T3 映射到同一个临时 worker 场景组，不按 task 一一拆 worker。

**task 与 worker 调度单元的区别（R12、3.1）**：tracker task（T1/T2/T3）是持久状态、依赖、授权范围与独立验收单元，保留原编号与粒度；worker 场景组是本轮临时调度单元，可含一个或多个 task，不落盘、不复制任务状态。

**分组决定（3.2）**：三者服务同一可观察场景（登录锁定），共享 auth 模块与 fixture，有“不组合即无独立价值”的紧密组内顺序，满足实质内聚信号；无独立审批/发布/回滚/迁移/安全权限/外部系统等强制拆分边界；成本收益为正（省 3 次上下文加载、fixture 准备与测试进程，且 diff/测试/失败证据仍可归因到底层 task）。任一门禁不满足或证据不清时保持独立组。

**组内顺序 internal_order（3.5）**：同一 worker、同一上下文内完成 RED→GREEN→REFACTOR。顺序：T1 先写失败测试并确认失败来自目标行为未实现而非语法/fixture/环境（有效 RED）→ T2 最小实现并循环跑新增及直接受影响测试至绿（GREEN）→ T3 补审计事件断言并入同组测试闭环；不把 RED/GREEN/REFACTOR 或测试/实现微任务切给不同 worker。

**验收与状态更新（3.4、3.6）**：worker 返回 `group_status`（DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/NEEDS_COORDINATION/BLOCKED）与逐 task `task_result`（SATISFIED/UNSATISFIED/BLOCKED 附证据），仅为验收建议。协调者核对真实 diff、allowed_writes、每项改动到 task 的映射、聚焦测试真实命令与结果后，**逐 task 更新权威 tracker**；不得因组级 DONE 一键完成 T1/T2/T3。

**暂停条件**：baseline 漂移（输出 `BASELINE_CHANGED`）、RED 因环境或 fixture 失败、worker 越界或并行重叠（冻结、保留改动、重划边界）、关键证据缺失、需扩授权边界。

**第一个实质动作（Stage 1）**：只读取证——读项目规则、实时生命周期状态与指令、当前分支/HEAD/status 及相关 baseline；不修改文件、不更新任
