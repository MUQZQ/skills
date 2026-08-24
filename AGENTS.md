# 核心规则

## 强制规则

| 规则 | 内容 |
|------|------|
| R0 | **测试驱动开发 (TDD)** — 新功能和 Bug 修复必须遵循红→绿→重构循环，不可跳过 |
| R1 | **代码质量门禁** — 提交前必须通过 `code-review` 审查，P0/P1 问题必须清零 |
| R2 | **如无必要勿增实体** — 优先复用现有代码和模块，不创建任务未要求的文件、抽象层或依赖 |
| R3 | **先想清楚再做** — 编码前必须理解需求、设计思路和影响范围 |
| R4 | **高内聚低耦合** — 模块内部紧密相关，模块之间依赖最小化 |
| R5 | **禁止操作主干分支** — 不在 `main`/`master` 上直接 commit；合入由人工完成 |
| R6 | **禁止 force push** — 永远不使用 `git push --force`，rebase 后使用 `--force-with-lease` |
| R7 | **节省token** 简单任务优先并行使用luna,更便宜更高效 |
| R8 | **编码规范** — 所有编码须遵守 `coding-standards` 通用核心条款（错误处理/外部数据防御/安全红线/行为验证等）；检视时由 `code-review` 全局审查项统一核对，语言细则以 lang-* 为准 |

## 执行约束原则

1. **严格步骤执行** — 执行 skill 时必须严格遵循其定义的 phase/step 顺序，不得跳过、合并、调序或提前执行后续步骤。

2. **单步完成制** — 同一时间仅执行一个步骤，完成该步并自我验证通过后，才允许进入下一步。

3. **复杂变更使用自适应编排** — 预估任务数 > 5、影响模块 > 2，或涉及架构、公共契约、数据迁移、安全与跨组件边界时，优先使用 `auto-code-generator` 做风险路由和实施编排；已有项目权威生命周期时必须服从其实时状态与指令。

## 输出约定

- **语言** — 所有输出、交流、审查记录、日志及代码注释均使用中文

- **换行符** — 编辑文件前读取确认当前行尾风格（LF 或 CRLF）；写入时 `newline=''` 保持原样，不改变文件既有换行风格

- **Emoji** — 不使用 emoji 字符

---

# 工作流 Skill 体系

## 全流程自动化

| Skill | 用途 | 触发 |
|-------|------|------|
| `auto-code-generator` | spec 驱动的自适应实施编排：风险路由→规划/维护视图投影→TDD 实施→审查验证→归档；默认自动使用共享 Sol-Luna provider，Git 动作另行授权 | "自动生成代码""全流程实施""一键实施变更" |

## 共享执行 Provider（非 Skill）
-为了提高执行效率，大任务执行时luna卡槽建议拉满。spawn_agent并发上限是 6 个子subAgent ,已经实际验证过
- Sol-Luna 是 `auto-code-generator` 内部可选执行模式，不是独立 skill 或第二套生命周期；自动编码只有一个用户入口。
- Luna 默认开启并使用 `mode=auto`；有效配置为 `off`，或用户在当前任务明确说“不用 Luna”“只用 Sol”时关闭。当前用户明确要求 Luna 时可单次覆盖 `off`，但不得改写持久配置。
- 委派保持完整内聚场景和同一上下文中的 `RED → GREEN → REFACTOR`；无法保真委派时回退 Sol，不为迁就 provider 切碎 TDD。
- Sol 始终拥有架构决策、任务验收、冲突处理、最终结论及 Git/PR/部署权限；provider 的返回只是待核验执行证据。
- 维护视图投影只服从项目生命周期已经声明的契约；没有契约时不发明投影，结构有效也不能替代语义审查。


## 代码质量

| Skill | 用途 | 触发 |
|-------|------|------|
| `code-review` | 审查路由协调者，按文件类型分派子审查 | 提交前、"review""审查" |
| `coding-standards` | 跨语言通用编码规范（通用核心条款，编码时遵守，检视时全局审查统一核对；子技能 refactor-tdd 重构流程） | "编码规范""按规范写""代码风格""重构""refactor" |
| `code-review-before-commit` | 5 轮审查循环 + 用户确认 + git commit | 提交前审查 |

## 分支与同步

| Skill | 用途 | 触发 |
|-------|------|------|
| `branch-manager` | Git 分支管理工作流 | "创建分支""stash""checkpoint""rebase" |


## 方法论体系

