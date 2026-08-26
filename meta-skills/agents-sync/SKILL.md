---
name: agents-sync
description: >
  检查并同步全局 agent 指令文件（Codex、Claude Code、OpenCode）与权威 AGENTS.md，
  以及 skill 目录与权威源 .cc-switch/skills 的 Junction 链接。
  当用户提到"同步 agents""检查 agents""AGENTS.md 更新了""软链接 agents""同步 skills""同步 skill"时触发。
---

# Agents 同步器

## 概述

维护权威 `AGENTS.md`（位于 ``<skill-dir>/../../AGENTS.md`（即 .cc-switch/skills/AGENTS.md）`）与权威
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
只为根注册表中的一级领域 Skill 创建 Junction。领域子 Skill 通过父 Skill Junction 的目录树发现，不创建顶层叶子别名。

## "未同步"判定标准

### 指令文件

| 状态 | 条件 | 处理方式 |
|------|------|---------|
| ✅ 已同步 | 符号链接指向权威源，或硬链接/普通副本内容与权威源一致 | 无需操作 |
| ⚠️ 内容过期 | 普通文件，且内容与权威源不一致 | 备份旧文件 → 创建符号链接，失败时恢复 |
| ⛔ 外部链接 | 符号链接指向其他位置 | 停止并报告，禁止自动覆盖 |
| ❌ 缺失 | 目标文件不存在（但父目录存在） | 直接创建符号链接 |
| ⊘ 跳过 | 父目录不存在（该 agent 未安装） | 跳过，不报错 |

### Skill 目录

| 状态 | 条件 | 处理方式 |
|------|------|---------|
| ✅ 已同步 | Junction 指向权威源 `<skill-dir>` | 无需操作 |
| ⚠️ 受管 Junction 失效 | Junction 指向本仓库但目标不是当前权威源 | 备份旧 Junction → 创建 Junction，失败时恢复 |
| ⛔ 路径冲突 | 普通目录、普通文件或指向其他位置的链接 | 停止并报告，禁止自动删除或覆盖 |
| ❌ 缺失 | 目标 skill 目录不存在 | 直接创建 Junction |

## 工作流

### 步骤 1：确认权威源

由调用方传入当前 `agents-sync` Skill 目录的绝对路径。若其父域是 Junction，先读取父域 Junction
的目标再解析权威 skill 根目录；直接从权威仓库调用时才向上两级解析。禁止依赖交互式 PowerShell
中可能为空的 `<绝对路径>\meta-skills\agents-sync`。若源不存在或解析结果越界则报错退出。

```powershell
$agentSyncDir = (Resolve-Path -LiteralPath "<绝对路径>\meta-skills\agents-sync").Path
$domainEntryPath = Split-Path $agentSyncDir -Parent
$domainEntry = Get-Item -LiteralPath $domainEntryPath -Force -ErrorAction Stop
if ($domainEntry.LinkType -eq "Junction") {
    $domainSource = [IO.Path]::GetFullPath(@($domainEntry.Target)[0])
    $srcRoot = [IO.Path]::GetFullPath((Split-Path $domainSource -Parent))
} else {
    $srcRoot = [IO.Path]::GetFullPath((Join-Path $agentSyncDir "../.."))
}
$targets = @(
    "$env:USERPROFILE\.config\opencode\skills",
    "$env:USERPROFILE\.codex\skills",
    "$env:USERPROFILE\.claude\skills"
)
```

### 步骤 2：检查指令文件目标

对每个指令文件目标，以及三个消费者 skills 根目录下的 `skill-domain-mapping.yaml` 目标执行同一
套安全文件同步。注册表源为 `$srcRoot\skill-domain-mapping.yaml`，目标分别为
`<consumer-skills>\skill-domain-mapping.yaml`：

```powershell
$fileSyncPairs = @(
    [pscustomobject]@{ Source = (Join-Path $srcRoot "AGENTS.md"); Target = "<Codex AGENTS.md>" },
    [pscustomobject]@{ Source = (Join-Path $srcRoot "AGENTS.md"); Target = "<Claude CLAUDE.md>" },
    [pscustomobject]@{ Source = (Join-Path $srcRoot "AGENTS.md"); Target = "<OpenCode AGENTS.md>" }
)
foreach ($consumerRoot in $targets) {
    $fileSyncPairs += [pscustomobject]@{
        Source = (Join-Path $srcRoot "skill-domain-mapping.yaml")
        Target = (Join-Path $consumerRoot "skill-domain-mapping.yaml")
    }
}

$pair = "<当前 source-target 对>"
$target = [IO.Path]::GetFullPath($pair.Target)
$source = (Resolve-Path -LiteralPath $pair.Source).Path
$managedFileTargets = @($fileSyncPairs.Target | ForEach-Object { [IO.Path]::GetFullPath($_) })
if ($managedFileTargets -notcontains $target) {
    throw "目标不在受管文件白名单: $target"
}

$parent = Split-Path $target -Parent
if (-not (Test-Path $parent)) { return "skip" }

$item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
if ($null -ne $item) {
    $resolvedTarget = @($item.Target) | ForEach-Object { [IO.Path]::GetFullPath($_) }
    if ($item.LinkType -eq "SymbolicLink") {
        if ($resolvedTarget -contains $source) { return "ok" }
        return "conflict"
    }
    if ($item.PSIsContainer -or ($null -ne $item.LinkType -and $item.LinkType -ne "HardLink")) {
        return "conflict"
    }
    if ((Get-FileHash -LiteralPath $target).Hash -eq (Get-FileHash -LiteralPath $source).Hash) {
        return "ok"
    }
    return "stale"
} else {
    return "missing"
}
```

