---
name: feature-replication-methodology
description: >
  跨仓库功能复刻方法论：从源仓库（如 ZCode）复刻功能到目标仓库（如 QEDAgent）时的系统化
  流程与踩坑防线。覆盖装配链先通、声明面四处一致、证据驱动验证三大支柱。触发场景：
  复刻功能、搬运功能、像素级对齐、跨仓库移植、装配链、声明面、工具面挂载、face 装配、
  源码级还原、模型调不到工具、代码写了但不生效、目录注册了但模型看不见、SKILL.md 写了
  但测试红、vite 预打包缓存、UI 卡片不出现。适用于任何「源码在手、目标仓库结构不同」的场景。
---

# 跨仓库功能复刻方法论

## 前置条件

- 源仓库已 clone 到本地（如 `E:/QedAgent/ZCode-main`）
- 目标仓库可编译（tsc / vitest 至少一类可运行）
- 已知要复刻的功能名称与源码入口文件
- 模型凭据已配置（涉及 actor 会话的场景）

## 场景路由

| 用户意图 | 对应章节 |
|---------|---------|
| 复刻一个新功能（从零开始） | → 支柱 1 装配链先通 |
| 功能写了但不生效 / 模型调不到 | → 支柱 2 声明面四处一致 |
| UI 元素不出现 / 截图对不上 | → 支柱 3 证据驱动验证 |
| 测试用例移植 | → [references/test-porting.md](references/test-porting.md) |
| 页面效果 / 交互体感 | → [references/visual-spec.md](references/visual-spec.md) |

## 支柱 1：装配链先通

> 复刻不是翻译代码，是接通链路。先画装配链路图，确认每条链在目标仓库走通，再写代码。

### 操作步骤

1. **画装配链路图**：回答四问
   - face 激活时 ctx 是哪棵树？
   - 工具/服务注册进哪个实例？
   - 模型面从哪聚合？
   - 有几个实例？
2. **找同款先例**：在源码里找已跑通的同构路径
3. **识别多树/多实例陷阱**
4. **先试最小直移**

### 完成标准

- [ ] 装配链路图已画（face 树 + runtime 树 + 模型面聚合点）
- [ ] 同款先例已定位（源码路径 + 行号）
- [ ] 多实例陷阱已识别

## 支柱 2：声明面四处一致

### 四层清单

| 层 | 声明位置 | 作用 | 缺失症状 |
|---|---------|------|---------|
| 1 | composition toolIds | 组合声明面（随包裁剪退场） | 组合产物不含工具 id |
| 2 | SkillSpec requiredToolRefs | 模型面（合并进 spec） | 模型工具清单不含 |
| 3 | 目录 tools.register | 执行面（可执行） | 调用时 DriverError |
| 4 | AgentSpec requiredToolRefs | 会话 spec 面 | 主对话 spec 不含 |

### 操作步骤

1. 逐层检查四层声明是否都有 → 补缺
2. 校验闭包语义：声明面随包裁剪整体退场，无悬挂引用
3. 载荷不原样过边界：宿主按 wire 契约映射，客户端按契约消费

### 错误处理

| 错误 | 根因 | 修法 |
|------|------|------|
| DriverError: not wired | 层 3 缺（目录未注册） | face 激活时 mountWorkflowOrchestration |
| 模型清单不含该工具 | 层 2 缺（技能 requiredToolRefs 留空） | 技能 SkillSpec 补 requiredToolRefs |
| ArtifactStoreUnavailable: no session scope | parentSessionId 未绑 | bindArtifactPublish 闭包加 parentSessionId |
| World read not wired | executeWorldRead 未接线 | bindWorldRead 闭包接 fileSystemPort + executionPort + cwd |

## 支柱 3：证据驱动验证

### 三档验证

| 档 | 手段 | 判据 |
|----|------|------|
| ① 静态对账 | tsc 全链 + 组合产物 toolIds 对账 + 测试全绿 | 全部通过 |
| ② 活体计算样式 | CDP getComputedStyle / 运行时 schemas() 逐类核对 | 实测 = 预期 |
| ③ 实景截图 | 真实键鼠操作后 Page.captureScreenshot 存档 | 元素在场且形态正确 |

### 证据通道交叉

