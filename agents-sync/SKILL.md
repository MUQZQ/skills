---
name: agents-sync
description: >
  检查并同步全局 agent 指令文件（Codex、Claude Code、OpenCode）与权威 AGENTS.md，
  以及 skill 目录与权威源 .cc-switch/skills 的 Junction 链接。
  当用户提到"同步 agents""检查 agents""AGENTS.md 更新了""软链接 agents""同步 skills""同步 skill"时触发。
---

# Agents 同步器

## 概述

维护权威 `AGENTS.md`（位于 ``<skill-dir>/../AGENTS.md`（即 .cc-switch/skills/AGENTS.md）`）与权威
skill 目录（即 `.cc-switch/skills`）。指令文件通过符号链接注入到各 agent 工具的全局配置；skill 目录
通过 Junction 链接到各 agent 的 skills 目录。当权威内容更新后，检查所有目标是否同步，未同步则自动修复。

## 铁律

| 规则 | 内容 |
|------|------|
| R0 | **链接优先** — 优先创建链接而非复制文件；仅当权限不足时降级为复制 |

## 两种同步类型

| 类型 | 权威源 | 目标 | 链接方式 | 权限要求 |
|------|--------|------|---------|---------|
| 指令文件 | `.cc-switch/skills/AGENTS.md` | 各 agent 全局配置 | 文件符号链接（SymbolicLink） | 需管理员或开发者模式 |
| Skill 目录 | `.cc-switch/skills/<skill>/`（顶层含 `SKILL.md` 的目录） | 各 agent skills 目录 | 目录 Junction | 无需特殊权限 |

## 前置条件

- 权威 AGENTS.md 存在于 `.cc-switch/skills/AGENTS.md`
- 权威 skill 目录存在于 `.cc-switch/skills`，顶层含 `SKILL.md` 的目录视为一个 skill
- 目标路径的父目录已存在
- 指令文件符号链接需要管理员权限（若无则降级为文件复制）；skill 目录使用 Junction，无需特殊权限

## 目标路径

### 指令文件目标

自动检测规则（按优先级）：

| Agent 工具 | 检测方式 | 目标文件名 |
|-----------|---------|--------|
| Codex | 固定路径 `$env:USERPROFILE\.codex\` | `AGENTS.md` |
| Claude Code | 检测 `$env:USERPROFILE\CLAUDE.md` 或 `$env:USERPROFILE\.claude\CLAUDE.md`（优先已存在的路径） | `CLAUDE.md` |
| OpenCode | 检测 `$env:USERPROFILE\.opencode\`（目录存在则同步） | `AGENTS.md` |

### Skill 目录目标

固定三组 skills 目录，目录存在才同步：

| Agent 工具 | 目标目录 |
|-----------|---------|
| OpenCode | `$env:USERPROFILE\.config\opencode\skills` |
| Codex | `$env:USERPROFILE\.codex\skills` |
| Claude Code | `$env:USERPROFILE\.claude\skills` |

注意：目标 skills 目录中不在权威源列表内的条目（如 Codex 的 `.system`）一律保留不动。

## "未同步"判定标准

### 指令文件

| 状态 | 条件 | 处理方式 |
|------|------|---------|
| ✅ 已同步 | 符号链接指向权威源 | 无需操作 |
| ⚠️ 内容过期 | 非符号链接，且内容与权威源不一致 | 删除旧文件 → 创建符号链接 |
| ❌ 缺失 | 目标文件不存在（但父目录存在） | 直接创建符号链接 |
| ⊘ 跳过 | 父目录不存在（该 agent 未安装） | 跳过，不报错 |

### Skill 目录

| 状态 | 条件 | 处理方式 |
|------|------|---------|
| ✅ 已同步 | Junction 指向权威源 `<skill-dir>` | 无需操作 |
| ⚠️ 拷贝或失效链接 | 普通目录拷贝，或 Junction 目标不是权威源 | 删除旧目录 → 创建 Junction |
| ❌ 缺失 | 目标 skill 目录不存在 | 直接创建 Junction |

## 工作流

### 步骤 1：确认权威源

读取 ``$PSScriptRoot/../AGENTS.md` 与权威 skill 根目录（从 skill 自身位置向上推导）。若源不存在则报错退出。

