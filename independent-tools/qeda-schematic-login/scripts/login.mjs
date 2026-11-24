#!/usr/bin/env node
// 启云方原理图站点登录/进入工程脚本（qeda-schematic-login skill 的脚本化流程）。
// 只连接已有浏览器的 CDP 调试端口，不启动浏览器、不注册新实例。
//
// 用法：
//   node login.mjs check
//   node login.mjs captcha --account <账号> [--out <放大图路径>]
//   node login.mjs submit  --captcha <4位数字>
//   node login.mjs enter   --project <projectId> [--sheet <图页标题>]
//   node login.mjs open    --sheet <图页标题>
//
// 全局参数：--cdp <本机调试地址>（默认 http://127.0.0.1:9222）、--target <页签 ID>

const SCHEMATIC = 'https://schematic.qyf.df2cloud.com'

function argValue(name, fallback) {
  const index = process.argv.indexOf('--' + name)
  if (index === -1 || index + 1 >= process.argv.length) {
    if (fallback !== undefined) return fallback
    console.error(`缺少参数 --${name}`)
    process.exit(2)
  }
  return process.argv[index + 1]
}

const sub = process.argv[2]
const cdpUrl = argValue('cdp', 'http://127.0.0.1:9222')
const targetId = argValue('target', '')
const isLoopback = hostname => ['127.0.0.1', '[::1]', 'localhost'].includes(hostname)

async function listPages() {
  const cdp = new URL(cdpUrl)
  if (cdp.protocol !== 'http:' || !isLoopback(cdp.hostname) || cdp.username || cdp.password) {
    throw new Error('CDP 必须是本机 HTTP 调试地址')
  }
  const response = await fetch(new URL('/json/list', cdp), { signal: AbortSignal.timeout(5000), redirect: 'error' })
  if (!response.ok) throw new Error(`CDP 返回 ${response.status}`)
  return (await response.json()).filter(target => {
    if (!['page', 'webview'].includes(target.type) || (targetId && target.id !== targetId)) return false
    if (!URL.canParse(target.url) || !URL.canParse(target.webSocketDebuggerUrl)) return false
    const socket = new URL(target.webSocketDebuggerUrl)
    return new URL(target.url).origin === SCHEMATIC && socket.protocol === 'ws:' && socket.host === cdp.host
  })
}

async function connect(page) {
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      ws.close()
      reject(new Error('CDP WebSocket 连接超时'))
    }, 5000)
    ws.onopen = () => { clearTimeout(timer); resolve() }
    ws.onerror = () => { clearTimeout(timer); reject(new Error('CDP WebSocket 连接失败')) }
  })
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    pending.get(message.id)?.(message)
  })
  ws.addEventListener('close', () => {
    for (const finish of pending.values()) finish({ error: { message: '方枢调试目标已关闭，请检查客户端及启动日志' } })
  })
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const messageId = ++id
    const finish = message => {
      clearTimeout(timer)
      pending.delete(messageId)
      if (message.error) reject(new Error(message.error.message))
      else resolve(message.result)
    }
    const timer = setTimeout(() => finish({ error: { message: `CDP ${method} 执行超时` } }), 7000)
    pending.set(messageId, finish)
    try {
      ws.send(JSON.stringify({ id: messageId, method, params }))
    } catch (error) {
      finish({ error })
    }
  })
  const evalJs = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error('页面执行异常：' + (result.exceptionDetails.text || ''))
    return result.result?.value
  }
  return { ws, send, evalJs }
}

function findPage(pages, loginOnly = false) {
  const targets = loginOnly ? pages.filter(page => new URL(page.url).hash.includes('/login')) : pages
  if (!targets.length) throw new Error(loginOnly ? '未找到方枢登录页' : '未找到方枢页')
  if (targets.length > 1) throw new Error('存在多个方枢页签，请用 --target 指定调试目标 ID')
  return targets[0]
}

async function pageState(evalJs) {
  return await evalJs(`({
    url: location.origin + location.pathname,
    login: location.hash.includes('/login'),
    portalDenied: location.hash.includes('noPermission'),
    transitioning: location.pathname === '/versionSelect.html' || new URLSearchParams(location.search).has('code'),
    project: location.hash.match(/(?:^|[#,/])id=([A-Za-z0-9_-]+)(?:,|$)/)?.[1],
    tabs: document.querySelectorAll('#tabbar .tabbar-tab').length,
    editor: !!document.querySelector('#tabbar_bodies iframe')
  })`)
}

