依据冻结 v4.2 快照（`SKILL.md`，版本 4.2，最后更新 2026-08-14）回答 eval_id=1：

**生命周期所有者**：仓库无 AGENTS、无 OpenSpec/权威流程、无任务系统（1.1 检测前三项为空），由本 skill v4.2 的**最小 fallback 结构**管理；唯一持久真相源为当前计划中的任务列表（3.1），不创建额外持久文件。

**风险档位**：**Light**（1.2）——根因已知且单点、局部可逆、无公共契约/数据/安全/跨组件影响。

**TDD/验证路线**：Light 由协调者直做单一场景组（3.2）。行为任务执行完整 RED→GREEN→REFACTOR（3.5）：先为 UTC 日期边界写失败测试并确认失败源于目标行为（非语法/fixture/环境），再对 `src/date.ts` 做最小修复，必要时重构并复跑同组测试。最终用项目原生命令（如 `npm test` / vitest）验证，结论只取 VERIFIED/BLOCKED/INCOMPLETE（4.2）。

**边界**：允许写入仅 `src/date.ts` 及其边界测试；禁止扩范围、禁止建第二状态账本；Git 权限 NONE（R10），不 stage/commit/push/PR/部署。

**暂停条件**：基线漂移（输出 BASELINE_CHANGED 待确认）；RED 因环境/fixture 失败（不虚构 TDD）；连续根因假设失败；需越界修改或 Critical/Important 未清零。

**第一个实质动作**：只读取证（Stage 1）——读 `package.json` 测试脚本、`src/date.ts`、既有测试文件、当前分支/HEAD/status；不改文件、不动任务状态、不做 Git mutation。
