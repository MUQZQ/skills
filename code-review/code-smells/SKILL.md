---
name: code-smells
description: 代码坏味道检查：长函数、重复代码、God Class、过长参数、魔法数字等经典坏味道检测
requires_source: true
source_context: review_diff_or_shared_snippets
---

# 代码坏味道检查

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

模式门禁只有两条：

- 全量代码审查时始终激活。
- 快速模式仅在 `code-review` 协调器明确判定变更涉及坏味道治理或结构重构时激活；不得根据后续重点场景自行扩大范围。

## 已激活后的重点场景

- 新增或修改业务逻辑代码
- 重构已有代码
- 代码复杂度较高的模块

## 审查检查清单

### 1. 长函数 (Long Method)

函数过长导致难以理解、测试和维护。

```go
// ✅ 正确 - 拆分为小函数
func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        common.AbortWithBadRequest(c, err.Error())
        return
    }

    user := buildUser(&req)
    if err := validateUser(user); err != nil {
        common.AbortWithBadRequest(c, err.Error())
        return
    }

    if err := saveUser(user); err != nil {
        common.AbortWithInternalServerError(c, err.Error())
        return
    }

    sendWelcomeEmail(user)
    common.OkWithData(c, user)
}
```

```python
# ✅ 正确 - 拆分为小函数
def create_user(data: dict) -> User:
    user = build_user(data)
    validate_user(user)
    user = save_user(user)
    send_welcome_email(user)
    return user
```

**检查项**:
- [ ] 函数行数合理（Go < 50 行, Python < 40 行）
- [ ] 函数缩进层级合理（<= 3 层）
- [ ] 函数通过抽取子函数来拆分
- [ ] 函数名准确描述其行为

---

### 2. 重复代码 (Duplicate Code)

同样的代码出现多次，应提取复用。

```go
// ❌ 错误 - 重复的验证逻辑
func CreateUser(c *gin.Context) {
    var req struct{ Name string; Email string }
    c.ShouldBindJSON(&req)
    if req.Name == "" {
        c.JSON(400, gin.H{"error": "name required"})
        return
    }
    if !strings.Contains(req.Email, "@") {
        c.JSON(400, gin.H{"error": "invalid email"})
        return
    }
    // ...
}

func UpdateUser(c *gin.Context) {
    var req struct{ Name string; Email string }
    c.ShouldBindJSON(&req)
    if req.Name == "" {  // 重复验证
        c.JSON(400, gin.H{"error": "name required"})
        return
    }
    if !strings.Contains(req.Email, "@") {  // 重复验证
        c.JSON(400, gin.H{"error": "invalid email"})
        return
    }
    // ...
}
```

```python
# ✅ 正确 - 提取验证函数
def validate_user(data: dict) -> List[str]:
    errors = []
    if not data.get("name"):
        errors.append("name required")
    if "@" not in data.get("email", ""):
        errors.append("invalid email")
    return errors
```

