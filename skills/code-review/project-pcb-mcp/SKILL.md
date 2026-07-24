---
name: project-pcb-mcp
description: PCB MCP Server 项目代码审查规则
origin: pcb-mcp
requires_source: true
source_context: shared_snippets
---

# PCB MCP Server 项目代码审查

## 上下文协议

本 skill 从 code-review 协调层接收 **共享源码片段**（`shared_snippets`）。

审查输入包含：
1. **变更文件**: 待审查的代码文件
2. **共享上下文**: `【共享上下文：{模块路径}】...【共享上下文结束】` 标记的代码片段

**审查规则**:
- 审查目标始终是**变更代码**
- 共享上下文标注为"仅供审查参考"
- 按 P0/P1/P2 优先级输出问题列表

## 何时激活

- 变更涉及 `src/pcb_mcp/`
- 变更涉及 `frontend/`
- 变更涉及 `tests/`
- 变更涉及 `AGENTS.md`
- 变更涉及 `pyproject.toml`
- **任何 PCB MCP 项目代码审查时都应用此规则**

## 项目架构

- **WebSocket 桥接 + MCP HTTP Server**: 双协议支持
- **工具组注册机制**: 按功能分组暴露工具
- **测试分层**: L2/L3/L4/L5 完整覆盖

### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| MCP 服务器 | `src/pcb_mcp/server.py` | 资源/提示词注册，工具转发 |
| WebSocket 服务器 | `src/pcb_mcp/ws_server.py` | WebSocket 连接管理 |
| PCB 客户端 | `src/pcb_mcp/pcb_client.py` | PCB 工具调用封装 |
| 工具注册表 | `src/pcb_mcp/tools/registry.py` | 工具装饰器，转发逻辑 |
| 工具组路由 | `src/pcb_mcp/tools/__init__.py` | 工具组分组，HTTP 路由 |

## 目录约定

| 目录 | 用途 | 审查要点 |
|------|------|---------|
| `src/pcb_mcp/tools/` | 工具组 | 注册机制、命名规范、分组正确 |
| `src/pcb_mcp/server.py` | MCP 服务器 | 资源/提示词注册正确 |
| `src/pcb_mcp/ws_server.py` | WebSocket 服务器 | 连接管理、消息处理 |
| `src/pcb_mcp/` | 核心模块 | 遵循 AGENTS.md 约定 |
| `frontend/` | 前端代码 | i18n、加载状态、错误处理 |
| `tests/` | 测试代码 | L3/L4 覆盖，测试命名 |

### 工具组命名规范

```python
# 工具组目录命名：kebab-case
src/pcb_mcp/tools/
├── board_display/    # 板级显示相关
├── auto_routing/     # 自动布线相关
├── place_by_page/    # 按页放置相关
└── edit/             # 编辑操作相关

# 工具命名：snake_case
@tool("get_board_info")
def get_board_info(...) -> ...:
    ...
```

## 配置管理

### 环境变量优先级

```
配置优先级 (从高到低):
1. 环境变量 (MCP_PORT, WS_PORT, PCB_SERVER_URL, etc.)
2. .env 文件
3. 默认值
```

### 关键配置项

| 配置项 | 说明 | 审查要点 |
|--------|------|---------|
| `MCP_PORT` | MCP HTTP 服务端口 | 不硬编码，支持配置 |
| `WS_PORT` | WebSocket 服务端口 | 不硬编码，支持配置 |
| `PCB_SERVER_URL` | PCB 服务器地址 | 支持内网/外网配置 |
| `LOG_LEVEL` | 日志级别 | 开发/生产环境区分 |

## Python/uv 规范

### 强制规则

- **必须使用 `uv run` 执行脚本**，禁止 `python`/`python3`/`pip`
- **必须使用 `uv sync` 管理依赖**，禁止 `pip install`

