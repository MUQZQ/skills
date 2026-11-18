#!/usr/bin/env node
// 启云方原理图站点登录/进入工程脚本（qeda-schematic-login skill 的脚本化流程）。
// 只连接已有浏览器的 CDP 调试端口，不启动浏览器、不注册新实例。
//
// 用法：
//   node login.mjs check
//   node login.mjs captcha --account <账号> --password <密码> [--out <放大图路径>]
//   node login.mjs submit  --captcha <4位数字>
//   node login.mjs enter   --project <projectId> [--sheet <图页标题>]
//   node login.mjs open    --sheet <图页标题>
//
// 全局参数：--cdp <url>（默认 http://127.0.0.1:9222；IPv6 环境用 http://[::1]:9222）

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
const cdpUrl = process.argv.includes('--cdp') ? argValue('cdp', 'http://127.0.0.1:9222') : 'http://127.0.0.1:9222'

async function listPages() {
  const response = await fetch(cdpUrl + '/json/list', { signal: AbortSignal.timeout(5000) })
  if (!response.ok) throw new Error(`CDP ${cdpUrl} 返回 ${response.status}`)
  return (await response.json()).filter(target => target.type === 'page')
}

async function connect(page) {
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = () => reject(new Error('CDP WebSocket 连接失败')) })
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id !== undefined && pending.has(message.id)) { pending.get(message.id)(message); pending.delete(message.id) }
  })
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const messageId = ++id
    pending.set(messageId, message => message.error ? reject(new Error(message.error.message)) : resolve(message.result))
    ws.send(JSON.stringify({ id: messageId, method, params }))
  })
  const evalJs = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error('页面执行异常：' + (result.exceptionDetails.text || ''))
    return result.result?.value
  }
  return { ws, send, evalJs }
}

function findPage(pages, needle) {
  const page = pages.find(t => (t.url || '').includes(needle))
  if (!page) throw new Error(`未找到含 ${needle} 的页面`)
  return page
}

async function pageState(evalJs) {
  return JSON.parse(await evalJs(`JSON.stringify({ url: location.href, tabs: document.querySelectorAll('#tabbar .tabbar-tab').length, editor: !!document.querySelector('#tabbar_bodies iframe'), text: (document.body.innerText || '').slice(0, 150) })`))
}

// ---------- check ----------
async function runCheck() {
  const pages = await listPages()
  const page = pages.find(t => (t.url || '').includes('schematic.qyf'))
  if (!page) { console.log('NO_SCHEMATIC_PAGE'); return }
  const { evalJs, ws } = await connect(page)
  const state = await pageState(evalJs)
  console.log(JSON.stringify(state))
  ws.close()
}

// ---------- captcha ----------
async function runCaptcha() {
  const account = argValue('account')
  const password = argValue('password')
  const outPath = process.argv.includes('--out') ? argValue('out') : 'qeda-captcha.png'
  const pages = await listPages()
  const page = findPage(pages, 'uiam')
  const { evalJs, ws } = await connect(page)
  const count = await evalJs(`(function(){
    var set = function(el, v) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
    var ins = Array.from(document.querySelectorAll('input.el-input__inner'))
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
  const page = findPage(pages, 'uiam')
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
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 700))
    const state = await evalJs(`JSON.stringify({ url: location.href, text: (document.body.innerText || '').slice(0, 160) })`)
    const parsed = JSON.parse(state)
    if (!parsed.url.includes('/login')) {
      console.log('LOGIN_OK url=' + parsed.url)
      if (parsed.url.includes('noPermission')) console.log('注意：noPermission 是认证通过信号，约 6 秒后跳回登录页，请立即运行 enter 子命令')
      ws.close()
      return
    }
    if (/验证码错误|密码错误/.test(parsed.text || '')) {
      console.log('LOGIN_FAIL ' + parsed.text.replace(/\n/g, ' | '))
      console.log('验证码已刷新，需重新运行 captcha 子命令取新图')
      ws.close()
      return
    }
  }
  console.log('LOGIN_TIMEOUT 仍在登录页且无明确错误')
  ws.close()
}

// ---------- enter ----------
async function runEnter() {
  const project = argValue('project')
  const pages = await listPages()
  const page = findPage(pages, 'schematic.qyf')
  const { evalJs, send, ws } = await connect(page)
  await send('Page.navigate', { url: `${SCHEMATIC}/#/,id=${project}` })
  await new Promise(r => setTimeout(r, 2000))
  await send('Page.reload', { ignoreCache: true })
  let last = ''
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1500))
    const state = await pageState(evalJs)
    last = JSON.stringify(state)
    if (state.tabs >= 1 && state.editor) { console.log('ENTER_OK ' + last); ws.close(); return }
  }
  console.log('ENTER_TIMEOUT ' + last)
  ws.close()
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
  const page = findPage(pages, 'schematic.qyf')
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
