# Sol-Luna 共享 Provider 契约

## 定位

本目录是 `auto-code-generator` 的共享 Sol-Luna 执行 provider，不是用户触发 skill：无 `SKILL.md`、
无 frontmatter，不进入 skill 列表。**自动编码的唯一用户入口是 `auto-code-generator`**；执行委派由其
适配层调用。Sol 始终是当前主会话所用的高能力模型，不在 Luna 模型列表中。管理员用
`scripts/bootstrap.sh` 做项目初始化；控制器的管理与诊断子命令为 `status`、`models`、`mode`、`model`、
`configure-claude`、`sync`、`audit` 和 `smoke`。Codex 原生委派由 `auto-code-generator` 编排层发起，
不由 Python 控制器递归启动子 Agent；`scripts/sol_luna.py run` 只实现外部 runner。

## 运行时范围

- **Luna 默认开启**：默认有效配置为 `mode=auto`。有效配置为 `off`，或用户在当前任务明确说“不用 Luna”
  “只用 Sol”时关闭自动委派。
- 外部 runner 仅通过 `scripts/sol_luna.py` 的 `run` / `smoke` 命令执行；`auto` / `force` 无需额外标志。
  `--user-triggered` 仅用于当前用户明确要求 Luna 时单次覆盖有效 `off`，且不写持久配置。它是受信任编排
  层传递的当前请求声明，不是操作系统级凭据或安全边界；能直接执行本地控制器的调用者本身已经拥有
  启动 runner 的权限。原生 runner 由编排层直接调用宿主 `spawn_agent`。
- 任务卡六项各占一行，严格使用 `字段：非空内容`：目标、允许范围、禁止范围、约束、预期输出、验证证据；
  任一项缺失或为空时拒绝委派。
- `auto-code-generator` 必须把完整内聚场景组作为一个可观察目标写入任务卡；不得为了满足长度限制拆分
  `RED → GREEN → REFACTOR`。完整场景组无法保真表达时，provider 不适用并回退 Sol 或项目原生执行。
- scout/critic 保持 plan-only；tester 只被预授权 Bash 以运行 Sol 指定的测试，worker 被预授权工作区编辑与
  Bash 以完成同一场景的 TDD。所有角色仍受六字段任务卡和权限边界约束，禁止 bypass 权限。

## Luna 模型列表

- `luna-models.json` 是用户维护的有序 Luna 低成本模型列表；第一项是默认模型，第二项可作为套餐额度优先的
  备选。初始顺序是 `gpt-5.6-luna`、`gpt-5.3-codex-spark`，Sol 不得自动改写或联网刷新该列表。
- 不指定模型以及选择 `auto` / `default` 时均使用第一项；也可按 `id` 或 `aliases` 显式选择，未知项拒绝执行。
- 公共字段是 `id`、`label`、`backend`、`provider_model` 和 `aliases`。`backend=codex` 还需
  `reasoning_effort`；`backend=claude` 还需 `claude_model` 与 `override_model`。缺少 `backend` 的旧条目按
  `claude` 解释。列表不得包含密钥、Token 或服务地址。
- `backend` 与 `runner` 分离：Codex 条目按 `native_spawn → codex_exec` 选择，Claude 条目使用
  `claude_code`。runner 是当前会话的动态执行决策，不写入用户维护的模型列表。
- `backend=codex` 时，编排层仅在所选**精确模型**位于当前会话暴露的原生 allowlist 且权限满足角色边界时
  使用 `native_spawn`；必须显式传入模型、reasoning effort 与输入受限的 assignment，不得继承 Sol 或
  静默换模。allowlist 与权限能力只取自当前 `spawn_agent` 工具说明，不从 CLI 缓存推断。否则仅在启动前
  回退同一模型的 `codex_exec`。用户要求 `native only` 时不可回退。
- `codex_exec` 由控制器通过临时会话、明确模型和沙箱执行，不得加入 bypass、ignore-rules 或额外写目录
  参数。其 JSONL 当前只能证明命令请求的模型，返回标记为 `model_verification=command_only`，不得伪称
  等价于实际模型证明。`spawn_agent` 返回 Agent 标识即视为 `native_spawn` 已启动；之后失败不得自动再跑
  CLI，以免重复副作用。
- `backend=claude` 由 `claude_code` runner 执行；用户调整 Claude 条目后应运行 `configure-claude` 合并映射，
  并通过 `modelUsage` 核验实际 provider 模型。`configure-claude` 不处理 Codex 条目。
- `models` 和 `status` 是只读查看命令。`run` / `smoke` 在 `auto` / `force` 下直接执行；有效 `off` 下只有
  当前用户明确要求 Luna 时才可用 `--user-triggered` 单次覆盖。`smoke` 默认只验证第一项；只有显式指定
  `--model all` 才遍历整个列表。

## 管理资产

- `scripts/sol_luna.py`：配置、双后端模型路由、角色同步/审计、运行与 smoke 控制器；
- `luna-models.json`：用户维护的 Luna 模型列表，第一项为默认；
- `references/result-schema.json`：双后端统一的组状态、逐 task 结果、文件和验证证据返回契约；Codex 通过
  `--output-schema` 前置约束，Claude 的最终文本由控制器按同一契约解析和复核；
- `scripts/bootstrap.sh`：可选安装 Claude 角色文件和共享政策指引；不生成 Codex 模型目录；
- `references/project-template`：Claude 角色与项目级指导模板；
- `tests/test_sol_luna.py`：provider 控制面回归测试。

## 边界

- provider 不拥有生命周期、任务状态或 Git 授权；由 `auto-code-generator`（Sol）依据逐 task 的 diff、
  测试和证据验收，不得由 provider 自行宣告整体完成。
- `group_status` 与 `task_results[].status` 必须分别使用 consumer 定义的状态集；完成态要求每个 task 都为
  `SATISFIED`，task 证据和组级验证均不得为空。
- provider 不创建 phase、artifact、tracker 或第二套完成结论；项目权威生命周期始终优先。
