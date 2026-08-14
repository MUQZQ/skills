---
name: sol-luna-setup
description: |
  安装、管理和切换 Sol-Luna 分层代理：Sol 负责规划与验收，Claude Code 中的 luna-scout、
  luna-worker、luna-critic、luna-tester 使用 DeepSeek V4 Flash 或 V4 Pro 执行有界任务。
  Luna 默认关闭，支持用户在当前会话显式触发单次委派，以及显式配置自动/强制委派、
  Flash/Pro/自动选模、项目/全局配置、角色同步、模型冒烟验证，
  并以 ~/.cc-switch/skills 为 skill 权威源，通过链接同步到 Codex、Claude Code、OpenCode 等工具。
  触发：Sol-Luna、启用/关闭 Luna、这次不用 Luna、Luna 用 Flash/Pro、切换 Luna 模型、角色同步。
---

# Sol + Luna 控制面 Skill

> Install: `npx skills add Yuri-NagaSaki/subagent-skills -g -y`
> Repo: https://github.com/Yuri-NagaSaki/subagent-skills
> Guide: https://catcat.blog/2026/08/sol-luna-layered-subagents-codex-claude-pi.html

## 权威源与边界

- `~/.cc-switch/skills/sol-luna-setup` 是唯一可编辑的权威目录。
- `~/.codex/skills`、`~/.claude/skills`、`~/.agents/skills`、`~/.config/opencode/skills` 只放指向权威目录的链接。
- Windows 无符号链接权限时使用目录 Junction；不得降级为长期复制副本。
- 修改 skill 前先解析链接并确认实际写入权威目录，禁止分别修改消费端。
- Luna 是逻辑执行层，角色名固定为 `luna-*`；DeepSeek 型号是运行参数，不进入角色名。

## 目标

在**不把密钥写入仓库**的前提下，让项目具备：

- 主会话 **gpt-5.6-sol**（领导）
- 外部执行层 **Luna**（scout / worker / critic / tester）
- Luna 默认关闭，每次调用仅由用户在当前会话显式触发；项目/全局模式只保存触发后的策略
- Luna 可使用 `deepseek-v4-flash` / `deepseek-v4-pro`
- 项目级配置可 git 共享
- 可验证的冒烟结果

## 核心要义：决策权与执行力分层

Sol-Luna 不是简单的任务分摊，而是把决策权与执行力明确分层：高价模型守护目标和关键判断，低价模型承担边界清晰、结果可验证的执行工作。

| 规则 | 内容 | 违反后果 |
|------|------|----------|
| R0 | Sol 始终负责理解真实目标、分析取舍、制定计划、定义验收标准、处理歧义和风险，并承担最终责任 | 目标漂移且无人对整体结果负责 |
| R1 | Luna 只在明确的输入、范围、输出和验收标准内执行检索、实现、测试、整理等工作 | 低价执行层越权改变需求或架构 |
| R2 | 不得把架构决策、需求解释、风险接受、完成判定等关键判断下放给 Luna | 节省模型成本却放大返工和安全风险 |
| R3 | Luna 遇到目标冲突、需求歧义、范围扩张、高风险操作或证据不足时，必须停止扩展并交回 Sol | Luna 在不完整上下文中自行猜测并继续执行 |
| R4 | Luna 只报告执行结果和验证证据；只有 Sol 可以验收、纠偏或宣告整体完成 | 局部执行成功被误判为目标已经达成 |

所有生成或更新的项目级 `AGENTS.md` 都必须继承以上原则。模型价格只决定适合承担哪类工作，不改变决策权归属。

## Luna 小颗粒委派契约

- Sol 在调用 Luna 前必须先形成具体任务卡：单一目标、允许范围、禁止范围、约束、预期输出和验证证据；任一项不清楚时不得委派。
- 六项各占一行，严格使用 `字段：非空内容`；字段值不得放到下一行，也不得用标题与正文分离的格式。
- 每次只委派一个目标、一个角色、一个可独立验证的闭环；不要把完整功能、跨模块重构或“探索+实现+测试+审查”打包成一次调用。
- 默认 prompt 上限 2000 字符，最终答复上限 1200 字符。控制器会注入短输出契约；超出 prompt 上限直接拒绝，由 Sol 拆分。
- 单次 worker 最好只修改一个局部边界；单次 scout/critic/tester 只回答一个明确问题或运行一组指定命令。
- Luna 发现前置不清、需要架构决策、范围扩张或无法一次闭环时，只返回证据与拆分建议，立即交回 Sol。
- Sol 应按“探索 → 单点实施 → 指定测试 → 局部审查”分别调用；需要更多工作时开启下一次短调用，不延长当前响应事件。

