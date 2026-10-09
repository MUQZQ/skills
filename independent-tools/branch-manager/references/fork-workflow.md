# Fork / Upstream 双仓工作流

> 受众：agent（辅助人执行 git 操作时使用）。

## 前提

- 本文只管 git 层。项目授权层归各自 AGENTS.md。
- 分支命名遵循项目约定，本文统一用 `<branch>` 占位。

## 三种工作模式

| 模式 | 适用场景 | 特点 |
|---|---|---|
| **fork 集成主线**（当前默认） | 有自动评审服务把关 fork PR 的个人/团队 | 特性 PR 先落 fork main（过评审门禁），定期批量 PR 到 upstream |
| **持续集成分支** | 中大型功能、多特性打包交付但无 fork PR 评审 | fork 上养长生命周期分支，持续合 upstream，完成后一次性 PR |
| **逐特性分支** | 小修复、独立小功能 | 每个特性切短分支，直接 PR upstream，合完删 |

---

## 模式〇：fork 集成主线 + 双阶段 PR（当前默认）

### 核心思想

fork 的 main 是唯一集成点：所有特性以 PR 形式合入 **fork main**（不是 upstream），
每个 fork PR 先过虚拟机自动评审（每 30 分钟轮询，评论 + 邮件作者，按评论循环修正），
确认 ✅ 后才合入 fork main；由人定期把 fork main 批量 PR 到 upstream。
upstream 只见批量出口，fork 内部闭环消化所有迭代。

### 拓扑

```
upstream/main ──(4h 自动同步)──► fork/main ──(定期批量 PR，人手动)──► upstream/main
                                    ▲
                                    │ 特性 PR（base=fork main）+ VM 评审门禁
                              qin/<特性>  codex/<特性>
```

### 流程

1. **切分支**：`git checkout -b qin/<主题> origin/main`（基于最新 fork main）
2. **开发 + 本地基础检视**（typecheck/单测/自查）→ push 到 fork
3. **开 PR：base 必须选自己 fork 的 main**——Gitea 建 PR 时默认建议 upstream，
   要在 base 下拉里手动切到 `<你的用户名>/<仓库名>` 的 `main`
4. **VM 评审门禁**（全自动，每 30 分钟）：占用 → 上下文打包 → 读码 + 实机截图验证
   → 发布评论（fork 模式一律 `--no-mail`：PR 作者即本人，评论即通知）
   → 看评论**在同分支追加修复再 push**，VM 下轮自动复审
   （判据：最新 commit 后无标记评论），循环到结论 ✅
5. **合入 fork main**（评审 ✅ 后）
6. **定期批量出口**：fork main → upstream 开 PR（人工决定时机），CI + 团队检视 → 合入
7. **回环**：宿主机 4h 同步自动化把 upstream main 拉回 fork main，供下批分支基线

### 注意

- fork main 同时承载 upstream 同步内容与你已验证的特性，是 upstream 的超集——出口 PR 即批量交付
- upstream 合入后 fork main 与 upstream 重新收敛，无需重置
- VM 评审脚本的 fork 模式环境变量（**每条命令都要带**，shell 间不持久；漏带会 fail-open 到 upstream）：
  `QEDA_REPO_OWNER=<fork用户名> QEDA_REPO_NAME=<仓库名> QEDA_UPSTREAM_REMOTE=origin QEDA_REPO_DIR=<QEDAgent 克隆路径>`
- **upstream 按需评审**（不自动化）：在 VM 里 unset 上述环境变量后跑脚本即为 upstream 模式
  （默认值即 upstream），发布评论**不带** `--no-mail`（邮件此时生效，通知真实同事）；
  与 fork 撞号（同号 PR 同时在审）时 `--force` 接管或等一轮

---

## 模式一：持续集成分支（默认推荐）

### 核心思想

不在 upstream 上开多个 PR 排队，而是在自己的 fork 上养一条集成分支，持续吸收 upstream 新代码，等整体功能完备后一次性 PR 到 upstream。消除多 PR 级联同步问题。

### 拓扑

```
upstream/main（组织仓）              origin/fork（你的 fork）
┌──────────────┐                   ┌──────────────────┐
│ main (保护)  │◄──── 大 PR ────── │ <集成分支>        │
│              │                   │  (持续开发中)     │
└──────────────┘                   └──────────────────┘
       ▲                                  ▲
       │ 定期 merge（保持不偏离）           │ 日常开发
       └──────────────────────────────────┘
```

### 流程

#### ① 初始化（一次性）

```bash
# 在 Gitea 网页上 fork 目标仓库
git clone https://<host>/<你的用户名>/<仓库名>.git
cd <仓库名>
git remote add upstream https://<host>/<组织名>/<仓库名>.git
git checkout -b <集成分支> upstream/main
git push -u origin <集成分支>
```

#### ② 日常开发 + 持续同步

```bash
# 每天开始工作前（或每次 fetch 发现 main 推进了）
git fetch upstream --prune
git checkout <集成分支>

# 有新提交才合入（避免空 merge）
if [ $(git rev-list --count <集成分支>..upstream/main) -gt 0 ]; then
  git merge upstream/main
  # 解决冲突（如有）→ 跑测试
  git push origin <集成分支>
fi

# 正常开发
# ... 编码 → 测试 → git commit
git push origin <集成分支>
```

