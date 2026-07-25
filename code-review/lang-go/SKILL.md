---
name: lang-go
description: Go 编码规范：命名、错误处理、接口、并发、代码格式化
---

# Go 编码规范

## 何时激活

- 变更涉及 `*.go` 文件
- 新增或修改 Go 代码
- 编写 Go 工具或库

---

# Go 基础规范

## 命名

### 类型和结构体

```go
// ✅ 正确：类型使用 PascalCase
type UserService struct {}
type CreateUserRequest struct {}
type ChannelConfig struct {}
```

### 函数和方法

```go
// ✅ 导出函数使用 PascalCase
func GetUser() {}
func (s *UserService) Create() {}

// ✅ 私有函数使用小写
func getUserByToken(token string) (*User, error) {}
func validateInput(input string) bool {}
```

### 变量和常量

```go
// ✅ 包级导出变量使用 PascalCase
var DB *gorm.DB

// ✅ 包私有变量使用小写
var dbPath string

// ✅ 常量使用 UPPER_SNAKE_CASE
const MaxRetries = 3
```

### 函数命名

```go
// ✅ 使用描述性动词
func GetUserList() {}
func CreateUser() {}
func ValidateToken() {}

// ✅ 布尔函数使用 Is/Has/Can 前缀
func IsUserActive(user *User) bool
func HasPermission(user *User, action string) bool
```

## 错误处理

### 核心原则

- [ ] 不忽略错误 (不 `_, _ = ...`)
- [ ] 错误包装使用 `%w` 动词 (不 `%v`)
- [ ] 错误检查紧跟可能出错的函数调用
- [ ] 使用哨兵错误做类型判断

```go
// ✅ 正确：返回错误，使用 %w 包装
func DoSomething() error {
    if err := validate(); err != nil {
        return fmt.Errorf("验证失败：%w", err)
    }
    return nil
}

// ✅ 正确：哨兵错误
var ErrUserNotFound = errors.New("用户未找到")

func handleUser() error {
    user, err := getUser()
    if err != nil {
        if errors.Is(err, ErrUserNotFound) {
            // 处理不存在
        }
        return fmt.Errorf("处理用户：%w", err)
    }
    return nil
}
```

## 结构体设计

### 使用标签进行序列化

```go
type Channel struct {
    Id          int    `json:"id" gorm:"primaryKey"`
    Type        int    `json:"type" gorm:"default:0"`
    Key         string `json:"key" gorm:"type:text"`
    Password    string `json:"-"` // 排除 JSON
}
```

### 接口

- [ ] 接口定义在调用方 (接收者)
- [ ] 接口小而专 (1-2 个方法)
- [ ] 单方法接口使用 -er 后缀

```go
// ✅ 正确：调用方定义接口
type Reader interface {
    Read(p []byte) (n int, err error)
}

type TokenValidator interface {
    Validate(token string) bool
}
```

### 接收器命名

```go
// ✅ 使用类型的首字母
func (u *User) GetName() string { return u.Name }
func (s *UserService) Create() {}
```

## 并发安全

- [ ] 共享数据使用 Mutex 或 Channel 保护
- [ ] goroutine 不会无限运行
- [ ] 使用 `sync.WaitGroup` 等待 goroutine 完成
- [ ] 不泄漏 goroutine
- [ ] 使用 `context` 进行取消/超时

```go
// ✅ 正确：WaitGroup + context
func processBatch(users []User) error {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    var wg sync.WaitGroup
    for _, user := range users {
        wg.Add(1)
        go func(u User) {
            defer wg.Done()
            ctxErr := ctx.Err()
            if ctxErr != nil {
                return
            }
            processUser(u)
        }(user)
    }
    wg.Wait()
    return nil
}
```

## 资源管理

```go
// ✅ 正确：defer + context
func readFile(path string) (string, error) {
    f, err := os.Open(path)
    if err != nil {
        return "", err
    }
    defer f.Close()
    
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    _ = ctx
    return "", nil
}
```

## 代码格式化

- [ ] 使用 `gofmt` 或 `go fmt` 格式化代码
- [ ] 导入分组 (标准库 / 第三方 / 本地)
- [ ] 每行不超过 120 字符
- [ ] 不使用 `any` 类型 (使用 `interface{}`)

```go
// ✅ 正确 - 导入分组
import (
    "context"
    "fmt"
    
    "github.com/gin-gonic/gin"
    
    "myproject/model"
)
```

## 注释规范

- [ ] 导出函数和类型有注释
- [ ] 注释以函数名/类型名开头
- [ ] 解释"为什么"而非"做什么"

```go
// ✅ 正确
// GetUserByID returns a user by its ID.
// Returns ErrNotFound if the user does not exist.
func GetUserByID(id int) (*User, error) {}
```

---

# 审查检查清单

- [ ] 命名符合规范 (PascalCase / camelCase / UPPER_SNAKE_CASE)
- [ ] 错误处理完整 (不忽略错误，使用 `%w`)
- [ ] 接口定义在调用方 (小而专)
- [ ] 并发安全 (Mutex/Channel/WaitGroup)
- [ ] 使用 context 进行超时控制
- [ ] 资源使用 defer 关闭
- [ ] 导出函数和类型有注释
- [ ] 使用 `gofmt` 格式化代码

---

**记住**: 为人类编写代码，清晰的命名和显式的错误处理总是胜过巧妙的技巧。
