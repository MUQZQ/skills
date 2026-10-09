#!/usr/bin/env node
/**
 * pr-watch.mjs — 监控自己在 Gitea 上所有开 PR 的状态、评论与 CI，输出与上次快照的变化。
 *
 * 配置（必须提供，否则报错退出）：
 *   方式一：脚本同目录 pr-watch.config.json
 *     {"server":"https://<host>","repo":"<owner>/<repo>","login":"<你的用户名>"}
 *   方式二：环境变量 GITEA_SERVER + GITEA_REPO + GITEA_LOGIN
 *   方式三：命令行参数 node pr-watch.mjs <PR号> <owner>/<repo>
 *     （server 和 login 仍需从配置或环境变量提供）
 *
 * 用法：
 *   node pr-watch.mjs                    # 扫描配置仓库下自己的全部开 PR
 *   node pr-watch.mjs 94                  # 只监控指定 PR
 *   node pr-watch.mjs 94 owner/repo      # 指定 PR + 仓库
 *
 * 状态快照写在脚本同目录 pr-watch.state.json（按 repo#PR 分键）；删除即重置。
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
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));

// ── 配置解析（三级覆盖：命令行 > 环境变量 > 配置文件）──
function readConfigFile() {
  try { return JSON.parse(readFileSync(join(HERE, 'pr-watch.config.json'), 'utf8')); } catch { return {}; }
}
const CFG = readConfigFile();
const argRepo = process.argv[3];
const SERVER = process.env.GITEA_SERVER || CFG.server || '';
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
    const host = new URL(SERVER).host;
    const cred = execFileSync('git', ['credential', 'fill'], {
      input: `protocol=https\nhost=${host}\n\n`,
      env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GCM_INTERACTIVE: 'never' },
      timeout: 20_000,
    }).toString();
    return cred.match(/^password=(.*)$/m)?.[1] ?? '';
  } catch { return ''; }
}
const token = readTokenFile() || process.env.GITEA_TOKEN || readTokenFromGcm();

// ── HTTP（令牌优先，失败降级匿名）──
function curl(path, useToken = Boolean(token)) {
  const args = [TLS_INSECURE ? '-sk' : '-s', '--max-time', '30'];
  if (useToken && token) args.push('-H', `Authorization: token ${token}`);
  args.push(`${SERVER}${path}`);
  const out = execFileSync('curl', args, { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe'] });
  return JSON.parse(out);
}
function curlSafe(path) {
  try { return curl(path, true); } catch { try { return curl(path, false); } catch (e) { throw e; } }
}

// ── 状态（按 repo#PR 分键，跨仓库不冲突）──
function loadState() {
  try { return JSON.parse(readFileSync(STATE_FILE, 'utf8')); } catch { return {}; }
}
function saveState(state) {
  writeFileSync(STATE_FILE, `${JSON.stringify(state, null, 2)}\n`);
}

// ── 快照与报告 ──
function snapshotPr(repo, prNumber) {
  const pr = curlSafe(`/api/v1/repos/${repo}/pulls/${prNumber}`);
  const comments = curlSafe(`/api/v1/repos/${repo}/issues/${prNumber}/comments?limit=50&sort=created&direction=desc`);
  const head = pr.head?.sha ?? '';
  const ci = head ? curlSafe(`/api/v1/repos/${repo}/commits/${head}/status`) : { statuses: [] };
  const last = Array.isArray(comments) && comments.length ? comments[0] : null;
  return {
    pr,
    now: {
      at: new Date().toISOString(),
      state: pr.state ?? 'unknown',
      merged: Boolean(pr.merged),
      head: head.slice(0, 9),
      mergeable: pr.mergeable,
      comments: pr.comments ?? 0,
      lastComment: last ? { id: last.id, user: last.user?.login, at: last.created_at } : null,
      ci: Object.fromEntries((ci.statuses ?? []).map(s => [s.context.replace('CI / ', '').replace(' (pull_request)', ''), s.status])),
    },
    ciRaw: ci,
  };
}

function reportPr(repo, prNumber, title, prev, now, ciRaw) {
  const lines = [`\n━━ PR ${repo}#${prNumber} ${title.slice(0, 45)}`];
  lines.push(`状态: ${now.state}${now.merged ? '（已合并）' : ''} | head: ${now.head} | mergeable: ${now.mergeable} | 评论: ${now.comments}`);
  lines.push(`CI: ${Object.entries(now.ci).map(([k, v]) => `${k}=${v}`).join(' ') || '未注册'}`);
  if (!prev) { lines.push('（首次监控，已记录基线）'); return { lines, changed: true, first: true }; }

  const changes = [];
  if (prev.head !== now.head) changes.push(`head ${prev.head} → ${now.head}（有新推送）`);
  if (prev.mergeable !== now.mergeable) changes.push(`mergeable ${prev.mergeable} → ${now.mergeable}`);
  if ((prev.comments ?? 0) !== now.comments) {
    const last = now.lastComment;
    changes.push(`评论 ${prev.comments} → ${now.comments}（最新 #${last?.id} by ${last?.user} @ ${last?.at?.slice(0, 16).replace('T', ' ')}）`);
  }
  for (const [k, v] of Object.entries(now.ci)) {
    if ((prev.ci?.[k] ?? '未注册') !== v) changes.push(`CI ${k}: ${prev.ci?.[k] ?? '未注册'} → ${v}`);
  }
  if (prev.state !== now.state || prev.merged !== now.merged) changes.push(`PR 状态 ${prev.state} → ${now.state}${now.merged ? '（已合并）' : ''}`);

  if (changes.length) lines.push(`变化:\n${changes.map(c => `  - ${c}`).join('\n')}`);
  else lines.push('较上次无变化');

  const failedHints = (ciRaw.statuses ?? [])
    .filter(x => x.status === 'failure')
    .map(x => {
      const m = String(x.target_url ?? '').match(/runs\/(\d+)\/jobs\/(\d+)/);
      return m ? `  失败日志: ${SERVER}/${repo}/actions/runs/${m[1]}/jobs/${m[2]}/logs` : '';
    })
    .filter(Boolean);
  if (failedHints.length) lines.push(failedHints.join('\n'));

  return { lines, changed: changes.length > 0, first: false };
}

// ── 主流程 ──
function main() {
  const argPr = process.argv[2];
  const repo = DEFAULT_REPO;
  const stateKey = repo; // 按 repo 分键
  const state = loadState();
  const tracked = state[stateKey] ?? {};

  let targets;
  if (argPr) {
    const n = Number(argPr);
    if (!Number.isInteger(n) || n <= 0) { console.error(`无效 PR 号: ${argPr}`); process.exit(1); }
    targets = [{ number: n }];
  } else {
    const all = curlSafe(`/api/v1/repos/${repo}/pulls?state=open&limit=50`);
    targets = all.filter(p => p.user?.login === MY_LOGIN).map(p => ({ number: p.number, title: p.title }));
  }

  if (targets.length === 0) {
    console.log(`在 ${repo} 下没有 ${MY_LOGIN} 的开 PR。`);
    process.exit(0);
  }

  console.log(`监控 ${targets.length} 个 PR @ ${new Date().toISOString().slice(0, 19).replace('T', ' ')}`);
  let anyChanged = false;
  let allClosed = true;
  let hadError = false;

  for (const { number, title: tOverride } of targets) {
    try {
      const { pr, now, ciRaw } = snapshotPr(repo, number);
      const title = tOverride ?? pr.title ?? '';
      const prev = tracked[String(number)];
      const result = reportPr(repo, number, title, prev, now, ciRaw);
      if (result.changed) {
        console.log(result.lines.join('\n'));
        anyChanged = true;
      }
      // 无变化时静默（cron 友好）；首次也输出（建立基线）
      if (now.state === 'open') allClosed = false;
      tracked[String(number)] = now;
    } catch (error) {
      console.error(`PR #${number}: 读取失败 — ${String(error.message || error).split('\n')[0]}`);
      hadError = true;
    }
  }

  state[stateKey] = tracked;
  saveState(state);

  if (hadError) process.exit(1);
  if (allClosed) {
    console.log('\n所有监控的 PR 均已关闭/合并。');
    process.exit(2);
  }
}

main();
