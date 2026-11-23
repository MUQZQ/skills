# Fork / Upstream 双仓工作流

> 受众：agent（辅助人执行 git 操作时使用）。

## 前提

- 分支、PR、工作树创建，远端写入和分支清理沿用项目 AGENTS.md 及当前授权；合入见 branch-manager R8。
- 分支命名遵循项目约定，本文统一用 `<branch>` 占位。

## 三种工作模式

| 模式 | 适用场景 | 特点 |
|---|---|---|
| **fork 集成主线** | 有自动评审服务把关 fork PR 的个人/团队 | 特性 PR 先落 fork main（过评审门禁），定期批量 PR 到 upstream |
| **持续集成分支** | 中大型功能、多特性打包交付但无 fork PR 评审 | fork 上养长生命周期分支，持续合 upstream，完成后一次性 PR |
| **逐特性分支** | 小修复、独立小功能 | 每个特性切短分支，直接 PR upstream，合完删 |

---

## 模式〇：fork 集成主线 + 双阶段 PR

### 核心思想

特性 PR 先进入 fork main。项目已有评审服务时，按该服务核对当前候选的评审、CI 与正式审批。维护者决定何时从 fork main 批量交付到 upstream。

### 拓扑

```
upstream/main ──(按项目同步)──► fork/main ──(定期批量 PR，人手动)──► upstream/main
                                    ▲
                                    │ 特性 PR（base=fork main）+ 项目评审门禁
                              qin/<特性>  codex/<特性>
```

### 流程

1. **切分支**：`git checkout -b qin/<主题> origin/main`（基于最新 fork main）
2. **开发 + 本地基础检视**（typecheck/单测/自查）→ push 到 fork
3. **开 PR：base 必须选自己 fork 的 main**——Gitea 建 PR 时默认建议 upstream，
   要在 base 下拉里手动切到 `<你的用户名>/<仓库名>` 的 `main`
4. **评审与复验**：阅读项目评审全文并按问题追加修复，推送后确认最新结论与当前 head 匹配。适用时按 [QEDAReview 使用前同步](../../../orchestration/auto-code-generator/references/qedareview-local-verification.md#使用前同步)更新工具，显式指定目标仓库，确认上下文属于当前 PR。
5. **合入 fork main**：按 [PR 收敛与合入状态](pr-records.md#评审发布与合入状态)核对门禁，等待维护者确认。
6. **批量出口**：维护者决定建立 fork main → upstream 的 PR。按上游门禁重新验证。
7. **同步基线**：按项目约定更新 fork main。已有同步任务时复用，周期安排按用户授权。

---

## 模式一：持续集成分支

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

同步频率按实际分支推进情况与项目约定确定。周期自动同步需明确授权，适用的冲突、验证和推送门禁照常执行。

#### ③ 阶段性子任务（可选）

集成分支上可以用临时分支隔离实验性改动：

```bash
git checkout -b <临时分支> <集成分支>
# 实验...
# 成功且获准合入 → 合回集成分支
git checkout <集成分支> && git merge <临时分支>
# 清理前按 branch-manager 的分支清理与工作树规则核对
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

确认上游已合入且集成分支无待交付改动。项目允许继续复用时按当前基线同步；清理或创建下一条分支按 branch-manager 的分支管理流程执行。出现分叉时先核对两边提交与上游合并方式。

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
# 评审 → 修改 → 经维护者确认合入
# 合入后的清理由 branch-manager 的分支清理流程处理
```

### 注意

如果同时有多个小 PR 排队合入，会遇到级联同步问题——此时应回到模式一。

---

## 公共规则（三种模式通用）

### 同步 PR 基线与推送前检查

对已开的 PR，先用 [PR 修改前状态确认](../SKILL.md#pr-修改前状态确认)核对平台实际目标仓库、分支和提交。已有同步授权时按项目规则合并目标基线，验证冲突影响范围后再推送。提交前审查按项目已选模式执行，项目原生验证按 [本地验证入口](../../../orchestration/auto-code-generator/references/pre-pr-local-verification.md)执行。

### 冲突解决原则

| 冲突类型 | 处理方式 |
|---|---|
| 追加型（两侧各加一节） | 双方保留，删标记行 |
| 重构型（变量改名/结构变化） | 把功能重放到新结构上 |
| 语义型（合并后测试仍挂） | 两侧意图叠加 |

通用方法：`git show <sha>:<file>` 看原文 → 理解意图 → 合成 → 测试验证。

### 常见故障与恢复

| 故障 | 症状 | 恢复 |
|---|---|---|
| 基线偏离太久 | 一次 merge 冲突 50+ 处 | 增加同步频率；或考虑重放（cherry-pick 核心提交到新分支） |
| GCM JWT 过期 | push 认证失败 | 用固定令牌（~/.gitea-token） |
| CI 作业失败 | 本地复跑与远端结果不一致 | 读原作业日志，按 [CI 失败与重跑](pr-records.md#ci-失败与重跑)处理 |
| 集成分支积累太多无关改动 | PR diff 巨大，评审困难 | 用临时分支拆分，分批 PR |

---

## Fork 定期维护

定期核对 fork 分支。清理前确认分支所有者、活动 PR 和远端引用，按项目授权执行。
