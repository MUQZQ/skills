---
name: feature-replication-methodology
description: >
  跨仓库功能复刻的方法论：从源仓库（如 ZCode）复刻功能到目标仓库（如 QEDAgent）时的
  系统化流程与踩坑防线。触发词：复刻功能、搬运功能、像素级对齐、移植测试、装配链、
  声明面、工具面挂载、face 装配、跨仓对齐、源码级还原。适用于任何「源码在手、
  目标仓库结构不同」的场景——不只是 ZCode→QEDAgent。
---

# 跨仓库功能复刻方法论

## 核心结论

> 复刻功能不是「翻译代码」，是「接通链路」。源码在手时，每一行自研代码都是一次偏离——
> 先找到源码里同款功能的最小装配路径，确认它的每条声明链和执行链在目标仓库里也能走通，
> 再决定哪些可以直移、哪些必须适配。

所有返工都源于同一模式：**代码写了但链路没通**。工具注册了但模型看不见（声明链断）、
存储有了但会话 id 没绑（执行链断）、技能注册了但 requiredToolRefs 留空（模型面断）。
修复本身只需几行代码，但发现它们花了数小时——因为链路未通时凭直觉写代码，错了不知道错在哪。

## 三支柱

### 支柱 1：装配链先通（读通再动手）

动手前画出目标功能的端到端装配链路图，确认每条链在目标仓库里走通。

#### P1.1 画装配链路图

复刻前回答四个问题：

1. face 激活时 ctx 是哪棵树？（宿主 cordis / agent runtime cordis / 渲染端 React）
2. 工具/服务注册进哪个实例？（face 树的实例 / agent runtime 的 / 渲染端的）
3. 模型面从哪聚合？（spec.requiredToolRefs + 技能 requiredToolRefs 合并链）
4. 有几个实例？（宿主 face 树 / 工程会话 runtime 树 / 页签保活 DOM——多实例共存是常态）

#### P1.2 找同款先例

在源码里找**已跑通的同构路径**作为参考，不自己设计：

| 找什么 | 例子 | 学到什么 |
|--------|------|----------|
| 外部工具进模型面 | KB 查询：`SKILL.requiredToolRefs` → `registerSkillSpec` | 技能 requiredToolRefs 合并链 |
| 斜杠命令 | `builtin-workflow-command.ts` | prompt 型命令展开体发模型 |
| 表面登记 | `QedaAgentClientSurfacePort.registerCoordination` | 表面行经 registerXxx 挂进对话列 |
| saved 清单载荷 | KB 同款 `KNOWLEDGE_QUERY_SKILL` | 不把存储形态原样过边界 |

#### P1.3 识别多树/多实例陷阱

| 陷阱 | 症状 | 解法 |
|------|------|------|
| 宿主 face 树 ≠ agent runtime 树 | 目录注册了但模型看不见 | 确认两侧用同一实例或经 face 传递 |
| 页签保活多 DOM 实例 | querySelector 撞隐藏实例 | 取证过滤 `checkVisibility()` |
| vite optimizeDeps 预打包 | 源码改动需重启 dev 才生效 | 改完重启，别在缓存上调 |
| 跨包同名文件 | 栈帧归属混乱 | 栈帧必须分清包属 |

#### P1.4 先试最小直移

每个适配点先试纯函数/投影类的**最小直移**（只改 import），验证映射表；
遇到 API 差异再逐个适配。不要一次性全改再跑。

### 支柱 2：声明面四处一致（四层同步闭合）

工具/能力的可见性与可执行性由四层声明共同决定，任何一层缺失或错位
都会导致「注册了但不可用」或「可见但调不到」。

#### 四层清单

```
层 1  composition toolIds        → 组合声明面（随包裁剪整体退场）
层 2  SkillSpec requiredToolRefs → 模型面（经 mergeSkillIntoCompiledSpec 合并进 spec）
层 3  目录 tools.register        → 执行面（可执行）
层 4  spec.requiredToolRefs      → 会话 spec 面（AgentSpec 声明）
```

#### 每层断裂的症状与修法

| 断裂层 | 症状 | 修法 |
|--------|------|------|
| 层 1 缺 | 组合产物不含工具 id | composition.ts 的 artifacts.toolIds 补声明 |
| 层 2 缺 | 模型工具清单不含（技能 requiredToolRefs 留空） | 技能 SkillSpec 的 requiredToolRefs 补声明 |
| 层 3 缺 | 调用时 DriverError「not wired」 | 宿主 face 激活时 mountWorkflowOrchestration 注册 |
| 层 4 缺 | 主对话 spec 不含该工具 | AgentSpec 声明的 requiredToolRefs 或经技能合并链 |

