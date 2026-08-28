# 核心规则

## 强制规则

| 规则 | 内容 |
|------|------|
| R0 | **测试驱动开发 (TDD)** — 新功能和 Bug 修复必须遵循红→绿→重构循环，不可跳过 |
| R1 | **提交前审查选择门禁** — 用户请求提交且未明确模式时，由 `code-review-before-commit` 只询问一次 `1. 快速 / 2. 不做 / 3. 全量`；不得自动开启 `code-review`。快速模式仅以 P0 阻止提交，不做模式明确跳过审查，全量模式须将 P0/P1 清零 |
| R2 | **如无必要勿增实体** — 优先复用现有代码和模块，不创建任务未要求的文件、抽象层或依赖 |
| R3 | **先想清楚再做** — 编码前必须理解需求、设计思路和影响范围 |
| R4 | **高内聚低耦合** — 模块内部紧密相关，模块之间依赖最小化 |
| R7 | **节省token** 简单任务优先并行使用luna,更便宜更高效 |
| R8 | **编码规范** — 所有编码须遵守 `coding-standards` 通用核心条款（错误处理/外部数据防御/安全红线/行为验证等）；检视时由 `code-review` 全局审查项统一核对，语言细则以 lang-* 为准 |
| R9 | **Skill 全程实载** — 执行任务引用到 skill 时，必须完整加载其 SKILL.md（按其中指示按需加载 references/scripts 等附属文件），不得凭记忆、只加载摘要或部分步骤执行；执行过程中出现没有把握、需要推测的步骤时，先回到对应 skill 查阅是否已有相关指导，确认无指导再自行处理，禁止跳过 skill 指导自创流程 |

## 默认 Git 安全建议

以下规则默认生效，但用户在当前任务中明确要求时可以覆盖：

| 规则 | 内容 |
|------|------|
| R5 | **主干分支保护** — 默认不在 `main`/`master` 上直接 commit 或合入；用户明确要求时，可在确认目标分支和提交范围后执行 |
| R6 | **安全强制推送** — 默认不使用 `git push --force`；用户明确授权强制推送时优先使用 `--force-with-lease`，只有用户明确指定 `--force` 时才执行 |

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

## Skill 领域路由

统一路由层级：`AGENTS.md → 领域模块 → 具体 Skill`。

全仓领域注册表的唯一权威源是根目录 `skill-domain-mapping.yaml`。`AGENTS.md` 只引用该表，
不维护领域或叶子 Skill 清单；新增、移动 Skill 时无需修改本文件。

路由约束：

- 先读取 `skill-domain-mapping.yaml` 选择一级领域入口。
- 进入领域模块后，再读取该模块的权威映射并选择一个主 Skill。
- 用户显式指定具体 Skill 时直接服从，不经过领域推荐覆盖。
- 元技能、独立工具和跨域编排均通过各自父域路由，仓库顶层不暴露叶子 Skill。

---

# 工程约定

## Git 约定

- **分支命名** — 新功能 `feat/<name>`，修复 `fix/<name>`，重构 `refactor/<name>`；Codex 自动分支使用 `codex/<name>`
- **提交信息** — conventional commit 格式：`<type>(<scope>): <description>`
- **提交前** — 进入 `code-review-before-commit` 选择门禁；未指定时只询问一次 `1. 快速 / 2. 不做 / 3. 全量`，按所选模式执行，不得自动开启审查
- **合入主干** — 默认由人工完成；用户在当前任务中明确要求时，agent 可在确认分支、提交范围和远端后执行
- **换行符** — 不改变文件既有换行风格；读取文件时 Python 使用默认 `newline=''`

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