async function authenticated(evalJs) {
  return await evalJs(`(async () => {
    if (location.origin !== ${JSON.stringify(SCHEMATIC)}) return false;
    try {
      const response = await fetch('/gateway/systemManage/v1/sso/login', {
        credentials: 'same-origin', signal: AbortSignal.timeout(2500)
      });
      if (!response.ok) return false;
      const {data} = await response.json();
      const name = data?.username ?? data?.userName;
      return typeof name === 'string' && name.trim().length > 0;
    } catch (error) {
      if (error instanceof TypeError || error.name === 'TimeoutError') return false;
      throw error;
    }
  })()`)
}

// ---------- check ----------
async function runCheck() {
  const pages = await listPages()
  if (!pages.length) { console.log('NO_SCHEMATIC_PAGE'); return }
  const page = findPage(pages)
  const { evalJs, ws } = await connect(page)
  const state = await pageState(evalJs)
  const signedIn = !state.login && !state.transitioning && await authenticated(evalJs)
  console.log(JSON.stringify({ ...state, type: page.type, authenticated: signedIn }))
  ws.close()
}

// ---------- captcha ----------
async function runCaptcha() {
  const account = argValue('account')
  const password = argValue('password', process.env.QEDA_SCHEMATIC_PASSWORD ?? '')
  if (!password) throw new Error('请通过 QEDA_SCHEMATIC_PASSWORD 提供测试账号密码')
  const outPath = process.argv.includes('--out') ? argValue('out') : 'qeda-captcha.png'
  const pages = await listPages()
  const page = findPage(pages, true)
  const { evalJs, ws } = await connect(page)
  const count = await evalJs(`(function(){
    var set = function(el, v) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
    var ins = Array.from(document.querySelectorAll('input.el-input__inner'))
    if (ins.length < 3) return ins.length
    set(ins[0], ${JSON.stringify(account)})
    set(ins[1], ${JSON.stringify(password)})
    return ins.length
  })()`)
  if (typeof count !== 'number' || count < 3) throw new Error(`登录表单输入框数量异常：${count}`)
  // 页面内 canvas 放大：NEAREST（imageSmoothingEnabled=false）×12，零外部依赖
  const base64 = await evalJs(`(function(){
    var img = Array.from(document.querySelectorAll('img')).find(function(i){ return (i.src || '').startsWith('data:image') })
    if (!img) return null
    return new Promise(function(resolve, reject) {
      var image = new Image()
      image.onload = function() {
        var scale = 12
        var canvas = document.createElement('canvas')
        canvas.width = image.width * scale
        canvas.height = image.height * scale
        var ctx = canvas.getContext('2d')
        ctx.imageSmoothingEnabled = false
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/png'))
      }
      image.onerror = function() { reject(new Error('验证码图片加载失败')) }
      image.src = img.src
    })
  })()`)
  if (!base64) throw new Error('未找到 data:image 验证码图片')
  const { writeFileSync } = await import('node:fs')
  writeFileSync(outPath, Buffer.from(base64.replace(/^data:image\/png;base64,/, ''), 'base64'))
  console.log(`CAPTCHA_SAVED=${outPath}`)
  console.log('请读取验证码（4 位数字，每位一种颜色），然后运行：node login.mjs submit --captcha <答案>')
  ws.close()
}

// ---------- submit ----------
async function runSubmit() {
  const captcha = argValue('captcha')
  if (!/^\d{4}$/.test(captcha)) throw new Error('验证码应为 4 位数字')
  const pages = await listPages()
  const page = findPage(pages, true)
  const { evalJs, ws } = await connect(page)
  const submitted = await evalJs(`(function(){
    var set = function(el, v) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
    var ins = Array.from(document.querySelectorAll('input.el-input__inner'))
    if (ins.length < 3) return 'inputs=' + ins.length
    set(ins[2], ${JSON.stringify(captcha)})
    var button = document.querySelector('button.el-button--primary')
    if (!button) return 'no-button'
    button.click()
    return 'submitted'
  })()`)
  if (submitted !== 'submitted') throw new Error('提交失败：' + submitted)
  let portalDenied = false
  const deadline = Date.now() + 25000
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 700))
    const state = await pageState(evalJs)
    portalDenied ||= state.portalDenied
    if (!state.login && !state.portalDenied && !state.transitioning && await authenticated(evalJs)) {
      console.log('LOGIN_OK 方枢业务会话已确认')
      ws.close()
      return
    }
    if (state.login && await evalJs(`/验证码错误|密码错误/.test(document.body.innerText || '')`)) {
      ws.close()
      throw new Error('LOGIN_FAIL 登录表单拒绝，请重新核对凭据或获取验证码')
    }
  }
  ws.close()
  throw new Error(portalDenied ? 'LOGIN_PORTAL_DENIED 门户返回无权限，尚未确认方枢业务会话' : 'LOGIN_TIMEOUT 尚未确认方枢业务会话')
}

