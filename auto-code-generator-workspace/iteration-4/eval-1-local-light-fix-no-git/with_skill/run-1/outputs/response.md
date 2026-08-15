**决策（修改前）**

- **生命周期所有者**：本仓库无 OpenSpec/任务系统/AGENTS 权威流程，按 SKILL Stage 1.1 第 3 行判定，由 auto-code-generator v4.3 的最小 fallback 计划管理生命周期；本 skill 仅负责 src/date.ts 修复的 TDD 实施与验证，不建第二套账本、不创建额外持久文件（R0）。
- **风险档位**：Light —— 根因已知、单点、局部可逆，无公共契约/数据/安全/跨组件影响（Stage 1.2）。
- **执行意图/权限**：PLAN_AND_APPLY；Git 权限 NONE（用户明确“不要提交”，R10）。
- **Provider**：不启用 Luna（未获本会话显式同意，sol-luna.md 选择门禁）；Light 由协调者直接执行单组。

**边界**
- 允许写入：src/date.ts 及其行为测试文件（先 RED 后 GREEN）。
- 禁止：任何 Git mutation（stage/commit/push/PR）、其他文件、创建 issues.md/ledger 等第二状态源、顺手修相邻问题（R1、R11）。

**TDD/验证路线**（单一内聚场景组内闭环，不拆分，R5/3.5）
1. RED：先为 UTC 边界行为补失败测试，确认失败源于目标行为未实现（非语法/环境/fixture）。
2. GREEN：最小实现，循环跑聚焦测试至通过。
3. REFACTOR：必要时整理并复跑同组测试。
4. 最终用项目原生命令（package.json test 脚本，如 vitest/jest）验证，记录命令、退出码、关键结果；未执行不标通过（R9）。

**暂停条件**
- baseline 漂移（Apply/Achieve 前 HEAD 或工作树变化）→ 输出 BASELINE_CHANGED 等确认（R4）。
- RED 因环境/fixture 失败而非目标行为 → 修复测试基础后重建有效 RED。
- 连续根因假设失败/无法稳定复现 → 停止，禁止叠加猜测修复。
- 修复需越出允许写入范围 → 暂停请求扩边界（R1）。
- 原生测试入口缺失/环境不可用 → 结论 BLOCKED/INCOMPLETE，不伪造通过（R9）。

**第一个实质动作（只读）**：只读取证并锁基线 —— 读 package.json（test 脚本）、tsconfig、src/date.ts 及现有测试，记录分支、HEAD、git status 作为 Target baseline；不改文件、不更新状态、不 Git mutation（Stage 1）。

**证据**：SKILL.md auto-code-generator **v4.3**（2026
