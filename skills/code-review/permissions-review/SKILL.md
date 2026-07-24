---
name: permissions-review
description: 权限审查规则：角色定义、访问控制、权限升级、权限隔离
---

# 权限审查

## 何时激活

- 涉及用户角色定义
- 涉及访问控制中间件
- 涉及权限升级或授权逻辑
- 涉及敏感操作的管理员权限检查

## 审查检查清单

### 角色定义

- [ ] 角色常量使用清晰定义 (Guest / Common / Admin / Root)
- [ ] 角色值不使用魔法数字
- [ ] 角色层级清晰 (Guest < Common < Admin < Root)

```go
// ✅ 正确
const (
    RoleGuestUser  = 0
    RoleCommonUser = 1
    RoleAdminUser  = 10
    RoleRootUser   = 100
)

// ❌ 错误
func isAdmin(role int) bool {
    return role > 5  // 魔法数字
}
```

### 访问控制

- [ ] 路由按权限分组 (user / admin / root)
- [ ] 敏感操作有对应中间件保护
- [ ] 权限检查不可绕过

```go
// ✅ 正确
user := api.Group("/user")
user.Use(middleware.UserAuth())

admin := api.Group("/admin")
admin.Use(middleware.AdminAuth())

// ❌ 错误 - 管理员接口未加中间件
admin := api.Group("/admin")
// 缺少 AdminAuth()
```

### 权限升级

- [ ] 角色升级需要 Root 确认
- [ ] 权限升级有审计日志
- [ ] 禁止直接修改角色字段

```go
// ✅ 正确
func UpgradeRole(c *gin.Context) {
    // 需要 Root 权限
    role := GetRoleFromSession(c)
    if role < model.RoleRootUser {
        common.AbortWithForbidden(c, "需要 Root 权限")
        return
    }
    // 记录审计日志
    logger.SysLogf("用户 %d 角色升级为 %d", userId, newRole)
}
```

### 权限隔离

- [ ] 普通用户不能访问管理员接口
- [ ] 数据查询按用户隔离
- [ ] 列表接口只返回有权限的数据

## 最佳实践

1. **角色常量定义** - 使用常量，不魔法数字
2. **路由分组** - 按权限分组，统一中间件保护
3. **权限升级** - 需要 Root 确认 + 审计日志
4. **数据隔离** - 查询只返回有权限的数据