由 `method-router` 元 Skill 统一调度。遇到诊断分析、决策选型、设计规划、风险评估、总结汇报等任务时，优先经过 method-router 路由。

```
用户请求
    │
    ▼
method-router ──▶ 意图分类（diagnose/decide/design/improve/risk/report）
    │
    ├── 路由到单个 Skill
    ├── 编排 Skill 链
    └── 降级为手动引导
```

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
| `star` | 报告 | 情境→任务→行动→结果叙事 |
| `pdca-tuning` | 改进 | PDCA 循环流程优化 |

**触发规则**：
- 用户显式指定 > 路由推荐（用户说"用 5W2H"则直接执行，不经过路由器）
- 置信度 < 70% 时降级，展示选项让用户选择
- 紧急场景（线上故障/用户投诉）跳过确认，直接执行最短路径
- 输出统一使用 SCQA 模板（情境→冲突→问题→答案）

---

# 工程约定

## Git 约定

- **分支命名** — 新功能 `feat/<name>`，修复 `fix/<name>`，重构 `refactor/<name>`；Codex 自动分支使用 `codex/<name>`
- **提交信息** — conventional commit 格式：`<type>(<scope>): <description>`
- **提交前** — 运行 `code-review` 审查；禁止提交未审查的代码
- **合入主干** — 由人工完成，agent 仅做本地提交
- **换行符** — 不改变文件既有换行风格；读取文件时 Python 使用默认 `newline=None`

## 下载约定

- 下载依赖或外部资源时优先使用国内镜像加速

---

# 环境参考

## Platform: Windows + Git Bash

宿主 OS 为 Windows，shell 配置为 bash (Git Bash)。大部分 Unix 命令可用，但存在重要差异。

## Path Conventions

- Windows 原生路径使用反斜杠：`C:\Users\username\project`
- Git Bash 路径使用正斜杠：`/c/Users/username/project`
- 向 bash 命令传路径时优先使用正斜杠格式或加引号
- Windows 文件系统**大小写不敏感**但**保留大小写** — 避免依赖大小写区分路径
- 避免含空格且不加引号的路径；路径优先使用双引号包裹

## Command Behavior Differences

- `sed`、`awk`、`grep`、`find` 等由 Git Bash 提供，但与 GNU/Linux 版本可能存在细微差异
- `which` 在 Git Bash 中可用；`where` 是 Windows 等价命令
- `open` 不存在；使用 `explorer .` 在文件管理器中打开目录，使用 `start` 以默认程序打开文件
- `pbcopy`/`pbpaste` 不存在；使用 `clip` 和 `powershell Get-Clipboard` 替代
- `realpath` 可能不可用；使用 `readlink -f` 或 `cygpath -w`/`cygpath -u` 进行路径转换
- 符号链接需要管理员权限或启用开发者模式；优先使用 junction 或复制

## Line Endings

- Windows 使用 CRLF (`\r\n`)；Git Bash 工具通常输出 LF (`\n`)
- Git 可能根据 `core.autocrlf` 设置自动转换行尾
- 编辑文件时注意避免混合行尾风格

## Process & System Commands

- Git Bash 中的 `ps` 仅显示 MSYS2 进程；使用 `tasklist` 查看所有 Windows 进程
- `kill` 适用于 Git Bash 进程；使用 `taskkill /PID <pid> /F` 终止 Windows 进程
- 环境变量：bash 中使用 `$VAR` 或 `${VAR}`，不使用 `%VAR%`
- `echo $PATH` 显示冒号分隔的 bash 风格路径，非 Windows 分号分隔格式

## Networking

- `curl` 和 `ssh` 由 Git Bash 提供
- `netstat`、`ping`、`nslookup` 在 Git Bash 和 CMD 中均可使用

## File Permissions

- Unix 风格的 `chmod` 在 NTFS 上效果有限；执行权限由文件扩展名决定（`.exe`、`.bat`、`.cmd`、`.ps1`）
- 对无 Windows 扩展名的脚本执行 `chmod +x` 不会使其在 CMD/PowerShell 中可执行

## Node.js / npm

- 在 Git Bash 中正常使用 `npx` 和 `npm`
- 若 Node 脚本创建子进程，默认可能使用 CMD，除非显式配置

## Python

- 优先使用 `uv run` 管理虚拟环境
- `python` 或 `python3` 可能指向 Windows Python 或 Git Bash Python，取决于 PATH 顺序
