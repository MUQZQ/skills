# Git 与交付

仅执行已授权的本地提交或外部交付时，读取对应小节及共同的“Git 与外部动作边界”。
本文承接主 Skill 的阶段编号，不是另一套生命周期。无相应授权时不进入这些动作。

### 3.7 增量交付检查点

只有 Git authority 为 `LOCAL_COMMIT` 且 Commit mode 为 `INCREMENTAL_CHECKPOINT` 时，才在 DAG 执行中评估
阶段提交。用户说“分批提交”“阶段性提交”“做完一部分先提交”或明确要求避免最后一次提交过多文件，表示
授权当前任务产生多个本地提交；不推导 push、PR、部署或其他仓库权限。

每次 Sol 完成 3.6 验收后，按以下门禁形成一个完整验收的交付切片：

1. 切片包含一个或多个已满足的底层 task/场景组，提交后自身行为有效、可解释、可回退，不依赖未完成代码
   才能成立；单个 worker 返回、RED/GREEN 中间态或仅部分通过的场景组不合格；
2. 为下一次 commit 从实际 diff 重新计算准确的 `AUTHORIZED_COMMIT_SET`，其中每个文件的全部当前改动只属于
   该切片；排除
   预先存在、范围外、其他参与者以及混合未完成任务改动的文件，默认不使用补丁暂存绕过混合边界；
3. 对该切片执行项目规定的聚焦审查和必要验证，Critical/Important 清零；共享契约、manifest、生成链或
   测试证据不能独立归属时，继续累积到边界完整，不为减少文件数强行提交；
4. 暂停会修改该切片文件或目标仓库 Git 状态的调度，把 `AUTHORIZED_COMMIT_SET` 交给“Git 与外部动作边界”
   的统一事务协议；使用 conventional commit 记录已完成结果，不使用 `WIP:` 表示已验收交付；
5. 统一事务成功后更新完整 Target baseline 并恢复 `ready_queue`；保留原始 Change base，确保 Stage 4 对累计
   提交和剩余改动做 whole-change 审查。事务失败时保持冻结并按统一错误状态恢复，不复制另一套 Git 规则。

阶段提交只减少安全工作树中的累计改动，不触发归档、不把整个 change 标记完成，也不替代 3.6 的验收或
完成事件；DAG 后继是否释放仍只由真实任务/场景组验收决定。没有合格文件集时继续实施或重划边界，不创建
空提交，不把未完成改动硬塞进本批次。

## Stage 6：Fork PR 交付与评审戴明环

只有用户明确要求推送分支、开 PR、盯着评审修到过或合入时才进入本阶段；没有这些授权时，Stage 5 的报告就是终点，
只给出建议动作。本阶段不建立第二套 Git 或 PR 流程：分支创建、推送纪律、PR 修改前状态确认和 `pr-watch` 监控由
`independent-tools/branch-manager` 拥有，本阶段只规定进入条件、修复循环和终止判定。项目规则优先；QEDA 规定交付
动作必须由用户另行明确授权并命名目标分支，也不允许把当前工作分支合入目标分支当成验证或归档的一部分。

### 6.1 进入条件

- 最终结论为 `VERIFIED`，且 closeout 已完成或明确不适用；
- `Delivery authority` 已记录具体动作与**目标分支**：推送分支、开 PR、评审修复循环、合入分别是独立授权，
  不能从提交权限、验证结论或归档结果推导；
- `PR_REPAIR_LOOP` 缺少 `loop_budget` 或缺少目标分支时不进入循环，报告 `BLOCKED` 并要求用户给出上限，
  不自行设定预算；
- 目标分支取自用户指令或项目证据，不猜测；fork 集成主线的证据（分支归属、PR 基线惯例）通常指向 fork 的
  `main`，`upstream` 只用于用户另行要求的批量出口，并把所选依据写进报告；
- 分支命名沿用项目惯例（如 `qin/<主题>`、`codex/<任务>`），并说明本 PR 的基线分支；
- PR base 必须是验证时命名的目标分支；base 不同或目标分支在归档后推进时，按项目规则使用托管平台的
  合入候选检查或 linked follow-up change，不把归档报告当作该交付对象的证据。

### 6.2 推送与开 PR

1. 推送与开 PR 前按 branch-manager 的“PR 修改前状态确认”确认远程 head、目标分支是否推进和 PR 当前状态；
   需要同步才能继续时，只有 Git 授权已覆盖该方向（目标分支或远程 PR 分支 → 当前分支）才执行同步与冲突处理，
   缺少这项许可时报告 `BLOCKED` 并请求授权；同步完成后重新确认，不沿用旧结论；
