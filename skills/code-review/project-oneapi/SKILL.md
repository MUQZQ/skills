---
name: project-oneapi
description: One API 项目代码审查规则：Gin/GORM 架构、目录约定、配置管理、权限体系
origin: One API
---

# One API 项目代码审查

## 触发条件

变更涉及以下路径时自动触发：

- `controller/`
- `model/`
- `middleware/`
- `router/`
- `relay/`
- `common/`
- `web/`

## 项目架构

- **Go + Gin 后端** + **React 前端** 分离架构
- **三层架构**: controller (HTTP 处理) → model (数据操作) → relay (服务适配)
- **中间件层**: 认证 → 限流 → 日志
- **统一响应**: `common.Ok`, `common.AbortWith*`

### 层间依赖

```
请求流程:
客户端 → middleware (认证/限流/日志) → router (路由分发) → controller (参数绑定/验证) → model (数据库) → common.OkWithData
                                                                                          ↓
                                                                               common.AbortWith* (错误)
```

## 目录约定

| 目录 | 用途 | 审查要点 |
|------|------|---------|
| `controller/` | HTTP 请求处理器 | 统一响应、输入验证、错误处理 |
| `model/` | 数据模型和数据库操作 | 参数化查询、敏感字段 Omit |
| `middleware/` | 中间件 (认证、限流、日志) | 认证检查、权限控制、上下文设置 |
| `router/` | 路由定义 | 权限分组、路由注册 |
| `relay/` | 服务适配器 | LLM 服务调用、错误处理 |
| `common/` | 共享工具函数和响应助手 | 响应格式统一、配置管理 |
| `web/{theme}/src/` | React 前端 | i18n、加载状态、错误处理 |

## 配置管理

### 环境变量优先级

```
配置优先级 (从高到低):
1. 环境变量 (SQL_DSN, SESSION_SECRET, REDIS_CONN_STRING, LLM_API_KEY, etc.)
2. .env 文件
3. 默认值
```

### 关键环境变量

| 变量名 | 说明 | 审查要点 |
|--------|------|---------|
| `SQL_DSN` | 数据库连接字符串 | 不硬编码，支持 SQLite/MySQL/PostgreSQL |
| `SESSION_SECRET` | Session 加密密钥 | 必须从环境变量读取 |
| `REDIS_CONN_STRING` | Redis 连接字符串 | 缓存和会话存储 |
| `LLM_API_KEY` | LLM API 密钥 | 不硬编码，支持多 provider |
| `LLM_API_URL` | LLM API 地址 | OpenAI 兼容格式 |

## 请求处理审查

### 控制器层 (controller/)

```go
// ✅ 正确示例
func GetUserList(c *gin.Context) {
    // 1. 验证输入
    var req common.PageRequest
    if err := c.ShouldBindQuery(&req); err != nil {
        common.AbortWithBadRequest(c, err.Error())
        return
    }

    // 2. 调用模型层
    users, total, err := model.GetUsers(req.Page, req.PerPage)
    if err != nil {
        common.AbortWithInternalServerError(c, err.Error())
        return
    }

    // 3. 统一响应
    common.OkWithData(c, gin.H{
        "data":  users,
        "total": total,
    })
}

// ❌ 错误示例
func GetUserList(c *gin.Context) {
    // 缺失输入验证
    users := model.GetUsers() // 未处理错误
    c.JSON(200, users) // 未使用统一响应
}
```

**审查要点**:
- [ ] 使用 `ShouldBindQuery` / `ShouldBindJSON` 验证输入
- [ ] 所有错误都被处理并返回 `common.AbortWith*`
- [ ] 使用 `common.OkWithData` 统一响应格式
- [ ] 不向用户暴露内部错误详情
- [ ] 不返回敏感字段 (密码、令牌等)

### 模型层 (model/)

```go
// ✅ 正确示例
func ValidateUserToken(tokenKey string) (*Token, error) {
    var token Token
    err := DB.Where("key = ? AND status = ? AND (expired_time = -1 OR expired_time > ?)",
        tokenKey, TokenStatusEnabled, helper.GetTimestamp()).First(&token).Error
    if err != nil {
        return nil, err
    }
    return &token, nil
}

func GetUserById(id int, selectAll bool) (*User, error) {
    user := User{Id: id}
    var err error
    if selectAll {
        err = DB.First(&user, "id = ?", id).Error
    } else {
        // 默认不返回敏感字段
        err = DB.Omit("password", "access_token").First(&user, "id = ?", id).Error
    }
    return &user, err
}
```

**审查要点**:
- [ ] 使用参数化查询 (防止 SQL 注入)
- [ ] 使用 `Omit` 排除敏感字段 (password, access_token)
- [ ] 使用 `Preload` 避免 N+1 查询
- [ ] 事务使用正确 (返回 error 自动回滚)
- [ ] 数据库错误都被处理

### 中间件层 (middleware/)

