---
name: lang-python
description: Python 编码规范：命名、错误处理、类型提示、文件操作
---

# Python 编码规范

## 何时激活

- 变更涉及 `*.py` 文件
- 新增或修改 Python 脚本
- 编写 Python 工具或数据处理脚本

## 核心规范（强制，始终执行）

审查前先加载 `python-coding-standards`（权威路径 `.cc-switch/skills/python-coding-standards/SKILL.md`）的 27 条规范，逐条核对变更代码。命名、异常处理、日志、外部数据、安全红线以该规范为准，本文件下方清单为补充细节（工程单位、文件操作等）。

**冲突处理**：下方清单与本规范不一致时，以 27 条核心规范为准。已知对齐点：
- 日志使用懒格式化 `"%s", val`，禁止 f-string 拼日志（f-string 仅限普通字符串）
- 命名统一 `snake_case`（变量/函数/方法）
- 文件头编码声明为旧式约定，Python 3 默认 UTF-8，不作硬性要求

## 审查检查清单

### 编码与导入
- [ ] 文件头部编码声明 `# -*- coding: utf-8 -*-`
- [ ] 标准库 / 第三方库 / 本地模块分组导入
- [ ] 导入使用绝对路径而非相对路径

### 类型提示
- [ ] 函数参数有类型标注
- [ ] 函数返回值有类型标注
- [ ] 复杂类型使用 `typing` 模块 (Dict, List, Optional, Any)

```python
# ✅ 正确
from typing import Dict, List, Optional

def process_files(paths: List[str], output_dir: str) -> Dict[str, int]:
    ...

# ❌ 错误
def process_files(paths, output_dir):  # 缺少类型提示
    ...
```

### 错误处理
- [ ] 使用具体的异常类型 (不裸 `except Exception`)
- [ ] 异常处理有合适的恢复或日志记录
- [ ] 不忽略捕获的异常

```python
# ✅ 正确
try:
    result = process_data(file_path)
except FileNotFoundError:
    logger.error(f"文件不存在: {file_path}")
    return None
except ValueError as e:
    logger.error(f"数据格式错误: {e}")
    return None

# ❌ 错误
try:
    result = process_data(file_path)
except:  # 裸 except，捕获所有异常
    pass  # 静默忽略
```

### 日志使用
- [ ] 使用 `logging` 模块而非 `print`
- [ ] 日志级别合理 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [ ] 不记录敏感数据 (密码、API Key、Token)

```python
# ✅ 正确
import logging
logger = logging.getLogger(__name__)
logger.info("处理文件: %s", file_path)  # 懒格式化，避免无谓的字符串拼接
logger.error("处理失败: %s, 原因: %s", file_path, e)

# ❌ 错误
print(f"处理文件: {file_path}")
print(f"API Key: {api_key}")  # 泄露敏感信息
logger.info(f"处理文件: {file_path}")  # f-string 拼日志（懒格式化反模式）
```

### 文件操作
- [ ] 使用 `pathlib.Path` 而非 `os.path`
- [ ] 文件操作使用 `with` 语句确保关闭

```python
# ✅ 正确
from pathlib import Path

output_path = Path(output_dir) / "result.txt"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(data)

# ❌ 错误
import os
output_path = os.path.join(output_dir, "result.txt")
f = open(output_path, 'w')
f.write(data)
f.close()  # 忘记关闭
```

### 常量命名
- [ ] 常量使用 UPPER_SNAKE_CASE
- [ ] 变量/函数/方法使用 snake_case
- [ ] 类名使用 PascalCase

```python
# ✅ 正确
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 300
device_type = "DCDC"

class DataProcessor:
    pass

def process_data(input_file):
    pass
```

### 字符串处理
- [ ] 使用 f-string (Python 3.6+) 而非 `%` 或 `.format()`
- [ ] 路径拼接使用 `Path` 或 `os.path.join`

```python
# ✅ 正确
message = f"处理完成: {device_name} ({total} 个器件)"
file_path = Path(output_dir) / "result.yaml"

# ❌ 错误
message = "处理完成: %s (%d 个器件)" % (device_name, total)
file_path = output_dir + "/result.yaml"
```

### 配置读取
- [ ] 配置通过 `os.environ` 或 `os.getenv` 读取
- [ ] 敏感配置 (API Key) 必须从环境变量读取
- [ ] 提供合理的默认值

```python
# ✅ 正确
import os

api_key = os.getenv("LLM_API_KEY")
api_url = os.getenv("LLM_API_URL", "https://api.openai.com/v1")
timeout = int(os.getenv("LLM_TIMEOUT", "300"))

if not api_key:
    raise RuntimeError("LLM_API_KEY not configured")

# ❌ 错误
api_key = "sk-xxxxx"  # 硬编码密钥
```

## 最佳实践

1. **始终使用 `uv run`** - 不要直接使用 `python` 或 `pip`
2. **类型提示完整** - 提高代码可读性和 IDE 支持
3. **具体异常处理** - 不裸 catch，不忽略异常
4. **logging 而非 print** - 便于调试和监控
5. **Pathlib 而非 os.path** - 更现代的 API
6. **常量 UPPER_SNAKE_CASE** - 提高可读性
7. **敏感信息不硬编码** - 通过环境变量读取

### 工程单位处理

涉及工程单位的 Python 代码应遵循以下约定：

- [ ] 单位映射表使用 `_UNIT_FAMILIES` 命名，格式 `{base_unit: 1.0, derived: factor}`
- [ ] 单位解析函数命名为 `_parse_val_with_unit()`，返回 `(数值, 单位或None)` 元组
- [ ] 单位归一化函数命名为 `_normalize_unit()`，返回归一化后的数值或 None（无法转换时）
- [ ] 科学常量使用 `UPPER_SNAKE_CASE`（如 `_NEAR_ZERO_EPS`、`_DEFAULT_TOLERANCE`）

```python
# ✅ 正确 - 单位族映射
_UNIT_FAMILIES: dict[str, dict[str, float]] = {
    "V": {"V": 1.0, "mV": 1e-3, "μV": 1e-6},
    "A": {"A": 1.0, "mA": 1e-3, "μA": 1e-6},
}

_NEAR_ZERO_EPS = 1e-6

def _parse_val_with_unit(v: Any) -> tuple[float, str | None]:
    """解析带单位的值，返回 (数值, 单位)"""
    ...

def _normalize_unit(num: float, unit: str | None, target_unit: str | None) -> float | None:
    """归一化单位，无法转换时返回 None"""
    ...
```
