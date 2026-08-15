**结论（eval_id=12，with_skill，auto-code-generator v4.3）**

1. **生命周期所有者**：仓库无权威生命周期、无维护视图契约，故用本 skill 的 fallback 最小计划，不建第二套流程（R0 / 1.1）。所有权句：因仓库无权威流程，由 auto-code-generator fallback 管理生命周期，本 skill 仅负责实施与验证。

2. **风险档位**：根因已知、局部可逆、无公共契约/数据/安全/跨组件 → **Light**（1.2），协调者直做单任务/单组（3.2）。

3. **视图/投影处理**：未声明维护视图契约与投影 → 按 2.5 不处理、不创建、不伪造投影，不进入 A/B/C/D 状态机，不跑官方 init/check，**不阻塞**。

4. **执行 provider 选择**：Luna 默认关闭；持久 `mode=auto` 只描述触发后的委派策略，不能替代本次会话显式同意（sol-luna.md 选择门禁 + CONTRACT）。本会话未点名 Luna → **不选 Luna，不携带 `--user-triggered`，回退 Sol/项目原生直接执行**。

5. **TDD**：同一场景组同一上下文内完成 `RED → GREEN → REFACTOR`，不拆分（3.5 / R5）。RED 先写复现失败测试并确认失败来自根因而非环境；GREEN 最小修复；必要重构后复跑同组测试。

6. **权限边界**：执行意图 `PLAN_AND_APPLY`（“实施”）；Git 权限默认 `NONE`，不 commit/push/PR/部署（R10 / 3.7）；若分支为 main/master，即使后续被要求提交也需停止确认。

**阻塞/降级条件**
- 阻塞：baseline 漂移 → `BASELINE_CHANGED` 待重新确认；RED 因环境/fixture 失败不宣称 TDD 完成；若实际存在权威流程或维护视图损坏（D 态）→ BLOCKED。
- 降级：Luna 未显式授权 → 回退 Sol 直做；投影未声明 → 跳过投影处理。

**第一个实质动作**（只读取证，不改文件）：Stage 1 读取仓库 AGENTS/项目规则、当前分支、HEAD、`git status` 与相关 baseline，确认无权威生命周期且基线未漂移。