**同步频率**：手动每次做太容易忘，应建定时任务自动化。建议每 4 小时或每天早晚各一次。
（注：模式〇的部署形态已由宿主机 ZCode 定时自动化承担——每 4 小时同步 upstream/main → fork/main，
目标与下文脚本的"集成分支"不同；用模式〇时无需再跑本脚本。）

**定时同步脚本**（放 cron 或 ZCode 定时任务）：

```bash
#!/usr/bin/env bash
# auto-sync.sh — 定时拉取 upstream 并合入集成分支
set -euo pipefail
cd /path/to/<仓库名>
git fetch upstream --prune
COUNT=$(git rev-list --count <集成分支>..upstream/main)
if [ "$COUNT" -gt 0 ]; then
  git checkout <集成分支>
  git merge upstream/main
  # 冲突时退出并告警（不自动解决）
  if git status --porcelain | grep -q '^UU\|^AA\|^DD'; then
    echo "::error::同步冲突，需手动解决: $(git status --porcelain | head -5)"
    exit 1
  fi
  git push origin <集成分支>
  echo "$(date '+%H:%M') 合入 upstream/main $COUNT 个提交"
else
  echo "$(date '+%H:%M') upstream 无新提交"
fi
```

在 ZCode 中建定时任务：「每 4 小时执行 auto-sync.sh，有冲突时通知我」。

#### ③ 阶段性子任务（可选）

集成分支上可以用临时分支隔离实验性改动：

```bash
git checkout -b <临时分支> <集成分支>
# 实验...
# 成功 → 合回集成分支
git checkout <集成分支> && git merge <临时分支> && git branch -d <临时分支>
# 失败 → 直接删
git checkout <集成分支> && git branch -D <临时分支>
```

#### ④ 整体 PR（功能完备时）

```bash
# 最终同步，确保不偏离
git fetch upstream --prune
git merge upstream/main
# 跑全量测试确认

# 推送并开 PR
git push origin <集成分支>
# Gitea 网页: fork/<集成分支> → upstream/main 发 PR
```

#### ⑤ 合入后

```bash
# fork 上的集成分支与 upstream/main 一致了，继续用或重建
git fetch upstream --prune
# 选项 A：重置集成分支到新 main（干净起点）
git checkout <集成分支>
git reset --hard upstream/main
git push --force-with-lease origin <集成分支>
# 选项 B：删掉重建
git branch -D <集成分支>
git checkout -b <集成分支> upstream/main
```

### 为什么选这种模式

| 痛点（逐特性 PR 模式） | 持续集成分支如何解决 |
|---|---|
| N 个 PR 排队，每合一个其他都变 stale | 只有一个 PR，没有排队 |
| 多次同步 main，O(N²) 级联 | 持续小步同步，每次只解小冲突 |
| 每个 PR 独立 CI 跑全量 | 集成分支一次 CI 验证整体 |
| 小 PR 碎片化，评审上下文割裂 | 一个 PR 包含完整特性集，评审看全局 |

---

## 模式二：逐特性分支（小改动用）

适用于独立小修复、文档更新等不需要长期开发的场景。

### 流程

```bash
git fetch upstream --prune
git checkout -b <branch> upstream/main
# 开发 → 测试
git push -u origin <branch>
# PR: fork/<branch> → upstream/main
# 评审 → 修改 → 合入
git branch -d <branch>
git push origin --delete <branch>
```

### 注意

如果同时有多个小 PR 排队合入，会遇到级联同步问题——此时应回到模式一。

---

## 公共规则（两种模式通用）

### 同步 main 的纪律

```bash
# 合并前确认有多少新提交
git fetch upstream --prune
git rev-list --count HEAD..upstream/main

# 用 merge 不用 rebase（保持历史，评审人能看到同步点）
git merge upstream/main
```

### 推送前自审

执行 code-review skill 的提交前审查模式。如是 PR 更新推送，额外用评审人判据自查：CI 车道覆盖、测试锁生产装配、文档代码一致、冗余审计。

### 冲突解决原则

| 冲突类型 | 处理方式 |
|---|---|
| 追加型（两侧各加一节） | 双方保留，删标记行 |
| 重构型（变量改名/结构变化） | 把功能重放到新结构上 |
| 语义型（合并后测试仍挂） | 两侧意图叠加 |

通用方法：`git show <sha>:<file>` 看原文 → 理解意图 → 合成 → 测试验证。

### PR 修改前状态确认（R6）

```bash
git fetch upstream --prune
git ls-remote origin refs/heads/<branch>     # 远程 head 是否与本地一致
git rev-list --count HEAD..upstream/main     # main 是否又推进
```

### 常见故障与恢复

| 故障 | 症状 | 恢复 |
|---|---|---|
| 基线偏离太久 | 一次 merge 冲突 50+ 处 | 增加同步频率；或考虑重放（cherry-pick 核心提交到新分支） |
| GCM JWT 过期 | push 认证失败 | 用固定令牌（~/.gitea-token） |
| CI flaky | 全过但作业失败 | 空提交重触发 |
| 集成分支积累太多无关改动 | PR diff 巨大，评审困难 | 用临时分支拆分，分批 PR |

---

## Fork 定期维护

fork 时平台会复制上游全部分支，需一次性清理不属于你的分支。保留 `main` + 集成分支 + 活跃 PR 分支即可。