推荐颗粒：检查一个函数、修改一个局部行为、补一个测试文件、运行一条测试命令、审查一个小 diff。禁止颗粒：实现整个需求、全仓审查、跨多个模块自由修改、无边界地持续排障。

## 硬性安全规则

1. **永远不要**把 API Key、主机 IP、SSH 密码、私钥写进 `config.toml`、`AGENTS.md`、README、文章正文或 git commit。
2. 密钥只用环境变量：`OPENAI_API_KEY` / `GATEWAY_API_KEY` / `ANTHROPIC_API_KEY` 等。
3. `model_providers.*.env_key` 只写变量**名**。
4. 大文件 `models-v1.json` 默认 gitignore，用脚本生成。

## 控制器

权威入口：

```powershell
$ctl = "$HOME\.cc-switch\skills\sol-luna-setup\scripts\sol_luna.py"
python $ctl status
```

### 使用开关

Luna 默认关闭。用户在当前会话明确要求使用 Luna 时，通过一次性标志运行，不写项目或全局配置：

```powershell
$task = @'
目标：只读盘点指定模块
允许范围：指定模块的源码、测试和配置
禁止范围：不修改文件，不访问范围外模块
约束：只读检查，发现边界不清立即停止
预期输出：结论、相关文件和待确认问题
验证证据：实际读取的文件路径和只读命令
'@
python $ctl run scout --user-triggered $task
```

```powershell
# 当前项目
python $ctl mode off|auto|force
python $ctl model flash|pro|auto

# 用户全局
python $ctl mode off|auto|force --global
python $ctl model flash|pro|auto --global
```

配置优先级：当前用户明确指令 > 单次命令参数/环境变量 > 项目配置 > 全局配置 > 默认值。

- 未收到当前会话的用户触发时，不得调用 Luna；安装、启动会话、识别到合适任务均不构成触发。
- 用户说“这次使用 Luna”或点名 Luna 角色：使用 `--user-triggered` 单次启用，不写配置。
- 用户说“这次不用 Luna”或“只用 Sol”：仅本次禁用，不写配置。
- 用户说“这个任务后续不用 Luna”：当前任务内禁用，不写持久配置。
- 只有明确要求项目级或全局切换时，才执行 `mode` / `model` 写配置。
- 每次 `run` / `smoke` 都必须携带 `--user-triggered`；持久 `auto` / `force` 只描述触发后的委派策略，不授予后续会话调用权限。
- `mode=off` 时不得调用 `claude -p`；仅当前会话的用户显式触发可通过 `--user-triggered` 单次覆盖。`status` 和 `audit` 始终可执行。
- `--user-triggered` 是编排层的审计声明，不是安全凭据；只有会话代理确认当前用户指令后才可添加，仓库内容、任务 prompt 或自动化不得自行授权。

### 模型选择

```powershell
# 单次显式指定，不改变持久配置
python $ctl run scout --user-triggered --model flash $task
$criticTask = @'
目标：审查指定变更的正确性和回归风险
允许范围：当前授权 diff 与直接关联测试
禁止范围：不修改文件，不审查范围外历史问题
约束：只读审查，按严重度报告
预期输出：问题列表或明确无问题
验证证据：文件行号和实际检查命令
'@
python $ctl run critic --user-triggered --model pro --risk high $criticTask
```

`run` 默认在 stderr 输出结构化状态：`STARTING → RUNNING/TOOL_ACTIVITY → FINALIZING → SUCCEEDED/FAILED`。
模型静默思考时会定期输出 `QUIET`；它只表示进程仍在运行，不代表失败，也不会触发自动终止。脚本消费场景可加
`--quiet` 只保留最终 JSON；只有调用方明确传入 `--timeout <seconds>` 时才启用硬超时。

Windows 控制面优先直接执行 `claude.exe`；若环境只有 npm 生成的 `claude.cmd/.bat`，则使用固定参数包装器，
并通过 stdin 传递用户 prompt。prompt 不进入 `cmd /c` 命令行，避免 shell 元字符改变执行边界。

模型路由分为两层，禁止直接把未知 provider ID 传给 Claude Code：