```bash
# ✅ 正确 - 使用 uv run
uv run python -m pcb_mcp
uv run pytest
uv run ruff check

# ❌ 错误 - 直接调用 python
python -m pcb_mcp
pip install -e .
```

### 编码规范

```python
# ✅ 正确 - 类型提示完整
from typing import Optional, List

def get_component_info(
    component_id: str,
    include_pins: bool = False
) -> Optional[ComponentInfo]:
    """获取元件信息。
    
    Args:
        component_id: 元件标识符
        include_pins: 是否包含引脚信息
        
    Returns:
        元件信息对象，不存在时返回 None
    """
    ...

# ❌ 错误 - 缺少类型提示
def get_component_info(component_id, include_pins=False):
    ...
```

## 工具组实现规范

### 工具注册

```python
# ✅ 正确 - 使用 tool 装饰器
from pcb_mcp.tools.registry import tool

@tool("get_component_info")
async def get_component_info(
    component_id: str,
    include_pins: bool = False
) -> dict:
    """获取元件信息。"""
    ...

# ❌ 错误 - 未使用装饰器
async def get_component_info(component_id):
    ...
```

### 工具组注册

```python
# src/pcb_mcp/tools/board_display/__init__.py
from pcb_mcp.tools.registry import register_tools

def register_board_display_tools():
    """注册板级显示工具组。"""
    return [
        "get_board_info",
        "get_component_info",
        "get_net_info",
    ]

# 在 __init__.py 中注册
from pcb_mcp.tools.board_display import register_board_display_tools

TOOLSET_GROUPS["board-display"] = ["board", "display"]
_GROUP_REGISTRY["board_display"] = register_board_display_tools
```

## 测试规范

### 测试分层

| 层级 | 说明 | 文件位置 | 运行命令 |
|------|------|---------|---------|
| L2 | 集成测试 | `tests/test_*.py` | `uv run pytest` |
| L3 | 单元测试 | `tests/test_*.py` | `uv run pytest` |
| L4 | E2E 测试 | `tests/e2e/` | `uv run pytest tests/e2e/` |

### 测试命名规范

```python
# ✅ 正确 - 测试函数命名清晰
def test_get_component_info_returns_valid_component():
    """测试获取有效元件信息。"""
    ...

def test_get_component_info_returns_none_for_invalid_id():
    """测试无效元件 ID 返回 None。"""
    ...

# ❌ 错误 - 命名不清晰
def test1():
    ...
```

## 审查检查清单

### 项目架构

- [ ] 工具组按功能正确分组
- [ ] 工具注册机制正确实现
- [ ] WebSocket 连接管理正确
- [ ] MCP 服务器资源/提示词注册正确

### 目录约定

- [ ] 工具组目录命名符合 kebab-case
- [ ] 工具函数命名符合 snake_case
- [ ] 测试文件命名符合 `test_*.py`
- [ ] 文件位置符合约定

### 配置管理

- [ ] 端口配置不硬编码
- [ ] 环境变量优先级正确
- [ ] API Key 通过环境变量读取

### Python/uv 规范

- [ ] 使用 `uv run` 执行脚本
- [ ] 使用 `uv sync` 管理依赖
- [ ] 类型提示完整
- [ ] 文档字符串完整

### 工具组实现

- [ ] 使用 `@tool` 装饰器注册
- [ ] 工具组注册正确
- [ ] 工具参数验证正确
- [ ] 错误处理完整

### 测试覆盖

- [ ] L3 单元测试完整
- [ ] L4 E2E 测试必要场景覆盖
- [ ] 测试命名清晰
- [ ] 测试可独立运行

### 安全

