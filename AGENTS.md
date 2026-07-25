# Environment Notes

## Platform: Windows + Git Bash

The host OS is **Windows**, but the shell is configured as **bash** (Git Bash). This creates a hybrid environment where most Unix commands work, but there are important differences to be aware of.

## Path Conventions

- Windows native paths use backslashes: `C:\Users\username\project`
- Git Bash paths use forward slashes: `/c/Users/username/project`
- When passing paths to bash commands, prefer forward-slash format or quote the path
- Windows filesystem is **case-insensitive** but **case-preserving** — avoid relying on case-sensitive path distinctions
- Avoid paths with spaces without quoting; prefer double quotes around paths

## Command Behavior Differences

- `sed`, `awk`, `grep`, `find` etc. are available via Git Bash but may have subtle behavioral differences from GNU/Linux versions
- `which` works in Git Bash; `where` is the native Windows equivalent
- `open` does not exist; use `explorer .` to open a folder in File Explorer, or `start` to open files with default programs
- `pbcopy`/`pbpaste` do not exist; use `clip` and `powershell Get-Clipboard` as alternatives
- `realpath` may not be available; use `readlink -f` or `cygpath -w`/`cygpath -u` for path conversion
- Symbolic links require elevated privileges or Developer Mode enabled; prefer junctions or copies

## Line Endings

- Windows uses CRLF (`\r\n`); Git Bash tools typically output LF (`\n`)
- Git may auto-convert line endings depending on `core.autocrlf` setting
- When editing files, be mindful of mixed line endings

## Process & System Commands

- `ps` in Git Bash shows MSYS2 processes only; use `tasklist` for all Windows processes
- `kill` works for Git Bash processes; use `taskkill /PID <pid> /F` for Windows processes
- Environment variables: in bash use `$VAR` or `${VAR}`, not `%VAR%`
- `echo $PATH` shows bash-style colon-separated paths, not Windows semicolon-separated

## Networking

- `curl` and `ssh` are available via Git Bash
- `netstat`, `ping`, `nslookup` work from both Git Bash and CMD

## File Permissions

- Unix-style `chmod` has limited effect on NTFS; execute permission is determined by file extension (`.exe`, `.bat`, `.cmd`, `.ps1`)
- `chmod +x` on a script without a Windows extension won't make it executable in CMD/PowerShell

## Node.js / npm

- Use `npx` and `npm` from Git Bash as usual
- If Node scripts spawn child processes, they may use CMD by default unless explicitly configured

## Python

- If using Python, prefer `uv run` for virtual environment management as configured
- `python` or `python3` may point to the Windows Python or the Git Bash Python depending on PATH order

## 执行约束原则

1. **严格步骤执行** — 执行 skill 时，必须严格遵循其定义的 phase/step 顺序，不得跳过、合并、调序或提前执行后续步骤。

2. **单步完成制** — 同一时间仅执行一个步骤，完成该步并自我验证通过后，才允许进入下一步。

3. **如无必要勿增实体** — 不创建任务未要求的文件、抽象层、依赖或功能。仅实现明确指定的内容，不做过度设计。

4. **使用中文** — 所有输出、交流、审查记录、日志及代码注释均使用中文。用户的母语是中文，全程保持中文交流。

## 方法论 Skill 体系

本项目内置了一套**方法论 Skill 体系**，由 `method-router` 元 Skill 统一调度。遇到需要诊断分析、决策选型、设计规划、风险评估、总结汇报等任务时，优先经过 method-router 路由，而非直接调用具体方法论 Skill。

### 架构

```
用户请求（"为什么匹配率低""有风险吗""三个方案选哪个"）
    │
    ▼
method-router ──▶ 意图分类（diagnose/decide/design/improve/risk/report）
    │
    ├── 路由到单个 Skill（如 5W2H）
    ├── 编排 Skill 链（如 5W2H → SCQA）
    └── 降级为手动引导（Skill 缺失时）
```

### 已有 Skill

| Skill | 类别 | 用途 |
|-------|------|------|
| `method-router` | 元 | 统一路由器，分类 + 编排 |
| `cynefin` | 元 | 问题域判定（Simple/Complicated/Complex/Chaotic） |
| `deep-analysis` (5W2H) | 诊断 | 数据驱动的深度根因分析 |
| `5whys` | 诊断 | 逻辑追问式根因定位 |
| `ooda-loop` | 诊断 | 快速闭环，线上故障应急响应 |
| `scqa` | 报告 | 情境→冲突→问题→答案叙事框架 |
| `pre-mortem` | 风险 | 事前验尸，反向推导失败原因 |
| `first-principles` | 设计 | 第一性原理，从零重建方案 |
| `eisenhower-matrix` | 决策 | 紧急×重要四象限优先级 |
| `mece` | 分析 | 结构化穷举检查 |
| `dmaic` | 改进 | 数据驱动的六西格玛改进 |
| `fmea` | 风险 | 失效模式与影响分析 |
| `star` | 报告 | 情境→任务→行动→结果叙事 |
| `pdca-tuning` | 改进 | PDCA 循环流程优化 |

### 触发规则

- **用户显式指定 > 路由推荐**：用户说"用 5W2H 分析"则跳过路由器直接执行
- **置信度 < 70% 时降级**：不确定时展示选项让用户选，不猜测
- **紧急场景跳过确认**：线上故障/用户投诉等直接执行最短路径
- **输出统一用 SCQA 模板**：情境→冲突→问题→答案


# 全局规则

对话时尽量使用中文回答。

## 注意事项

- 不要使用 emoji 字符

- 下载时优先使用国内镜像加速

## 强制规则

- **先想清楚再做**: 编码前必须理解需求、设计思路和影响范围，避免盲目动手。

- **测试驱动开发 (TDD)**: 所有新功能和 Bug 修复必须遵循红绿循环：
  1. **红**: 先编写失败的测试
  2. **绿**: 编写最小实现使测试通过
  3. **重构**: 在测试保护下优化代码

- **如无必要勿增实体**: 优先复用现有代码和模块，避免过度设计和不必要的抽象。

- **高内聚低耦合**: 模块内部紧密相关，模块之间依赖最小化。

- **代码质量门禁**: 提交前必须通过 code-review skill 审查