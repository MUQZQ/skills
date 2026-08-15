eval_id=9 version=with_skill

依据 `auto-code-generator` SKILL.md **v4.3「2.5 维护视图投影」** 与 `_providers/sol-luna/CONTRACT.md`。前提：仅在生命周期声明维护架构投影契约并提供官方 init/check 脚本时才处理；未声明则不得创建/伪造投影。脚本只做确定性初始化与结构检查，Agent 做语义审查（结构有效≠语义正确）。

- **A 已有有效 change 投影**
  - 动作：复用现有投影，不静默覆盖，运行官方 check。
  - 阻塞：check 失败（结构损坏）→ 按 D 上报，不得降级为空白模板。
  - 首动作：只读运行官方 check 结构检查。

- **B change 投影缺失、当前维护视图有效**
  - 动作：调用官方 init，以有效当前维护视图为种子生成 change 投影后 check。
  - 阻塞：init 失败、种子视图实际无效、或语义审批未过。
  - 首动作：读官方 init/check 说明，确认当前维护视图有效后执行 init。

- **C 两者都不存在、schema 有全项目模板**
  - 动作：按 schema 全项目模板调用官方 init 覆盖全项目投影。
  - 阻塞：无全项目模板或未声明投影契约 → 停止，不伪造。
  - 首动作：确认 schema 模板与官方脚本存在后执行 init。

- **D 当前维护视图损坏**
  - 动作：必须 `BLOCKED`，不得降级为空白模板，上报官方生命周期修复。
  - 阻塞：结构损坏本身即阻塞；Agent 不自修、不伪造。
  - 首动作：运行 check 取得损坏证据并上报生命周期 owner。

边界：投影同步与归档属生命周期 owner；投影 init/check 不属 provider（provider 仅执行场景组 TDD，不拥有生命周期/任务状态/Git）；Git 默认 `NONE`，初始化脚本不授予 Git 权限。关键规则：R0（服从权威生命周期）、R10（Git 单独授权）、2.5 表、CONTRACT 边界。