2. 只推送授权范围内的分支，不使用 `--force`；需要 `--force-with-lease` 的窄边界情形必须先取得用户明确授权，
   再按 branch-manager 与项目 Git 规则执行，本阶段不自行决定；
3. 创建分支、PR 或工作树前确认项目要求的名称、基线、目标、提交范围或落点；已有明确确认直接复用。明确 base 与 head 后开 PR；PR 描述由既有 change、任务状态、审查与验证结论拼成，不新造报告、
   不建立第二份验收结论；
4. fork 模式下 PR 在 fork 内闭环评审，跨仓出口由既有机制或用户决定；
5. 推送和开 PR 不改变归档状态，也不把当前工作分支合入目标分支。

### 6.3 监控

用 `pr-watch`（指定本 PR 所属的 fork 仓库与 PR 号）建立快照基线，每轮读取本 PR 的 `state`、`head`、
`mergeable`、CI 和评论计数，无变化不打扰；它只给出变化信号，评论正文与评审结论按 branch-manager 的用法
另行读取。会话内可以轮询，也复用已有监控任务；只有用户明确要求时才新建定时监控任务，且不修改无关任务。
定时值守任务的提示词按 `independent-tools/branch-manager` 的「值守任务提示词的必备段落（PR 收敛 cron 统一写法）」生成（含必载 skill、工作区/凭证、四查、处置路由、收敛出口与基线债写法）；任务内的本地验证与推送前门禁按 `pre-pr-local-verification.md` 执行。
快照基线和轮次计数随会话与同一份报告记录，跨会话恢复时从 PR 上的评审结论重建轮次，本阶段不写第二套状态账本。

### 6.4 戴明环修复

每轮按 Plan → Do → Check → Act 闭环，只处理本轮新增证据：

1. **Plan**：把新评论与 CI 失败逐条归类为“当前变更相关 / 范围外”，再分 Critical、Important、Minor；
   范围外或需要扩授权边界的条目只报告，不顺手修；
2. **Do**：在授权和已确认边界内做最小修复，遵守项目测试策略、场景组粒度和文件归属；change 已经归档时
   先按项目对归档后更正的规则建立或继续 linked follow-up change，再在其 Apply 边界内修复，不把更正追加在
   已归档候选的报告下；
3. **Check**：重跑受影响的项目原生聚焦验证。项目有验证状态机制时，源码变化使旧结果失效：change 仍活动时
   返回复核与验证后重新 capture/check，不得只刷新指纹；已归档时不得声称可以对原 change 重新 capture/check，
   当前候选的复核与验证在 linked follow-up change 上完成；
4. **Act**：以追加提交推送修复，随后等待下一轮评审；同步更新轮次计数与本轮结论。

### 6.5 终止判定

| 情况 | 处理 |
|---|---|
| 评审 ✅ 绑定当前 head，且已注册的 CI 检查全部成功 | 交付动作完成；合入等待用户当场明确确认，本阶段不自行合入，也不得开启自动合并；该 PR 没有注册 CI 时必须明确记录这一点，不能当作已通过 |
| 达到 `loop_budget` 的轮次或时限 | 循环状态记 `INCOMPLETE`，保留 PR 与工作树现场，列出剩余问题 |
| 同一根因连续修复失败、需要扩边界或需要人类裁决 | 循环状态记 `BLOCKED`，停止叠加猜测性修复 |
| CI 失败来自基线噪音或与本变更无关 | 如实标注，不改代码掩盖；重跑使用项目原生方式 |
| `mergeable=false` 或目标分支已推进 | 按 branch-manager 的“PR 修改前状态确认”处理；在 Git 授权覆盖该同步方向时先把目标分支同步到当前分支再叠加修复，缺少许可时报 `BLOCKED`，候选变更后的复核与验证按 6.4 的 Check 处置；禁止直接覆盖远程 |

循环状态取 `进行中 | COMPLETE | INCOMPLETE | BLOCKED`，只写入报告的 PR 字段；`结果` 字段始终描述 change 的
验证结论，不因循环状态改变。同一情形命中多行时按最需要人类介入的一行判定，`BLOCKED` 优先于 `INCOMPLETE`。
评审 ✅ 必须绑定当前 head：结论里给出的 head 或评审提交要与当前 head 一致，之后有新推送即失效，不能只看
“最新 commit 之后没有新评论”；CI 为 `pending` 或未注册时不得视为通过，如实记录并按项目原生方式确认。不执行：不改写已推送历史（Stage 6.2 明确授权的 `--force-with-lease` 除外）、不自行合入、不部署、不用 PR 描述或修订记录掩盖历史。
完成后把最终 PR 事实补进同一份 Stage 5 报告，不新开报告。

