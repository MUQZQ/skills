# bootstrap/dynamic-workflow 测试移植状态（ZCode bootstrap/tests 直移）

来源：ZCode-main apps/zcode-cli/packages/bootstrap/tests（54 文件/959 用例），
按 QEDAgent 扁平 src 形态映射 import（../src/app/X.js → ../src/X.ts，
@zcode/{contracts,dynamic-workflow} → @qedagent/*）。

## ✅ 已通过（直移即绿）
- dynamic-workflow-run-holes.test.ts
- dynamic-workflow-run-label.test.ts
- dynamic-workflow-run-sequence-capture.test.ts
- workflow-git-world-read-real.test.ts

## ⏳ 已拷贝待适配（全部移至 tests-pending/ 目录——根 vitest 默认 include 只扫 *.test.ts，
放 tests/ 内改后缀仍会被部分运行形态扫到；适配完成后改回 tests/*.test.ts。
待适配清单含两类：约 20 个 @zcode/adapters|core|shared|protocol-v4 替身依赖
（需按 QEDAgent 端口/storage 形态重写），4 个近绿件（import 的会话 id 语义、
artifacts-projection 的单断言、launch-anchor 与 escalation 的 helper 缺失）。）（fixture 用 ZCode 形态，需按 QEDAgent 语义改写）
- dynamic-workflow-import.test.ts —— actor 会话 id 形态差异（ZCode `sess-A`
  vs QEDAgent `runId:site`），fixture 需按 QEDAgent 形态重写
- dynamic-workflow-run-artifacts-projection.test.ts —— 单布尔断言差，查因中
- workflow-escalation.test.ts —— import workflow-actor-tools.ts（QEDAgent 该
  面在 orchestration/actor-session-tools）与 helpers 缺
- dynamic-workflow-run-launch-anchor（缺 ZCode 测试 helper 模块）、
  progress-sink / elapsed / workspace / roster / report-reads —— 依赖
  @zcode/adapters/storage 或 protocol-v4 类型，需按 QEDAgent
  storage/roster 形态改写替身
- workflow-escalation —— import workflow-actor-tools.ts（QEDAgent 该面在
  orchestration/actor-session-tools）

## ❌ 已删除（QEDAgent 未移植对应模块，测试无对象）
- workflow-concurrency-governor / workflow-driver-quiescence /
  workflow-seat-gate / workflow-driver-seat-gate —— 席位闸门与静默判定内联在
  QEDAgent 的 workflow-driver.ts / run-service 重写形态中，无独立模块
- workflow-driver-ask-progress / workflow-fault-matrix.* —— 缺 ZCode 测试
  helpers（workflow-driver.helpers.js / fake-provider-server.ts）
- dynamic-workflow-policy —— zcode-protocol/policy 模块未移植
- workflow-driver-world-run —— escalation-registry 命名差异（QEDAgent 为
  escalation-registry.ts），改 import 后可回补
- workflow-driver.test / driver-concurrency / driver-submit-profile /
  child-spawn / run-control —— driver 装配形态差异（@zcode/adapters/core
  替身依赖），需按 QEDAgent driver-types 形态重写
