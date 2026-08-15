**决策（eval_id=3, version=with_skill）**：依据 auto-code-generator **v4.3** 评估模式答复；不实施、不修改任何文件、不做 Git mutation。仓库现有 spec 是唯一生命周期所有者，本 skill 仅负责编排（R0）。

**权限解释**：用户明确"本地 commit"→ Git 权限＝`LOCAL_COMMIT`，不扩大到 push/建 PR/部署，三者各自需单独授权（R10；"归档成功≠提交"）。跨两个 package 普通功能、无架构/公共契约/数据/安全边界 → **Standard** 档位。

**实施到提交的门禁**：服从现有 spec 生命周期（不另建流程）→ 场景组内完整 `RED→GREEN→REFACTOR`（R5）→ 最终审查 Critical/Important=0（R8）→ 项目原生验证（R9）→ 官方归档成功（Stage 5）→ 才执行一个 closeout commit。提交前：从最终 diff 锁定 `AUTHORIZED_COMMIT_SET`，排除预先存在/范围外改动；紧邻暂存前重读 branch/HEAD/status 对比 Target 基线，漂移即停；暂存后核对 `git diff --cached --name-status` 与内容，不一致即停；不 force push。

**分支保护**：当前分支为 `main`/`master` 时停止提交；仅项目分支工作流或用户另行授权后才可创建/切换分支。

**验证结论**：本次为评估模式，不产生真实 `VERIFIED`；实施后结论只能由项目原生命令给出 `VERIFIED/BLOCKED/INCOMPLETE`，未执行项不得标通过（R9）。

**边界与暂停条件**：无权威 spec/状态不明、基线漂移（`BASELINE_CHANGED`）、Critical/Important 未清零、验证或归档失败、staged 集合不匹配、主干分支——均停止并回报，不自动扩权。

**第一个实质动作**：只读取证——读仓库 AGENTS/规则、活动 change 与 spec 实时状态、当前 branch/HEAD/status；输出一句所有权决定后进入规划，不改文件、不更新任务状态。
