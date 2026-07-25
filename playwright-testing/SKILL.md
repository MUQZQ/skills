---
name: playwright-testing
description: ParamCompare 项目 Playwright 浏览器端到端测试。当用户提到"浏览器测试"、"UI自动化测试"、"E2E测试"、"页面测试"、"Playwright测试"、"端到端"、"端对端"、"测试页面操作"、"操作浏览器"、"写UI测试"、"截图验证"、"browser test"时必须使用。用于编写、运行和调试基于 Playwright 的 NiceGUI 应用浏览器测试，包括 Monaco Editor、AG Grid、Quasar 组件的交互测试。
---

# Playwright 浏览器测试

ParamCompare 是一个 **NiceGUI** (Quasar/Vue3 + FastAPI) 单页应用，当前 UI 测试使用 `nicegui.testing.User` 模拟器，多个关键测试因 **Quasar Splitter 懒加载**、**Monaco Editor Shadow DOM** 等问题被 skip。Playwright 可穿透这些复杂组件实现真实浏览器测试。

---

## 快速开始

### 1. 运行现有测试

```bash
# 所有单元测试 + E2E 测试
uv run pytest tests/ -v

# 仅运行浏览器 UI 测试（通过 nicegui.testing.User 模拟器）
uv run pytest tests/param_compare/test_e2e_ui.py -v

# 指定单个测试
uv run pytest tests/param_compare/test_e2e_ui.py::test_initial_empty_state -v
```

### 2. 启动应用（供 Playwright 连接测试）

```bash
uv run python -m param_compare.app.main
# 默认监听 http://localhost:27182（可通过 NICEGUI_PORT 环境变量覆盖）
# 测试中建议指定端口避免冲突：NICEGUI_PORT=27183 uv run python -m param_compare.app.main
```

### 3. 安装 Playwright 浏览器

> 详细安装指南（含镜像加速、网络排查）见 **[references/setup.md](references/setup.md)**。

### 4. 两种 API 模式

项目同时支持同步和异步 API，不要混用：

| 模式 | 导入 | 适用场景 |
|------|------|---------|
| **同步 API** | `from playwright.sync_api import sync_playwright` | 独立脚本、快速验证（如 `test_browser_quick.py`） |
| **异步 API** | `from playwright.async_api import async_playwright` | pytest-asyncio 测试（推荐用于测试文件） |

**同步示例**（脚本直跑）：
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:27182")
    page.wait_for_selector("text=ParamCompare")
    browser.close()
```

**异步示例**（pytest fixture）：
```python
import pytest
from playwright.async_api import async_playwright, Page

@pytest.fixture(scope="module")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser):
    page = await browser.new_page()
    yield page
    await page.close()

@pytest.mark.asyncio
async def test_initial_page_loads(page: Page):
    await page.goto("http://localhost:27182")
    await page.wait_for_selector("text=ParamCompare")
