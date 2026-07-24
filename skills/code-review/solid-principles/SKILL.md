---
name: solid-principles
description: SOLID 五大原则审查：单一职责(SRP)、开闭(OCP)、里氏替换(LSP)、接口隔离(ISP)、依赖倒置(DIP) + 常见设计模式误用检测
requires_source: true
source_context: shared_snippets
---

# SOLID 原则与设计模式审查

## 上下文协议

本 skill 从 design-review 协调层接收 **共享源码片段**（`shared_snippets`）。

审查输入包含：
1. **设计文档**：待审查的 .md 文档
2. **共享上下文**：`【共享上下文：{模块路径}】...【共享上下文结束】` 标记的代码片段

**审查规则**：
- 审查目标始终是**设计文档**，源码仅作为对照参考
- 共享上下文标注为"仅供审查参考，审查目标为设计文档"
- 不修改共享上下文中的源码，只检查设计文档与源码的一致性
- 如需源码修复，交由 design-review 协调层路由到 `code-review/SKILL.md`

## 何时激活

- **任何代码审查时都应用此规则**
- 新增或修改核心业务逻辑
- 设计新的接口或抽象层
- 添加新功能模块

## 审查检查清单

### SRP - 单一职责原则 (Single Responsibility)

每个函数、类、模块应该有且只有一个引起它变化的原因。

```go
// ✅ 正确 - 职责分离
func GetUser(id int) (*User, error) {
    var user User
    err := db.Where("id = ?", id).First(&user).Error
    return &user, err
}

func SendWelcomeEmail(user *User) error {
    tmpl, err := template.Parse("welcome.html")
    if err != nil {
        return fmt.Errorf("解析模板：%w", err)
    }
    return mail.Send(user.Email, "欢迎", tmpl)
}
```

```python
# ✅ 正确 - 职责分离
def get_user(user_id: int) -> Optional[User]:
    return db.session.get(User, user_id)

def send_welcome_email(user: User) -> None:
    template = render_template("welcome.html", user=user)
    mail.send(to=user.email, subject="欢迎", body=template)
```

```python
# ❌ 错误 - 一个函数做太多事
def process_user(user_id):  # 查询 + 验证 + 发邮件 + 写日志 + 更新状态
    user = db.get(User, user_id)
    if not user:
        return None
    validate(user)
    send_email(user.email, "欢迎")
    user.status = "active"
    db.save(user)
    logging.info(f"User {user_id} processed")
    return user
```

```go
// ❌ 错误 - God Function
func ProcessUser(c *gin.Context) {
    // 查询数据库
    // 验证参数
    // 发送邮件
    // 更新状态
    // 写日志
    // 返回响应
    // ...一个函数干了所有事
}
```

**检查项**:
- [ ] 函数/方法职责单一，不做多余的事
- [ ] 类/结构体方法数量合理（Go < 15, Python < 20）
- [ ] 每个函数/类有清晰的单一目的命名
- [ ] 文件长度合理（Go < 300 行, Python < 500 行）

---

### OCP - 开闭原则 (Open/Closed)

对扩展开放，对修改关闭。通过抽象和接口扩展行为，而非修改已有代码。

```go
// ✅ 正确 - 通过接口扩展
type Notifier interface {
    Send(message string) error
}

type EmailNotifier struct{}
func (e *EmailNotifier) Send(message string) error { ... }

type SmsNotifier struct{}
func (s *SmsNotifier) Send(message string) error { ... }

// 新增通知方式无需修改已有代码
type WechatNotifier struct{}
func (w *WechatNotifier) Send(message string) error { ... }
```

```python
# ✅ 正确 - 通过继承/组合扩展
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...

class EmailNotifier(Notifier):
    def send(self, message: str) -> None: ...

class SmsNotifier(Notifier):
    def send(self, message: str) -> None: ...
```

```python
# ❌ 错误 - 通过 if/elif 扩展
def send_notification(notify_type, message):
    if notify_type == "email":
        send_email(message)
    elif notify_type == "sms":
        send_sms(message)
    elif notify_type == "wechat":  # 每次新增都要改这个函数
        send_wechat(message)
```

**检查项**:
- [ ] 新增功能通过扩展而非修改实现
- [ ] 核心逻辑使用接口/抽象类
- [ ] 避免 if/elif 枚举类型分发
- [ ] 使用策略模式替代条件分支

---

### LSP - 里氏替换原则 (Liskov Substitution)

子类型必须能够替换它们的基类型，而不破坏程序正确性。

```go
// ✅ 正确 - 子类型行为一致
type Drawer interface {
    Draw() error
}

type Circle struct{}
func (c *Circle) Draw() error { ... }  // 总是成功或返回错误

type Square struct{}
func (s *Square) Draw() error { ... }  // 总是成功或返回错误

// 可以互换使用
func RenderAll(drawers []Drawer) {
    for _, d := range drawers {
        d.Draw()  // 不需要关心具体类型
    }
}
```

```python
# ❌ 错误 - 子类型行为不一致
class Rectangle:
    def set_width(self, w): self.width = w
    def set_height(self, h): self.height = h

class Square(Rectangle):
    def set_width(self, w):  # 改变了基类型的预期行为
        self.width = w
        self.height = w
    def set_height(self, h):
        self.width = h
        self.height = h

# 替换后行为异常
r = Rectangle()
r.set_width(10)
r.set_height(5)
# 预期 area=50，但如果传入 Square: area=100
```

**检查项**:
- [ ] 子类没有缩小或改变父类的契约
- [ ] 子类方法的 precondition 不更强，postcondition 不强于父类
- [ ] 不使用 isinstance/type check 做特殊分支
- [ ] 异常类型与父类一致或更具体