**检查项**:
- [ ] 没有重复的验证/业务逻辑
- [ ] 相似代码通过参数化提取为函数
- [ ] 复制粘贴的代码块被识别并提取
- [ ] 遵循 DRY (Don't Repeat Yourself)

---

### 3. 巨型类 / God Class (God Class)

一个类承担了太多职责，方法过多。

```go
// ❌ 错误 - God Class
type UserService struct {
    db *gorm.DB
}

func (s *UserService) GetUser(id int) {}           // 查询
func (s *UserService) CreateUser(req) {}           // 创建
func (s *UserService) SendEmail(user) {}           // 发邮件
func (s *UserService) GenerateReport() {}          // 生成报表
func (s *UserService) CacheUser(user) {}           // 缓存
func (s *UserService) ValidateEmail(email) {}      // 验证
func (s *UserService) HashPassword(pwd) {}         // 密码处理
// ... 20+ 方法
```

```python
# ❌ 错误 - God Class
class UserService:
    def get_user(self): ...          # 查询
    def create_user(self): ...       # 创建
    def send_email(self): ...        # 发邮件
    def generate_report(self): ...   # 生成报表
    def cache_user(self): ...        # 缓存
    # ... 15+ 方法
```

**检查项**:
- [ ] 类/结构体方法数量合理（Go < 15, Python < 20）
- [ ] 类/结构体字段数量合理（< 10）
- [ ] 类名准确反映其单一职责
- [ ] 职责多的类考虑拆分

---

### 4. 过长参数列表 (Long Parameter List)

函数参数过多增加调用复杂度和出错概率。

```go
// ❌ 错误 - 参数过多
func CreateUser(name string, email string, phone string,
    address string, city string, province string,
    zipCode string, role int, status int) (*User, error) {
}
```

```python
# ✅ 正确 - 使用结构体/字典
@dataclass
class CreateUserRequest:
    name: str
    email: str
    phone: str
    address: str
    city: str
    province: str
    zip_code: str
    role: int
    status: int

def create_user(req: CreateUserRequest) -> User:
    ...
```

```go
// ✅ 正确 - 使用结构体
type CreateUserRequest struct {
    Name     string `json:"name"`
    Email    string `json:"email"`
    Phone    string `json:"phone"`
    Address  string `json:"address"`
    City     string `json:"city"`
    Province string `json:"province"`
    ZipCode  string `json:"zip_code"`
    Role     int    `json:"role"`
    Status   int    `json:"status"`
}

func CreateUser(req CreateUserRequest) (*User, error) {
    ...
}
```

**检查项**:
- [ ] 函数参数不超过 5 个
- [ ] 相关参数组合为结构体/对象
- [ ] 可选参数使用 builder 或 option pattern
- [ ] 布尔参数需要警惕（可能是 SRP 违规）

---

### 5. 魔法数字 (Magic Number)

代码中直接使用未经解释的数字或字符串字面量。

```go
// ❌ 错误
if user.Status == 1 { ... }
if age > 18 { ... }
time.Sleep(30 * time.Second)
```

```go
// ✅ 正确
const (
    StatusActive  = 1
    StatusInactive = 0
)
const MinAge = 18
const DefaultTimeout = 30 * time.Second

if user.Status == StatusActive { ... }
if age >= MinAge { ... }
time.Sleep(DefaultTimeout)
```

```python
# ❌ 错误
if user.status == 1: ...
if age > 18: ...
time.sleep(30)
```

```python
# ✅ 正确
STATUS_ACTIVE = 1
STATUS_INACTIVE = 0
MIN_AGE = 18
DEFAULT_TIMEOUT = 30

if user.status == STATUS_ACTIVE: ...
if age >= MIN_AGE: ...
time.sleep(DEFAULT_TIMEOUT)
```

**检查项**:
- [ ] 没有魔法数字/字符串
- [ ] 常量用于可复用的值
- [ ] 常量命名清晰表达其含义
- [ ] 枚举使用 iota 或常量组

---

### 6. 发散式变化 (Divergent Change)

一个类/函数被不同原因修改，因为不同功能聚集在一起。

```python
# ❌ 错误 - 导出逻辑聚集，但被不同原因修改
def export_data(format):
    if format == "csv":
        # CSV 导出逻辑
        ...
    elif format == "excel":
        # Excel 导出逻辑
        ...
    elif format == "pdf":
        # PDF 导出逻辑
        ...
    elif format == "json":
        # JSON 导出逻辑
        ...

# 新增一个格式要改这个函数
# 修改 CSV 逻辑不影响 Excel 逻辑
```

```python
# ✅ 正确 - 职责分离
class Exporter(ABC):
    @abstractmethod
    def export(self, data): ...

class CSVExporter(Exporter):
    def export(self, data): ...

class ExcelExporter(Exporter):
    def export(self, data): ...

# 新增格式只需新增类，无需修改已有代码
```

**检查项**:
- [ ] 没有函数/类被不同原因修改
- [ ] 不同功能逻辑已分离
- [ ] 使用策略模式替代条件分发

---

### 7. 夸夸其谈通用性 (Premature Generalization)

过早或过度抽象，增加复杂度但不带来实际好处。

```go
// ❌ 错误 - 过度设计
type GenericService[T any] struct {
    repo GenericRepo[T]
    cache GenericCache[T]
    logger GenericLogger
    validator GenericValidator[T]
    // ... 过多抽象层
}
```

```python
# ✅ 正确 - 简单直接
def get_user(user_id):
    return db.get(User, user_id)
```

**检查项**:
- [ ] 没有为假设的需求做抽象
- [ ] 抽象有实际复用支撑
- [ ] 三层以上抽象需要 justification
- [ ] 简单问题用简单方案

---

### 8. 依懒过多的类 (Feature Envy)

函数/类过于依赖另一个模块的数据或逻辑。

```python
# ❌ 错误 - UserOrderService 过于依赖 Order 的内部字段
class UserOrderService:
    def get_total(self, user):
        total = 0
        for order in user.orders:
            total += order.price * (1 - order.discount)  # 太多细节泄露
        return total
```

```python
# ✅ 正确 - 委托给对象本身
class Order:
    def total_price(self):
        return self.price * (1 - self.discount)

class UserService:
    def get_total(self, user):
        return sum(order.total_price() for order in user.orders)
```

**检查项**:
- [ ] 函数没有过多访问其他对象的内部状态
- [ ] 逻辑放在数据所属的类/模块中
- [ ] 通过接口而非直接访问获取数据

---

### 9. 注释过多 (Comments)

需要大量注释才能理解的代码，说明代码本身不够清晰。

```python
# ❌ 错误 - 代码不够自解释
# 获取用户信息
# 遍历用户订单列表
# 计算总金额
# 过滤出状态为已支付的订单
# 返回结果
def get_data(u, o):  # 参数名没有意义
    # 开始循环
    for x in o:  # 变量名没有意义
        if x.s == 1:  # 魔法数字 + 缩写
            t += x.p  # 缩写
    return t  # 缩写
```

```python
# ✅ 正确 - 代码自解释
def get_total_paid_amount(user: User) -> float:
    return sum(
        order.price
        for order in user.orders
        if order.status == StatusPaid
    )
```

**检查项**:
- [ ] 代码不需要注释来解释"做什么"
- [ ] 注释解释"为什么"而非"是什么"
- [ ] 变量/函数命名自解释
- [ ] 注释不过于冗长（> 10 行注释需警惕）

---

### 10. 过长消息链 (Middle Man / Feature Envy Chain)

一连串的 get 调用导致可读性差和脆弱。

```go
// ❌ 错误 - 消息链过长
city := user.Address.City.Name  // 4 层访问
```

```python
# ❌ 错误 - 消息链过长
total = user.orders[0].items[0].product.category.parent.name
```

```python
# ✅ 正确 - 通过方法封装
class User:
    @property
    def city_name(self) -> str:
        if self.address:
            return self.address.city.name
        return ""
```

```go
// ✅ 正确 - 通过方法封装
func (u *User) CityName() string {
    if u.Address != nil && u.Address.City != nil {
        return u.Address.City.Name
    }
    return ""
}
```

**检查项**:
- [ ] 对象访问链不超过 2 层
- [ ] 通过委托方法封装深层访问
- [ ] 使用 nil-safe 访问

---

### 11. 数据泥团 (Primitive Obsession)

多个数据总是一起出现，却没有封装为对象。

```python
# ❌ 错误 - 用多个参数表示一个概念
def create_address(street, city, province, country, zip_code, latitude, longitude):
    pass

def update_address(user_id, street, city, province, country, zip_code, latitude, longitude):
    pass

def search_address(street, city, province, country, zip_code, latitude, longitude):
    pass
```

```python
# ✅ 正确 - 封装为对象
@dataclass
class Address:
    street: str
    city: str
    province: str
    country: str
    zip_code: str
    latitude: float
    longitude: float

def create_address(addr: Address): pass
def update_address(user_id: int, addr: Address): pass
```

```go
// ✅ 正确 - 使用结构体
type Address struct {
    Street   string
    City     string
    Province string
    Country  string
    ZipCode  string
    Lat      float64
    Lng      float64
}

func CreateAddress(addr Address) error { ... }
```

**检查项**:
- [ ] 相关数据组合为结构体/对象
- [ ] 没有 4+ 个同类参数总是一起出现
- [ ] 地址/坐标/日期范围等概念有封装

---

### 12. 过深的嵌套 (Deep Nesting)

代码嵌套层级过深，降低可读性。

```go
// ❌ 错误 - 嵌套过深
func Process(c *gin.Context) {
    if err := validate(c); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    data, err := fetchData()
    if err != nil {
        c.JSON(500, gin.H{"error": err.Error()})
        return
    }
    if data != nil {
        for _, item := range data.Items {
            if item.Active {
                if result, err := processItem(item); err == nil {
                    results = append(results, result)
                }
            }
        }
    }
    c.JSON(200, results)
}
```

```go
// ✅ 正确 - 卫语句 + 提前返回
func Process(c *gin.Context) {
    data, err := fetchData()
    if err != nil {
        common.AbortWithInternalServerError(c, err.Error())
        return
    }

    var results []Result
    for _, item := range data.Items {
        if !item.Active {
            continue
        }
        result, err := processItem(item)
        if err != nil {
            continue
        }
        results = append(results, result)
    }

    c.JSON(200, results)
}
```

**检查项**:
- [ ] 嵌套层级 <= 3 层（if/for/swtich）
- [ ] 使用提前返回（guard clause）减少嵌套
- [ ] 使用 continue/break 简化循环逻辑

---

## 最佳实践

1. **小函数** - 一个函数做一件事，行数合理
2. **不重复** - 提取复用，遵循 DRY
3. **单一职责** - 类/模块职责清晰不泛滥
4. **命名清晰** - 变量/函数名自解释
5. **少抽象** - 不要为假设的需求过度设计
6. **封装数据** - 相关数据组合为对象
7. **浅嵌套** - 使用卫语句和提前返回
8. **常量化** - 拒绝魔法数字和字符串
