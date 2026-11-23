#!/usr/bin/env node
/**
 * pr-watch.mjs — 监控 Gitea PR 的候选提交、合入状态、评论、正式评审事件与 CI。
 *
 * 配置（必须提供，否则报错退出）：
 *   方式一：脚本同目录 pr-watch.config.json
 *     {"server":"https://<host>","repo":"<owner>/<repo>","login":"<你的用户名>"}
 *   方式二：环境变量 GITEA_SERVER + GITEA_REPO + GITEA_LOGIN
 *   方式三：命令行参数 node pr-watch.mjs <PR号> <owner>/<repo>
 *     （server 仍需从配置或环境变量提供；login 仅扫描自己的全部 PR 时必需）
 *
 * 用法：
 *   node pr-watch.mjs                    # 扫描配置仓库下自己的全部开 PR
 *   node pr-watch.mjs 94                  # 只监控指定 PR
 *   node pr-watch.mjs 94 owner/repo      # 指定 PR + 仓库
 *
 * 状态快照写在脚本同目录 pr-watch.state.json（按服务器与仓库隔离）；删除即重置。
 *
 * 认证顺序：
 *   1. ~/.gitea-token（唯一存放位置，branch-manager skill R7 约定；不进任何仓库）
 *   2. 环境变量 GITEA_TOKEN
 *   3. git 凭据管理器（GCM，可能过期，仅应急）
 * 仓库匿名可读时无令牌也可用（自动降级匿名）。
 *
 * TLS：默认严格校验证书；自签证书环境显式设置 GITEA_INSECURE=1（等价 curl -k）。
 * 退出码：0 正常；1 配置缺失或运行时错误；2 全部监控 PR 已关闭/合并。
 */
import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));

// ── 配置解析（三级覆盖：命令行 > 环境变量 > 配置文件）──
function readConfigFile() {
  try { return JSON.parse(readFileSync(join(HERE, 'pr-watch.config.json'), 'utf8')); } catch { return {}; }
}
const CFG = readConfigFile();
const argRepo = process.argv[3];
const SERVER = (process.env.GITEA_SERVER || CFG.server || '').replace(/\/+$/, '');
const DEFAULT_REPO = argRepo || process.env.GITEA_REPO || CFG.repo || '';
const MY_LOGIN = process.env.GITEA_LOGIN || CFG.login || '';

if (!SERVER) { console.error('缺少 server 配置。请设置 GITEA_SERVER 或在 pr-watch.config.json 中写入 {"server":"https://<host>",...}'); process.exit(1); }
if (!DEFAULT_REPO) { console.error('缺少 repo 配置。请设置 GITEA_REPO 或在 pr-watch.config.json 中写入 {"repo":"<owner>/<repo>",...}，或用命令行第三参数指定。'); process.exit(1); }
if (!MY_LOGIN && !process.argv[2]) { console.error('缺少 login 配置（扫描自己的 PR 需要知道用户名）。请设置 GITEA_LOGIN 或在 pr-watch.config.json 中写入 {"login":"<用户名>",...}，或指定 PR 号跳过扫描。'); process.exit(1); }

const STATE_FILE = join(HERE, 'pr-watch.state.json');
const USER_TOKEN_FILE = join(process.env.USERPROFILE ?? process.env.HOME ?? '', '.gitea-token');
const TLS_INSECURE = process.env.GITEA_INSECURE === '1';

// ── 令牌（可选，匿名可读仓库不需要；只读用户级唯一位置）──
function readTokenFile() {
  try { return readFileSync(USER_TOKEN_FILE, 'utf8').trim(); } catch { return ''; }
}
function readTokenFromGcm() {
  try {
    const { protocol, host } = new URL(SERVER);
    const cred = execFileSync('git', ['credential', 'fill'], {
      input: `protocol=${protocol.slice(0, -1)}\nhost=${host}\n\n`,
      env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GCM_INTERACTIVE: 'never' },
      timeout: 20_000,
    }).toString();
    return cred.match(/^password=(.*)$/m)?.[1] ?? '';
  } catch { return ''; }
}
const token = readTokenFile() || process.env.GITEA_TOKEN || readTokenFromGcm();

