---
name: qeda-integration
description: QEDA 测试集成审查规则
origin: pcb-mcp
requires_source: true
source_context: shared_snippets
---

# QEDA 测试集成审查

## 上下文协议

本 skill 从 code-review 协调层接收 **共享源码片段**（`shared_snippets`）。

审查输入包含：
1. **变更文件**: 待审查的代码文件
2. **共享上下文**: `【共享上下文：{模块路径}】...【共享上下文结束】` 标记的代码片段

**审查规则**:
- 审查目标始终是**测试覆盖完整性**
- 按 P0/P1/P2 优先级输出问题列表

## 何时激活

- **任何代码审查时都应用此规则**
- 新增/修改 API 端点
- 新增/修改前端组件
- Bug fix
- 重构代码

## 测试覆盖检查

### 变更类型 → 测试层级映射

| 变更类型 | L2 | L3 | L4 | L5 |
|---------|----|----|----|----|
| 新增/修改 API 响应格式 | ✓ | ✓ | ✓ | - |
| 新增前端组件 | ✓ | ✓ | **✓ P** | - |
| 修改前端渲染逻辑 | ✓ | ✓ | **✓ P** | - |
| 新增 Python 函数/模块 | ✓ | ✓ | - | - |
| 新增 API 端点 | ✓ | ✓ | **✓ E** | - |
| 修改前端↔后端交互协议 | ✓ | ✓ | ✓ | **✓** |
| 涉及 SCH/PCB 真实交互 | ✓ | ✓ | - | **✓** |
| 新增 MCP tool | ✓ | ✓ | - | - |
| Bug fix | ✓ | **✓ 回归** | 视范围 | - |

**说明**:
- L4 标记 **P** = Playwright mock e2e，**E** = Python e2e（tests/e2e/）
- L5 直接连真实服务，无需 mock

### 测试文件位置

| 测试类型 | 文件位置 | 运行命令 |
|---------|---------|---------|
| L2/L3 单元测试 | `tests/test_*.py` | `uv run pytest` |
| L3 前端单元测试 | `frontend/src/**/*.test.{ts,tsx}` | `pnpm vitest run` |
| L4 Python e2e | `tests/e2e/` | `uv run pytest tests/e2e/` |
| L4 前端 e2e | `frontend/e2e/` | `pnpm exec playwright test` |
| 全量门禁 | `scripts/gate/verify.sh` | `bash scripts/gate/verify.sh` |

## 执行步骤

### Step 1: 写产品代码

正常实现功能。不需要在这一步想测试。

### Step 2: 写 L3 单元测试

每个新增函数/组件/route handler 都要有对应单元测试。

```python
# tests/test_component.py
def test_get_component_info_returns_valid_component():
    """测试获取有效元件信息。"""
    component = get_component_info("C1")
    assert component is not None
    assert component.id == "C1"
```

```typescript
// frontend/src/components/ComponentInfo.test.tsx
test('displays component information correctly', () => {
  render(<ComponentInfo componentId="C1" />);
  expect(screen.getByText(/C1/)).toBeInTheDocument();
});
```

### Step 3: L4 强制检查（关键步骤）

**这一步是本 skill 存在的核心原因。做完 L3 后必须停下来回答以下问题：**

**问题 A：改了前端组件或渲染逻辑？**
→ 必须在 `frontend/e2e/` 下有对应 spec 文件
→ 参考 `.claude/skills/create-e2e-test` 了解 mock 方案
→ 运行 `pnpm exec playwright test` 验证

**问题 B：新增了 Python API 端点或 MCP tool handler？**
→ 必须在 `tests/e2e/` 下有对应 e2e 测试
→ 参考 `tests/e2e/conftest.py` 了解 server 启动 + mock PCB client 模式
→ 运行 `uv run pytest tests/e2e/` 验证

**如果 A 和 B 都不适用 → 跳过 L4**

### Step 4: 运行验证

```bash
# L2+L3+L4: 全量门禁（必跑）
bash scripts/gate/verify.sh

# 或按需单独跑：
uv run pytest                              # Python 单元测试
uv run pytest tests/e2e/                   # Python e2e
cd frontend && pnpm vitest run             # 前端单元测试
cd frontend && pnpm exec playwright test   # 前端 e2e
```

## 完成前自检

声明"完成"之前，逐项确认：

- [ ] 新增的前端组件 → `frontend/e2e/` 下有对应 `.spec.ts`？
- [ ] 新增的 API 端点 → `tests/e2e/` 有对应测试？
- [ ] Bug fix → 有回归测试覆盖出 bug 的具体 case？
- [ ] `uv run pytest` 通过？
- [ ] `pnpm vitest run` 通过？
- [ ] `playwright test` 通过（如有前端 L4 变更）？

**任何一项未通过 → 不能标记完成。**

## 提交规范

- 测试代码和产品代码在同一 commit 中提交
- commit message 遵循 `type(scope): 中文描述`
- 测试用例较多时可单独 commit，但同一 PR 内

## 不需要做的事

- 不为纯重构写新 L4/L5 测试——只更新受影响的现有测试
- 纯配置变更（pyproject.toml、vitest.config.ts）不需要测试
- 不要创建不必要的测试文件——优先编辑现有文件
- 不要写注释多的测试代码——和产品代码一样保持简洁

## 审查检查清单

### 测试覆盖

- [ ] 新增函数/组件有对应 L3 单元测试
- [ ] 新增 API 端点有对应 L4 e2e 测试
- [ ] 新增前端组件有对应 L4 Playwright 测试
- [ ] Bug fix 有回归测试覆盖

### 测试质量

- [ ] 测试命名清晰描述测试意图
- [ ] 测试可独立运行，无顺序依赖
- [ ] 测试使用正确的 mock/stub
- [ ] 测试断言准确，不过度断言

### 测试运行

- [ ] `uv run pytest` 全部通过
- [ ] `pnpm vitest run` 全部通过
- [ ] `playwright test` 全部通过（如有）
- [ ] 全量门禁 `bash scripts/gate/verify.sh` 通过

### 测试文件组织

- [ ] 测试文件命名符合 `test_*.py` / `*.test.tsx`
- [ ] E2E 测试文件位置正确（`tests/e2e/` 或 `frontend/e2e/`）
- [ ] 测试代码与产品代码分离

## 最佳实践

1. **测试优先** - 先写测试，再实现功能
2. **单一职责** - 每个测试只验证一个行为
3. **独立运行** - 测试之间无依赖，可并行执行
4. **清晰命名** - 测试函数名描述测试场景和预期
5. **适度 Mock** - 只 Mock 外部依赖，不 Mock 业务逻辑
6. **完整覆盖** - 关键路径必须有测试覆盖