#### 闭包与裁剪语义

- 声明面随包裁剪整体退场——包被移出装载集时，toolIds/技能/目录注册全部消失，
  **不允许悬挂引用**
- 声明面与执行面必须一致——声明了但目录没有（裁剪后残留声明）→ missing-tool issue
- requiredToolRefs 的归属选择：**优先走技能合并链**（技能随包裁剪整体退场，
  无悬挂引用），不挂在 AgentSpec 基础面（裁剪后残留引用）

#### 载荷不原样过边界

存储形态（`{entries, invalid}`）不等于模型面视图（`{workflows: [...]}`）——
**宿主按 wire 契约映射**，客户端按 wire 契约消费。错位 = TypeError = 对话列整体降级。

### 支柱 3：证据驱动验证（不接受代理信号）

「代码已写」「文件已改」「测试通过」都不是完成证据。每步必须有可独立验证的实证，
且证据来源不能是可能被污染的通道。

#### 三档验证

| 档 | 手段 | 判据 |
|----|------|------|
| ① 静态对账 | tsc 全链零错误 + 组合产物 toolIds 对账 + 测试全绿 | 全部通过 |
| ② 活体计算样式 | CDP `getComputedStyle` / 运行时目录 `schemas()` 逐类核对 | 实测值 = 预期值 |
| ③ 实景截图 | 真实键鼠操作后 `Page.captureScreenshot` 存档 | 视觉上元素在场且形态正确 |

#### 证据通道交叉

| 通道 | 能看到 | 看不到 |
|------|--------|--------|
| 宿主诊断日志（jsonl） | face 装载/失败、agent.run、tool.execute | **error 字段是脱敏投影**（只剩「Error details omitted」） |
| CDP Runtime.consoleAPICalled | **完整错误对象**（含 stack） | 需要直连渲染端 |
| journal SQLite | run 状态/事件序列/phase/actor | 需 copyfile+WAL 才能查 |
| CDP DOM querySelector | **可见实例的 DOM**（过滤 checkVisibility） | 多实例共存时撞隐藏实例 |
| React 组件函数探针 | **可能被并发渲染丢弃**（假绿/假红） | 以提交后 DOM 为准 |

#### 取证假象清单

| 假象 | 根因 | 对策 |
|------|------|------|
| 入口忽有忽无 | 页签保活多 DOM 实例共存 | 取证过滤 checkVisibility / 按可见实例定位 |
| 源码改动不生效 | vite optimizeDeps 预打包缓存 | **改完重启 dev**，别在缓存上调 |
| 组件探针假绿/假红 | React 并发渲染丢弃函数调用 | 以提交后 DOM 为准，不信任函数执行探针 |
| 错误只剩脱敏占位 | 宿主诊断投影约束了 console | 直连渲染端 CDP 抓完整错误 |

#### 文件操作纪律

| 坑 | 症状 | 对策 |
|----|------|------|
| 多轮 stash pop 留 UU 冲突 | JSON 损坏 / vite 启动崩 | git status 的 UU 状态**即时清理** |
| rename 与 checkout 交错 | 文件版本混乱 | 以 git 为唯一真相，恢复后校验 |
| python 写文件被「回滚」 | 内容与写入不符 | 用 os.replace 原子写 + 立即读回校验 |
| shell heredoc 转义 | `\n` 变真实换行 / 反斜杠丢失 | 用 Edit 工具替代 python 写入 |
| JSON.stringify 隐式丢 undefined 键 | 面板状态假阴性 | 断言前检查键存在性 |

---

## 使用指南

### 新功能复刻时

1. 按 P1 画装配链路图 → 确认每条链端到端 → 找同款先例
2. 按 P2 检查四层声明面是否一致 → 补缺
3. 按 P3.1 三档验证 → 发现问题按 P3.2-P3.4 取证
4. 每完成一步 PDCA：Plan（方案）→ Do（实施）→ Check（三档验证）→ Act（提交+归档）

### 出问题时

1. 先按 P3.2-P3.4 排除取证假象
2. 再按 P1.3 排查多树/多实例
3. 最后按 P2 逐层检查四层声明面

### 实机验收时

- **前端交付必须截图看**——DOM 断言 ≠ 视觉验收
- 用 scenario.mjs 等声明式驱动器替代手写 CDP 循环
- 确保操作序列与截图之间无时序错位
