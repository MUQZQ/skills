---
name: lang-react
description: React 前端编码规范：组件、Hooks、i18n、状态管理、错误处理
---

# React 前端编码规范

## 何时激活

- 变更涉及 `web/` 目录下的文件
- 变更涉及 `*.jsx` 或 `*.tsx` 文件
- 新增或修改 React 组件

## 审查检查清单

### 组件结构
- [ ] 组件使用 PascalCase 命名
- [ ] 组件放在 `components/` 目录下
- [ ] 页面组件放在 `pages/` 目录下
- [ ] 使用函数组件 + Hooks (不-class 组件)

```jsx
// ✅ 正确
const UserList = ({ users, onEdit, onDelete }) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  
  return (
    <Table>
      <Table.Body>
        {users.map(user => (
          <Table.Key key={user.id}>
            <Table.Cell>{user.name}</Table.Cell>
            <Table.Cell>
              <Button onClick={() => onEdit(user)}>
                {t('common.edit')}
              </Button>
            </Table.Cell>
          </Table.Key>
        ))}
      </Table.Body>
    </Table>
  )
}

export default UserList
```

### i18n 国际化
- [ ] 所有用户可见文本使用 `t()` 函数
- [ ] 键名使用 `模块.子模块.键名` 格式
- [ ] 不使用字符串字面量

```jsx
// ✅ 正确
import { useTranslation } from 'react-i18next'

const { t } = useTranslation()
return <Button>{t('user.edit')}</Button>

// ❌ 错误
return <Button>Edit</Button>  // 硬编码字符串
```

### 状态管理
- [ ] 使用 `useState` 管理组件状态
- [ ] 使用 `useEffect` 处理副作用
- [ ] 使用 `useMemo` / `useCallback` 优化性能
- [ ] 使用 `React.memo` 包裹纯组件

```jsx
// ✅ 正确
const UserList = React.memo(({ users }) => {
  const [loading, setLoading] = useState(false)
  
  const filteredUsers = useMemo(() => {
    return users.filter(u => u.active)
  }, [users])
  
  return <Table data={filteredUsers} />
})
```

### 数据获取与加载
- [ ] 数据加载使用 `useEffect` + API 调用
- [ ] 实现加载状态 (`loading={loading}`)
- [ ] 实现错误状态提示
- [ ] 使用 try-catch 处理异常

```jsx
const UserList = () => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true)
      try {
        const res = await API.get('/api/users/')
        setUsers(res.data.data)
      } catch (err) {
        setError(err)
        showError(err)
      } finally {
        setLoading(false)
      }
    }
    fetchUsers()
  }, [])
  
  if (error) return <Message error={error.message} />
  
  return <Table loading={loading} data={users} />
}
```

### 路由与导航
- [ ] 使用 `useParams` 获取路由参数
- [ ] 使用 `useNavigate` 进行页面跳转
- [ ] 路由懒加载 (动态 import)

```jsx
// ✅ 正确
import { useNavigate, useParams } from 'react-router-dom'

const UserProfile = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  
  const handleBack = () => {
    navigate(-1)  // 返回上一页
  }
  
  return <div>User {id}</div>
}

// 路由懒加载
const SettingsPage = lazy(() => import('./pages/Settings'))
```

### 表单处理
- [ ] 表单验证在提交前执行
- [ ] 错误提示清晰可见
- [ ] 输入字段有合适的类型和验证

```jsx
const RegisterForm = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [errors, setErrors] = useState({})
  
  const validate = () => {
    const newErrors = {}
    if (formData.username.length < 3) {
      newErrors.username = '用户名至少 3 个字符'
    }
    if (formData.password.length < 8) {
      newErrors.password = '密码至少 8 个字符'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }
  
  const handleSubmit = () => {
    if (!validate()) return
    // 提交逻辑
  }
  
  return (
    <Form onSubmit={handleSubmit}>
      <Field name="username" error={errors.username} />
      <Field name="password" type="password" error={errors.password} />
      <Button type="submit">注册</Button>
    </Form>
  )
}
```

### 安全
- [ ] 不使用 `dangerouslySetInnerHTML`
- [ ] 敏感信息不存储在 localStorage
- [ ] API 请求使用正确的认证头
- [ ] 表单输入验证

```jsx
// ✅ 正确
const UserInput = ({ value }) => <div>{value}</div>

// ❌ 错误
const UserInput = ({ value }) => (
  <div dangerouslySetInnerHTML={{ __html: value }} />  // XSS 风险
)
```

## 最佳实践

1. **函数组件 + Hooks** - 不使用 class 组件
2. **i18n 全覆盖** - 所有用户文本使用 `t()`
3. **加载状态** - 数据获取必须有 loading 状态
4. **错误处理** - try-catch + 错误提示
5. **key 唯一** - 列表渲染使用唯一 ID
6. **性能优化** - `React.memo` / `useMemo` / `useCallback`
7. **安全** - 不直接使用 `dangerouslySetInnerHTML`
