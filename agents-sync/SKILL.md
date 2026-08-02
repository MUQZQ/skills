---
name: agents-sync
description: >
  检查并同步全局 agent 指令文件（Codex、Claude Code、OpenCode）与权威 AGENTS.md。
  当用户提到"同步 agents""检查 agents""AGENTS.md 更新了""软链接 agents"时触发。
---

# Agents 同步器

## 概述

维护一份权威 `AGENTS.md`（位于 `C:\Users\Admin\.cc-switch\skills\AGENTS.md`），通过符号链接注入到各 agent 工具的全局配置中。当权威文件更新后，检查所有目标是否同步，未同步则自动修复。

## 前置条件

- 权威 AGENTS.md 存在于 `.cc-switch/skills/AGENTS.md`
- 目标路径的父目录已存在
- Windows 上创建符号链接可能需要管理员权限

## 目标路径

| Agent 工具 | 目标路径 | 文件名 |
|-----------|---------|--------|
| Codex | `C:\Users\Admin\.codex\` | `AGENTS.md` |
| Claude Code | `C:\Users\Admin\` (或 `%USERPROFILE%\.claude\`) | `CLAUDE.md` |
| OpenCode | `%USERPROFILE%\.opencode\` | `AGENTS.md` |

## 工作流

### 步骤 1：读取权威源

读取 `C:\Users\Admin\.cc-switch\skills\AGENTS.md`，获取最新内容和修改时间。

### 步骤 2：检查所有目标

对每个目标路径，依次检查：

```
1. 目标文件是否存在
2. 是否为符号链接（Windows: 检查 LinkType）
3. 符号链接是否指向权威源
4. 若不是链接：内容是否与权威源一致
```

Windows 检测命令：
```powershell
Get-Item <target> | Select-Object LinkType, Target
```

### 步骤 3：同步状态报告

```
== Agents 同步状态 ==

| Agent | 路径 | 状态 | 说明 |
|-------|------|------|------|
| Codex | C:\Users\Admin\.codex\AGENTS.md | ✅ | 符号链接已指向源 |
| Claude Code | C:\Users\Admin\CLAUDE.md | ❌ | 缺少文件 |
| OpenCode | C:\Users\Admin\.opencode\AGENTS.md | ⚠️ | 内容不一致 |
```

### 步骤 4：自动修复

对未同步的目标，按优先级修复：

1. **优先创建符号链接**（推荐，自动同步）
2. 若符号链接失败（权限不足），则复制文件内容

创建符号链接：
```powershell
# 删除旧文件（如有）
Remove-Item "<target>" -Force -ErrorAction SilentlyContinue
# 创建符号链接
New-Item -ItemType SymbolicLink -Path "<target>" -Target "C:\Users\Admin\.cc-switch\skills\AGENTS.md" -Force
```

**Claude Code 特殊处理**：Claude Code 读取 `CLAUDE.md`（非 `AGENTS.md`），但文件名不同。仍需创建指向 `AGENTS.md` 的符号链接，让 Claude Code 通过链接名 `CLAUDE.md` 读取权威内容。

### 步骤 5：最终确认

修复后重新运行步骤 2，确认全部 ✅。

## 自动触发

- 每次 `AGENTS.md` 提交后，可手动或通过 hook 触发同步
- 定期检查（建议每次启动 Codex 时运行一次）

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 目标父目录不存在 | 自动创建父目录后重试 |
| 符号链接创建失败（权限） | 降级为文件复制，并提示用户手动授权 |
| 权威源不存在 | 报错退出，提示源文件路径 |
| 目标被占用（文件锁定） | 跳过，标记为 ⚠️ 待处理 |

---

*版本：1.0*
*最后更新：2026-08-02*
