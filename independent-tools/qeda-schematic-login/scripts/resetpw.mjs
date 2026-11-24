#!/usr/bin/env node
// 启云方 UIAM 登录页批量改密脚本（qeda-schematic-login skill 的批量初始化密码能力）。
// 前提：登录表单已填账号与初始密码并取得验证码（用 login.mjs captcha）。验证码由使用者读取后传入。
//
// 用法：
//   node resetpw.mjs run --captcha <4位数字> --password <新密码>
//
// 判定输出（RESULT=）：
//   RESET_OK            弹窗改密成功，出现「用户修改密码成功」
//   SKIP_ALREADY_RESET  站点拒绝登录（密码错误类提示），说明初始密码已失效，跳过
//   CAPTCHA_RETRY       验证码错误，请重新 login.mjs captcha 取图
//   LOGGED_IN_UNEXPECTED 未弹改密窗直接登录成功（管理端已关闭强制改密），需人工处理
//   TIMEOUT             25 秒内未出现任何已知终态
//
// 全局参数：--cdp <本机调试地址>（默认 http://127.0.0.1:9222）、--target <页签 ID>
// 密码纪律：新密码经 --password 传入仅用于本进程内页面注入，不写入日志。

function argValue(name, fallback) {
  const index = process.argv.indexOf('--' + name)
  if (index === -1 || index + 1 >= process.argv.length) {
    if (fallback !== undefined) return fallback
    console.error(`缺少参数 --${name}`)
    process.exit(2)
  }
  return process.argv[index + 1]
}

const cdpUrl = argValue('cdp', 'http://127.0.0.1:9222')
const isLoopback = hostname => ['127.0.0.1', '[::1]', 'localhost'].includes(hostname)

async function findLoginPage() {
  const cdp = new URL(cdpUrl)
  if (cdp.protocol !== 'http:' || !isLoopback(cdp.hostname)) throw new Error('CDP 必须是本机 HTTP 调试地址')
  const targets = await (await fetch(new URL('/json/list', cdp), { signal: AbortSignal.timeout(5000) })).json()
  const pages = targets.filter(t => t.type === 'page' && URL.canParse(t.url) && t.url.includes('uiam'))
  if (pages.length !== 1) throw new Error(`方枢页签数量异常：${pages.length}（应恰好 1 个）`)
  return pages[0]
}

async function connect(page) {
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { ws.close(); reject(new Error('CDP WebSocket 连接超时')) }, 5000)
    ws.onopen = () => { clearTimeout(timer); resolve() }
    ws.onerror = () => { clearTimeout(timer); reject(new Error('CDP WebSocket 连接失败')) }
  })
  let id = 0
  const pending = new Map()
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id && pending.has(message.id)) { pending.get(message.id)(message); pending.delete(message.id) }
  })
  const send = (method, params = {}) => new Promise(resolve => {
    const messageId = ++id
    pending.set(messageId, message => resolve(message.error ?? message.result))
    ws.send(JSON.stringify({ id: messageId, method, params }))
  })
  const ev = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result?.exceptionDetails) {
      throw new Error('页面执行异常：' + String(result.exceptionDetails.exception?.description || result.exceptionDetails.text).slice(0, 200))
    }
    if (!result?.result || result.result.value === undefined) throw new Error('CDP 响应异常：' + JSON.stringify(result).slice(0, 120))
    return result.result.value
  }
  return { ws, ev }
}

const state = `JSON.stringify({
  dialog: (function(){
    var d = Array.from(document.querySelectorAll('.el-dialog')).find(function(x){ return x.offsetParent !== null && (x.textContent||'').includes('旧密码') })
    return !!d
  })(),
  messages: Array.from(document.querySelectorAll('.el-message')).map(function(m){ return (m.textContent||'').trim() }),
  errors: Array.from(document.querySelectorAll('.el-form-item__error')).map(function(e){ return (e.textContent||'').trim() }).filter(Boolean),
  pageText: (function(){
    var t = (document.body.innerText || '').replace(/\\s+/g, ' ')
    var hit = t.match(/账号或密码验证失败[^。]*。?|验证码[^。]{0,12}|锁定/g)
    return hit ? hit.join(' | ').slice(0, 200) : ''
  })(),
  loginHash: location.hash.includes('/login'),
  inputs: document.querySelectorAll('input.el-input__inner').length
})`

