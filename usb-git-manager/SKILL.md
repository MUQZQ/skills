---
name: usb-git-manager
description: 本地硬盘与 U 盘之间的 git 仓库双向同步。当用户提到"推到 U 盘"、"从 U 盘拉代码"、"U 盘同步"、"usb git"、"U盘备份"、"U盘git"时必须使用。处理 FAT32/exFAT 文件系统的 safe.directory 权限问题，支持裸仓库和非裸仓库两种模式。
---

# USB Git Manager

本地和 U 盘之间的 git 代码同步工具。U 盘文件系统（FAT32/exFAT）不记录文件 owner，git push 会被 safe.directory 安全检查拦截；直接用非裸仓库 push 会失败。

## 场景路由

| 用户意图 | 操作 |
|---------|------|
| 首次设置 U 盘仓库 | 初始化裸仓库 |
| Push 到 U 盘（已有裸仓库） | 直接 push |
| Push 到 U 盘（非裸仓库） | bundle + fetch |
| 从 U 盘拉取 | remote fetch |
| 从 U 盘克隆到新机器 | clone / bundle unbundle |

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|:------:|
| R0 | 非裸仓库用 git bundle，禁止 git push | 被 safe.directory 拦截 |
| R1 | 首次使用必须先确认 U 盘路径 | 写到错误位置 |
| R2 | push 前确认分支名，默认用当前分支 | 推错分支 |
| R3 | 操作后验证 commit 历史一致 | 静默失败 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 | 实际后果 |
|---------------------|---------|:------:|---------|
| "git config safe.directory 就能解决" | U 盘文件系统不记录 owner，对 push 内部 spawn 的子进程无效 | R0 | 反复失败 |
| "用 robocopy 直接拷 .git" | 不更新 refs，可能损坏仓库 | R0 | 仓库损坏 |
| "F 盘肯定是 U 盘" | 可能有多个 U 盘或网络驱动器 | R1 | 写到错误位置 |

## 工作流：首次设置裸仓库

1. 确认 U 盘路径（让用户提供或列出可用盘符）
2. 在 U 盘上创建：git init --bare <U盘路径>/<仓库名>.git
3. 回到本地仓库，添加 remote：git remote add usb <U盘路径>/<仓库名>.git
4. 推送：git push usb <分支名>
5. 验证：git log --oneline usb/<分支名> -3

## 工作流：Push 到非裸仓库（bundle 方式）

1. 确认 U 盘仓库路径存在
2. 创建 bundle：git bundle create <U盘路径>/<分支名>.bundle <分支名>
3. 在 U 盘仓库中 fetch：cd <U盘路径> && git fetch <bundle路径> <分支名>:<分支名>
4. 清理 bundle 并验证 commit 历史一致

## 工作流：Push 到裸仓库（直接 push）

git push usb <分支名>

如遇 safe.directory 拦截，尝试 git config --global --add safe.directory "<路径>"，仍失败则降级到 bundle 方式。

## 工作流：从 U 盘拉取

1. git fetch usb <分支名>
2. git merge usb/<分支名>
3. 验证 commit 历史

## 工作流：从 U 盘克隆到新机器

- U 盘上创建 bundle：git bundle create <路径>/repo.bundle --all
- 新机器上克隆：git clone <路径>/repo.bundle <目标目录>
- 或直接克隆裸仓库：git clone <U盘路径>/<仓库名>.git

## 错误处理

| 环节 | 失败条件 | 处理方式 |
|------|---------|---------|
| 首次设置 | U 盘路径不存在 | 请求用户确认 |
| Push | safe.directory 拦截 | 降级到 bundle |
| Push | bundle 创建失败 | 检查 U 盘空间 |
| Fetch | 分支不存在 | 确认分支名 |
| 验证 | commit 不一致 | 重新执行 |

## 输出建议

显示本地和 U 盘的 commit 对比，操作完成后显示同步状态。如果使用 bundle，说明原因。