- [ ] API Key 未硬编码
- [ ] 输入验证完整
- [ ] 错误消息不泄露内部详情
- [ ] **禁止 eval 注入** — 用户输入不得通过 f-string 直接拼接到 `ws_server.send_browser_action("evaluate", {"function": f"...{user_input}..."})` 中，必须通过 `_CUSTOM_INVOKE_HANDLERS` 以参数安全传入
- [ ] **bridge.js 分层** — jsonCache 读取放 `_CUSTOM_INVOKE_HANDLERS`（通过 `sch_page_invoke` 调用），DOM 操作放独立 browser_action（通过 `send_browser_action` 调用），禁止混用
- [ ] **IndexedDB 数据源优先** — 当工具需要获取工程数据（原理图列表、图页列表、图页详情）时，优先使用 IndexedDB 直连查询（`indexeddb_get` / `indexeddb_get_by_index`），而非不可靠的后端 HTTP API（`sch_client`）。已确认稳定的 store：`projectInfo`（工程信息）、`schSheetData`（图页数据）
- [ ] **双数据源回退** — IndexedDB 路径依赖 `ws_server` 已连接，必须保留 `ws_server is None` 时的 `sch_client` HTTP API 回退分支，确保测试环境和脱机场景下工具仍可用
- [ ] **bridge.js 返回值解析** — 从 `send_browser_action` 接收返回值时，必须处理 `str` 类型的 JSON 字符串（`json.loads`），因 bridge.js 在某些场景下返回未解析的 JSON 字符串而非 `dict`
- [ ] **_parse_idb_result 模式** — IndexedDB 查询返回格式多样（`dict.value`、`dict.result`、`dict.data`、`list` 直接、`str` JSON），应使用统一的 `_parse_idb_result(raw)` 辅助函数处理，兼容所有格式

## 设计模式

### IndexedDB 数据源替换模式

当后端 HTTP API 参数格式不确定或行为异常时，可通过 IndexedDB 直连替代：

```python
# ✅ 正确: IndexedDB 优先 + sch_client 回退
async def sch_get_schematics(project_uuid: str) -> str:
    if ws_server is not None:
        raw = await ws_server.send_browser_action("indexeddb_get", {
            "db_name": project_uuid,
            "store_name": "projectInfo",
            "key": project_uuid,
        })
        data = _parse_idb_result(raw)
        info = data[0] if data else {}
        boards = info.get("all", info).get("boards", [])
        # ... 从 boards 构建返回数据
    else:
        result = await sch_client.list_schematics_async(project_uuid)
        return json.dumps(result, ...)

# ❌ 错误: 仅依赖不可靠的 HTTP API (参数格式未知时)
result = await sch_client.list_schematics_async(project_uuid)
```

### _parse_idb_result 统一解析

```python
def _parse_idb_result(raw) -> list[dict]:
    """统一解析 IndexedDB 查询返回的各种格式"""
    if isinstance(raw, dict):
        val = raw.get("value") or raw.get("result") or raw.get("data")
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list): return parsed
                if isinstance(parsed, dict): return [parsed]
            except (json.JSONDecodeError, TypeError): pass
        if isinstance(val, list): return val
    if isinstance(raw, list): return raw
    return []
```

### bridge.js 返回值 JSON 解析

```python
# ✅ 正确: 先检查 str 类型并 json.loads
tmpl_result = await ws_server.send_browser_action("list_sheet_templates", None)
if isinstance(tmpl_result, str):
    try:
        tmpl_result = json.loads(tmpl_result)
    except (json.JSONDecodeError, TypeError): pass
if isinstance(tmpl_result, dict):
    templates = tmpl_result.get("data", tmpl_result).get("templates", [])

# ❌ 错误: 假设返回值一定是 dict
templates = tmpl_result.get("data", {}).get("templates", [])
```

## 最佳实践

1. **工具组独立** - 每个工具组独立目录，职责单一
2. **使用 uv** - 始终使用 `uv run` 和 `uv sync`
3. **类型提示** - 所有函数必须有完整的类型提示
4. **测试优先** - 先写测试，再实现功能
5. **文档完整** - 所有公开函数必须有文档字符串
6. **错误处理** - 所有异常必须有明确处理
