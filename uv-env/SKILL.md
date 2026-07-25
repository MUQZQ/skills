---
name: uv-env
description: Python 虚拟环境管理（uv）。当用户提到"安装依赖"、"添加包"、"移除包"、"创建虚拟环境"、"Python版本"、"uv sync"、"pip install"、"package"、"依赖"、"venv"、"环境管理"、"uv add"、"uv remove"、"uv run"、"uv lock"时必须使用。用于使用 uv 管理 Python 项目依赖和虚拟环境。
---

# uv 虚拟环境管理

[uv](https://docs.astral.sh/uv/) 是 Rust 编写的极速 Python 包管理器，替代 pip + venv + pip-tools 的组合。

---

## 项目初始化

### 从零创建项目

```bash
uv init my-project             # 创建新项目
cd my-project
uv venv                        # 创建虚拟环境
source .venv/bin/activate      # 激活 (Linux/macOS)
# 或 .venv\Scripts\activate    # 激活 (Windows PowerShell)
```

### 已有项目的日常操作

```bash
uv sync                        # 根据 pyproject.toml 安装所有依赖
uv sync --no-dev               # 仅安装生产依赖（不含 dev 组）
uv sync --group dev            # 含 dev 依赖组
uv run pytest tests/           # 在虚拟环境中运行命令
```

---

## 依赖管理

### 添加依赖

```bash
uv add requests fastapi        # 添加到生产依赖
uv add --dev pytest pytest-asyncio  # 添加到 dev 依赖组
uv add "django>=4.0,<5.0"     # 带版本约束
uv add --group docs mkdocs     # 添加到自定义分组
uv add git+https://github.com/user/repo.git  # Git 依赖
uv add ./local-package/        # 本地路径依赖
```

### 移除依赖

```bash
uv remove requests             # 从生产依赖移除
uv remove --dev pytest         # 从 dev 依赖组移除
```

### 查看依赖

```bash
uv tree                        # 依赖树（需 0.7+）
uv lock --check                # 检查 lock 文件是否过期
uv pip list                    # 查看已安装的包
pip list                       # 传统 pip 也可用（需激活 venv）
```

---

## Python 版本管理

```bash
uv python list                 # 列出可安装的 Python 版本
uv python install 3.13         # 安装指定版本（自动下载）
uv python install 3.12 3.11    # 安装多个版本
uv python pin 3.13             # 固定项目 Python 版本

# 指定 Python 版本创建环境
uv venv --python 3.12
uv venv --python .python-version
```

---

## 环境配置

### `.python-version` 文件

```
3.13
```

### `pyproject.toml` 示例

```toml
[project]
name = "my-project"
version = "1.0.0"
requires-python = ">=3.13"
dependencies = [
    "nicegui>=3.14.0",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.4.0",
]
docs = ["mkdocs"]

[tool.uv]
package = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## 常用命令速查

| 操作 | 命令 |
|------|------|
| 同步依赖 | `uv sync` |
| 添加包 | `uv add <package>` |
| 添加开发包 | `uv add --dev <package>` |
| 移除包 | `uv remove <package>` |
| 运行命令 | `uv run <command>` |
| 运行测试 | `uv run pytest tests/ -v` |
| 锁定依赖 | `uv lock --upgrade` |
| 更新单包 | `uv lock --upgrade-package <package>` |
| 创建 venv | `uv venv` |
| 安装 Python | `uv python install 3.13` |
| 列出已安装包 | `uv pip list` |
| 导出 requirements | `uv pip freeze > requirements.txt` |

---

## 常见场景

### 场景1：克隆项目后首次运行

```bash
git clone <repo>
cd <project>
uv sync
uv run python main.py
```

### 场景2：运行测试

```bash
uv run pytest tests/ -v
uv run pytest tests/ -v -k "test_specific_name"
uv run pytest tests/ -v --tb=short
```

### 场景3：添加新功能需要新依赖

```bash
uv add httpx                    # 生产依赖
uv add --dev pytest-mock        # 测试依赖
uv run pytest tests/ -v         # 验证
```

### 场景4：升级依赖到最新兼容版本

```bash
uv lock --upgrade               # 升级所有依赖
uv lock --upgrade-package nicegui  # 仅升级特定包
uv sync                         # 同步到虚拟环境
```

### 场景5：检查依赖安全漏洞

```bash
uv lock --check                 # 检查 lock 文件过期
uv pip list --outdated          # 查看可升级的包
```

---

## 与 pip 的对比

| 操作 | pip | uv |
|------|-----|-----|
| 安装包 | `pip install <pkg>` | `uv add <pkg>` |
| 安装开发包 | 无原生支持 | `uv add --dev <pkg>` |
| 虚拟环境 | `python -m venv .venv` | `uv venv` |
| 同步依赖 | `pip install -r requirements.txt` | `uv sync` |
| 运行命令 | 需先 activate | `uv run <cmd>` |
| 锁定版本 | `pip freeze > requirements.txt` | `uv.lock` |
| 速度 | 慢 | 快（10-100x） |
| Python 管理 | 需手动安装 | `uv python install` |

---

## 注意事项

1. **不要混用 pip 和 uv**：`uv sync` 后可用 `pip list` 查看，但不要用 `pip install` 安装新包——用 `uv add` 代替。
2. **uv.lock 应提交到 Git**：确保团队使用一致的依赖版本。
3. **无需手动 activate**：`uv run` 自动使用 `.venv` 环境，省去激活步骤。
4. **Windows Git Bash**：Python 虚拟环境的 activate 脚本为 `.venv/Scripts/activate` 或直接使用 `.venv\Scripts\activate`。
5. **网络问题**：可通过 `UV_INDEX_URL` 或工具自带的镜像方案解决，如 Rye 的 config。
