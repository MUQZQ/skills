# 项目工作流适配

## 读取边界

只有目标项目声明权威流程时使用本参考。先读项目入口，再只读当前阶段引用的必要正文；
引用 Skill 时完整读取其 SKILL.md。这里是导航与适配边界，不复制或安装参考项目的流程。
每次执行使用目标项目实际安装的版本；没有活动 change 不等于没有项目流程。
本 skill 后文的 fallback 默认值不叠加生效，不强行填入 DEMO_FAST/FULL。

已有流程决定任务组、测试时机、独立上下文、状态更新和授权要求；主 Skill 的场景组合并、
六字段任务卡与 provider 降级只能在这些边界内使用。不能删除项目要求的信息或新增第二个 owner。
目标项目不是 QEDA 时，使用其对应入口，不要求 QEDA 文件或脚本存在。

## QEDA：识别与续接

读取项目安装的 `openspec/references/qeda/qeda-workflow-contract.md`，按其中的入口解析项目与
活动变更；现行入口使用 `openspec context --json`、`openspec list --json`，不靠 change 名称关键词猜测。
根据目标行为、capability、当前制品、相关源码测试和 diff 判断相关性。唯一相关 active change
继续拥有本次工作；多个候选无法消歧时只问一次；无关 change 不劫持请求。

修复继续同一 change 的实时 Apply。制品错误时从最早受影响的权威制品修正并刷新依赖；
仅实现错误时不制造制品改动。恢复受影响任务及失效复核/验证，范围未变不重复授权。
归档后的行为修复按项目要求使用 linked follow-up change，不恢复已归档权威。

## QEDA：规划与 Vibe

读取项目当前路由，不从本 Skill 的 Light/Standard/Strict 推导项目 schema。
现行 QEDA 新变更使用 Patch、Strict 或 Vibe；已有 legacy Standard/Architecture 继续其原流程，
不得仅因本 skill 把架构列为 Strict 而二次升级、增加 reviewer 或改变历史 schema。

`VIBE_ACTIVE` 是尚无 change 的直接开发阶段，不能等同于 `qeda-vibe-coding` 收敛 schema。
它不强制 TDD，不要求额外选择 FULL；没有 tracker 时仅用当前对话协调。
开发阶段只报告候选实现和实际运行结果，不宣称正式收尾或自行归档。

准备提交或用户要求提前整理时，读取项目安装的 Vibe Skill 及其 `qeda-vibe-convergence.md`。
现行 QEDA 要求 Vibe 开发结束、准备提交前总结全部迭代与相关差异并完成收敛，
不等待额外 `VIBE: CONVERGE` 指令。按目标项目当前要求执行，不能沿用旧版“仅显式要求才收敛”。
必要收敛不授予 Git、扩范围或 Archive 权限，保留项目的 Achieve 门禁。

QEDA 规划不建立持久指纹；与当前决定无关的变化不要求重新确认。规划阶段的实时读取
不能用来豁免 Git 精确暂存检查或最终验证状态绑定。具体约束读取项目 `qeda-authorization.md`。

## QEDA：Apply 与 Strict 执行

实施前读实时 Apply 指令及其上下文。Strict 完整读取项目的 `qeda-subagent-execution.md`；
以项目顶层任务组为 worker 单元，不用本 Skill 的临时合组改写其边界。
缺少真实 worker 能力时保持 BLOCKED，不降为协调者自实施；串行只表示逐组派遣 worker。
原 worker 失败后先核对实际 diff 并按项目恢复，不能因 Luna 不可用或失败而内联接管 Strict。

assignment 传递当前项目/模块规则路径、测试设计、映射代码交付、生产入口、失败处理和验收要求。
映射测试代码的交付与测试执行状态分开；高层测试的运行时机遵循项目当前指令，
不把环境限制当作缺少测试代码的豁免，也不把发现用例或编译成功当作场景通过。
若已安装规则对执行时机等有实质冲突，核对实时指令并报告具体矛盾，不凭本参考替项目裁决。

项目要求 Strict 执行记录时，保留其 QEDA project/change/role 标记、完整任务书与原始宿主日志。
按当前命令执行 `check --task-group`、`check --closeout review|final` 及 `--execution-log` 检查；
检查失败不勾选任务，不加工或伪造日志。宿主无法提供所需记录时如实保持 INCOMPLETE，
不能退化成只检查报告文字；只有读取并核对完整返回与行为证据后才更新项目状态。

## QEDA：复核、验证与收尾

正式收尾先读取项目 `qeda-verification.md`、实现复核与目标同步规则。缺少必要同步授权时报告具体阻塞；
同步仅沿已授权的目标分支到工作分支方向完成，再审查最终实现。项目要求独立上下文时严格保留：
Strict 的实现复核与整体验证分别使用全新上下文，彼此不同且都不同于规划复核，不由执行者自评替代。

复用项目 `qeda-verification-state.mjs` 的当前 capture/check 协议：复核输入绑定、复核门禁、
实际验证、最终状态绑定和最终门禁按项目顺序执行；Apply 收尾及归档预检运行 `check`。
旧 capture/check 不自动替代项目新增的 closeout 或执行记录检查。项目要求完整重新复核时，
源码、测试、配置或规划变更后重新提供完整最终差异；不能用本 Skill 的受影响部分复查代替。
不能只刷新指纹来恢复通过；没有该机制的项目不安装 QEDA 脚本或自行引入状态协议。

用户操作变化时读取项目文档 Skill，在现有任务内维护受影响指导；按实际范围报告已更新、
无需更新依据或待补证据。项目有 feature.md、特性目录或问题登记时按当前 Apply/验证要求更新，
不将本地通过写成已发布，也不把问题只留在聊天。没有这些项目资产时不自行创建整套体系。
归档和 Git 动作遵守各自已有授权，不从 VERIFIED 推导执行许可。