// HTTP 状态与 JSON 数据分别核对，避免把 API 错误正文当作有效快照。
function curl(path, useToken) {
  const args = ['--silent', '--show-error', '--max-time', '30', '--write-out', '\\n%{http_code}'];
  if (TLS_INSECURE) args.push('--insecure');
  const url = SERVER + path;
  const input = useToken ? 'url = ' + JSON.stringify(url) + '\nheader = ' + JSON.stringify('Authorization: token ' + token) + '\n' : undefined;
  args.push(...(useToken ? ['--config', '-'] : ['--url', url]));
  let out;
  try {
    out = execFileSync('curl', args, {
      encoding: 'utf8',
      maxBuffer: 16 * 1024 * 1024,
      input,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
  } catch (error) {
    throw new Error('请求失败（' + (error.code || error.status || '未知错误') + '）：' + path);
  }
  const split = out.lastIndexOf('\n');
  const status = Number(out.slice(split + 1));
  if (status < 200 || status >= 300 || !Number.isInteger(status)) {
    throw Object.assign(new Error('HTTP ' + status + '：' + path), { status });
  }
  try {
    return JSON.parse(out.slice(0, split));
  } catch {
    throw new Error('响应不是 JSON：' + path);
  }
}

function get(path) {
  try {
    return curl(path, Boolean(token));
  } catch (error) {
    if (!token || ![401, 403, 404].includes(error.status)) throw error;
    try {
      return curl(path, false);
    } catch {
      throw error;
    }
  }
}

function getPages(path, readRows = result => result) {
  const items = [];
  const collected = new Set();
  const separator = path.includes('?') ? '&' : '?';
  const pageSize = 50;
  for (let page = 1; ; page++) {
    const result = get(path + separator + 'limit=' + pageSize + '&page=' + page);
    const batch = readRows(result);
    if (!Array.isArray(batch)) throw new Error('列表响应格式无效：' + path);
    for (const item of batch) {
      const id = item?.id ?? item?.number;
      if (id == null || collected.has(id)) throw new Error('分页数据变化或无效：' + path);
      collected.add(id);
      items.push(item);
    }
    if (batch.length < pageSize) return items;
  }
}

function loadState() {
  let raw;
  try {
    raw = readFileSync(STATE_FILE, 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') return {};
    throw error;
  }
  const state = JSON.parse(raw);
  if (!state || typeof state !== 'object' || Array.isArray(state)) throw new Error('监控状态格式无效');
  return state;
}

function saveState(key, updates) {
  if (!Object.keys(updates).length) return;
  const state = loadState();
  state[key] = { ...state[key], ...updates };
  const scratch = STATE_FILE + '.' + randomUUID() + '.tmp';
  try {
    writeFileSync(scratch, JSON.stringify(state, null, 2) + '\n', { flag: 'wx' });
    renameSync(scratch, STATE_FILE);
  } finally {
    rmSync(scratch, { force: true });
  }
}

function fingerprint(records) {
  return createHash('sha256').update(JSON.stringify(records)).digest('hex');
}

function briefSha(sha) {
  return sha ? sha.slice(0, 9) : '未知';
}

function pullState(pr) {
  const head = pr?.head?.sha ?? '';
  const base = pr?.base?.sha ?? '';
  if (!['open', 'closed'].includes(pr?.state) || typeof head !== 'string' || typeof base !== 'string'
      || (pr.state === 'open' && (!head || !base))) {
    throw new Error('PR 响应缺少状态或 head/base');
  }
  return {
    state: pr.state,
    merged: Boolean(pr.merged),
    draft: Boolean(pr.draft),
    head,
    base,
    baseRef: pr.base?.ref ?? '',
    baseRepo: pr.base?.repo?.full_name ?? pr.base?.repo_id ?? '',
    mergeable: pr.mergeable ?? null,
  };
}

function latestChecks(path, head) {
  const byContext = new Map();
  if (!head) return byContext;
  const rows = getPages(path, result => {
    if (result?.sha && result.sha !== head) throw new Error('CI 响应与当前提交不匹配');
    return Array.isArray(result) ? result : result?.statuses;
  });
  for (const row of rows) {
    const status = row?.status ?? row?.state;
    if (!row?.context || typeof status !== 'string' || !status) throw new Error('CI 记录缺少检查名或状态');
    const prior = byContext.get(row.context);
    const date = Date.parse(row.updated_at || row.created_at || '') || 0;
    const id = Number(row.id) || 0;
    if (!prior || date > prior.date || (date === prior.date && id > prior.id)) {
      byContext.set(row.context, { status, url: row.target_url, date, id });
    }
  }
  return byContext;
}

function formalReviews(path, head) {
  let reviews;
  try {
    reviews = getPages(path);
  } catch (error) {
    if (![401, 403, 404].includes(error.status)) throw error;
    return { reviewDigest: null, approvals: null };
  }
  const sorted = reviews.sort((a, b) => a.id - b.id);
  const latestVotes = new Map();
  const voteStates = new Set(['APPROVED', 'REQUEST_CHANGES', 'CHANGES_REQUESTED', 'DISMISSED']);
  for (const item of sorted) {
    const voter = item.user?.id ?? item.user?.login;
    if (voter != null && item.commit_id === head && voteStates.has(item.state)) {
      latestVotes.set(voter, item.state === 'APPROVED' && !item.dismissed && !item.stale);
    }
  }
  const reviewDigest = fingerprint(sorted.map(item => [
    item.id, item.user?.id, item.user?.login, item.state, item.commit_id, item.dismissed, item.stale,
    item.submitted_at, item.updated_at, item.body,
  ]));
  return { reviewDigest, approvals: [...latestVotes.values()].filter(Boolean).length };
}

function snapshotPr(repo, number) {
  const root = '/api/v1/repos/' + repo;
  const path = root + '/pulls/' + number;
  const pr = get(path);
  const candidate = pullState(pr);
  const comments = getPages(root + '/issues/' + number + '/comments').sort((a, b) => a.id - b.id);
  const checks = latestChecks(root + '/commits/' + encodeURIComponent(candidate.head) + '/status', candidate.head);
  const formal = formalReviews(path + '/reviews', candidate.head);
  if (JSON.stringify(candidate) !== JSON.stringify(pullState(get(path)))) {
    throw new Error('读取期间 PR 状态或提交变化，本次快照未保存');
  }
  return {
    title: pr.title ?? '',
    now: {
      ...candidate,
      ...formal,
      comments: comments.length,
      lastComment: comments.at(-1)?.id ?? null,
      commentDigest: fingerprint(comments.map(item => [item.id, item.created_at, item.updated_at, item.body])),
      ci: Object.fromEntries([...checks].map(([name, info]) => [name, info.status])),
      ciReceipts: Object.fromEntries([...checks].map(([name, info]) => [name, fingerprint(info)])),
    },
    checks,
  };
}

function reportPr(repo, number, title, previous, current, checks) {
  const changes = [];
  if (!previous) {
    changes.push('首次监控，已记录基线');
  } else {
    if (previous.head !== current.head) changes.push('head ' + briefSha(previous.head) + ' → ' + briefSha(current.head));
    if (previous.base !== current.base || previous.baseRef !== current.baseRef || previous.baseRepo !== current.baseRepo) {
      changes.push('目标分支 ' + previous.baseRef + '@' + briefSha(previous.base) + ' → ' + current.baseRef + '@' + briefSha(current.base));
    }
    if (previous.mergeable !== current.mergeable) changes.push('冲突状态变化');
    if (previous.draft !== current.draft) changes.push('草稿状态变化');
    if (previous.state !== current.state || previous.merged !== current.merged) changes.push('PR 状态变化');
    if (previous.commentDigest !== current.commentDigest) changes.push('评论有新增、编辑或移除');
    if (previous.reviewDigest !== current.reviewDigest || previous.approvals !== current.approvals) changes.push('正式评审记录变化');
    for (const name of new Set([...Object.keys(previous.ci ?? {}), ...Object.keys(current.ci)])) {
      const was = Object.hasOwn(previous.ci ?? {}, name) ? previous.ci[name] : undefined;
      const now = Object.hasOwn(current.ci, name) ? current.ci[name] : undefined;
      if (was !== now) {
        changes.push('CI ' + name + '：' + (was ?? '未注册') + ' → ' + (now ?? '未回报'));
      } else if (previous.ciReceipts?.[name] !== current.ciReceipts[name]) {
        changes.push('CI ' + name + '：' + now + '，作业回执变化');
      }
    }
  }
  if (!changes.length) return;
  console.log('\n━━ PR ' + repo + '#' + number + ' ' + title.slice(0, 45));
  console.log('状态 ' + current.state + (current.merged ? '（已合并）' : '') + (current.draft ? '（草稿）' : '')
    + ' | head ' + briefSha(current.head) + ' | base ' + current.baseRef + '@' + briefSha(current.base)
    + ' | mergeable ' + (current.mergeable ?? '未知') + ' | 评论 ' + current.comments);
  console.log('当前提交正式批准记录 ' + (current.approvals ?? '不可读') + '，分支保护门槛以平台为准');
  console.log('CI ' + (Object.entries(current.ci).map(([name, state]) => name + '=' + state).join(' ') || '未见回执'));
  for (const change of changes) console.log('  - ' + change);
  for (const [name, row] of checks) {
    if (['failure', 'error'].includes(row.status) && /^https?:\/\/[^\s]+$/i.test(row.url ?? '')) {
      console.log('  失败作业 ' + name + ' ' + row.url);
    }
  }
}

function main() {
  const repo = DEFAULT_REPO;
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) throw new Error('仓库配置应为 owner/repo');
  const parsedServer = new URL(SERVER);
  if (!['http:', 'https:'].includes(parsedServer.protocol) || parsedServer.username || parsedServer.password || parsedServer.search || parsedServer.hash) {
    throw new Error('server 应为不含凭证、查询或片段的 HTTP(S) 地址');
  }
  const stateKey = SERVER + '|' + repo;
  const previous = loadState()[stateKey] ?? {};
  const updates = {};
  const requested = process.argv[2];
  const number = Number(requested);
  if (requested && (!Number.isInteger(number) || number <= 0)) throw new Error('PR 号无效');
  const targets = requested ? [number]
    : getPages('/api/v1/repos/' + repo + '/pulls?state=open').filter(pr => pr.user?.login === MY_LOGIN).map(pr => pr.number);

  if (!targets.length) {
    console.log('在 ' + repo + ' 下没有 ' + MY_LOGIN + ' 的开 PR。');
    return;
  }
  let allClosed = true;
  let hadError = false;
  for (const pr of targets) {
    try {
      const { title, now, checks } = snapshotPr(repo, pr);
      const before = previous[pr];
      reportPr(repo, pr, title, before, now, checks);
      if (JSON.stringify(before) !== JSON.stringify(now)) updates[pr] = now;
      if (now.state === 'open') allClosed = false;
    } catch (error) {
      console.error('PR #' + pr + ' 读取失败：' + error.message);
      hadError = true;
    }
  }
  saveState(stateKey, updates);
  if (hadError) process.exitCode = 1;
  else if (allClosed) {
    console.log('所有监控的 PR 均已关闭或合并。');
    process.exitCode = 2;
  }
}

try {
  main();
} catch (error) {
  console.error('PR 监控失败：' + error.message);
  process.exitCode = 1;
}
