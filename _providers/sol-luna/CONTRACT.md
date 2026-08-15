# Sol-Luna 共享 Provider 契约

## 定位

本目录是 `auto-code-generator` 的共享 Sol-Luna 执行 provider，不是用户触发 skill：无 `SKILL.md`、
无 frontmatter，不进入 skill 列表。**自动编码的唯一用户入口是 `auto-code-generator`**；执行委派由其
适配层调用。Sol 始终是当前主会话所用的高能力模型，不在 Luna 模型列表中。管理员用
`scripts/bootstrap.sh` 做项目初始化；控制器的管理与诊断子命令为 `status`、`models`、`mode`、`model`、
`configure-claude`、`sync`、`audit` 和 `smoke`。

## 运行时范围

- 仅通过 `scripts/sol_luna.py` 的 `run` / `smoke` 命令执行，且必须携带 `--user-triggered`。
- **Luna 默认关闭**：只有当前会话用户明确同意后，才可用 `--user-triggered` 单次启用，不写持久配置；
  持久 `auto` / `force` 只描述触发后的委派策略，不能替代当前会话显式同意。
- 任务卡六项各占一行，严格使用 `字段：非空内容`：目标、允许范围、禁止范围、约束、预期输出、验证证据；
  任一项缺失或为空时拒绝委派。
- `auto-code-generator` 必须把完整内聚场景组作为一个可观察目标写入任务卡；不得为了满足长度限制拆分
  `RED → GREEN → REFACTOR`。完整场景组无法保真表达时，provider 不适用并回退 Sol 或项目原生执行。
- scout/critic 保持 plan-only；tester 只被预授权 Bash 以运行 Sol 指定的测试，worker 被预授权工作区编辑与
  Bash 以完成同一场景的 TDD。所有角色仍受六字段任务卡和 `--user-triggered` 门禁约束，禁止 bypass 权限。

## Luna 模型列表

- `luna-models.json` 是用户维护的有序 Luna 低成本模型列表；第一项是默认模型，第二项可作为套餐额度优先的
  备选。初始顺序是 `gpt-5.6-luna`、`gpt-5.3-codex-spark`，Sol 不得自动改写或联网刷新该列表。
- 不指定模型以及选择 `auto` / `default` 时均使用第一项；也可按 `id` 或 `aliases` 显式选择，未知项拒绝执行。
- 公共字段是 `id`、`label`、`backend`、`provider_model` 和 `aliases`。`backend=codex` 还需
  `reasoning_effort`；`backend=claude` 还需 `claude_model` 与 `override_model`。缺少 `backend` 的旧条目按
  `claude` 解释。列表不得包含密钥、Token 或服务地址。
- `backend=codex` 由控制器通过受限的 `codex exec` 执行：临时会话、明确模型和沙箱，不使用原生
  `spawn_agent`，不得加入 bypass、ignore-rules 或额外写目录参数。其 JSONL 当前只能证明命令请求的模型，
  返回标记为 `model_verification=command_only`，不得伪称等价于实际模型证明。
- `backend=claude` 由 Claude Code 执行；用户调整 Claude 条目后应运行 `configure-claude` 合并映射，
  并通过 `modelUsage` 核验实际 provider 模型。`configure-claude` 不处理 Codex 条目。
- `models` 和 `status` 是只读查看命令，不代表当前会话已授权 Luna；真正的 `run` / `smoke` 仍需
  `--user-triggered`。`smoke` 默认只验证第一项；只有显式指定 `--model all` 才遍历整个列表。

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
