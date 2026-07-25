---
name: yaml-format
description: YAML 格式检查：语法正确性、缩进规范、键名规范、类型一致性、配置文件专项检查
---

# YAML 格式检查

## 何时激活

- **变更文件中包含 `*.yaml` 或 `*.yml` 文件时触发**
- 新增或修改 YAML 配置文件
- 修改项目配置 (config.yaml, .env.yaml, docker-compose.yml 等)
- 修改 CI/CD 配置 (.github/workflows/*.yml, Makefile 等)
- 修改 Helm charts、K8s manifests 等

## 审查检查清单

### 1. YAML 语法正确性

语法错误会导致配置无法加载，属于 P0 问题。

**检查项**:
- [ ] 无缩进错误（使用空格，禁止 Tab）
- [ ] 冒号后有空格（`key: value` 不是 `key:value`）
- [ ] 列表项格式正确（`- value` 不是 `value`）
- [ ] 字符串正确引号处理（含特殊字符时加引号）
- [ ] 无重复的键名
- [ ] 注释格式正确（`# 注释`）

```yaml
# ❌ 错误 - Tab 缩进
key:	value

# ❌ 错误 - 冒号后无空格
key:value

# ❌ 错误 - 列表格式错误
list:
  item1
  item2

# ❌ 错误 - 重复键名
name: foo
name: bar

# ❌ 错误 - 未引用的特殊字符
note: this is: a colon
email: user@example.com:8080

# ✅ 正确
key: value

list:
  - item1
  - item2

name: foo

note: "this is: a colon"
email: user@example.com

# 这是正确的注释格式
```

### 2. 缩进与格式规范

缩进不一致会导致解析歧义，属于 P1 问题。

**检查项**:
- [ ] 统一使用 2 空格缩进（不是 4 空格或 Tab）
- [ ] 同一层级缩进一致
- [ ] 文件末尾有换行符
- [ ] 文件编码为 UTF-8
- [ ] 无 BOM 头

```yaml
# ❌ 错误 - 缩进不一致
database:
  host: localhost
    port: 5432       # 4 空格混入
  name: mydb

# ✅ 正确 - 统一 2 空格
database:
  host: localhost
  port: 5432
  name: mydb
```

### 3. 键名规范

键名不规范影响可读性和维护性，属于 P1 问题。

**检查项**:
- [ ] 键名使用 snake_case 或 kebab-case 保持一致
- [ ] 键名不使用数字开头
- [ ] 键名不使用特殊字符（保留 `#`、`&`、`*`、`!`、`|`、`'`、`"`、`>`、`%`、`@`、`` ` ``）
- [ ] 嵌套层级合理（<= 4 层）

```yaml
# ❌ 错误 - 风格不统一
DatabaseHost: localhost
db-port: 5432
api_key: abc123
DB_NAME: mydb

# ❌ 错误 - 数字开头
1st_level: value

# ❌ 错误 - 特殊字符
&context: value

# ✅ 正确 - 统一 snake_case
database_host: localhost
db_port: 5432
api_key: abc123
db_name: mydb
```

### 4. 类型一致性与引号使用

类型错误会导致运行时解析异常，属于 P1 问题。

**检查项**:
- [ ] 数字不需要引号（`port: 8080` 不是 `port: "8080"`）
- [ ] 布尔值使用标准形式（`true`/`false`/`yes`/`no`，不加引号）
- [ ] 布尔值警惕隐式转换（`on`/`off`/`y`/`n` 在 YAML 1.1 中被解析为布尔）
- [ ] 时间/日期格式正确或用引号包裹
- [ ] 空值使用 `null` 或 `~` 明确表示
- [ ] 文件路径、IP 地址等用引号包裹防止隐式转换

```yaml
# ❌ 错误 - 类型不规范
port: "8080"            # 数字不应加引号
enable: on              # 隐式布尔，不同 YAML 版本行为不一致
date: 2024/01/01        # 日期格式不一致
email: user@example.com # 可能被解析为字符串但存在歧义
empty:                   # 值为 null 但写法不清晰
ip: 192.168.1.1         # IP 可能被解析为浮点数

# ✅ 正确
port: 8080
enable: true
date: "2024-01-01"
email: "user@example.com"
empty: null
ip: "192.168.1.1"
version: "3.10"         # 版本字符串，防止解析为 3.1
```

### 5. 配置文件专项检查

针对项目配置文件的额外检查，属于 P1/P2 问题。

**检查项**:
- [ ] 配置项有注释说明用途
- [ ] 默认值合理，敏感信息不硬编码
- [ ] 配置结构分层清晰
- [ ] 必填字段都有默认值或占位提示
- [ ] 环境相关配置通过环境变量区分
- [ ] 配置值范围合理（端口、超时时间等）

```yaml
# ❌ 错误 - 无注释、无默认值、敏感信息硬编码
server:
  port: 8080
  secret: sk-xxxxx
  password: admin123

# ✅ 正确 - 有注释、敏感信息占位
server:
  port: 8080                  # HTTP 端口，默认 8080
  host: "0.0.0.0"             # 监听地址
  # API 密钥，通过环境变量 API_SECRET 设置
  # API_SECRET: ""
  timeout: 30                 # 请求超时秒数
  max_connections: 1000        # 最大连接数

database:
  host: "localhost"            # 数据库地址
  port: 5432                   # PostgreSQL 端口
  name: "myapp"                # 数据库名称
  pool_size: 25                # 连接池大小
```

### 6. 列表与集合规范

列表格式错误是常见陷阱，属于 P1 问题。

**检查项**:
- [ ] 列表项格式统一（block style 或 flow style）
- [ ] 列表中不同类型元素使用显式类型标记
- [ ] 大列表使用 block style 提高可读性
- [ ] 列表项无缩进错误

```yaml
# ❌ 错误 - 风格混用
tags:
  - go
  - python
features: [a, b, c]           # 短列表混用 flow style

items:
  - name: foo
  port: 8080                   # 错误缩进，不属于列表

# ✅ 正确 - 统一 block style
tags:
  - go
  - python

features:
  - a
  - b
  - c

items:
  - name: foo
    port: 8080
```

### 7. 引用与锚点

锚点和引用使用不当会导致维护困难，属于 P2 问题。

**检查项**:
- [ ] 锚点命名清晰表达其含义
- [ ] 合理使用 `*` 引用和 `<<` 合并
- [ ] 不过度使用引用（简单值直接写）
- [ ] 引用目标存在且正确

```yaml
# ❌ 错误 - 锚点命名不清晰
a: &x
  key: value
b: *x

# ✅ 正确 - 清晰命名
defaults: &defaults
  timeout: 30
  retries: 3
  pool_size: 25

dev:
  <<: *defaults
  host: "localhost"

prod:
  <<: *defaults
  host: "db.production.com"
```

### 8. 超大文件与嵌套

文件过大或嵌套过深影响可维护性，属于 P2 问题。

**检查项**:
- [ ] 单文件不超过 500 行
- [ ] 嵌套层级 <= 4 层
- [ ] 大文件拆分多个文件并用 `!include` 或 `<<: *anchor` 合并
- [ ] 使用 `!!str` / `!!int` 等类型标记明确复杂值

```yaml
# ❌ 错误 - 嵌套过深
service:
  deployment:
    spec:
      template:
        spec:
          containers:
            - name: app

# ✅ 正确 - 拆分文件
# deployment.yaml
deployment:
  replicas: 3
  strategy: rollingUpdate

# k8s/manifests 拆分
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
```

## 优先级分类

| 优先级 | 类型 | 检查项 | 处理 |
|--------|------|--------|------|
| **P0** | 阻塞性 | 语法错误、Tab 缩进、重复键名、冒号后无空格 | **必须修复** |
| **P1** | 重要 | 缩进不一致、类型错误、引号误用、键名不规范、列表格式错误 | **建议修复** |
| **P2** | 建议 | 注释缺失、锚点命名、嵌套过深、文件过大 | **可选修复** |

## 常用验证命令

```bash
# Python yaml 语法检查
python -c "import yaml; yaml.safe_load(open('file.yaml'))"

# 使用 yq 检查
yq eval '.' file.yaml

# 使用 yamllint
yamllint file.yaml

# Docker Compose 验证
docker compose config
```

## 最佳实践

1. **空格缩进** - 统一 2 空格，禁用 Tab
2. **冒号后空格** - `key: value` 格式
3. **类型正确** - 数字不加引号，字符串含特殊字符时加引号
4. **注释充分** - 配置项添加注释说明用途
5. **敏感信息** - 不硬编码密钥密码，使用占位或环境变量
6. **风格一致** - 键名风格、列表风格统一
7. **适度嵌套** - 嵌套 <= 4 层，过大则拆分文件
8. **引用清晰** - 锚点名表达语义，不滥用引用