```

### 5. 编写 Playwright 测试文件

---

## 项目 UI 组件定位速查表

### 侧边栏 (Sidebar) — `sidebar.py`

| 目标 | 定位方式 |
|------|---------|
| AI 文件路径输入框 | `page.get_by_placeholder("AI 提取的 YAML 文件路径")` |
| GT 文件路径输入框 | `page.get_by_placeholder("Ground Truth YAML 文件路径")` |
| GT 库目录输入框 | `page.get_by_placeholder("GT 库目录路径")` |
| Manifest 路径输入框 | `page.get_by_placeholder("manifest.yaml 路径")` |
| 器件搜索框 | `page.get_by_placeholder("搜索器件...")` |
| "加载" 按钮 (AI) | `page.get_by_role("button", name="加载")` |
| "重新加载" 按钮 (GT) | `page.get_by_role("button", name="重新加载")` |
| "加载 Manifest" 按钮 | `page.get_by_role("button", name="加载 Manifest")` |
| "刷新全部对比" 按钮 | `page.get_by_role("button", name="刷新全部对比")` |
| "保存为 GT" 按钮 | `page.get_by_role("button", name="保存为 GT")` |
| "裁剪保存为 GT" 按钮 | `page.get_by_role("button", name="裁剪保存为 GT")` — 无GT文件时显示 |
| 对话框"确认保存"按钮 | `page.get_by_role("button", name="确认保存")` |
| P0 筛选复选框 | `page.get_by_role("checkbox", name="P0")` |
| P1 筛选复选框 | `page.get_by_role("checkbox", name="P1")` |
| P2 筛选复选框 | `page.get_by_role("checkbox", name="P2")` |
| "仅显示差异" 复选框 | `page.get_by_role("checkbox", name="仅显示差异")` |

### Diff 面板 (并排对比) — `diff_panel.py`

| 目标 | 定位方式 |
|------|---------|
| 上一个差异 | `page.locator(".diff-nav-prev")` |
| 下一个差异 | `page.locator(".diff-nav-next")` |
| 采用当前项 | `page.locator(".diff-accept")` |
| 全部采用 | `page.locator(".diff-accept-all")` |
| 忽略当前项 | `page.locator(".diff-ignore")` |
| 取消全部忽略 | `page.locator(".diff-unignore")` |
| Monaco 容器 | `page.locator("#monaco-diff-container")` |

### 主布局 — `main.py` (视图切换)

| 目标 | 定位方式 |
|------|---------|
| 切换并排对比 | `page.locator(".q-btn-toggle").get_by_role("button", name="📄 并排对比")` |
| 切换表格对比 | `page.locator(".q-btn-toggle").get_by_role("button", name="📊 表格对比")` |

> **注意**：视图切换是 Quasar QBtnToggle 组件，仅在双文件加载时显示，空状态/单文件模式下不存在。

### 表格视图 — `table_panel.py`

| 目标 | 定位方式 |
|------|---------|
| AG Grid 容器 | `page.locator(".ag-theme-balham")` |
| 筛选匹配行 | `page.get_by_role("button", name=re.compile("✓.*匹配"))` |
| 筛选不匹配行 | `page.get_by_role("button", name=re.compile("✗.*不匹配"))` |
| 筛选 AI 独有 | `page.get_by_role("button", name=re.compile("→.*AI独有"))` |
| 筛选 GT 独有 | `page.get_by_role("button", name=re.compile("←.*GT独有"))` |
| 清除筛选 | `page.get_by_role("button").filter(has=page.locator(".q-icon:has-text('filter_alt_off')"))` |
| "全部采用" 按钮 | `page.get_by_role("button", name=re.compile("全部采用"))` |
| "全部忽略" 按钮 | `page.get_by_role("button", name="全部忽略")` |
| 导出 CSV | `page.get_by_role("button", name="导出CSV")` |

### 树形视图 — `tree_panel.py`

| 目标 | 定位方式 |
|------|---------|
| 树搜索框 | `page.get_by_placeholder("搜索键名或值...")` |
| 展开全部 | `page.get_by_role("button", name="展开全部")` |
| 折叠全部 | `page.get_by_role("button", name="折叠全部")` |

GT 编辑模式下的批量操作工具栏（仅在进入 GT 编辑时显示）：

| 目标 | 定位方式 |
|------|---------|
| "全选" 按钮 | `page.get_by_role("button", name="全选")` |
| "反选" 按钮 | `page.get_by_role("button", name="反选")` |
| "清空" 按钮 | `page.get_by_role("button", name="清空")` |

### 键盘快捷键

| 按键 | 功能 | 测试写法 |
|------|------|---------|
| `j` | 下一个差异 | `page.keyboard.press("j")` |
| `k` | 上一个差异 | `page.keyboard.press("k")` |
| `Enter` | 采用当前差异 | `page.keyboard.press("Enter")` |
| `i` | 忽略当前差异 | `page.keyboard.press("i")` |
| `a` | 全部采用 | `page.keyboard.press("a")` |
| `u` | 取消全部忽略 | `page.keyboard.press("u")` |

---

## 关键测试场景

### 场景 1: 加载文件并验证匹配率

```python
async def test_load_files_shows_match_rate(page: Page):
    await page.goto(BASE_URL)

    # 填写路径
    await page.get_by_placeholder("AI 提取的 YAML 文件路径").fill(ai_path)
    await page.get_by_placeholder("Ground Truth YAML 文件路径").fill(gt_path)

    # 点击重新加载
    await page.get_by_role("button", name="重新加载").click()

    # 等待匹配率出现
    await page.wait_for_selector("text=95%", timeout=5000)
```

### 场景 2: Diff 导航（键盘操作）

```python
async def test_diff_keyboard_navigation(page: Page):
    # ... 先加载文件 ...
    # 依赖 diff 视图已渲染
    await page.wait_for_selector("#monaco-diff-container", timeout=5000)

    # 按 j 跳下一个差异
    await page.keyboard.press("j")
    # 验证差异导航计数器更新
    await page.wait_for_selector("text=/\\d+/\\d+")

    # 按 Enter 采用差异
    await page.keyboard.press("Enter")
