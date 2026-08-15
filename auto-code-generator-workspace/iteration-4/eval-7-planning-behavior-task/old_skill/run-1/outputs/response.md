**决策**：T1/T2/T3 合并为 1 个 tracker task，禁止按 TDD 阶段拆成 3 个微任务。

**依据（v4.2）**：R5、R12、§2.3——同一可观察行为的 RED/GREEN/REFACTOR 与测试/实现不得切成独立委派微任务。T1/T2/T3 是“token 过期重置失败并写审计”这一行为的测试与实现，各自不能给出有意义验收证据，只有整体场景通过才可验收，共享同模块与 fixture，且无独立审批/回滚/迁移/契约边界，正是 R12“微任务过度委派”反例。

**任务内容**：单 task——token 过期时密码重置失败并产生审计事件（整体通过才验收）。T1、T3 并入同一 RED（同 fixture 断言失败+审计写入），T2 为 GREEN 最小实现。

**TDD/验收项**：① RED 添加失败测试，确认失败源于行为未实现而非 fixture/环境；② GREEN 实现过期判断+审计写入，复跑新增与受影响测试；③ REFACTOR 后复跑同组；④ 组级验收用项目原生命令跑该场景全绿。单 worker 场景组内闭环，不跨 worker 切碎（§3.5）。

**边界**：一个真相源一个 task，不新增编号、不扩权其他审计/范围外；风险档位按 §1.2 属 Strict（安全/权限/审计），实施期用单 bounded worker、不并行。

**暂停条件**：BASELINE_CHANGED；RED 因 fixture/环境失败先修基础；权威 schema 要求更细或审计演变为公共契约需独立消费者时停止确认。

**第一个实质动作**：Stage 1 只读取证（AGENTS/权威生命周期/当前 tracker 状态/分支 HEAD status），输出所有权决定后按 §2.1 写入该单任务定义；不写文件、不改状态。

**证据**：`C:\Users\30960\.cc-switch\skills\auto-code-generator-workspace\iteration-4\skill-snapshot\SKILL.md` v4.2（2026-08-14）R5、R12、§1.2、§2.1、§2.3、§3.5；eval_id=7 version=old_skill。
