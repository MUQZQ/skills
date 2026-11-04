# 无项目流程时的最小编排

仅项目没有相应权威规则时读取；已有项目流程的同名要求优先。

### 1.2 选择风险档位

以下三档仅用于项目未定义风险路由的 fallback；项目已有档位时保留其名称、审查和执行要求。

| 档位 | 典型证据 | 最低控制 |
|---|---|---|
| Light | 根因已知、局部可逆、无公共契约/数据/安全/跨组件影响 | 聚焦计划、场景内 TDD、自审、聚焦验证 |
| Standard | 普通多文件功能或重构，无架构和高风险边界变化 | 完整规格追踪、测试计划、最终审查和项目原生验证 |
| Strict | 架构、公共契约、持久化数据/迁移、安全/权限/隐私/支付、并发一致性、跨组件或外部系统影响 | 项目要求的架构/独立评审、全新 bounded worker、独立整体验证 |

如果项目 schema 已经完成风险路由，直接使用其结果，不做第二次分类。风险事实不清且会改变档位时先取证；
仍不清楚则停止并说明缺失项，不靠“更严格总没错”替代授权决定。

### 1.2.1 Delivery profile

本节的默认模式、适用性阻塞和报告字段仅适用于项目未定义交付流程的 fallback。项目已有流程时
报告项目实际模式，不强行填入 DEMO_FAST/FULL，也不因用户未说 FULL 而增加确认。项目只定义部分
约束时，fallback 仅补充未定义项；两者发生冲突时服从项目规则。

默认 Delivery profile 为 `DEMO_FAST`，不需要用户说“快速 Demo”，也不持久化。只有当前用户明确、正向的执行意图
要求“有 spec”、“按 spec 实施”、“完整模式”、“全流程”或“生产级”等 spec-bound/full 交付时，才选择
`FULL`；否定、引用、历史转述或仅讨论词语本身都不算授权，不能按关键词子串匹配。意图冲突且无法消歧时结果为 `BLOCKED`，请求用户明确，不自行选更重的流程。不能从文件数量或 Agent 自行偏好切 FULL。

启用任一 profile 前仍须完成只读基线和权限检查。只有 `DEMO_FAST` 要求一个可观察 Demo 目标和排除项；
`FULL` 使用 spec 或任务定义的可观察交付目标。项目已有 QEDA、OpenSpec 或强制生命周期时仍由其拥有权威，
任何 profile 都不能绕过其状态、审批和工件。

`FULL` 只改变交付深度，不改变生命周期所有者或风险档位；选择后必须同时输出生命周期所有者和 `Light | Standard | Strict` 风险档位，并按该档位保留相应门禁。

`DEMO_FAST` 只允许 `Light` 风险档位，且只适用于本地、可逆、单一可演示 happy path；风险档位门禁优先于 Delivery profile。
若收敛后的候选范围为 Standard 或 Strict，必须停止并报告 `BLOCKED`，要求用户把 Demo 目标缩小到 Light，或明确
改为 spec/FULL 后按对应最低控制执行；不得静默缩减需求、降低风险档位或升级 FULL。文件数量本身不能自动选择
`FULL`，但仍可按 1.2 的事实参与风险分类。若候选范围不能收敛为一个本地、可逆、单一可演示 happy path，也按
同一规则阻塞并要求用户缩小 Demo 目标或明确改为 spec/FULL。

若命中架构、公共契约、数据迁移、安全权限隐私支付、并发一致性、不可逆外部操作或项目强制门禁，而用户没有
明确 spec/FULL 意图，必须停止并报告 `BLOCKED`，说明需要用户明确改为 spec/FULL；不得静默升级 FULL，也不得
继续极速实施。无权威生命周期时计划留在当前对话；默认只形成一个场景组，不构造 DAG 或多 worker。

`DEMO_FAST` 的最小流程仍保留：同一场景组有效执行 `RED → GREEN → REFACTOR`；不能合理测试的脚手架使用可重复 smoke，
不虚构 RED；完成聚焦自审、项目原生聚焦测试和本地 Demo smoke。不得做未要求的生产加固、全量回归或多轮
review，不得自行创建额外归档工件；这不能跳过项目官方归档、关闭或强制门禁，项目规则或实际影响要求更广验证时
不得省略。保留既有 `VERIFIED`、`BLOCKED`、`INCOMPLETE` 状态。

报告必须写明 Delivery profile：`DEMO_FAST | FULL`。`PLAN_AND_APPLY` 实际完成验证时，`DEMO_FAST` 报告明确
`production_ready=false`、已验证 happy path、延期项/风险和运行 Demo 命令；`PLAN_ONLY` 只能报告计划的 happy path、
`validation=PENDING`、延期项/风险和拟运行 Demo 命令；`PLAN_ONLY` 的最终结果为 `INCOMPLETE`，不得写 `VERIFIED`
或声称已经运行。`Demo VERIFIED` 只代表
演示场景证据，不代表生产就绪，也不推导 commit/push/PR/deploy。
