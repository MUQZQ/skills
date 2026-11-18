---
name: qeda-schematic-login
description: >
  自动登录启云方原理图站点（schematic.qyf.df2cloud.com 的 UIAM 单点登录）：填账号密码、取出 base64
  验证码图片并识别（或交用户读取）、提交、处理 noPermission 跳转，并在浏览器重启丢失会话后快速重登，
  供实机验收与页面自动化前使用。当用户提到「登录原理图」「启云方登录」「schematic 登录」
  「实机验收前先登录」「验证码登录」，或给出 schematic.qyf.df2cloud.com 链接要求进入工程、图页时使用。
---

# 启云方原理图站点登录

把「打开登录页 → 填账号密码 → 读取验证码 → 提交 → 进工程」做成可复用流程。验证码是
`data:image/jpeg;base64` 内嵌图，**取出后放大即可由 Agent 直接读图识别**，不需要人工转述；
连续识别失败时再交用户读取。

## 前置条件

1. **浏览器带调试端口**（本流程用 CDP 驱动）。Edge 示例：

   ```powershell
   Start-Process 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' -ArgumentList `
     '--remote-debugging-port=9222','--ignore-certificate-errors',`
     '--user-data-dir=C:\Users\<用户>\AppData\Local\Microsoft\Edge\User Data',`
     'https://schematic.qyf.df2cloud.com/uiam/#/login'
   ```

   - `--ignore-certificate-errors` 必须带：站点证书是 `*.df2cloud.com` 单级通配符，
     `schematic.qyf.df2cloud.com` 是三级子域，严格校验会报 `ERR_CERT_COMMON_NAME_INVALID`。
   - 调试端口可能只绑 IPv6：先试 `http://127.0.0.1:9222`，连不上改 `http://[::1]:9222`。
   - **登录态不跨浏览器重启**（内存级会话），每次重启浏览器都要重登一次。

2. **CDP 目标**：`GET /json/list` 取 `type === 'page'` 且 URL 含 `uiam` 的条目。

3. **账号**：默认测试账号见下；生产/他人账号必须显式传入。

## 默认测试账号（仅测试环境）

| 项 | 值 |
|---|---|
| 账号 | `qinzuoquan` |
| 密码 | `qin123$%` |

> 用户提供的测试账号，仅用于验证登录流程。实测认证通过，但该账号在 UIAM 门户无权限，
> 登录后落到 `#/noPermission`——**这不代表登录失败**；导航到工程 URL 后编辑器可正常加载。
> 生产或真实数据操作必须换有权限账号。凭据不得写入 URL、cookie、日志或提交到仓库。

## 执行流程

### 1. 填账号与密码（Element Plus）

`v-model` 需要原生 value setter + `input` 事件，直接赋 `.value` 不生效：

```js
const set = (el, v) => {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)
  el.dispatchEvent(new Event('input', { bubbles: true }))
  el.dispatchEvent(new Event('change', { bubbles: true }))
}
const ins = Array.from(document.querySelectorAll('input.el-input__inner'))
// ins[0] 账号、ins[1] 密码（type=password）、ins[2] 验证码
set(ins[0], account)
set(ins[1], password)
```

### 2. 取验证码并识别

```js
const img = Array.from(document.querySelectorAll('img'))
  .find(i => (i.src || '').startsWith('data:image'))
img.src // data:image/jpeg;base64,...
```

识别要点（实测有效）：

1. 解码保存原图（约 95×35 px），用 **NEAREST 放大 10–12 倍**——双线性/LANCZOS 会把彩色笔画糊掉；
2. 验证码为 **4 位数字**，每位一种颜色（黑/橄榄绿/蓝/暗红），图上叠加斜线噪声；
3. 逐位读，不猜；一次读数最多用 30 秒（验证码 45 秒内不变，实测稳定）；
4. 提交失败后验证码会自动刷新，**必须重新取图**，不要拿旧图重试。

### 3. 提交并捕获登录成功信号

```js
set(ins[2], captcha)
document.querySelector('button.el-button--primary').click()
```

登录按钮文字是「登 录」（含空格），按文字匹配容易失败，**按 class 定位**。

轮询 `location.href`（每 0.7s，最多约 14s），以下任一即为认证成功：

- URL 变成 `https://schematic.qyf.df2cloud.com/?code=<SSO code>`（本次实测形态）；
- URL 进入 `#/noPermission`（门户无权限，但认证已通过）；
- URL 进入 `#/,id=<projectId>`。

仍在 `#/login` 且出现「验证码错误/密码错误」= 失败，重新取验证码重试（最多 3 次）。

> `#/noPermission` 页面会在约 6 秒后自动跳回登录页。识别到该 URL 后**立即**导航到工程 URL，
> 不要等待。

### 4. 进入工程（必须硬刷新）

```js
Page.navigate({ url: 'https://schematic.qyf.df2cloud.com/#/,id=<projectId>' })
// 2 秒后
Page.reload({ ignoreCache: true })
```

成功判据（比标题可靠）：

```js
({ url: location.href, tabs: document.querySelectorAll('#tabbar .tabbar-tab').length,
   editor: !!document.querySelector('#tabbar_bodies iframe') })
// 期望 tabs >= 1 且 editor === true
```

只 navigate 不 reload 时，路由可能停在工程列表；**硬刷新才稳定进入编辑器**。

## 登录后连接核对（重要）

**不要用页面内 `fetch('http://127.0.0.1:8080/...')` 判断桥是否可达**：Edge/Chrome 对
「公网 https 页面访问本机回环」有限制，页面内会得到 `Failed to fetch` 或超时，但站点的
QEDA MCP 客户端本身仍能建立 WebSocket。实测同一页面：页面内 fetch 报错，桥侧显示
`active` 连接（294 个 handler）。

正确核对方式是从本机查桥：

```bash
curl -s 'http://127.0.0.1:8080/api/bridge/status?projectId=<projectId>'
# 期望 connections 中 status=active、projectId 匹配、handlers 数量可观
```

若确需页面侧证据，读页面底部 QEDA MCP 面板文案（「已连接」/「未连接」），不要自己造 fetch 探针。

## 失败分支

| 现象 | 原因 | 处置 |
|---|---|---|
| `ERR_CERT_COMMON_NAME_INVALID` | 缺 `--ignore-certificate-errors` | 带该参数重启浏览器 |
| CDP 9222 连不上 | 未带调试端口/端口被占 | `netstat -ano \| findstr 9222`，换端口 |
| `fetch failed` 但端口在听 | 调试端口绑 IPv6 | 改 `http://[::1]:9222` |
| 表单填了值但提交无效 | 直接赋 `.value` 未触发框架事件 | 原生 setter + `input`/`change` |
| 验证码错误 | 识别错/用了刷新前的图 | 重新取图，NEAREST 放大再读 |
| 登录后回登录页 | 未在 6 秒内离开 noPermission，或验证码/密码错 | 识别到 noPermission 立即导航工程 URL |
| 工程页停在项目列表 | 只 navigate 未 reload | `Page.reload({ ignoreCache: true })` |
| 页面内 fetch 127.0.0.1 失败 | 浏览器本地网络限制 | 用桥状态接口核对，不要据此判断桥挂了 |

## 安全边界

- 凭据只在内存与本文件默认值中使用；**不写入** URL、cookie、localStorage、日志或提交。
- 只对测试环境使用默认测试账号；生产账号必须由用户当场提供。
- 识别只用当前 Agent 的图像读取能力，不接第三方打码服务；失败交用户读取。
- 不修改站点权限、不调用管理接口；`noPermission` 不绕过，只按工程 URL 继续业务页面。
