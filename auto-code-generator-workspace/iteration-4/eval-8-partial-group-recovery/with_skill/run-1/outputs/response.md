状态判定：拒绝接受 `group_status=DONE`。依据 auto-code-generator SKILL.md v4.3 §3.4，`DONE` 要求全部 task 与组级场景满足；worker 同时报 T2=UNSATISFIED、T3=BLOCKED，与 DONE 自相矛盾，应按 `NEEDS_COORDINATION`/`BLOCKED` 处理，不整组完成（§3.1「组完成不等于 task 自动完成」；CONTRACT.md「provider 不得自行宣告整体完成」）。

逐 task 更新：协调者先核对共享工作树真实 diff、allowed_writes、聚焦测试命令与结果（§3.6、R7），证据支持才逐项更新权威 tracker：T1=SATISFIED → 仅 T1 完成；T2=UNSATISFIED → 未完成（缺 schema 决策）；T3=BLOCKED → 未完成，不得越过 T2。

改动保留：完整保留 T1 diff 与部分 T2 diff，不覆盖、不清理、不自动回退（§3.6、错误与恢复表「worker 越界或并行重叠…保留改动」）。

依赖与重新调度：T2 阻塞点是 required_decisions（schema 决策）未消费。可推导则补最小上下文恢复；需授权/设计则请求用户裁决。解决后按实时依赖、当前 diff 与写入范围重算恢复组：T2 先续接部分 diff，验收通过后再调度 T3；T3 依赖 T2，不得提前并行或越过。

暂停条件：schema 决策无法自解或 T1 证据不足以验收时暂停，返回缺失项；不猜测、不伪造通过、不更新 tracker。

第一个实质动作：只读取证——重读权威 tracker 状态、Git diff/status 与聚焦测试，逐文件核对实际 diff 到 task 的映射，确认 T1 证据后才更新 T1，同时锁定 T2 缺失决策并请求补齐/裁决。

验证证据：`auto-code-generator/SKILL.md` v4.3（§3.1/§3.4/§3.6、R7、错误与恢复表）；`references/execution-providers/sol-luna.md`（返回与验收）；`_providers/sol-luna/CONTRACT.md`（边界）。eval_id=8 version=with_skill。
