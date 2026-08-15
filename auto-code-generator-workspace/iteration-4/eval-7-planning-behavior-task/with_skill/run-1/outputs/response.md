已完成只读取证：`SKILL.md` v4.3、`references/execution-providers/sol-luna.md`、`evals/evals.json`（eval_id=7）。

## 任务粒度决定

将草稿 T1/T2/T3 合并为**一个持久 task**「密码重置 token 过期即失败并记录审计事件」，不建立三个 task、不拆 change。

## 任务内容

一个可独立验收的可观察行为：token 过期时重置失败，且产生对应审计事件。范围仅含该场景的过期判断与审计断言；不含信件发送、账户锁定、全站审计框架等相邻行为。

## TDD/验收项（同一 task 内部步骤）

1. RED：先写过期失败测试并附审计事件断言，运行确认失败源于行为缺失，而非 fixture/环境/无关设置。
2. GREEN：最小实现过期判断，循环运行聚焦测试直至通过。
3. REFACTOR：仅必要整理，复跑同组测试。
4. 组级验收：过期失败 + 审计事件整体通过才判 VERIFIED；聚焦验证用项目原生命令（如 `pytest -k password_reset_expiry`），全量/跨场景验证留待 Stage 4。

## 理由

- §2.3：粒度下限是「能否单独给出有意义验收证据」——T1 只有失败测试、T2 无测试、T3 无独立场景，三者共享模块与 fixture，只有整体通过才产生可见价值，故写成同一 task 的步骤/验收项。
- R5/§3.5：RED→GREEN→REFACTOR 是同一行为闭环，不得拆给不同 worker 或阶段。
- R12：持久 task 是验收单元，禁止按测试/实现/文件/Agent 机械拆 task。
- §2.4：默认单一 change；无独立交付、回滚/迁移边界，不拆 change。
- sol-luna.md 委派粒度同样禁止拆分 TDD；且需本会话显式同意 Luna——本题未授权，不调用 provider。

## 边界

不新增第二真相源/change/并行组；审计仅限本场景；不推断 commit/push/PR/部署权限。

## 暂停条件

缺审计事件 schema/格式决策、执行意图（PLAN_ONLY / PLAN_AND_APPLY）未确认、baseline 漂移、RED 因 fixture 失败，或权威 tracker 已存在更细 task（不重写，改为映射到同一临时场景组）时停止并返回缺失项。

## 第一个实质动作

Stage 1 只读取证：读项目生命周期所有者与实时状态、当前分支/HEAD/status、审计事件接口决策；输出所有权决定并锁定 Target baseline，再写入该唯一 task（场景 + 验收项 + 原生验证命令）至 Apply-ready。

证据
