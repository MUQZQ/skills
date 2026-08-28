---
name: security-review
description: 安全审查规则：密钥管理、输入验证、SQL 注入防护、XSS/CSRF、限流
requires_source: true
source_context: review_diff_or_shared_snippets
---

# 安全审查

## 上下文协议

本 skill 可从 `code-review` 接收待审查代码 diff，也可从 design-review 接收设计文档与共享源码片段。

审查输入包含：
1. **代码审查**：审查目标为协调器指定的唯一 diff/range，提交前必须是精确暂存快照。
2. **设计审查**：审查目标为待审查的设计文档，共享源码片段仅用于一致性对照。

**审查规则**：
- 按调用协调器声明的审查目标执行，不自行切换到其他 diff、文件或工作树状态。
- 设计审查中的共享上下文只作对照；代码审查中的 diff 是审查目标本身。
- 本 skill 只报告问题，不直接修改审查目标。

## 何时激活

- 涉及认证或授权
- 处理用户输入或文件上传
- 创建新的 API 端点
- 处理密钥或凭证
- 存储或传输敏感数据
- 集成第三方 API
- **任何代码审查时都应用此规则**

## 审查检查清单

### 1. 密钥管理

#### ❌ 错误示例 - 永远不要这样做

```go
const apiKey = "sk-proj-xxxxx"  // 硬编码的密钥
const dbPassword = "password123" // 在源代码中
```

#### ✅ 正确示例 - 始终这样做

```go
// 使用环境变量
apiKey := os.Getenv("OPENAI_API_KEY")
dbUrl := os.Getenv("DATABASE_URL")

// 验证密钥存在
if apiKey == "" {
    logger.FatalLog("OPENAI_API_KEY not configured")
}
```

**检查项**:
- [ ] 没有硬编码的 API 密钥、令牌或密码
- [ ] 所有密钥存储在环境变量中
- [ ] `.env` 文件在 `.gitignore` 中
- [ ] git 历史中没有密钥泄露

### 2. 输入验证

**检查项**:
- [ ] 所有用户输入使用 schema 验证
- [ ] 文件上传有大小、类型、扩展名限制
- [ ] 查询中不直接使用用户输入
- [ ] 使用白名单验证 (不是黑名单)
- [ ] 错误消息不泄露敏感信息

```go
// ✅ 正确 - 输入验证
func Register(c *gin.Context) {
    var username, password string
    if len(username) < 3 || len(username) > 32 {
        common.AbortWithBadRequest(c, "用户名长度必须在 3-32 之间")
        return
    }
    if len(password) < 8 || len(password) > 20 {
        common.AbortWithBadRequest(c, "密码长度必须在 8-20 之间")
        return
    }
}

// ❌ 错误 - 无输入验证
func Register(c *gin.Context) {
    username := c.Query("username")
    password := c.Query("password")
    // 直接处理...
}
```

### 3. SQL 注入防护

**检查项**:
- [ ] 所有数据库查询使用参数化查询
- [ ] SQL 中没有字符串拼接
- [ ] 正确使用 GORM

```go
// ✅ 正确 - 参数化查询
DB.Where("email = ?", userEmail).Find(&users)
DB.Raw("SELECT * FROM users WHERE email = ?", userEmail).Scan(&users)

// ❌ 错误 - SQL 拼接
query := "SELECT * FROM users WHERE email = '" + userEmail + "'"
db.Raw(query).Scan(&users)
```

### 4. 认证与授权

**检查项**:
- [ ] 令牌存储在 httpOnly cookies 中 (不是 localStorage)
- [ ] 敏感操作前有授权检查
- [ ] 实现了基于角色的访问控制
- [ ] Session 管理安全

```go
// ✅ 正确 - 认证中间件
func UserAuth() func(c *gin.Context) {
    return func(c *gin.Context) {
        authHelper(c, model.RoleCommonUser)
    }
}
```

### 5. 敏感数据泄露

**检查项**:
- [ ] 日志中没有密码、令牌或密钥
- [ ] 用户看到的错误消息是通用的
- [ ] 详细错误只在服务器日志中
- [ ] 不向用户暴露堆栈跟踪

```go
// ✅ 正确 - 日志脱敏
logger.SysLogf("用户登录：userId=%d, username=%s", user.Id, user.Username)

// ❌ 错误 - 泄露敏感信息
logger.SysLogf("用户登录：%v", user.Password)
```

## 最佳实践

1. **密钥环境变量化** - 所有密钥通过环境变量读取
2. **输入必验证** - 所有用户输入必须经过验证
3. **参数化查询** - 防止 SQL 注入
4. **脱敏日志** - 日志中不记录敏感信息
5. **通用错误** - 向用户展示通用错误消息