| 通道 | 能看到 | 看不到 |
|------|--------|--------|
| 宿主诊断日志 jsonl | face 装载/失败 | **error 字段是脱敏投影** |
| CDP Runtime.consoleAPICalled | **完整错误对象** | 需直连渲染端 |
| journal SQLite | run 状态/事件序列 | 需 copyfile+WAL |
| CDP DOM querySelector | 可见实例的 DOM | 多实例时撞隐藏实例 |
| React 组件函数探针 | 可能被并发渲染丢弃 | 以提交后 DOM 为准 |

### 取证假象清单

| 假象 | 根因 | 对策 |
|------|------|------|
| 入口忽有忽无 | 页签保活多 DOM 实例共存 | 过滤 checkVisibility |
| 源码改动不生效 | vite optimizeDeps 预打包缓存 | **改完重启 dev** |
| 组件探针假绿/假红 | React 并发渲染丢弃调用 | 以提交后 DOM 为准 |
| 错误只剩脱敏占位 | 宿主诊断投影约束 console | 直连渲染端 CDP |
| JSON.stringify 丢 undefined 键 | 面板状态假阴性 | 断言前检查键存在性 |
| buildImportedCache 会话 id 形态差异 | ZCode `sess-A` vs QEDAgent `runId:site` | fixture 按 QEDAgent 形态重写 |

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|---------|
| R1 | composition.ts 是保留路径（纯 FaceRecord 数据，只允许类型导入，禁值导入） | 隔离产物装载在临时目录解析外部依赖时 TypeError |
| R2 | 声明面四处一致（composition toolIds / 技能 requiredToolRefs / 目录注册 / spec requiredToolRefs） | 模型调不到工具（清单不含）或执行时 DriverError |
| R3 | 模型面经技能合并链聚合（不走目录注册链）——外部工具必须经 SkillSpec requiredToolRefs 声明 | 目录注册了但模型永远看不见 |
| R4 | vite optimizeDeps 预打包源码——源码改动后必须重启 dev | 在旧缓存上调代码，以为修了但没生效 |
| R5 | 多 DOM 实例共存是常态——取证必须过滤 checkVisibility | CDP 撞隐藏实例，误判为「状态衰减」 |
| R6 | 宿主诊断 error 字段是脱敏投影 | 只看日志永远拿不到完整错误对象 |
| R7 | 表面组件身份必须稳定（禁内联箭头包装组件） | React 判别为新组件→卸载重挂→弹层 useState 永远丢失 |
| R8 | SSR 静态渲染下 useSyncExternalStore 走 getServerSnapshot（恒缺席） | 活动行高频重渲染场景不可用；改用 context 快照读 |
| R9 | stash pop 留 UU 冲突必须即时清理 | JSON 损坏 / vite 启动崩（exit 3221226505） |
| R10 | 载荷不原样过边界（宿主按 wire 契约映射） | 客户端按存储形态消费 → TypeError → 对话列整体降级 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 | 实际后果 |
|---------------------|---------|---------|---------|
| 「目录注册了就行」 | 模型面经技能合并链聚合，不走目录注册链 | R2 | 模型清单 15 个零工作流工具 |
| 「requiredToolRefs 留空，工具面由功能门控决定」 | /workflow 展开体要求主对话直接调 CreateWorkflow，留空 = 调不到 | R2 | 30 节点流水线设计完但无法启动 |
| 「artifactStore 传了就行」 | parentSessionId 也必须绑定（store 写入按会话记账） | R2 | ArtifactStoreUnavailable |
| 「弹层状态用 useState 就行」 | 内联箭头包装组件被 React 判别为新类型→卸载重挂 | R7 | 弹层 open 永远 false |
| 「测试 stub 的 RunBadge 渲染 data 属性就行」 | stub 与真实组件 props 不同步（client prop 新增后 stub 没改） | R10 | 测试绿但实机组件崩 |
| 「修完源码刷新页面就行」 | vite optimizeDeps 预打包 face 入口——源码改动不进 deps 产物 | R4 | 反复修改无效 |

## 参考文档索引

| 文件 | 用途 |
|------|------|
| `references/visual-spec.md` | ZCode 工作流 UI 高保真视觉与交互规格（483 行，六组界面+状态语义） |
| `references/test-porting.md` | bootstrap/dynamic-workflow 测试移植状态台账（4 绿 + 24 pending + 15 缺源删） |
