**决策（eval_id=10 version=with_skill；依据 `auto-code-generator` SKILL.md v4.3）**

新增跨包运行时依赖属于相对已批准 change 投影的**语义偏差**（SKILL.md §2.5 末段明确以"新增跨包运行时依赖"为例）；"现有测试仍通过"**不豁免**——测试通过 ≠ 投影获批，结构/测试有效不代表语义正确（§2.5、铁律 R7/R9）。

**Worker（或 provider，仅返回证据，不拥有状态/审批/归档）**
- 立即停止基于越界假设的实现，不凭测试通过继续（§3.4/§3.5 边界）。
- 返回 `group_status=NEEDS_COORDINATION`（或 `BLOCKED`），受影响 `task_result=BLOCKED`，附真实 diff、依赖声明变化、命令结果，作为"疑虑/协调事项"上报（§3.4 `return_contract`、§3.6 第 5 项）。

**协调者（Sol）**
1. 投影：暂停受影响任务，调用官方 init/check **刷新 change 投影**，不静默覆盖、不伪造投影（§2.5 状态表）；脚本只做确定性结构检查，语义审批另由 Agent/官方执行。
2. 审批：重新做结构检查 + 语义审批；**未获批不恢复**（§2.5"获批后才能继续"）。
3. 任务状态：只更新权威 tracker；受影响 task 置 BLOCKED/未完成并逐项更新，不做组级一键完成（铁律 R2/R7、§3.6）。
4. 最终验证：§4.2 三方比较——**实际实现 vs 已批准 change 投影 vs prospective current view**；同步与归档留给官方生命周期（§2.5、Stage 5），本 skill 不伪造归档。

**阻塞/降级**
- 未获语义重新批准 → 保持 BLOCKED，禁止继续/归档/提交。
- 当前维护视图损坏或投影无法由官方脚本重建 → §2.5 状态 D，**BLOCKED 上报官方**，不降级空白模板。
- 若走 Sol-Luna 且完整场景组无法保真表达 → 回退 Sol/项目原生执行，**不切碎 TDD**（§3.7、`references/execution-providers/sol-luna.md`）。

**第一个实质动作**
协调者：读取官方投影 init/check 实时状态，暂停受影响 task 并触发投影刷新；worker：上报偏差证据与新依赖声明，停止继续写实现。
