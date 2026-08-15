快照版本：**auto-code-generator v4.2**（2026-08-14，SKILL.md L11/L393）。以下均只依据该快照，不引用快照外规则。

**决策**
1. 生命周期：仓库无权威流程、无维护视图契约 → 按 Stage 1.1 末行用本 skill **最小 fallback 计划**，不新建持久工件、不建第二真相源（R0/R2）。所有权句："因无 QEDA/OpenSpec/任务系统/维护视图契约，由本 skill fallback 管理生命周期，仅负责场景内 TDD、验证与报告。"
2. 投影/视图：v4.2 **未定义"维护视图投影/投影"概念**，故不发明投影；等价于 2.1 最小 fallback（一个可观察结果 + 范围内外 + 依赖排序 + 验证方法）。
3. 执行 provider：v4.2 **无 Sol/Luna/provider 概念**；"全局 mode=auto 历史配置"与"本会话未提 Luna"均非本快照规则，不构成授权或降级依据。按 1.2 判 **Light**（根因已知、局部可逆、无公共契约/数据/安全/跨组件）；按 3.2 末行/3.4 **协调者直做单 task/单组**，不启用 worker 委派，worker 也不拥有 task 状态、Git 与完成判定。
4. TDD：按 3.5 **组内 TDD**：先写失败测试并确认失败源于目标行为未实现（有效 RED）→ 最小实现 GREEN → 必要 REFACTOR；不虚构 RED。
5. Git/权限边界：前置输入 Git 默认 **NONE**；R10 完成/归档不授予 Git 权限；本会话未要求提交 → 不 stage/commit/push/PR/deploy。

**阻塞/降级**：本场景无阻塞（根因与档位事实清楚）。暂停条件：baseline 漂移 → 输出 `BASELINE_CHANGED` 重确认（1.3）；风险事实不清且改变档位 → 停止取证（1.2）；验证环境不可用 → 结论 `BLOCKED/INCOMPLETE`，不标通过（4.2）。Git 无授权非阻塞，完成到归档/报告即停。

**第一个实质动作**：Stage 1 规定"每次执行的第一个实质动作都是只读取证"——读取项目规则/实时状态、当前分支/HEAD/status 与 baseline，确认无权威流程、锁定 Light 与 Git=NONE；其后的第一个修改动作才是 RED 失败测试。

（eval_id=12 version=old_skill）
