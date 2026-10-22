# 项目取证工具箱登记表

evidence-driven-dev 的项目专属适配登记。**首次**在某项目做探针/取证时,先探明本机/关联仓的现成测试基建,验证可用后按下方模板登记;此后同项目直接查表复用,不重复发现、不重写脚本。本表只放指针与一句用途,工具细节以工具箱自己的 README/AGENTS.md 为唯一事实源。

## 登记表

### QEDAgent / QEDA 桌面应用

- **工具箱**:`E:\QEDAReview`(PR 评审与验证工具仓;被评审产品仓为 QEDA/QEDAgent)
- **登记日**:2026-10-22
- **用法**:`node scripts/<脚本>.mjs`;参数与全量清单见 `E:\QEDAReview\README.md`,行为约束见其 `AGENTS.md`
- **核心脚本**(验证/取证相关):

| 脚本 | 用途 |
|------|------|
| `scripts/scenario.mjs` | 声明式场景驱动:同一串操作在 before/after 实例各跑一遍,自动出观察点对照表;`record --port` 倒出页面锚点,替代手写 CDP 探针 |
| `scripts/app.mjs` | 应用/替身服务生命周期编排:同步等真就绪(日志 ready+调试端口目标,不靠 sleep)、独立 EDA bridge 端口、进程组收干净 |
| `scripts/shot.mjs` | CDP 页内截图(`--port 9222` 连现成 dev 实例) |
| `scripts/native-shot.mjs` | 原生 UI 取证:tooltip/右键菜单等渲染进程外画面;`--hover-selector` 真实光标悬停 |
| `stubs/fake-model.mjs` | OpenAI 兼容脚本化模型替身:验依赖模型/外部服务的功能,配 `app.mjs serve` 起停 |
| `lib/cdp.mjs` / `lib/fixtures.mjs` | CDP 直控助手(连接/取值/点击/受控输入/截图)与场景前奏/就绪判定 |

- **配套纪律**:桌面应用增量纪律(全屏截图、剪贴板+UIA 交互、前台恢复)见 SKILL.md 黑盒探针一节

## 新项目首次适配模板

复制以下字段登记;没有现成基建的项目如实记"无",不要为登记而造工具。

- **工具箱**:`<本机路径>`(一句话说明是什么)
- **登记日**:`<YYYY-MM-DD>`
- **用法**:`<入口命令>`,详见 `<README 路径>`
- **核心脚本**:只列验证/取证相关,表格式"脚本|用途"