async function readState(ev) {
  return JSON.parse(await ev(state))
}

// 在改密弹窗内填写「设置新密码」「确认新密码」并点击保存。
// 选择器限定在可见弹窗内：第 2、3 个 password 输入框，避免依赖全局索引。
async function fillNewPasswordAndSave(ev, newPassword) {
  return await ev(`(function(){
    var set = function(el, v) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
    var dialog = Array.from(document.querySelectorAll('.el-dialog')).find(function(x){ return x.offsetParent !== null && (x.textContent||'').includes('旧密码') })
    if (!dialog) return 'no-dialog'
    var pws = Array.from(dialog.querySelectorAll('input.el-input__inner')).filter(function(i){ return i.type === 'password' })
    if (pws.length < 3) return 'pwd-inputs=' + pws.length
    set(pws[1], ${JSON.stringify(newPassword)})
    set(pws[2], ${JSON.stringify(newPassword)})
    var save = Array.from(dialog.querySelectorAll('button')).find(function(b){ return (b.textContent||'').replace(/\\s/g,'') === '保存' })
    if (!save) return 'no-save-btn'
    save.click()
    return 'save-clicked'
  })()`)
}

async function run() {
  const captcha = argValue('captcha')
  const newPassword = argValue('password')
  if (!/^\d{4}$/.test(captcha)) throw new Error('验证码应为 4 位数字')
  if (!newPassword) throw new Error('缺少 --password <新密码>')

  const page = await findLoginPage()
  const { ws, ev } = await connect(page)
  try {
    // 1. 提交验证码
    const submitted = await ev(`(function(){
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

    // 2. 轮询判定终态（最多 25 秒）
    let s = null
    const deadline = Date.now() + 25000
    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 700))
      s = await readState(ev)
      if (s.dialog) break // 初始密码有效 → 强制改密弹窗
      const joined = (s.messages.join(' ') + ' ' + s.errors.join(' ') + ' ' + (s.pageText || '')).trim()
      if (/账号或密码验证失败|密码错误/.test(joined)) { console.log('RESULT=SKIP_ALREADY_RESET detail=' + joined); return }
      if (/验证码错误|验证码不正确|验证码已失效|验证码不正确/.test(joined)) { console.log('RESULT=CAPTCHA_RETRY detail=' + joined); return }
      if (/锁定/.test(joined)) { console.log('RESULT=LOCK_RISK detail=' + joined); return }
    }
    if (!s?.dialog) {
      console.log('RESULT=TIMEOUT state=' + JSON.stringify(s))
      return
    }

    // 3. 弹窗改密
    const filled = await fillNewPasswordAndSave(ev, newPassword)
    if (filled !== 'save-clicked') { console.log('RESULT=RESET_FAIL fill=' + filled); return }

    // 4. 等待改密结果（最多 15 秒）
    const deadline2 = Date.now() + 15000
    while (Date.now() < deadline2) {
      await new Promise(r => setTimeout(r, 700))
      s = await readState(ev)
      if (/修改密码成功/.test(s.messages.join(' '))) {
        console.log('RESULT=RESET_OK messages=' + JSON.stringify(s.messages))
        return
      }
      if (!s.dialog && s.errors.length) { console.log('RESULT=RESET_FAIL errors=' + JSON.stringify(s.errors)); return }
      if (!s.dialog) break // 弹窗关闭但暂无消息，再确认一轮
    }
    console.log('RESULT=' + (/修改密码成功/.test((s.messages || []).join(' ')) ? 'RESET_OK' : 'TIMEOUT') + ' state=' + JSON.stringify(s))
  } finally {
    ws.close()
  }
}

try {
  await run()
} catch (error) {
  console.error('ERROR ' + error.message)
  process.exit(1)
}
