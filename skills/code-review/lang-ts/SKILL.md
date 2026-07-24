---
name: lang-ts
description: TypeScript 编码规范：类型定义、泛型、接口、枚举、装饰器、工具类型
---

# TypeScript 编码规范

## 何时激活

- 变更涉及 `*.ts` 或 `*.tsx` 文件
- 新增或修改 TypeScript 代码
- 编写类型定义文件 `*.d.ts`

---

# TypeScript 基础规范

## 命名

### 类型和接口

```typescript
// ✅ 正确：PascalCase
interface User {
  id: string
  name: string
  email: string
}

type UserRole = 'admin' | 'user' | 'guest'

class UserService {
  async findById(id: string): Promise<User> { ... }
}
```

### 类型别名 vs 接口

```typescript
// ✅ 正确：接口用于对象类型，类型别名用于联合/交叉/原始类型
interface Config {
  apiUrl: string
  timeout: number
}

// 联合类型使用 type
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

// 交叉类型使用 type
type AdminUser = User & { role: 'admin' }
```

### 枚举 vs 联合类型

```typescript
// ✅ 推荐：使用联合类型（更灵活）
type Status = 'pending' | 'active' | 'completed'

// ✅ 可接受：需要值映射时
enum Priority {
  Low = 'low',
  Medium = 'medium',
  High = 'high',
}
```

## 类型定义

### 优先使用类型推断

```typescript
// ✅ 正确：可推断类型
const count = 0
const name = 'test'
const isActive = true

// ✅ 必要：明确标注函数返回类型
function formatUser(user: User): string {
  return `${user.name} (${user.email})`
}
```

### 不使用 any

```typescript
// ✅ 正确：使用 unknown
function processData(input: unknown): void {
  if (typeof input === 'string') {
    console.log(input.toUpperCase())
  }
}

// ✅ 正确：使用具体类型
function getUser(id: string): User | null {
  return users.find(u => u.id === id) ?? null
}

// ❌ 错误：使用 any
function getData(id: string): any {
  return fetch(`/api/data/${id}`)
}
```

### 避免类型断言

```typescript
// ✅ 正确：类型守卫
function isUser(obj: unknown): obj is User {
  return typeof obj === 'object' && obj !== null && 'name' in obj
}

// ❌ 错误：强制类型断言
const user = data as User
```

## 泛型

### 泛型约束

```typescript
// ✅ 正确：泛型约束
function getById<T extends { id: string }>(items: T[], id: string): T | null {
  return items.find(item => item.id === id) ?? null
}

// ✅ 正确：泛型默认值
interface ApiResponse<T = unknown> {
  data: T
  status: number
  message: string
}
```

### 泛型命名

```typescript
// ✅ 正确：T, U, V 或 T extends ...
function map<T, U>(arr: T[], fn: (item: T) => U): U[] { ... }

class Repository<T extends BaseEntity> {
  find(id: string): T | null { ... }
}
```

## 接口设计

### 接口继承

```typescript
// ✅ 正确：通过 extends 扩展
interface BaseUser {
  id: string
  name: string
}

interface AdminUser extends BaseUser {
  permissions: string[]
  department: string
}
```

### 可选属性

```typescript
// ✅ 正确：明确可选
interface UserProfile {
  name: string
  email: string
  avatar?: string  // 可选
  bio?: string | null  // 可选且可为 null
}
```

## 工具类型

### 使用内置工具类型

```typescript
// ✅ 正确：Pick / Omit / Partial / Required
type UserCreateInput = Omit<User, 'id' | 'createdAt'>
type UserUpdateInput = Partial<Pick<User, 'name' | 'email'>>

// ✅ 正确：Record
type RolePermissions = Record<string, string[]>

// ✅ 正确：Exclude / Extract
type NonNull<T> = Exclude<T, null>
type StringArray = Extract<string, number | string | boolean>
```

### 不使用 any with generics

```typescript
// ✅ 正确：使用 Record 或 Map
type ConfigMap = Record<string, Config>
const configMap = new Map<string, Config>()

// ❌ 错误
const configMap: { [key: string]: Config } = {}
```

## 装饰器

```typescript
// ✅ 正确：使用 decorator 类型
declare type MethodDecorator = <T>(
  target: object,
  propertyKey: string | symbol,
  descriptor: TypedPropertyDescriptor<T>
) => TypedPropertyDescriptor<T> | void

// ✅ 正确：参数装饰器类型
declare type ParamDecorator = (
  target: object,
  propertyKey: string | symbol,
  parameterIndex: number
) => void
```

## 模块导入导出

```typescript
// ✅ 正确：类型导入分离
import type { User, UserRole } from './types'
import { UserService } from './service'

// ✅ 正确：命名导出
export interface Config { ... }
export class Service { ... }

// ✅ 正确：类型重新导出
export type { User, UserRole } from './types'
```

## 严格模式

- [ ] 启用 `strict: true`
- [ ] 不使用 `@ts-ignore`（除非必要并有注释）
- [ ] 不使用 `@ts-expect-error`（除非必要并有注释）
- [ ] 不关闭 `noImplicitAny`
- [ ] 不关闭 `strictNullChecks`

```typescript
// ✅ 正确：处理 null/undefined
function getUserName(user: User | null): string {
  return user?.name ?? '匿名'
}

// ❌ 错误：非空断言
function getUserName(user: User): string {
  return user!.name  // 危险
}
```

## 错误处理

### 错误类型

```typescript
// ✅ 正确：自定义错误
class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message)
    this.name = 'AppError'
  }
}
```

### 错误响应

```typescript
// ✅ 正确：统一错误响应
interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: ApiError | null
}

interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}
```

## 最佳实践

1. **strict 模式** - 始终启用 TypeScript 严格模式
2. **类型推断** - 让 TS 推断简单类型，标注函数签名
3. **避免 any** - 使用 `unknown` 或具体类型
4. **泛型约束** - 使用 `extends` 限制泛型
5. **接口扩展** - 使用 `extends` 而非合并
6. **工具类型** - 善用 `Pick`, `Omit`, `Partial` 等
7. **空值处理** - 使用 `?.` 和 `??` 而非 `!`
8. **联合类型** - 优先于 `any`
9. **类型守卫** - 使用 `is` 而非类型断言
10. **装饰器类型** - 正确声明装饰器类型