---

### ISP - 接口隔离原则 (Interface Segregation)

客户端不应该被迫依赖它不使用的方法。接口要小而专。

```go
// ✅ 正确 - 小而专的接口
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type Closer interface {
    Close() error
}

// 需要读写关闭的，组合三个接口
type ReadWriter interface {
    Reader
    Writer
}
```

```python
# ❌ 错误 - 胖接口
class Worker(ABC):
    @abstractmethod
    def work(self): ...
    @abstractmethod
    def eat(self): ...  # 机器人不需要 eat

class Robot(Worker):
    def work(self): ...
    def eat(self): ...  # 被迫实现但什么都不做
```

```python
# ✅ 正确 - 拆分为小接口
class Workable(ABC):
    @abstractmethod
    def work(self): ...

class Eatable(ABC):
    @abstractmethod
    def eat(self): ...

class Human(Workable, Eatable): ...
class Robot(Workable): ...  # 不需要 eat
```

**检查项**:
- [ ] 接口定义小而专（1-3 个方法）
- [ ] 没有空实现或只抛 NotImpementedError
- [ ] 客户端只依赖它实际需要的方法
- [ ] 大型接口考虑拆分

---

### DIP - 依赖倒置原则 (Dependency Inversion)

高层模块不应依赖低层模块，二者都应依赖抽象。抽象不应依赖细节，细节应依赖抽象。

```go
// ✅ 正确 - 依赖抽象
type Repository interface {
    FindByID(id int) (*User, error)
    Save(user *User) error
}

type UserService struct {
    repo Repository  // 依赖接口，不依赖具体实现
}

func (s *UserService) CreateUser(name string) error {
    user := &User{Name: name}
    return s.repo.Save(user)
}

// 测试时传入 mock
type MockRepo struct{ Repository }
func (m *MockRepo) Save(user *User) error { return nil }
```

```python
# ✅ 正确 - 依赖抽象
class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

class UserService:
    def __init__(self, repo: UserRepository):  # 依赖注入
        self.repo = repo

# 测试时注入 mock
class MockRepository(UserRepository):
    def get_by_id(self, user_id):
        return User(id=user_id, name="test")
```

```python
# ❌ 错误 - 直接依赖具体实现
class UserService:
    def __init__(self):
        self.repo = MySQLUserRepository()  # 硬编码依赖
    
    def get_user(self, user_id):
        return self.repo.get_by_id(user_id)  # 难以测试，难以替换
```

**检查项**:
- [ ] 模块间通过接口/抽象通信
- [ ] 依赖通过构造函数/参数注入
- [ ] 不使用 new/getInstance 创建依赖
- [ ] 代码可单元测试（能注入 mock）

---

### 设计模式误用检测

#### 1. 单例 (Singleton) 误用

```go
// ❌ 错误 - 全局变量伪装单例
var DefaultConfig *Config  // 全局可修改
```

```python
# ❌ 错误 - 类变量单例，线程不安全
class Config:
    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)  # 非线程安全
        return cls._instance
```

**误用检查**:
- [ ] 不使用全局变量代替单例
- [ ] 单例需要线程安全保证
- [ ] 考虑依赖注入是否比单例更合适
- [ ] 单例没有隐藏依赖关系

---

#### 2. 工厂 (Factory) 误用

```go
// ❌ 错误 - 工厂变得过于复杂
func CreateNotifier(t string) (Notifier, error) {
    switch t {
    case "email": return &EmailNotifier{}, nil
    case "sms": return &SmsNotifier{}, nil
    case "wechat": return &WechatNotifier{}, nil
    case "push": return &PushNotifier{}, nil
    // ... 新增一个类型改一次
    }
    return nil, fmt.Errorf("unknown type: %s", t)
}
```

**误用检查**:
- [ ] 工厂方法数量合理（< 10）
- [ ] 复杂的工厂考虑使用注册表/映射
- [ ] 工厂不封装简单的 new/构造
- [ ] 工厂函数职责单一

---

#### 3. 观察者 (Observer) 误用

**误用检查**:
- [ ] 观察者处理了订阅/取消订阅的生命周期
- [ ] 观察者不会导致内存泄漏（取消订阅）
- [ ] 通知同步/异步选择合理
- [ ] 没有观察者抛异常导致发布者崩溃
- [ ] 观察者之间没有隐式依赖顺序

---

#### 4. 策略 (Strategy) 误用

**误用检查**:
- [ ] 策略模式不是简单 if/elif 的过度封装
- [ ] 策略数量合理，不为了用模式而用模式
- [ ] 策略接口小而专（通常 1 个方法）
- [ ] 策略之间行为正交

---

#### 5. 装饰器 (Decorator) 误用

**误用检查**:
- [ ] 装饰器嵌套不超过 3 层
- [ ] 装饰器不改变原始对象的核心行为
- [ ] 每个装饰器职责单一
- [ ] 装饰器链可读性良好

---

#### 6. 适配器 (Adapter) 误用

**误用检查**:
- [ ] 适配器不引入过多转换逻辑
- [ ] 适配器不替代重写（重写可能更清晰）
- [ ] 适配器接口与目标接口一致
- [ ] 适配器不隐藏真正的兼容性问题

---

## 最佳实践

1. **SRP** - 一个函数只做一件事，函数过长考虑拆分
2. **OCP** - 新增功能通过扩展实现，修改已有功能要谨慎
3. **LSP** - 子类型行为与父类型一致，不要改变契约
4. **ISP** - 接口小而专，不为用者不需要的功能
5. **DIP** - 依赖抽象通过注入，便于测试和替换
6. **设计模式** - 模式是工具不是目标，不要为了用模式而用模式