```

### 场景 3: 表格视图 — 双击编辑单元格

```python
async def test_table_edit_cell(page: Page):
    # ... 先加载文件并切换到表格视图 ...
    await page.get_by_role("button", name="📊 表格对比").click()
    await page.wait_for_selector(".ag-theme-balham", timeout=5000)

    # 双击第一个行中的 AI 值单元格（AG Grid 是可编辑的）
    cell = page.locator(".ag-row").first.locator('[col-id="ai_val"]')
    await cell.dblclick()

    # 输入新值
    input_field = page.locator(".ag-cell-editor input")
    await input_field.fill("新值")
    await input_field.press("Enter")
```

### 场景 4: 通知/提示验证

```python
async def test_save_notification(page: Page):
    await page.get_by_role("button", name="保存为 GT").click()
    # NiceGUI 用 Quasar notify 弹出提示
    await page.wait_for_selector(".q-notification", timeout=3000)
    content = await page.locator(".q-notification__message").text_content()
    assert "已保存" in content
```

### 场景 5: Manifest 批量对比

```python
async def test_manifest_load_and_navigate(page: Page):
    await page.goto(BASE_URL)

    # 填写 manifest 路径
    await page.get_by_placeholder("manifest.yaml 路径").fill(manifest_path)
    await page.get_by_role("button", name="加载 Manifest").click()

    # 等待器件列表出现
    await page.wait_for_selector("text=LDO_3V3", timeout=5000)
    await page.wait_for_selector("text=2 个器件", timeout=5000)
```

---

## 测试文件模板

新建 `tests/param_compare/test_browser.py` 时，复制以下模板：

```python
"""Playwright 浏览器端到端测试 — 真实浏览器渲染验证"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, Page, Browser

SANDBOX = Path(__file__).resolve().parent.parent.parent / "sandbox"
AI_PATH = str(SANDBOX / "ai" / "LDO_3V3_ai_params.yaml")
GT_PATH = str(SANDBOX / "gt" / "LDO_3V3_gt.yaml")
MANIFEST_PATH = str(SANDBOX / "manifest.yaml")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:27183")

# ---------------------------------------------------------------------------
# Fixture: 启动 NiceGUI 服务器 + 浏览器
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_url():
    """启动 NiceGUI 应用，返回 URL，测试结束后关闭"""
    env = os.environ.copy()
    # 使用非默认端口避免冲突
    env.setdefault("NICEGUI_PORT", "27183")
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "param_compare.app.main"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env,
    )
    # 轮询等待服务就绪，比固定 sleep 更可靠
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            import httpx
            httpx.get(BASE_URL, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    yield BASE_URL
    proc.terminate()
    proc.wait()

@pytest.fixture(scope="module")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser: Browser, server_url: str):
    page = await browser.new_page()
    await page.goto(server_url)
    yield page
    await page.close()


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initial_page_renders(page: Page):
    """页面初始加载：显示标题和空状态提示"""
    await page.wait_for_selector("text=ParamCompare", timeout=3000)
    await page.wait_for_selector("text=加载 AI 与 GT 文件开始对比", timeout=3000)


@pytest.mark.asyncio
async def test_load_files_detects_mismatch(page: Page):
    """加载 AI+GT 文件：检测到 Dropout Voltage 差异"""
    # 输入路径
    await page.get_by_placeholder("AI 提取的 YAML 文件路径").fill(AI_PATH)
    await page.get_by_placeholder("Ground Truth YAML 文件路径").fill(GT_PATH)

    # 点击重新加载
    await page.get_by_role("button", name="重新加载").click()

    # 等待匹配率出现（不匹配时不会是 100%）
    await page.wait_for_selector("text=/\\d+%/", timeout=5000)


@pytest.mark.asyncio
async def test_manifest_loading_shows_devices(page: Page):
    """Manifest 加载：显示器件列表"""
    await page.get_by_placeholder("manifest.yaml 路径").fill(MANIFEST_PATH)
    await page.get_by_role("button", name="加载 Manifest").click()

    await page.wait_for_selector("text=2 个器件", timeout=5000)
    await page.wait_for_selector("text=LDO_3V3", timeout=3000)
```

---

## 核心注意事项

### 1. Quasar Splitter 不再受限

NiceGUI `User` fixture 无法穿透 `.q-splitter__after`，但 Playwright 使用真实浏览器渲染，**所有 slot 内容都可正常访问**。之前被 skip 的测试（`test_accept_all_reaches_full_match`、`test_ignore_current_diff` 等）现在都可以用 Playwright 实现。

### 2. Monaco Editor 操作

Monaco Editor 内容在 Shadow DOM 中，常规 `fill()` 无效。使用以下方式：

```python
# 聚焦 Monaco 编辑器并输入
monaco = page.locator("#monaco-diff-container")
await monaco.click()

# 使用 Monaco 的键盘操作
await page.keyboard.press("Control+a")   # 全选
await page.keyboard.type("new content")  # 输入

# 或通过 Monaco API 设置内容
await page.evaluate("""
    const editor = document.querySelector('#monaco-diff-container').__vue_app__;
    // 通过 Quasar/Vue ref 访问 editor 实例
