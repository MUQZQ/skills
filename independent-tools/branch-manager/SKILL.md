---
name: branch-manager
description: >
  Git 分支管理工作流：创建分支、暂存恢复、checkpoint 提交、feature 分支工作流、
  hotfix 紧急修复、rebase/merge 同步上游、cherry-pick 挑选提交、
  交互式 rebase 整理历史、bisect 二分查找、分支对比、分支清理、
  PR 修改前状态确认、验证清单刷新、Gitea API 令牌管理。
  当用户提到"创建分支"、"切换分支"、"stash"、"暂存"、"checkpoint"、
  "工作区检查"、"回退点"、"feature 分支"、"hotfix"、"cherry-pick"、
  "整理提交"、"rebase"、"merge 冲突"、"bisect"、"更新 PR"、"改 PR 分支"、
  "PR 状态"、"刷新 PR 验证列表"、"令牌"、"token"、"API token"、"fork PR"、"双阶段 PR"、
  "fork 集成"、"合入 upstream"、"评审门禁"时触发。
---

# 分支管理器

## 前置条件

- 当前目录为 git 仓库
- git 已正确配置 user.name 和 user.email

## 场景路由

| 用户意图 | 操作 | 对应章节 |
|---------|------|---------|
| 创建新分支 | 检查工作区 → 命名 → 创建 → 切换 | 分支命名与创建 |
| 暂存/恢复改动 | stash push/pop | 暂存与恢复 |
| 建立/回退 checkpoint | 提交 checkpoint → 按需 reset | Checkpoint |
| 新功能开发全流程 | 切分支 → 开发 → 同步上游 → 合并 | Feature 分支工作流 |
| 线上紧急修复 | 切 hotfix → 修复 → 同步多分支 | Hotfix 工作流 |
| 把 main 的更新合入 feature | rebase 或 merge 当前分支 | 同步上游 |
| 从其他分支摘取特定提交 | cherry-pick → 解决冲突 | Cherry-pick |
| 提交前整理历史 | 交互式 rebase squash/fixup | 提交历史整理 |
| 对比两个分支差异 | log/diff 两种维度对比 | 分支对比 |
| 定位引入 bug 的 commit | 二分查找 bad/good commit | Bisect 二分查找 |
| 管理工作树 | 按位置/命名约定创建、迁移、删除 | 工作树（worktree）管理 |
| 清理旧分支 | 列出 → 确认 → 删除 | 分支清理 |
| 修改已有 PR 的分支 | 确认 PR 状态 → 同步基线 → 修改 → 推送 | PR 修改前状态确认 |
| 刷新 PR 验证清单或核对历史失败 | 读取当前和历史证据 → 同步清单 → 回读 | [PR 验证记录](references/pr-records.md#刷新-pr-验证清单) |
| 发布、编辑、回复 PR 评论或处理评审线程 | 检查最新状态 → 判断同步需要 → 刷新内容 → 写入前复核 | PR 评论与评审线程操作前检查 |
| 跟踪 PR 评审或 CI | 核对当前候选 → 按变化处置 → 判定收敛和可合入 | [PR 值守与收敛](references/pr-records.md#pr-值守与收敛) |
| fork/upstream 双仓操作 | 特性 PR → fork main（项目评审门禁）→ 批量交付 upstream，或按项目选择集成分支和逐特性模式 | references/fork-workflow.md |

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|:------:|
| R0 | 创建/切换分支前必须确保工作区清洁（无未提交变更） | 未提交变更被意外带至其他分支或丢失 |
| R1 | Checkpoint commit 使用统一前缀 `WIP:` 便于识别和清理 | 无法区分 checkpoint 和正式提交，历史混乱 |
| R2 | 回退操作前必须确认没有后续 commit 依赖当前状态 | 丢失基于回退点之后的正常提交 |
| R3 | 合并/切换前先 stash 或提交当前变更，零例外 | 合并冲突中混入无关改动，难以分离 |
| R4 | 永远不要在公共分支上做 force push 或 hard reset | 其他协作者基于已删除的 commit 工作，仓库分裂 |
| R5 | rebase 前先确认没有其他人基于当前分支工作 | 协作者的提交历史被破坏，需要强制同步 |
| R6 | 修改已开 PR 的分支或操作 PR 评论、评审线程前，先检查最新 head/base、CI、评审和线程内容，再判断是否需要同步代码、证据与待发布内容；具体按下文对应检查清单执行 | 基于过期状态操作：覆盖新修复或新回复、重复处理已解决的问题、发布与当前代码不符的结论 |
| R7 | API 令牌只存用户级固定位置（`~/.gitea-token`，ACL 仅本人），不进任何 git 仓库、脚注或会话输出 | 令牌泄漏进仓库历史或日志；轮换时找不到全部副本 |
| R8 | 按当前候选的评审、必需 CI、基线和冲突状态结束值守，按平台正式审批等门禁确认合入资格。**agent 不得自动合入 PR**：禁止 `gh pr merge`、平台合并接口、开启自动合并；合入必须由用户当场人工确认，此前授权推送或值守不构成合入授权 | 越权合入他人仓库；不可逆合并 |
| R9 | **创建闸门**：创建分支、PR、工作树前必须先与用户确认（分支名与基线 / PR 目标分支与提交范围 / 工作树路径与分支），确认后再执行，不得自行创建 | 擅自产生多余分支、PR 与工作树，污染远端与磁盘 |

## 分支命名与创建

### 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feature/<name>` | `feature/add-auth-middleware` |
| 修复 | `fix/<name>` | `fix/sql-injection-filter` |
| 重构 | `refactor/<name>` | `refactor/extract-user-service` |
| 热修复 | `hotfix/<name>` | `hotfix/prod-login-crash` |
| 文档 | `docs/<name>` | `docs/api-reference-update` |
| 实验 | `exp/<name>` | `exp/switch-to-postgres` |

> 项目级前缀约定优先于本表（如 QEDAgent 仓库：`qin/<主题>` 为人工主导分支、
> `codex/<任务>` 为 agent 主导分支），见各仓库 AGENTS.md / 实际分支惯例。

### 工作区检查与分支创建

```bash
git status --porcelain                  # 工作区清洁检查
git checkout -b <type>/<name>           # 创建并切换
git branch --show-current               # 确认当前分支
git push -u origin <type>/<name>        # 推送到远程（如需要）
```

- 存在未跟踪文件: 询问加入 `.gitignore` 或暂存
- 存在未暂存修改: 先提交或 stash
- 存在 rebase/merge 进行中: 先完成或中止

---

## Feature 分支工作流

完整的新功能开发流程：

```
 main (或 develop)
   │
   ├── git checkout -b feature/xxx     # 1. 从主分支切出
   │
   ├── git commit ...                  # 2. 开发中多次提交
   ├── git commit ...
   │
   ├── git fetch origin                # 3. 同步上游最新变更
   ├── git rebase main                   （推荐 rebase 保持线性历史）
   │
   ├── git checkout main               # 4. 合并回主分支
   ├── git merge feature/xxx             （非远程协作分支可用 --squash）
   │
   └── git branch -d feature/xxx       # 5. 删除已完成的分支
```

### 同步上游：rebase vs merge

| 方式 | 效果 | 适用场景 |
|------|------|---------|
| `git rebase main` | 将 feature 分支的提交"搬到"main 最新 commit 之后，历史线性干净 | 个人分支、尚未分享给他人 |
| `git merge main` | 在 feature 分支上创建一个合并 commit，保留完整时间线 | 多人协作的分支 |

**推荐**: 个人开发用 rebase 保持历史简洁；多人协作用 merge 避免破坏他人历史。

### 冲突解决流程

```bash
git rebase main                        # 触发冲突
# 编辑冲突文件，解决 <<<<<< 标记
git add <resolved-files>               # 标记已解决
git rebase --continue                  # 继续 rebase
# 或
git rebase --skip                      # 跳过此 commit
# 或
git rebase --abort                     # 放弃整个 rebase，回到初始状态
```

---

## PR 修改前状态确认

修改已开 PR 的分支或刷新 PR 描述中的验证列表之前，先核对平台记录的 head 与 base 提交。目标分支即使名称未变也可能推进，并使原 head 产生新冲突。

### 检查清单（按顺序）

先读取平台上的 head/base 仓库、分支与完整提交，按 `git remote -v` 对应到本地 remote。fork PR 的 base 可以在 fork，也可以在上游。以下占位值按实际 PR 替换。

```bash
git fetch <base-remote> --prune
git fetch <head-remote> --prune               # 与 base remote 相同只 fetch 一次
git rev-list --count HEAD..<base-remote>/<base-branch>
git ls-remote <head-remote> refs/heads/<head-branch>
```

通过托管平台核对合入条件。

| 检查项 | 关注点 | 异常时动作 |
|--------|--------|-----------|
| PR head/base | head 是否仍是自己的分支、指向的提交与本地是否一致、base 是否被人变更 | 远程领先本地先拉取；base 变更先评估影响 |
| mergeable | 平台可能在重算，用 `git merge-tree --write-tree <head-sha> <base-sha>` 核对实际冲突 | 复查平台回执，确认冲突后按授权同步基线并验证 |
| CI / 评审 | 当前 head 对应的 checks、最新评审及其绑定的提交 | 有新评审先读全文；运行中的作业按任务和日志确认 |
| 正式审批 | 实际满足的审批数及目标分支要求 | 从平台合入页或有权读取的保护规则确认。评审应用的结论单独记录，权限不足时注明未核实门槛 |

刷新验证清单或核对某条失败记录时，加载[PR 验证记录](references/pr-records.md#刷新-pr-验证清单)。按当前验证、历史验证和人工用例逐区核对。CI、评审、冲突与正式审批分别以其平台凭据为准。写入前重新核对正文和 head/base，写入后回读。

### 确认通过后的推送纪律

- 基线已推进且影响候选时，按已有授权先同步目标分支并复验冲突影响面，再推送候选。单纯刷新验证清单可以先记录当前状态。
- 远程 head 领先本地：先拉取合并，禁止直接覆盖
- 快进更新用普通 push。改写已推送历史须有用户明确授权，并按项目规则核对分支归属、协作者和远端预期 SHA，再用 `--force-with-lease`（见 R4/R5）。
- 同步目标分支后重算交付面：旧依赖 pin、脚本硬编码计数、spec/feature/test 映射；旧 head 的 CI 与评审结论失效，必须在新 head 重跑

> 经验教训：目标分支在评审期高频推进时，「拉取 → 合并 → 推送」可能要做多轮；
> 每轮推送后重新确认 mergeable 与 CI，不要沿用推送前的旧结论。

---

## PR 评论与评审线程操作前检查

发布、修改、回复 PR 评论或处理评审线程时，加载[评论与评审线程](references/pr-records.md#评论与评审线程)。先读最新正文与线程，再判断同步和复验范围。发布结论以远端提交和对应证据为准。

---

## Gitea API 令牌管理

自托管 Gitea 的 API 写操作（发评论、改 PR 描述、重跑 CI）不能依赖 git 凭据管理器：
GCM 的 OAuth JWT 每小时过期且刷新可能挂起。用固定 API 令牌。

### 固定位置（唯一主存）

```bash
# 主存：用户级、仓库外、ACL 仅本人
~/.gitea-token        # 即 C:\Users\<user>\.gitea-token
icacls "$env:USERPROFILE\.gitea-token" /inheritance:r /grant:r "$env:COMPUTERNAME\<user>:F"
```

- 生成入口：Gitea 网页 → 头像 → 设置 → 应用 → 生成新令牌；scope 按需最小化
  （评论/改 PR 用 `write:issue` + `write:repository` 即可，不必给 `read:user`）。
- 读取顺序约定：`~/.gitea-token`（唯一存放位置）→ 环境变量 `GITEA_TOKEN` →
  GCM 兜底（仅应急，见上）。不设任何仓库内令牌副本，避免随 Junction 同步扩散。
- 令牌不入 git 仓库、不写进提交信息、不回显到会话输出。

### 验证与轮换

用 `tools/pr-watch.mjs` 或已配置的 API 客户端读取实际业务端点验证权限。轮换时在平台生成新令牌，更新用户级令牌文件，验证后撤销旧令牌。

### 使用模式（脚本内）

```js
const token = readFileSync(join(process.env.USERPROFILE, '.gitea-token'), 'utf8').trim();
fetch(url, { headers: { Authorization: `token ${token}` } });
```

---

## PR 状态监控与收敛

读取单次 PR 状态、跟踪变化或按评审意见收敛时，加载[PR 值守与收敛](references/pr-records.md#pr-值守与收敛)。附带的 `tools/pr-watch.mjs` 轮询 Gitea，报告候选、CI、评论与正式评审信号。单个 PR 的本轮收敛在当前会话进行。用户明确需要周期监视时再创建定时任务。

---

## Hotfix 工作流

线上紧急修复的标准操作：

```
 main (生产分支)
   │
   ├── git checkout -b hotfix/bug-name         # 1. 从 main 切热修复分支
   │
   ├── git commit -m "fix: xxx"                # 2. 修复 + 测试
   │
   ├── git checkout main                        # 3. 合并回 main
   ├── git merge --no-ff hotfix/bug-name         （--no-ff 保留分支痕迹，可追溯）
   ├── git tag v1.2.1                            （打版本标签）
   │
   ├── git checkout develop                      # 4. 同步到开发分支（如有）
   ├── git merge hotfix/bug-name
   │
   └── git branch -d hotfix/bug-name             # 5. 清理
```

### 热修复 cherry-pick 备选

如果 main 和 develop 已分歧较多，可在合并到 main 后 cherry-pick 修复 commit 到 develop：

```bash
git checkout main
git merge hotfix/bug-name
# 获取修复 commit 的 hash
git checkout develop
git cherry-pick <fix-commit-hash>
```

---

## Cherry-pick

从其他分支摘取特定提交到当前分支：

```bash
git log <source-branch> --oneline -10        # 查看源分支最近提交
git cherry-pick <commit-hash>                # 摘取单个提交
git cherry-pick <hash1>..<hash3>             # 摘取连续范围的提交（不含 hash1）
git cherry-pick <hash1>^..<hash3>            # 含 hash1
git cherry-pick --no-commit <hash>           # 摘取但不自动提交（可修改后再提交）
```

冲突时处理：
```bash
# 解决冲突后
git add <files>
git cherry-pick --continue
# 或放弃
git cherry-pick --abort
```

---

## 暂存与恢复

临时保存当前工作区的改动（切换分支前避免提交半成品）：

```bash
git stash push -m "描述当前工作状态"      # 保存改动
git stash list                            # 查看所有 stash
git stash pop                             # 恢复最近一次并删除记录
git stash apply stash@{0}                # 恢复指定 stash，不删除
git stash drop stash@{0}                 # 删除指定 stash
git stash clear                           # 清空所有 stash
```

---

## Checkpoint 回退点

在重构、实验等高风险操作中，每完成一个阶段创建 checkpoint：

```bash
git add -A
git commit -m "WIP: <阶段描述>"
```

**Checkpoint 序列示例**:
- `WIP: characterization tests passed`
- `WIP: new implementation with tests`
- `WIP: callers switched`
- `WIP: old code removed`

回退：
```bash
git log --oneline | grep WIP              # 找到 checkpoint
git reset --hard <checkpoint-hash>        # 回退（危险操作）
```

**注意**: `reset --hard` 会丢弃后续提交，执行前确认无重要后续提交。

---

## 提交历史整理

在合并到主分支前整理 feature 分支的提交历史：

### 交互式 rebase

```bash
git rebase -i HEAD~N                      # 整理最近 N 个提交
git rebase -i main                        # 整理分支上所有提交（基于 main）
```

**常用操作**:

| 指令 | 效果 |
|------|------|
| `pick` | 保留此提交，不变 |
| `reword` | 保留提交，修改 commit message |
| `squash` | 合并到上一个提交，合并 message |
| `fixup` | 合并到上一个提交，丢弃本 message（推荐） |
| `drop` | 删除此提交 |
| `edit` | 暂停，允许修改提交内容 |

> 不要在已推送的公共分支上使用 rebase -i，会破坏他人历史。

---

## 分支对比

### 查看 commit 差异

```bash
git log main..feature/xxx --oneline       # feature 有而 main 没有的提交
git log feature/xxx..main --oneline       # main 有而 feature 没有的提交
git log --left-right main...feature/xxx   # 双侧差异，< 表示左侧 > 表示右侧
```

### 查看内容差异

```bash
git diff main...feature/xxx --stat        # 文件级变更统计
git diff main...feature/xxx               # 完整内容差异
```

---

## Bisect 二分查找

当不确定哪个 commit 引入了 bug，用二分法自动缩小范围：

```bash
git bisect start                          # 开始二分查找
git bisect bad                            # 标记当前版本有问题
git bisect bad <commit>                   # 或指定已知有问题的 commit
git bisect good <commit>                  # 指定已知正常的 commit

# git 自动切换到中间 commit，测试后标记：
git bisect good                           # 此版本正常
git bisect bad                            # 此版本有问题
# ... 重复直到定位到首个 bad commit ...

git bisect reset                          # 结束二分，回到原始位置
```

**自动化二分**（如果有可脚本化的测试）:
```bash
git bisect start HEAD <good-commit>
git bisect run pytest tests/test_affected.py
# 自动运行测试直到找到引入问题的 commit
```

---

## 工作树（worktree）管理

并行任务各自使用独立工作树时，遵循统一的位置、命名与生命周期约定，避免工作树与主仓库平铺在同一层级、越攒越多。

### 位置与命名

| 约定 | 规则 |
|------|------|
| 位置 | 工作树统一放在专用容器目录（如 `<盘符>/worktrees/<仓库标识>/`），不得与主仓库平铺在同一层级；具体容器路径以各仓库 AGENTS.md 为准 |
| 命名 | `<仓库标识>_<主题>`，与分支主题对应，一眼可辨归属 |
| 唯一检出 | 同一分支同时只允许检出一处；创建前先确认目标分支未被其他工作树占用 |

```bash
git worktree add <容器目录>/<名称> -b <分支名>   # 新建工作树 + 分支
git worktree move <旧路径> <新路径>              # 迁移（要求工作树干净、无进程占用；不要手工剪切粘贴，登记指针会断）
git worktree remove <路径>                       # 删除（有未提交变更时 git 会拒绝，禁止随手 --force）
git worktree prune                               # 清理已失效的登记
git worktree list                                # 核对
```

### 生命周期

- **创建**：并行任务开工时创建，登记路径与分支；创建前按 R9 与用户确认或取消。
- **迁移**：容器目录调整时用 `git worktree move`；Windows 上有进程占用或长路径文件时会失败，先停进程再迁。
- **删除**：任务收尾（已合入或已废弃）即删工作树，删除前逐项过下面的检查单。

### 清理检查单（删除前逐项过）

1. **未提交变更**：`git status --porcelain` 非空 → 先提交、stash 或明确弃置，不得带变更删除（`remove` 被拒是保护，不是障碍）。
2. **未推送/未合并提交**：`git rev-list --count @{upstream}..HEAD`（无 upstream 时对照基线分支）> 0 → 确认这些提交随分支留存即可，还是需要先推送/合并。
3. **未跟踪制品**：`.tmp/`、原型、导出物等未跟踪文件是否还有用；有用先归档再删。
4. **特殊载体**：该工作树是否是开着的 PR 的 head 载体、或承载未提交的规格/规划制品 → 是则保留到 PR 收口。
5. **跨仓跟进项**：分支 pin 指向源仓库未合并分支/PR 时，登记该跟进项；工作树删除不代表依赖已收口。

两条边界：

- **分支不随工作树删除**：`git worktree remove` 只删目录，分支与提交保留；分支本身要不要删，按「分支清理」章节另行确认。
- **detached HEAD 的临时工作树**：删除前确认其 commit 可从某个分支可达（`git branch -a --contains <hash>`），不可达则先建分支再删，否则该提交最终会被 GC。

---

## 分支清理

```bash
git branch                                # 列出本地分支
git branch -a                             # 列出所有分支（含远程）
git branch --merged main                  # 已合并到 main 的分支
git branch --no-merged main               # 未合并到 main 的分支

git branch -d <branch>                    # 安全删除已合并分支
git branch -D <branch>                    # 强制删除（即使未合并）
git push origin --delete <branch>         # 删除远程分支
git remote prune origin                   # 清理本地已失效的远程跟踪引用
```

---

## 错误处理

| 场景 | 原因 | 处理方式 |
|------|------|---------|
| `git stash pop` 冲突 | stash 与当前工作区冲突 | 手动解决冲突后 `git stash drop` |
| `git checkout` 失败 | 工作区有未提交变更 | stash 或提交后重试 |
| detached HEAD | 当前不在任何分支上 | `git checkout -b <new-branch>` 创建跟踪分支 |
| 误删分支 | 仍有未合并 commit | `git reflog` → `git checkout -b <name> <hash>` |
| rebase 中途卡住 | 冲突未解决 | 解决冲突后 `git add` + `git rebase --continue`；或 `git rebase --abort` |
| merge 中途卡住 | 冲突未解决 | 解决后 `git add` + `git merge --continue`；或 `git merge --abort` |
| cherry-pick 冲突 | 目标分支上下文不同 | 解决冲突后 `git add` + `git cherry-pick --continue`；或 `--abort` |
| force push 被拒绝 | 远程分支有保护 | 绝不要 `--force`；改用正常 push，或确认无协作者后联系管理员 |
| bisect 中途丢失 | 忘记 `bisect reset` | 先用 `git bisect reset` 回到起始位置再重新来 |