### 步骤 3：检查 skill 目录目标

读取根注册表中的一级领域名称，对每个目标 skills 目录逐一检查。禁止通过文件系统扫描扩大准入范围：

```powershell
$registryPath = Join-Path $srcRoot "skill-domain-mapping.yaml"
$registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skills = @($registry.domains.PSObject.Properties.Name)

foreach ($t in $targets) {
    if (-not (Test-Path $t)) { continue }
    foreach ($name in $skills) {
        $target = Join-Path $t $name
        $source = Join-Path $srcRoot $name
        $item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
        if ($null -ne $item) {
            $resolvedTarget = @($item.Target) | ForEach-Object { [IO.Path]::GetFullPath($_) }
            if ($item.LinkType -eq "Junction" -and $resolvedTarget -contains ([IO.Path]::GetFullPath($source))) {
                # ok
            } elseif ($item.LinkType -eq "Junction" -and ($resolvedTarget | Where-Object {
                $_.StartsWith($srcRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
            })) {
                # stale-managed：受管旧 Junction，可进入备份重建
            } else {
                # 普通目录或非受管链接：停止并报告，禁止覆盖
            }
        } else {
            # missing：创建 Junction
        }
    }
}
```

检查目标根目录中的其他条目时，只允许把“名称不在 `$skills` 且 Junction 目标位于 `$srcRoot` 内”的
旧顶层叶子别名标记为受管遗留项并移入备份；普通目录、普通文件、外部链接和 `.system` 等非受管条目
一律保留并报告，不得删除或覆盖。

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
| claude   | independent-tools | 缺失 | 创建父域 Junction       |
```

### 步骤 5：自动修复

仅处理 ⚠️ 和 ❌ 状态。

指令文件修复（文件符号链接）：

```powershell
$backupRoot = Join-Path $env:TEMP "agents-sync-backup"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backup = Join-Path $backupRoot ("instruction-" + [Guid]::NewGuid().ToString("N"))

 $item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
if ($null -ne $item) {
    if ($managedFileTargets -notcontains [IO.Path]::GetFullPath($target)) {
        throw "目标不在受管文件白名单: $target"
    }
    if ($item.PSIsContainer -or ($null -ne $item.LinkType -and $item.LinkType -ne "HardLink")) {
        throw "目标不是普通文件或受管 HardLink，拒绝自动替换: $target"
    }
    Move-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
}

try {
    New-Item -ItemType SymbolicLink -Path $target -Target $source -ErrorAction Stop | Out-Null
} catch {
    try {
        New-Item -ItemType HardLink -Path $target -Target $source -ErrorAction Stop | Out-Null
    } catch {
        try {
            Copy-Item -LiteralPath $source -Destination $target -ErrorAction Stop
        } catch {
            if (Test-Path -LiteralPath $backup) {
                Move-Item -LiteralPath $backup -Destination $target -ErrorAction Stop
            }
            throw
        }
    }
}
```

Skill 目录修复（Junction 无需管理员权限）：

```powershell
$allowedRoots = @($targets | ForEach-Object { [IO.Path]::GetFullPath($_) })
$targetFull = [IO.Path]::GetFullPath($target)
$consumerRoot = $allowedRoots | Where-Object {
    [IO.Path]::GetDirectoryName($targetFull).Equals($_, [StringComparison]::OrdinalIgnoreCase)
} | Select-Object -First 1
if (-not $consumerRoot) {
    throw "目标越过允许的 skills 根目录: $targetFull"
}

$backupRoot = Join-Path $env:TEMP "agents-sync-backup"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backupName = "{0}-{1}-{2}-{3}" -f (
    Split-Path $consumerRoot -Leaf
), (Split-Path $target -Leaf), (Get-Date -Format "yyyyMMdd-HHmmssfff"), [Guid]::NewGuid().ToString("N")
$backup = Join-Path $backupRoot $backupName

$item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
if ($null -ne $item) {
    if ($item.LinkType -ne "Junction") {
        throw "目标不是受管 Junction，拒绝自动替换: $target"
    }
    $resolvedTarget = @($item.Target) | ForEach-Object { [IO.Path]::GetFullPath($_) }
    if (-not ($resolvedTarget | Where-Object { $_.StartsWith($srcRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) })) {
        throw "Junction 不指向本仓库，拒绝自动替换: $target"
    }
    Move-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
}

try {
    New-Item -ItemType Junction -Path $target -Target $source -ErrorAction Stop | Out-Null
    Write-Host "Junction 已创建"
} catch {
    if (Test-Path -LiteralPath $backup) {
        Move-Item -LiteralPath $backup -Destination $target -ErrorAction Stop
    }
    throw
}
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
| Skill Junction 创建失败 | 从备份恢复原 Junction 并报告错误，不静默降级为拷贝 |
| 目标是普通目录、文件或外部链接 | 停止并报告，禁止删除、覆盖或递归移动 |
| 权威源不存在 | 报错退出，提示源文件路径 |
| 目标被占用（文件锁定） | 跳过，标记 ⚠️ 并在报告中注明"文件被锁定" |

---

*版本：2.0*
*最后更新：2026-08-17*
*变更：新增 skill 目录 Junction 同步方法（枚举权威源顶层含 SKILL.md 的目录，向 OpenCode/Codex/Claude 三组 skills 目录建立或替换 Junction）；Junction 目标比较使用 Target 数组 join；区分指令文件符号链接与 skill 目录 Junction 的权限要求。*
