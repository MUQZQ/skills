---
name: project-datasheet-parse
description: DatasheetParse 项目代码审查规则：3-Agent Pipeline、目录约定、配置管理
origin: DatasheetParse
---

# DatasheetParse 项目代码审查

## 触发条件

变更涉及以下路径时自动触发：

- `AI_Data/`
- `skills/glm-ocr-parse/`
- `skills/datasheet-parse/`
- `skills/datasheet-param-compare/`
- `config.yaml`
- `AGENTS.md`

## 项目架构

- **3-Agent Pipeline**: PDF → OCR → LLM参数提取 → YAML → 对比
- **Skill 化设计**: 每个阶段独立为 skill，可单独使用
- **数据流**: `skills/` (脚本) → `AI_Data/` (输出) → 报告生成

### 阶段职责

| 阶段 | Skill | 职责 | 输入 | 输出 |
|------|-------|------|------|------|
| Agent-1 | glm-ocr-parse | PDF 转 Markdown | PDF 文件 | result.md |
| Agent-2 | datasheet-parse | LLM 参数提取 | result.md | *_ai_params.yaml |
| Agent-3 | validate_extraction | 质量验证 | YAML 文件 | 验证报告 |
| - | datasheet-param-compare | 参数对比 | YAML + Excel | comparison_report.md |

## 目录约定

| 目录 | 用途 | 审查要点 |
|------|------|---------|
| `AI_Data/` | AI 输出数据根目录 (按日期子目录组织) | 批次/器件元数据完整性 |
| `skills/glm-ocr-parse/` | PDF OCR 解析 | parse.py 正确性、DPI 设置 |
| `skills/datasheet-parse/` | 参数提取 | Schema/Prompt 使用、YAML 格式 |
| `skills/datasheet-param-compare/` | 参数对比 | 匹配算法、报告生成 |
| `references/` | 参考数据 | Schema、Prompt、参数映射配置 |

### AI_Data 目录结构

```
AI_Data/
├── 2025-01-15/                    # 日期文件夹 (YYYY-MM-DD)
│   ├── .batch_meta.json           # 批次元数据
│   ├── MIC28510YJL-TR/            # 器件目录
│   │   ├── .device_info.json      # 器件元数据 (含PDF源路径)
│   │   ├── result.md              # OCR 结果
│   │   ├── MIC28510YJL-TR_ai_params.yaml  # AI 参数提取
│   │   └── comparison_report.md   # 对比报告
│   └── comparison_summary.md      # 汇总报告
```

## 配置管理

### 配置文件层级

```
配置优先级 (从高到低):
1. 环境变量 (AI_DATA_ROOT, LLM_API_URL, LLM_API_KEY, OCR_API_URL)
2. config.yaml (项目根目录)
3. skills/datasheet-param-compare/config.yaml (skill 级配置)
4. references/*.yaml (参考数据: schemas.yaml, prompts.yaml, param_mappings.yaml)
5. 默认值
```

### config.yaml 关键配置项

| 配置项 | 说明 | 审查要点 |
|--------|------|---------|
| `ai_data.root_dir` | AI 输出数据根目录 | 必须与 `--ai-data` 参数一致 |
| `llm.api_url` | LLM API 地址 | 不硬编码，通过环境变量或配置 |
| `llm.api_key_env` | API Key 环境变量名 | 必须从环境变量读取，禁止硬编码 |
| `ocr.api_url` | OCR 服务地址 | 内网地址需配置可访问 |
| `ocr.timeout` | OCR 请求超时 | 合理设置 (120s) |
| `llm.timeout` | LLM 请求超时 | 合理设置 (300s) |

## Python/uv 规范

### 强制规则

- **必须使用 `uv run` 执行脚本**，禁止 `python`/`python3`/`pip`
- **Windows 环境强制 UTF-8 编码** (sys.stdout.reconfigure)

```python
# ✅ 正确 - 使用 uv run
uv run scripts/extract_yaml.py ./AI_Data/2025-01-15/MIC28510/result.md

# ❌ 错误 - 直接调用 python
python scripts/extract_yaml.py ./AI_Data/2025-01-15/MIC28510/result.md
pip install pyyaml
```

### 编码处理

```python
# ✅ 正确 - Windows UTF-8 编码
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
```

## 关键约定审查

| 约定 | 说明 | 审查要点 |
|------|------|---------|
| 覆盖保护 | 使用 `--force` 参数覆盖已有 YAML | 不强制时禁止覆盖已有结果 |
| 内容限制 | 参数提取最大 50KB (防提示词注入) | MAX_RESULT_CONTENT_LENGTH = 50000 |
| 输出命名 | `{device_name}_ai_params.yaml` | 命名格式统一 |
| 器件类型 | 9 种类型 (EEPROM, NOR_Flash, RTC, 无源/有源晶振, DCDC, LDO, ADC, DAC) | param_mappings.yaml 一致性 |

## 审查检查清单

### Pipeline 流程
- [ ] 3-Agent Pipeline 顺序正确 (OCR → 提取 → 验证)
- [ ] Skill 间数据流正确 (result.md → YAML → 对比)
- [ ] 输出文件位置符合约定 (AI_Data 日期目录)

### AI_Data 目录
- [ ] 批次元数据 `.batch_meta.json` 完整性
- [ ] 器件元数据 `.device_info.json` 包含 PDF 源路径
- [ ] 日期目录格式 YYYY-MM-DD

### 配置管理
- [ ] config.yaml 配置正确性
- [ ] API Key 通过环境变量读取，未硬编码
- [ ] 环境变量优先级高于 config.yaml

### Python 规范
- [ ] 使用 `uv run` 执行脚本
- [ ] Windows 环境 UTF-8 编码处理
- [ ] 编码声明 `# -*- coding: utf-8 -*-`

### OCR 解析 (glm-ocr-parse)
- [ ] DPI 设置合理 (默认 200)
- [ ] OCR 服务地址可配置
- [ ] 输出文件: result.md, merged.json, ocr_result.json

### 参数提取 (datasheet-parse)
- [ ] 器件类型自动识别或手动指定正确
- [ ] Rich YAML 格式规范 (7 字段完整)
- [ ] Schema/Prompt 使用正确
- [ ] --force 覆盖保护
- [ ] 50KB 内容限制防注入
- [ ] 参数来源标注 (表格/章节引用)
- [ ] 测试条件标注 (如适用)

### 参数对比 (datasheet-param-compare)
- [ ] 8 种匹配策略正确性 (完全匹配、最大值、最小值、范围、部分数值、单位转换、容差、别名)
- [ ] 对比报告生成规范
- [ ] 批量并行处理
- [ ] 增量处理 (失败重试)

### 安全
- [ ] API Key 未硬编码，通过环境变量读取
- [ ] PDF 内容限制 50KB
- [ ] 错误信息不泄露内部详情

## 最佳实践

1. **始终使用 `uv run`** - 不要使用 `python` 或 `pip` 直接命令
2. **覆盖保护** - 不强制时不要覆盖已有结果
3. **参数来源** - 每个参数必须标注具体出处 (Table/Chapter)
4. **测试条件** - 有特定测试条件的参数必须标注
5. **元数据完整** - AI_Data 中必须包含批次和器件元数据
