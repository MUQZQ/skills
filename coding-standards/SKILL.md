---
name: coding-standards
description: 跨语言通用编码规范（通用核心条款 + Python/Go/JS-TS/Java/Rust 各语言小节），融合大厂规约精华（阿里异常处理/华为安全编码/Google 风格）与通用工程教训（静默失败/行为验证/精确断言）。使用场景：(1) 写代码/生成代码时需遵守编码规范 (2) 审查代码时作为检查清单逐条核对 (3) 为新项目/新仓库创建 AGENTS.md 规范章节或全局层时作为模板 (4) 用户要求"按规范写""代码风格检查""配一套编码规范""规范模板"。触发词：编码规范、代码规范、coding standards、code style、按规范、规范检查。
---

# 通用编码规范（跨语言 v1）

> **文档定位**：本文件是编码规范的**单一权威来源**（独立 skill，git 版本管理），编码与检视两侧均只做关联引用，不做内容复制。

**关联方**：
- **编码侧**：权威 AGENTS.md 的 R8 强制规则（每会话加载，编码时生效）
- **检视侧**：`code-review` 各语言子技能（lang-python/lang-go/lang-js/lang-ts/lang-react）审查时加载对应小节逐条核对
- **变更原则**：规范调整只改本文件；引用方不需要改动（引用即生效）

**参数化原则**：条款中的版本/行宽/工具（py312、100、gofmt、ESLint 等）均为默认值，项目配置优先；本规范只约束"必须有"，不强制"必须用某版本"。

**冲突仲裁**：各语言 lang-* 详细清单（工程单位、领域细节等）为本规范的领域补充；有冲突时以本规范为准。

## 通用核心条款（所有语言适用）

1. **错误处理**：禁止静默失败——被捕获的错误必须记录（含上下文）后重抛或返回；捕获要具体，禁止宽泛兜底（裸 except / catch(Exception) / panic 业务化）
2. **外部输入不可信**：API/网页/配置文件/环境变量默认不可信，先校验（类型、范围、非空）再使用
3. **日志**：统一日志组件（logging/zerolog/console），级别语义 DEBUG 细节 / INFO 正常 / WARNING 降级重试 / ERROR 失败；禁用 print 调试；敏感信息脱敏
4. **外部调用**：必须设超时；失败走显式降级链 + 告警，不用隐式回退
5. **安全红线**：密钥/Token/凭证永不进代码、commit、日志；只走环境变量或 .env（.env 必须入 .gitignore）；输出一律脱敏
6. **数值敏感**：金额用精确类型（Decimal/BigDecimal/decimal），禁止浮点直接比较；JSON/配置解析用显式字段提取，禁止模糊模式匹配
7. **时间**：统一时区（存储 UTC、展示本地）；高精度时间戳用时间对象（datetime/Instant），不用裸整数
8. **并发**：共享状态原子写或加锁；长轮询/重试带退避 + 熔断
9. **格式工具强制**：提交前必须通过对应工具链（ruff/gofmt+vet/eslint+prettier/clippy）
10. **测试**：新逻辑必带测试，命名 test_<行为>；断言精确，禁止模糊匹配
11. **行为验证**：改动后必须验证真实行为（运行/重启/实测），"文件一致/配置正确"不可信
12. **提交纪律**：临时文件/审查记录/中间产物不入 git；涉及生产/主分支的提交先确认；commit 信息 conventional 格式
13. **输出约定**：代码、注释、日志、commit 不使用 emoji 字符
14. **命名原则**：按语言规范（见各小节）；类/类型 PascalCase；常量全大写；布尔用 is_/has_/should_ 前缀

## Python 小节

1. docstring 遵循摘要 + Args/Returns 结构（Google 风格），全项目统一语言
2. 类型注解：新代码必须完整注解（含 `x | None` 语义），公开 API 必须有类型；模块头加 `from __future__ import annotations`
3. 命名 snake_case（变量/函数/方法）、UPPER_SNAKE（常量）；配置类用 @dataclass + 默认值，禁止魔法值散落
4. 日志懒格式化 `"%s", val`，禁止 f-string 拼日志（f-string 仅限普通字符串）
5. import 分组：标准库 → 第三方 → 项目内，组内字母序
6. 类型改动不得新增 mypy 错误（若项目启用 mypy）
7. 遵循项目 pyproject.toml（默认行宽 100 / py312）；提交前 ruff check 通过

## Go 小节

1. 提交前 gofmt + go vet + golangci-lint 通过；依赖 go.mod 锁定
2. 错误显式返回（error 为最后返回值），禁止 panic 处理业务错误（panic 仅限不可恢复场景并注释）
3. 错误必须处理或显式忽略：`if err != nil` 分支不得静默；`_ = err` 需有注释说明
4. context 传播（超时/取消/元数据），不存为 struct 字段
5. 资源清理用 defer（文件/连接/锁）
6. 命名：导出 camelCase 首字母大写，接口小而精；常量 iota 场景按惯例
7. 并发：goroutine 生命周期受控（WaitGroup/context/errgroup），channel 关闭规范，避免 goroutine 泄漏
8. 安全场景用 crypto/rand 而非 math/rand

## JS/TS 小节

1. 提交前 ESLint + Prettier 通过；ESM 严格模式；lockfile（package-lock/pnpm-lock）提交
2. const/let，禁 var；可变优先 const
3. === / !== 严格相等，禁止隐式类型转换
4. async/await 必须处理错误：try/catch 或 .catch，禁止未处理 Promise 拒绝；禁止裸 catch 吞错
5. TS：公开接口显式类型，避免 any 泛滥；工具类型收窄
6. 可选链 ?. 与空值 ?? 替代 && / || 的隐式解数
7. 依赖安全：npm audit 无高危；依赖版本锁定

## Java 小节

1. 遵循阿里《Java 开发手册》强制条目（命名/异常/集合/并发/日期/浮点），IDE 配 p3c 插件扫描
2. 异常：不吞、不放 Exception 兜底；日志用 SLF4J 占位符 `logger.info("k={}", v)`，禁字符串拼接
3. 集合：明确初始容量；Map 遍历用 entrySet；禁止 foreach 中增删元素
4. 并发：线程池统一管理（禁无界池），锁粒度最小，volatile/原子类语义明确
5. 日期：LocalDateTime/LocalDate 替代 Date/Calendar；存储 UTC、展示带时区
6. 浮点比较用 BigDecimal；金额禁止 double
7. 可选值用 Optional 表达语义，禁止空集合/ null 魔法；依赖 BOM 统一版本

## Rust 小节

1. 提交前 cargo fmt + cargo clippy（-D warnings）通过
2. Result 处理：禁止业务代码 unwrap/expect；错误分层（库 thiserror / 应用 anyhow）
3. unsafe 最小化：禁止无理由 unsafe，必须注释安全论证
4. panic 语义：仅不可恢复错误；库代码禁止 panic 暴露给调用方
5. 引用/所有权：避免无谓 clone/Arc，借用生命周期明确；pub 暴露最小化
6. async：统一运行时（tokio），任务取消/超时处理，tracing 用于日志
7. 常量与枚举：错误枚举语义化，避免裸数字码

## 来源说明

- 核心 1-3：阿里 p3c《Java 开发手册》强制条目（异常/日志，跨语言通用）+ 华为《C&C++ 安全编程规范》（外部数据不可信）
- 各语言小节：Google Style Guides（Python/Go/JS）、阿里手册（Java）、Rust 官方惯例（Clippy）
- 通用教训抽象：静默失败、行为验证、精确断言、参数化默认值