## Git 与外部动作边界

- 默认不 stage、不 commit、不 push、不创建 PR、不部署；
- `AUTHORIZED_COMMIT_SET` 始终表示“下一次 commit 的准确文件及内容集合”，每次提交前重新计算：增量模式
  从 3.7 已完整验收的切片得到，closeout 模式从最终已确认 diff 得到；两种模式都排除预先存在、范围外或
  其他参与者的改动；
- Commit mode 默认为 `CLOSEOUT_ONCE`；只有用户明确要求多个本地提交、分批提交或阶段性提交时才设置
  `INCREMENTAL_CHECKPOINT`，该授权仅在当前任务和目标仓库/分支有效；
- 紧邻暂存前重新读取 branch、HEAD 和 status，并与 Target baseline 比较；发生漂移时停止。当前分支是
  `main`/`master` 时默认停止提交；用户当场明确允许该目标分支与提交范围时按其授权执行。
  创建分支或工作树须先确认名称、基线及落点，不把本地提交授权当作创建许可；
- 暂存前拒绝进行中的 merge/rebase/cherry-pick/revert（`MERGE_HEAD`、rebase state、`CHERRY_PICK_HEAD`、
  `REVERT_HEAD`）；普通本地 commit 授权不包含完成这些 Git 操作的权限；
- 从暂存开始到 commit/tree 核验完成，目标仓库的 Git index 和当前分支必须由协调者独占；其他 Agent、hook
  或流程造成的 HEAD/index 漂移都必须停止本次提交；
- 只暂存 `AUTHORIZED_COMMIT_SET` 中的明确路径，不改动预先存在的 staged 状态；暂存后必须检查
  `git diff --cached --name-status` 和 `git diff --cached`，文件集合或内容不完全匹配就停止提交；
- 提交前执行项目规定的审查与验证，并证明结果对应精确暂存快照；剩余工作树改动参与过的测试结果不能单独
  证明 staged tree 有效；不得 `--force`（Stage 6.2 明确授权的 `--force-with-lease` 情形除外）；
- 记录 `pre_commit_head` 和 `reviewed_tree = git write-tree`，紧邻 commit 前复核二者及完整 cached diff；
  提交后读取完整 parent 列表，验证新提交恰好一个 parent 且该 parent 等于 `pre_commit_head`，同时验证
  `HEAD^{tree}` 等于 `reviewed_tree`；任一不一致时报告 `COMMIT_TREE_MISMATCH` 并停止，不自动 amend、reset
  或 push；
- 一个 task、worker 返回、TDD transition 或 artifact 完成不会自动成为 commit 边界；
- `INCREMENTAL_CHECKPOINT` 按 3.7 的 `AUTHORIZED_COMMIT_SET` 提交完整验收切片，门禁是切片验收通过、
  切片必要审查/验证通过、准确暂存集、工作分支和独立 Git 授权；它不要求整个 change 已归档；
- 用户只要求“一个本地 commit”或未明确要求分批时使用 `CLOSEOUT_ONCE`，只创建一个 closeout commit；
- closeout commit 的统一门禁是 `VERIFIED + archive SUCCESS/N/A + 独立 Git 授权`；官方归档存在时必须
  `archive=SUCCESS`，fallback 无归档操作时允许 `archive=N/A`。提交后报告 hash 和 status；
- `INCREMENTAL_CHECKPOINT` 表示“零到多个 checkpoint + 一个最终 closeout”：Stage 4 修复、Stage 5 归档或
  其他剩余授权内 diff 在上述 closeout 门禁通过后形成最终 closeout；若没有剩余 diff，不创建空 commit，
  只报告已有 checkpoint hashes；
- 每次增量提交后更新完整 Target baseline，但保留原始 Change base；最终审查和验证必须覆盖 Change base
  以来的全部 checkpoint commits 与剩余 diff；
- push、PR、评审修复循环、合入和部署各自需要明确授权，不能从 commit 权限推导，也不能从验证或归档结论推导；
  授权必须命中用户指定的目标分支；
- 交付动作按 Stage 6 执行：分支、推送纪律、PR 状态确认和 `pr-watch` 归 `independent-tools/branch-manager`，
  本文件不复制其 Git 规则，也不建立第二套 PR 或监控账本；
- 本 skill 不自行合入目标分支、不改写已推送历史、不部署；合入必须由用户当场明确确认，不能从此前推送或值守授权推导，不得开启自动合并。