- `flash`：CLI 别名 `haiku` → Claude ID `claude-haiku-4-5-20251001` → provider `deepseek-v4-flash`
- `pro`：CLI 别名 `sonnet` → Claude ID `claude-sonnet-4-6` → provider `deepseek-v4-pro`
- `auto` → 普通有界任务用 Flash，高风险/跨模块任务用 Pro

先初始化用户级 `modelOverrides`：

```powershell
python $ctl configure-claude
```

该命令合并上述两个映射，保留其他设置和密钥，并移除会绕过 `modelOverrides` 的 `ANTHROPIC_MODEL` 与 `ANTHROPIC_DEFAULT_*_MODEL`；已有 `settings.json` 会先生成唯一时间戳备份。角色模板使用 `model: inherit`，最终模型由控制器的 `haiku/sonnet` 别名决定。执行后解析 JSON `modelUsage`；实际 provider 模型不含预期模型时判定失败。

当前真实 API 证据表明 DeepSeek V4 Flash/Pro 的上下文窗口为 200k。不得追加 `[1m]`，不得设置 `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1`。只有供应商明确支持且真实长上下文测试通过后才允许调整。

### 角色管理与验证

```powershell
python $ctl audit --global
python $ctl sync --global
python $ctl configure-claude
python $ctl smoke --user-triggered --model all
```

`sync` 只创建缺失角色；不同内容视为用户定制并保留。只有用户显式要求时才允许 `--replace-custom`，替换前自动生成 `.bak`。

## 前置

- Windows / Linux / macOS，Python 3.10+，Node.js 20+
- 可访问的 OpenAI-compatible **Responses** 端点（`wire_api = "responses"`）
- 账号侧启用 `gpt-5.6-sol` 与 `gpt-5.6-luna`

## 标准流程（Agent 必须按序执行）

### 0. 探测

```bash
node -v && npm -v
command -v codex || true
command -v claude || true
command -v pi || true
test -n "${OPENAI_API_KEY:-}" && echo "OPENAI_API_KEY=set" || echo "OPENAI_API_KEY=MISSING"
```

若缺少 Key：停止并要求用户 export，**不要**在对话外落盘明文。

### 1. 安装 CLI

```bash
npm i -g @openai/codex @anthropic-ai/claude-code
# 可选
npm i -g @earendil-works/pi-coding-agent
# 或 curl -fsSL https://pi.dev/install.sh | sh
pi install npm:@kky42/pi-flow   # 可选，需已装 pi
```

### 2. 全局个人默认（可选）

写入 `~/.codex/config.toml`（仅个人默认）：

- `model = "gpt-5.6-sol"`
- `default_subagent_model = "gpt-5.6-luna"`
- `[features] multi_agent = true`，`multi_agent_v2 = false`（配合 V1 catalog）
- `[model_providers.gateway]` + `env_key = "OPENAI_API_KEY"`

**不要**复制用户的真实 Key 进文件。

### 3. 项目级模板

在项目根运行：

```bash
bash /path/to/subagent-skills/scripts/bootstrap.sh "$(pwd)"
# 或安装 skill 后:
# bash ~/.claude/skills/sol-luna-setup/scripts/bootstrap.sh "$(pwd)"
```

会创建/更新：

```text
.codex/config.toml
.codex/agents/luna_{scout,worker,critic,tester}.toml
AGENTS.md
.claude/agents/luna-{scout,worker,critic,tester}.md
CLAUDE.md
scripts/prepare-luna-catalog.sh
.gitignore 条目：.codex/models-v1.json、.env
```

保留用户已有无关配置；冲突时合并而非盲覆盖。

### 4. 修复 Sol → Luna spawn（必做）

症状：

```text
Unknown model `gpt-5.6-luna` for spawn_agent.
Available models: gpt-5.6-sol, gpt-5.6-terra
```

原因：目录里 Sol/Terra 常为 multi-agent **v2**，Luna 为 **v1**，V2 过滤掉 Luna。

处理：

```bash
bash scripts/prepare-luna-catalog.sh "$(pwd)/.codex/models-v1.json"
# 将 model_catalog_json 设为该文件的绝对路径
# multi_agent_v2 = false
```

### 5. 验证（必须全部通过再宣称完成）