// ---------- enter ----------
async function runEnter() {
  const project = argValue('project')
  if (!/^[A-Za-z0-9_-]+$/.test(project)) throw new Error('工程 ID 格式无效')
  const pages = await listPages()
  const page = findPage(pages)
  const { evalJs, send, ws } = await connect(page)
  const initial = await pageState(evalJs)
  if (initial.login || initial.transitioning || initial.portalDenied || !await authenticated(evalJs)) {
    throw new Error('方枢业务会话未就绪，请先完成登录确认')
  }
  if (initial.project === project && initial.tabs >= 1 && initial.editor) {
    console.log('ENTER_OK ' + JSON.stringify(initial))
    ws.close()
    return
  }
  await send('Page.navigate', { url: `${SCHEMATIC}/#/,id=${project}` })
  // DSH 内嵌页跟随宿主导航，避免在 SSO 跳转后强制刷新。
  if (page.type === 'page') {
    await new Promise(r => setTimeout(r, 2000))
    await send('Page.reload', { ignoreCache: true })
  }
  let last = ''
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1500))
    const state = await pageState(evalJs)
    last = JSON.stringify(state)
    if (state.project === project && state.tabs >= 1 && state.editor) { console.log('ENTER_OK ' + last); ws.close(); return }
  }
  ws.close()
  throw new Error('ENTER_TIMEOUT ' + last)
}

// ---------- open（在树中点开图页；树面板折叠时自动展开）----------
// easyui/tianshu 控件不响应合成 MouseEvent，必须用 CDP Input 真实输入。
// easyui 树：单击仅选中，双击才打开图页。
async function clickViaCdp(send, x, y) {
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y })
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 })
  await new Promise(r => setTimeout(r, 80))
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 })
  await new Promise(r => setTimeout(r, 150))
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 2 })
  await new Promise(r => setTimeout(r, 80))
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 2 })
}

async function clickTreeTitle(evalJs, send, sheet) {
  const rect = await evalJs(`(function(){
    var title = Array.from(document.querySelectorAll('ul.easyui-tree .tree-title')).find(function(el){ return (el.textContent || '').trim() === ${JSON.stringify(sheet)} })
    if (!title || title.offsetParent === null) return null
    title.scrollIntoView({ block: 'center' })
    var node = title.closest('.tree-node') || title.parentElement
    var r = node.getBoundingClientRect()
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }
  })()`)
  if (!rect) return false
  await new Promise(r => setTimeout(r, 400))
  await clickViaCdp(send, rect.x, rect.y)
  return true
}

async function runOpen() {
  const sheet = argValue('sheet')
  const pages = await listPages()
  const page = findPage(pages)
  const { evalJs, send, ws } = await connect(page)
  let clicked = await clickTreeTitle(evalJs, send, sheet)
  if (!clicked) {
    // 左面板可能被折叠（.layout-toggler.left.close）：点把手展开后重试
    const toggler = await evalJs(`(function(){
      var t = document.querySelector('.layout-toggler.left.close') || document.querySelector('.layout-toggler.close')
      if (!t) return null
      var r = t.getBoundingClientRect()
      return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }
    })()`)
    if (!toggler) throw new Error('未找到图页标题且无折叠面板把手：' + sheet)
    await clickViaCdp(send, toggler.x, toggler.y)
    await new Promise(r => setTimeout(r, 2000))
    clicked = await clickTreeTitle(evalJs, send, sheet)
  }
  if (!clicked) throw new Error('未找到图页标题：' + sheet)
  await new Promise(r => setTimeout(r, 3500))
  const state = await pageState(evalJs)
  const active = await evalJs(`JSON.stringify((function(){
    var t = document.querySelector('#tabbar .tabbar-tab.sheet.active')
    return t ? { text: (t.textContent||'').trim().slice(0, 40), tabid: t.getAttribute('tabid') } : null
  })())`)
  console.log('OPEN_OK ' + JSON.stringify(state) + ' ACTIVE=' + active)
  ws.close()
}

const runners = { check: runCheck, captcha: runCaptcha, submit: runSubmit, enter: runEnter, open: runOpen }
const runner = runners[sub]
if (!runner) {
  console.error('子命令应为：check | captcha | submit | enter | open')
  process.exit(2)
}
try {
  await runner()
} catch (error) {
  if (String(error.message).includes('fetch failed')) {
    console.error('CDP 连接失败：' + error.message)
    console.error('提示：调试端口可能只绑 IPv6，改用 --cdp http://[::1]:9222')
  } else {
    console.error('ERROR ' + error.message)
  }
  process.exit(1)
}
