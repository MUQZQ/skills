---
name: branch-manager
description: >
  Git 分支管理工作流：创建分支、暂存恢复、checkpoint 提交、feature 分支工作流、
  hotfix 紧急修复、rebase/merge 同步上游、cherry-pick 挑选提交、
  交互式 rebase 整理历史、bisect 二分查找、分支对比、分支清理。
  当用户提到"创建分支"、"切换分支"、"stash"、"暂存"、"checkpoint"、
  "工作区检查"、"回退点"、"feature 分支"、"hotfix"、"cherry-pick"、
  "整理提交"、"rebase"、"merge 冲突"、"bisect"时触发。
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
| 清理旧分支 | 列出 → 确认 → 删除 | 分支清理 |

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|:------:|
| R0 | 创建/切换分支前必须确保工作区清洁（无未提交变更） | 未提交变更被意外带至其他分支或丢失 |
| R1 | Checkpoint commit 使用统一前缀 `WIP:` 便于识别和清理 | 无法区分 checkpoint 和正式提交，历史混乱 |
| R2 | 回退操作前必须确认没有后续 commit 依赖当前状态 | 丢失基于回退点之后的正常提交 |
| R3 | 合并/切换前先 stash 或提交当前变更，零例外 | 合并冲突中混入无关改动，难以分离 |
| R4 | 永远不要在公共分支上做 force push 或 hard reset | 其他协作者基于已删除的 commit 工作，仓库分裂 |
| R5 | rebase 前先确认没有其他人基于当前分支工作 | 协作者的提交历史被破坏，需要强制同步 |

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