### 步骤 2：检查指令文件目标

对每个指令文件目标：

```powershell
$target = "<目标路径>"
$source = "$PSScriptRoot/../AGENTS.md"

$parent = Split-Path $target -Parent
if (-not (Test-Path $parent)) { return "skip" }

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

### 步骤 3：检查 skill 目录目标

枚举权威源中顶层含 `SKILL.md` 的目录，对每个目标 skills 目录逐一检查：

```powershell
$srcRoot = (Get-Item $PSScriptRoot).Parent.FullName
$targets = @(
    "$env:USERPROFILE\.config\opencode\skills",
    "$env:USERPROFILE\.codex\skills",
    "$env:USERPROFILE\.claude\skills"
)

$skills = Get-ChildItem $srcRoot -Directory -Force |
    Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
    Select-Object -ExpandProperty Name

foreach ($t in $targets) {
    if (-not (Test-Path $t)) { continue }
    foreach ($name in $skills) {
        $target = Join-Path $t $name
        $source = Join-Path $srcRoot $name
        if (Test-Path -LiteralPath $target) {
            $item = Get-Item -LiteralPath $target -Force
            if ($item.LinkType -eq "Junction" -and ($item.Target -join ",") -eq $source) {
                # ok
            } else {
                # replace：删除旧目录 → 创建 Junction
            }
        } else {
            # missing：创建 Junction
        }
    }
}
```

注意：Junction 目标比较使用 `$item.Target -join ","`，因为 PowerShell 中 Target 可能返回数组。

### 步骤 4：输出状态报告

```
== Agents 同步状态 ==

指令文件：
| Agent       | 路径                       | 状态 | 说明                |
|-------------|----------------------------|------|---------------------|
| Codex       | ~\.codex\AGENTS.md         | ✅   | 符号链接已指向源     |
| Claude Code | ~\CLAUDE.md                | ⚠️  | 内容不一致，需更新   |
| OpenCode    | ~\.opencode\AGENTS.md      | ⊘   | 目录不存在，跳过     |

Skill 目录：
| Target   | Skill             | 状态 | 说明                    |
|----------|-------------------|------|-------------------------|
| opencode | method-router     | ✅   | Junction 已指向源       |
| codex    | method-router     | ⚠️  | 普通拷贝，替换为 Junction |
| claude   | bilibili-convert  | ❌   | 缺失，创建 Junction     |
```

### 步骤 5：自动修复

仅处理 ⚠️ 和 ❌ 状态。

指令文件修复（文件符号链接）：

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

Skill 目录修复（Junction 无需管理员权限）：

```powershell
# 1. 删除旧目录（⚠️ 状态，含普通拷贝与失效链接）
Remove-Item -LiteralPath $target -Recurse -Force

# 2. 创建 Junction
New-Item -ItemType Junction -Path $target -Target $source -Force | Out-Null
Write-Host "  ✅ Junction 已创建"
```

### 步骤 6：验证

修复后重新运行步骤 2 与步骤 3，确认所有非跳过目标均为 ✅。

## 一键执行

每次更新 AGENTS.md 或权威 skill 内容后，运行：

```
Skill: agents-sync
```

即可自动完成检查 + 修复 + 验证全流程。

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 目标父目录不存在 | 跳过该目标（标记 ⊘），不报错 |
| 指令文件符号链接创建失败（权限不足） | 降级为文件复制，提示用户手动授权以启用自动同步 |
| Skill Junction 创建失败 | 保留原目录并报告错误，不静默降级为拷贝 |
| 权威源不存在 | 报错退出，提示源文件路径 |
| 目标被占用（文件锁定） | 跳过，标记 ⚠️ 并在报告中注明"文件被锁定" |

---

*版本：2.0*
*最后更新：2026-08-17*
*变更：新增 skill 目录 Junction 同步方法（枚举权威源顶层含 SKILL.md 的目录，向 OpenCode/Codex/Claude 三组 skills 目录建立或替换 Junction）；Junction 目标比较使用 Target 数组 join；区分指令文件符号链接与 skill 目录 Junction 的权限要求。*
