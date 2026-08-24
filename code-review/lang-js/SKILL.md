---
name: lang-js
description: JavaScript 编码规范：命名、模块化、异步处理、错误处理、代码格式化
---

# JavaScript 编码规范

## 何时激活

- 变更涉及 `*.js` 或 `*.mjs` 文件
- 新增或修改 JavaScript 代码
- 编写 Node.js 脚本或工具

---

# JavaScript 基础规范

## 命名

### 变量和函数

```javascript
// ✅ 正确：camelCase
const userName = 'John'
const fetchUserList = async () => { ... }
const isValid = true

// ✅ 正确：描述性动词
function getUserById(id) { ... }
function hasPermission(user, action) { ... }
function formatData(data) { ... }
```

### 常量和配置

```javascript
// ✅ 正确：UPPER_SNAKE_CASE
const MAX_RETRIES = 3
const API_BASE_URL = 'https://api.example.com'
const DEFAULT_TIMEOUT = 30000
```

### 构造函数和类

```javascript
// ✅ 正确：PascalCase
class UserService {
  constructor(config) {
    this.baseUrl = config.apiUrl
  }
}

class EventEmitter {
  on(event, callback) { ... }
  emit(event, data) { ... }
}
```

### 文件命名

```javascript
// ✅ 正确：kebab-case
// user-service.js
// data-parser.js
// config-loader.js
```

## 模块化

### 导入导出

```javascript
// ✅ 正确：默认导出只有一个，命名导出多个
// user-service.js
export class UserService { ... }
export function createUser() { ... }

export default class MainService { ... }

// ✅ 正确：导入分组
import path from 'path'
import fs from 'fs'

import { UserService, createUser } from './user-service'
import { config } from './config'
```

### 不使用 require

```javascript
// ✅ 正确：ESM
import { foo } from './module'

// ❌ 错误：CommonJS
const { foo } = require('./module')
```

## 异步处理

### 使用 async/await

```javascript
// ✅ 正确：async/await
const fetchUser = async (id) => {
  try {
    const res = await fetch(`/api/users/${id}`)
    return await res.json()
  } catch (err) {
    console.error(`获取用户失败: ${err.message}`)
    throw err
  }
}

// ✅ 正确：并行请求
const fetchDashboard = async () => {
  const [users, stats] = await Promise.all([
    fetchUsers(),
    fetchStats()
  ])
  return { users, stats }
}
```

### 不使用 then 链

```javascript
// ❌ 错误：then 链
fetch('/api/data')
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err))

// ✅ 正确：async/await
const loadData = async () => {
  try {
    const res = await fetch('/api/data')
    const data = await res.json()
    console.log(data)
  } catch (err) {
    console.error(err)
  }
}
```

### Promise 处理

- [ ] 所有 Promise 都有 catch 处理
- [ ] 不使用未捕获的 Promise
- [ ] 并行请求使用 `Promise.all`

## 错误处理

### 核心原则

- [ ] 不忽略错误
- [ ] 使用 try-catch 处理异步错误
- [ ] 错误信息清晰可定位

```javascript
// ✅ 正确：完整的错误处理
const processFile = async (filePath) => {
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    const data = JSON.parse(content)
    return validate(data)
  } catch (err) {
    if (err.code === 'ENOENT') {
      console.error(`文件不存在: ${filePath}`)
    } else if (err instanceof SyntaxError) {
      console.error(`JSON 格式错误: ${err.message}`)
    } else {
      console.error(`处理失败: ${err.message}`)
    }
    throw err
  }
}

// ❌ 错误：忽略错误
fs.readFile(filePath, (err, data) => {
  // 什么也不做
})
```

### 自定义错误

```javascript
// ✅ 正确：自定义错误类型
class AppError extends Error {
  constructor(message, code) {
    super(message)
    this.code = code
    this.name = 'AppError'
  }
}

class ValidationError extends AppError {
  constructor(message) {
    super(message, 'VALIDATION_ERROR')
    this.name = 'ValidationError'
  }
}
```

## 代码格式化

- [ ] 使用 Prettier 或 ESLint 格式化代码
- [ ] 使用单引号
- [ ] 不使用分号（或项目统一使用）
- [ ] 每行不超过 120 字符
- [ ] 使用 `const` / `let`，不 `var`

```javascript
// ✅ 正确：const / let
const count = 10
let index = 0

while (index < count) {
  console.log(index)
  index++
}

// ❌ 错误：var
var name = 'test'
```

## 字符串处理

- [ ] 使用模板字符串
- [ ] 不使用字符串拼接

```javascript
// ✅ 正确：模板字符串
const message = `处理完成: ${userName} (${total} 个)`

// ❌ 错误：字符串拼接
const message = '处理完成: ' + userName + ' (' + total + ' 个)'
```

## 数组和对象

### 数组操作

```javascript
// ✅ 正确：现代数组方法
const activeUsers = users.filter(u => u.active)
const names = activeUsers.map(u => u.name)
const total = prices.reduce((sum, price) => sum + price, 0)

// ✅ 正确：展开运算符
const copy = [...original]
const merged = { ...obj1, ...obj2 }

// ❌ 错误：for 循环
for (let i = 0; i < arr.length; i++) {
  console.log(arr[i])
}
```

### 对象解构

```javascript
// ✅ 正确：解构赋值
const { name, age } = user
const { data, status } = await fetchData()

// ✅ 正确：默认值
const { name, age = 0, role = 'user' } = user
```

## 日志使用

- [ ] 使用 `console` 或 `winston` / `pino`
- [ ] 不使用 `debugger`
- [ ] 不记录敏感数据

```javascript
// ✅ 正确
console.info('处理文件:', filePath)
console.error('处理失败:', error.message)

// ❌ 错误
console.log('API Key:', apiKey)  // 泄露敏感信息
debugger  // 忘记删除
```

## 最佳实践

1. **const / let** - 不使用 `var`
2. **async/await** - 不使用 then 链
3. **箭头函数** - 优先使用箭头函数
4. **模板字符串** - 不使用字符串拼接
5. **展开运算符** - 不使用 `Object.assign`
6. **解构赋值** - 简化参数和返回值
7. **错误处理** - 完整的 try-catch
8. **模块化** - ESM 导入导出
9. **常量 UPPER_SNAKE_CASE** - 提高可读性
10. **文件 kebab-case** - 统一命名