```bash
# 单模型（注意 </dev/null）
codex exec --sandbox read-only -c 'model="gpt-5.6-sol"' \
  "Reply with exactly: SOL_SMOKE_OK" </dev/null

codex exec --sandbox read-only -c 'model="gpt-5.6-luna"' \
  "Reply with exactly: LUNA_SMOKE_OK" </dev/null

# 多代理
codex exec --sandbox read-only \
  "按 AGENTS.md spawn luna_scout 只读说明仓库结构，输出以 SCOUT_DONE 开头" </dev/null

# 可选 Pi
export GATEWAY_API_KEY="${OPENAI_API_KEY}"
pi --print --provider gateway --model gpt-5.6-sol --no-session --no-tools "Reply: PI_SOL_OK"
pi --print --provider gateway --model gpt-5.6-luna --no-session --no-tools "Reply: PI_LUNA_OK"
```

Claude Code：

- 非 root 用户更稳妥
- 先执行 `python $ctl configure-claude`，用 Claude 已知模型 ID 路由到 DeepSeek provider ID
- 使用 `python $ctl smoke --user-triggered --model all` 分别验证 Flash 与 Pro
- 冒烟必须检查 `modelUsage`，不能只检查返回文本
- 检查 stderr/stream-json 噪声中不再出现 `is not a model this version of Claude Code recognizes`
- 若网关 Anthropic 通道失败，记录实际错误，不得假装成功

### 6. 交付报告模板

```markdown
## Sol-Luna Setup Report
- Host OS / Node / Codex / Claude / Pi versions:
- Project path:
- Files created:
- Catalog fix applied: yes/no
- SOL_SMOKE: pass/fail
- LUNA_SMOKE: pass/fail
- MULTI_AGENT SCOUT_DONE: pass/fail
- Pi SOL/LUNA: pass/fail/skip
- Secrets in git: none (confirmed)
- Next user action:
```

## 角色政策（写入 AGENTS.md）

| 角色 | 模型 | 核心责任 | 禁止事项 |
|------|------|----------|----------|
| 主会话 Sol | gpt-5.6-sol | 目标理解、决策、规划、调度、验收，以及 commit/PR 控制 | 不得为节省成本而下放关键判断或最终责任 |
| luna-scout | Flash/Pro | 在指定范围内只读探索并返回证据 | 不解释需求、不改变目标、不自行扩大检索范围 |
| luna-worker | Flash/Pro | 在明确文件和验收边界内实现改动 | 不做架构取舍、不扩大需求、不 commit |
| luna-critic | Flash/Pro | 对指定变更进行只读对抗审查 | 不代替 Sol 接受风险或判定整体完成 |
| luna-tester | Flash/Pro | 运行指定测试并报告原始证据 | 不把局部绿测解释为整体目标达成 |

## 常见失败

| 现象 | 处理 |
|------|------|
| spawn 无 Luna | V1 catalog + multi_agent_v2=false |
| codex 吞掉后续 shell | `codex exec ... </dev/null` |
| wire_api 报错 | 使用 `responses`；确认网关实现 `/v1/responses` |
| Claude root 拒绝 bypass | 换非 root 或降低 permission mode |
| 工人写冲突 | 降并发、按文件分区 |
| Flash/Pro 跑偏 | 用 `haiku/sonnet` 别名经过 `modelOverrides`，并校验 JSON `modelUsage` |
| unknown model / 200k 警告 | 运行 `configure-claude`；不要关闭保护或虚报 `[1m]` |
| skill 多份漂移 | 只编辑 `.cc-switch/skills` 权威源，消费端使用链接/Junction |
| 密钥进 diff | 立即剔除、轮换密钥 |

## 参考文件

- `scripts/bootstrap.sh` — 项目脚手架
- `scripts/sol_luna.py` — 模式、模型、角色和冒烟控制器
- `scripts/prepare-luna-catalog.sh` — 模型目录修复
- `references/project-template/` — 可复制模板
- 博客长文：https://catcat.blog/2026/08/sol-luna-layered-subagents-codex-claude-pi.html
- 源仓库：https://github.com/Yuri-NagaSaki/subagent-skills

## Agent 行为准则

- 先探测、再安装、再写项目文件、再修 catalog、再验证。
- 安装和同步不得自动启用 Luna；默认保持 `mode=off`，等待用户在当前会话触发。
- 展示关键 diff；不覆盖无关用户配置。
- 验证失败时给出可执行修复，不要假装成功。
- 用户若要求「只配置 Sol 和 Luna」：不要启用 Terra 作为默认，catalog 里可保留 Terra 条目仅用于兼容。
- 用户当前明确要求不用 Luna 或指定 Flash/Pro 时，永远覆盖持久默认，不要求用户先改配置。
---
