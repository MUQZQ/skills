**决策：选择 Sol-Luna provider，整组单 worker 委派。**

**边界**：`auto-code-generator` v4.3（Sol）是唯一用户入口，拥有生命周期 owner、权威 tracker 状态、验收与 Git 授权；luna 仅做有界执行，不归档、不 commit/push/PR/deploy（R10、CONTRACT 边界）。维护视图投影只服从项目声明的契约，本场景无契约则不投影。

**选择**：本会话已显式点名 Luna → 满足 `references/execution-providers/sol-luna.md` 选择门禁；每次 `run`/`smoke` 必须带 `--user-triggered`，且不写持久配置。未显式同意即阻塞不调用。

**委派粒度**：失败测试、最小实现、重构验收共享 fixture 与写入范围，属同一可观察行为 → 合为一个完整内聚场景组（R5、R12、3.2 合组门禁），压缩为六字段任务卡（目标/允许范围/禁止范围/约束/预期输出/验证证据，均非空），交同一个 `luna-worker` 在同一执行上下文完成 RED→GREEN→REFACTOR；不拆分 TDD、不按阶段多次调用。该组可形成独立可验证闭环，不拆单。

**返回验收**：provider 只回 `group_status`、逐 task `task_result`、真实 diff/命令/证据；Sol 按 3.6 逐 task 核对 allowed_writes、聚焦测试与验收证据后更新权威 tracker，不得因组 DONE 一键完成。

**降级/阻塞**：六字段任一缺失或为空 → 拒绝委派并返回缺失项；完整组压缩后超出 prompt/结果限额或无法在任务卡内保真语义 → provider 不适用，回退 Sol/项目原生直接完成该组，不得切碎 TDD 迁就 provider。

**第一个实质动作**：只读取证（Stage 1）——读权威 tracker 实时状态、branch/HEAD/status 与基线；确认无漂移后生成该组六字段任务卡，经 `scripts/sol_luna.py run --user-triggered` 委派。

证据：SKILL v4.3（2026-08-15）；关键规则 R5/R10/R12 与 3.2/3.6/3.7；`auto-code-generator/references/execution-providers/sol-luna.md`；`_providers/sol-luna/CONTRACT.md`。eval_id=11 version=with_skill。
