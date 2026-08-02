---
name: agents-sync
description: >
  检查并同步全局 agent 指令文件（Codex、Claude Code、OpenCode）与权威 AGENTS.md。
  当用户提到"同步 agents""检查 agents""AGENTS.md 更新了""软链接 agents"时触发。
---

# Agents 同步器

## 概述

维护一份权威 `AGENTS.md`（位于 ``<skill-dir>/../AGENTS.md`（即 .cc-switch/skills/AGENTS.md）`），通过符号链接注入到各 agent 工具的全局配置中。当权威文件更新后，检查所有目标是否同步，未同步则自动修复。

## 铁律

| 规则 | 内容 |
|------|------|
| R0 | **符号链接优先** — 优先创建符号链接而非复制文件；仅当权限不足时降级为复制 |

## 前置条件

- 权威 AGENTS.md 存在于 `.cc-switch/skills/AGENTS.md`
- 目标路径的父目录已存在
- Windows 上创建符号链接需要管理员权限（若无则降级为文件复制）

## 目标路径

自动检测规则（按优先级）：

| Agent 工具 | 检测方式 | 目标文件名 |
|-----------|---------|--------|
| Codex | 固定路径 `$env:USERPROFILE\.codex\` | `AGENTS.md` |
| Claude Code | 检测 `$env:USERPROFILE\CLAUDE.md` 或 `$env:USERPROFILE\.claude\CLAUDE.md`（优先已存在的路径） | `CLAUDE.md` |
| OpenCode | 检测 `$env:USERPROFILE\.opencode\`（目录存在则同步） | `AGENTS.md` |

## "未同步"判定标准

| 状态 | 条件 | 处理方式 |
|------|------|---------|
| ✅ 已同步 | 符号链接指向权威源 | 无需操作 |
| ⚠️ 内容过期 | 非符号链接，且内容与权威源不一致 | 删除旧文件 → 创建符号链接 |
| ❌ 缺失 | 目标文件不存在（但父目录存在） | 直接创建符号链接 |
| ⊘ 跳过 | 父目录不存在（该 agent 未安装） | 跳过，不报错 |

## 工作流

### 步骤 1：确认权威源

读取 ``$PSScriptRoot/../AGENTS.md`（从 skill 自身位置向上推导）`，记录内容哈希和修改时间。若源不存在则报错退出。

### 步骤 2：遍历目标并检查

对每个目标：

```powershell
$target = "<目标路径>"
$source = "$PSScriptRoot/../AGENTS.md"

# 检查父目录是否存在
$parent = Split-Path $target -Parent
if (-not (Test-Path $parent)) { return "skip" }

# 检查目标文件
if (Test-Path $target) {
    $item = Get-Item $target -Force -ErrorAction Stop
    if ($item.LinkType -eq "SymbolicLink" -and $item.Target -eq $source) {
        return "ok"
    }
    return "stale"
} else {
    return "missing"
}
```

### 步骤 3：输出状态报告

```
== Agents 同步状态 ==

| Agent       | 路径                                      | 状态   | 说明               |
|-------------|------------------------------------------|--------|-------------------|
| Codex       | ~\.codex\AGENTS.md                     | ✅     | 符号链接已指向源    |
| Claude Code | ~\CLAUDE.md                             | ⚠️    | 内容不一致，需更新  |
| OpenCode    | ~\.opencode\AGENTS.md                  | ⊘     | 目录不存在，跳过    |
```

### 步骤 4：自动修复

仅处理 ⚠️ 和 ❌ 状态：

```powershell
# 1. 删除旧文件（⚠️ 状态）
Remove-Item $target -Force -ErrorAction SilentlyContinue

# 2. 尝试创建符号链接
try {
    New-Item -ItemType SymbolicLink -Path $target -Target $source -Force -ErrorAction Stop
    Write-Host "  ✅ 符号链接已创建"
} catch {
    # 3. 降级：复制文件内容
    Copy-Item $source $target -Force
    Write-Host "  ⚠️ 符号链接失败，已降级为文件复制（需管理员权限才能创建链接）"
}
```

### 步骤 5：验证

修复后重新运行步骤 2，确认所有非跳过目标均为 ✅。

## 一键执行

每次更新 AGENTS.md 后，运行：

```
Skill: agents-sync
```

即可自动完成检查 + 修复 + 验证全流程。

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 目标父目录不存在 | 跳过该目标（标记 ⊘），不报错 |
| 符号链接创建失败（权限不足） | 降级为文件复制，提示用户手动授权以启用自动同步 |
| 权威源不存在 | 报错退出，提示源文件路径 |
| 目标被占用（文件锁定） | 跳过，标记 ⚠️ 并在报告中注明"文件被锁定" |

---

*版本：1.2*
*最后更新：2026-08-02*
*变更：源路径改为从 skill 自身位置推导（PSScriptRoot），消除硬编码*