""")
```

### 3. AG Grid 操作

AG Grid 是 Canvas-based 渲染，DOM 中 `.ag-row` 是虚拟行。必须等待数据加载完成：

```python
# 等待 AG Grid 数据加载
await page.wait_for_selector(".ag-row", timeout=5000)

# 双击编辑
cell = page.locator(".ag-row").first.locator('[col-id="ai_val"]')
await cell.dblclick()
```

### 4. 异步等待

NiceGUI 通过 WebSocket 推送更新，页面不会整页刷新。关键模式：

```python
# ✅ 等待内容出现
await page.wait_for_selector("text=95%", timeout=5000)

# ✅ 等待网络空闲后再操作
await page.wait_for_load_state("networkidle")

# ❌ 不要用 time.sleep() — 用 wait_for_selector 更可靠
```

> **服务启动等待**：fixture 中启动应用后，用 HTTP 轮询代替固定 `time.sleep()`：
> ```python
> import httpx
> for _ in range(30):
>     try:
>         httpx.get(BASE_URL, timeout=1)
>         break
>     except Exception:
>         time.sleep(0.5)
> ```

### 5. 通知 (Quasar Notify)

```python
await page.wait_for_selector(".q-notification", timeout=3000)
msg = await page.locator(".q-notification__message").text_content()
```

---

## 运行命令

```bash
# 先启动应用（在另一个终端，或由 fixture 自动启动）
uv run python -m param_compare.app.main

# 然后运行 Playwright 测试（普通模式，无头浏览器）
uv run pytest tests/param_compare/test_browser.py -v

# 有头浏览器调试（需在 fixture 中设置 headless=False）
# 方法1: 直接修改测试文件中的 launch(headless=True) → launch(headless=False)
# 方法2: 安装 pytest-playwright 插件后使用 --headed 参数
#   uv add --dev pytest-playwright
#   uv run pytest tests/param_compare/test_browser.py -v --headed

# 仅运行同步脚本（不依赖 pytest）
uv run python tests/test_browser_quick.py
```

## 常见错误与处理

| 错误 | 原因 | 处理方式 |
|------|------|---------|
| `net::ERR_CONNECTION_REFUSED` | 应用未启动或端口冲突 | 检查应用是否运行，确认端口未被占用 |
| `wait_for_selector` 超时 | 元素未渲染、选择器错误或页面仍在加载 | 先检查 `page.content()` 确认页面状态，调整 wait timeout |
| Monaco Editor 操作无效 | 内容在 Shadow DOM 中，常规 `fill()` 无效 | 改用 `page.keyboard.type()` 或 Monaco API |
| AG Grid 行定位失败 | 虚拟滚动，行未在 DOM 中 | 先滚动到目标行位置，确保其进入视口 |
| `q-notification` 定位不到 | 通知已消失或尚未出现 | 使用 `wait_for_selector` 等待，必要时增加 timeout |
| fixture 端口冲突 | 指定端口被其他进程占用 | 更换端口号，或使用 `url_for` 动态分配 |
| 异步/同步 API 混用 | `sync_playwright` 中调用 `await` 或反之 | 检查导入来源，确保 API 模式一致 |

## 参考文档索引

| 文档 | 用途 |
|------|------|
| `references/setup.md` | Playwright 安装指南（含镜像加速、网络排查） |
| `tests/param_compare/test_browser.py` | 浏览器测试文件模板 |
| `tests/test_browser_quick.py` | 同步 API 快速验证脚本 |

---

当 opencode 已配置 Playwright MCP 时，可在对话中直接操控浏览器测试应用：

```
打开 http://localhost:27182 ，等待页面加载，截图看看当前状态
```

Playwright MCP 工具可用于：
- **交互探索**：实时操控浏览器，探索 NiceGUI 渲染后的真实 DOM 结构
- **快速回归**：手动加载文件、点击按钮、截图对比
- **元素定位**：通过 `page.locator()` 验证选择器是否有效
- **调试辅助**：当 NiceGUI User fixture 无法覆盖时，用 MCP 快速验证