```go
// ✅ 正确示例
func authHelper(c *gin.Context, minRole int) {
    session := sessions.Default(c)
    username := session.Get("username")
    role := session.Get("role")
    id := session.Get("id")
    status := session.Get("status")
    
    if username == nil {
        // 检查 Access Token
        accessToken := c.Request.Header.Get("Authorization")
        if accessToken == "" {
            c.AbortWithStatusJSON(401, gin.H{"success": false, "message": "未登录"})
            return
        }
        user := model.ValidateAccessToken(accessToken)
        if user == nil {
            c.AbortWithStatusJSON(401, gin.H{"success": false, "message": "Token 无效"})
            return
        }
    }
    
    // 检查用户封禁
    if status.(int) == model.UserStatusDisabled || blacklist.IsUserBanned(id.(int)) {
        c.AbortWithStatusJSON(200, gin.H{"success": false, "message": "用户已被封禁"})
        session.Clear()
        session.Save()
        return
    }
    
    // 检查角色权限
    if role.(int) < minRole {
        c.AbortWithStatusJSON(403, gin.H{"success": false, "message": "权限不足"})
        return
    }
    
    c.Next()
}
```

**审查要点**:
- [ ] 认证检查完整 (Session + Access Token)
- [ ] 授权检查正确 (角色权限)
- [ ] 用户封禁检查
- [ ] 上下文设置正确

## 权限体系

### 三级权限

| 角色 | 值 | 权限范围 |
|------|---|---------|
| GuestUser | 0 | 访客，只能访问公开接口 |
| CommonUser | 1 | 普通用户，使用 API |
| AdminUser | 10 | 管理员，管理配置和用户 |
| RootUser | 100 | Root 用户，管理所有配置 |

### 路由权限控制

```go
// router.go 示例
func SetRouter(r *gin.Engine) {
    // 普通用户路由
    user := api.Group("/user")
    user.Use(middleware.UserAuth())
    
    // 管理员路由
    admin := api.Group("/admin")
    admin.Use(middleware.AdminAuth())
    
    // Root 路由
    root := api.Group("/root")
    root.Use(middleware.RootAuth())
}
```

**审查要点**:
- [ ] 路由权限分组正确
- [ ] 敏感操作有对应中间件保护
- [ ] 权限升级需 Root 确认

## React 前端审查

### 组件规范

```jsx
// ✅ 正确示例
import { useTranslation } from 'react-i18next'
import { Table, Button } from 'semantic-ui-react'
import { API, showError, showSuccess } from '../helpers'

const TokensTable = ({ tokens, onDelete, onEdit }) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  
  const handleDelete = async (id) => {
    setLoading(true)
    try {
      const res = await API.delete(`/api/token/${id}/`)
      if (res.data.success) {
        showSuccess(t('token.messages.delete_success'))
        onDelete(id)
      }
    } catch (error) {
      showError(error)
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Table striped loading={loading}>
      <Table.Body>
        {tokens.map(token => (
          <Table.Key key={token.id}>
            <Table.Cell>{token.key}</Table.Cell>
            <Table.Cell>
              <Button onClick={() => onEdit(token)}>{t('common.edit')}</Button>
            </Table.Cell>
          </Table.Key>
        ))}
      </Table.Body>
    </Table>
  )
}
```

**审查要点**:
- [ ] 所有用户可见文本使用 `t()` 函数 (i18n)
- [ ] 使用 Semantic UI React 组件
- [ ] 实现加载状态 (`loading={loading}`)
- [ ] 实现错误处理 (try-catch + showError/showSuccess)
- [ ] 使用 Hooks (useState, useEffect)
- [ ] key 属性使用唯一 ID
- [ ] 不使用 `dangerouslySetInnerHTML`

## 审查检查清单

### Go 后端
- [ ] controller 使用统一响应和输入验证
- [ ] model 使用参数化查询和 Omit 敏感字段
- [ ] middleware 认证/授权/封禁检查完整
- [ ] 错误处理完整 (不忽略错误)
- [ ] 错误包装使用 `%w` 动词
- [ ] 命名符合规范 (PascalCase, camelCase)
- [ ] 导出函数和类型有注释

### 前端
- [ ] 使用 i18n (`useTranslation`)
- [ ] 实现加载和错误状态
- [ ] 使用 Semantic UI 组件
- [ ] 使用正确的 API 调用

### 安全
- [ ] API Key / Session Secret 通过环境变量读取
- [ ] 所有数据库查询使用参数化
- [ ] Session cookies 使用 httpOnly
- [ ] 限流配置合理
- [ ] 错误消息不泄露内部详情

## 最佳实践

1. **及时审查**: 代码提交前或 PR 创建后立即审查
2. **统一响应**: 始终使用 `common.Ok` / `common.AbortWith*`
3. **参数化查询**: 防止 SQL 注入
4. **敏感字段**: 默认不返回，按需选择
5. **权限控制**: 路由分组 + 中间件保护
