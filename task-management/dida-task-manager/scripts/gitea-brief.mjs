#!/usr/bin/env node
/**
 * gitea-brief.mjs — 晨报用 Gitea 只读取数（issue diff / 指派详情 / 本人 PR / 进度一句话）。
 *
 * 只读取，不关闭/修改/评论任何 issue 或 PR。滴答写入仍由 MCP 承担。
 *
 * 配置（命令行 > 环境变量 > 同目录 gitea-brief.config.json）：
 *   server   GITEA_SERVER              默认 https://qedai.df2cloud.com:60001
 *   repo     GITEA_REPO                默认 QEDA/QEDAgent
 *   login    GITEA_LOGIN               默认 qinzuoquan（扫描"指派给我/我创建的"）
 *   outDir   GITEA_BRIEF_OUT           默认脚本同目录（建议用 --out-dir 指到用户态目录）
 *   token    ~/.gitea-token（唯一来源，branch-manager R7）→ GITEA_TOKEN → git credential fill
 *
 * 用法：
 *   node gitea-brief.mjs issues     [--out-dir DIR] [--date YYYY-MM-DD] [--all]
 *   node gitea-brief.mjs assigned   [--out-dir DIR] [--date YYYY-MM-DD]
 *   node gitea-brief.mjs prs        [--out-dir DIR] [--date YYYY-MM-DD]
 *   node gitea-brief.mjs progress   [--out-dir DIR] [--date YYYY-MM-DD] [--numbers 1,2,3]
 *   node gitea-brief.mjs snapshot   --snapshot FILE [--out-dir DIR] [--date YYYY-MM-DD]
 *
 * 子命令：
 *   issues   分页拉全部开放 issue，落 issues.json；输出编号集合与两组统计
 *   assigned 基于 issues.json 拉取指派给我的 timeline 验真 + 评论 + PR 状态，落 assigned.json
 *   prs      分页拉开放 PR，筛本人，拉 reviews/CI/评论，落 my-prs.json
 *   progress 从 assigned.json 生成"进度一句话"素材（剥 HTML 注释、PR 状态以实际为准）
 *   snapshot 读旧快照 + issues.json 生成 diff 并写回新快照（日期参数化）
 *
 * 网络失败重试 3 次（退避 3/6/9 秒）。所有输出 UTF-8 JSON。
 * TLS 默认严格校验；自签环境显式 GITEA_INSECURE=1。
 * 退出码：0 正常；1 配置/运行时错误；2 网络全败。
 */
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));

function readJson(path, fallback = {}) {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return fallback; }
}

const CFG = readJson(join(HERE, 'gitea-brief.config.json'));
function arg(name) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}
function hasFlag(name) { return process.argv.includes('--' + name); }

const SERVER = (process.env.GITEA_SERVER || CFG.server || 'https://qedai.df2cloud.com:60001').replace(/\/+$/, '');
const REPO = process.env.GITEA_REPO || CFG.repo || 'QEDA/QEDAgent';
const LOGIN = process.env.GITEA_LOGIN || CFG.login || 'qinzuoquan';
const DATE = arg('date') || new Date().toISOString().slice(0, 10);
const OUT_DIR = resolve(arg('out-dir') || process.env.GITEA_BRIEF_OUT || HERE);
const TLS_INSECURE = process.env.GITEA_INSECURE === '1';

// ── 令牌：唯一来源 ~/.gitea-token → GITEA_TOKEN → GCM 应急 ──
function readTokenFile() {
  const p = join(process.env.USERPROFILE || process.env.HOME || '', '.gitea-token');
  try { return readFileSync(p, 'utf8').trim(); } catch { return ''; }
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
const TOKEN = readTokenFile() || process.env.GITEA_TOKEN || readTokenFromGcm();

function get(path, attempts = 3) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try {
      const args = ['--silent', '--show-error', '--max-time', '30', '--write-out', '\\n%{http_code}'];
      if (TLS_INSECURE) args.push('--insecure');
      const url = SERVER + path;
      const input = TOKEN
        ? 'url = ' + JSON.stringify(url) + '\nheader = ' + JSON.stringify('Authorization: token ' + TOKEN) + '\n'
        : undefined;
      args.push(...(TOKEN ? ['--config', '-'] : ['--url', url]));
      const out = execFileSync('curl', args, { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024, input, stdio: ['pipe', 'pipe', 'pipe'] });
      const split = out.lastIndexOf('\n');
      const status = Number(out.slice(split + 1));
      const body = out.slice(0, split);
      if (status < 200 || status >= 300) throw Object.assign(new Error('HTTP ' + status), { status });
      return JSON.parse(body);
    } catch (e) {
      last = e;
      if (i < attempts - 1) execFileSync('sleep', [String(3 * (i + 1))]);
    }
  }
  throw Object.assign(last || new Error('网络失败'), { networkFailed: true });
}

function getPages(path, pageSize = 50) {
  const items = [];
  for (let page = 1; ; page++) {
    const sep = path.includes('?') ? '&' : '?';
    const batch = get(`${path}${sep}limit=${pageSize}&page=${page}`);
    if (!Array.isArray(batch)) throw new Error('分页响应不是数组：' + path);
    items.push(...batch);
    if (batch.length < pageSize) break;
  }
  return items;
}

function save(name, data) {
  mkdirSync(OUT_DIR, { recursive: true });
  const p = join(OUT_DIR, name);
  writeFileSync(p, JSON.stringify(data, null, 2), 'utf8');
  return p;
}

const api = (p) => `/api/v1/repos/${REPO}${p}`;
const day = (s) => (s || '').slice(0, 10);
function daysSince(s) {
  if (!s) return null;
  const [y, m, d] = day(s).split('-').map(Number);
  const [ty, tm, td] = DATE.split('-').map(Number);
  return Math.round((Date.UTC(ty, tm - 1, td) - Date.UTC(y, m - 1, d)) / 86400000);
}

// 剥 HTML 注释，取首条非空行
function stripComments(text) { return (text || '').replace(/<!--[\s\S]*?-->/g, ''); }
function firstNonempty(text) {
  for (const line of stripComments(text).split('\n')) if (line.trim()) return line.trim();
  return '';
}
// PR 引用：/pulls/N 或 PR #N
function prRefs(text) {
  const out = new Set();
  for (const m of (text || '').matchAll(/\/pulls\/(\d+)/g)) out.add(Number(m[1]));
  for (const m of (text || '').matchAll(/\bPR\s*#?(\d+)/gi)) out.add(Number(m[1]));
  return [...out];
}

// PR 与 issue 的语义：PR 报告/发现的问题(finding) ≠ 修复的问题(fixed)。
// 检测到发现类措辞时标记 finding:true，禁止据此判定完成。
const FINDING_HINT = /(发现于|发现[^，。；\s]{0,4}问题|发现该|复现|仍可复现|待确认|待处理|等待.{0,12}确认|另行推进|未合入|等待检视)/;
function findingHint(text) {
  return FINDING_HINT.test(text || '');
}

const MEANINGFUL = new Set(['comment', 'close', 'reopen', 'label', 'assignees', 'title', 'milestone', 'reviewed', 'approved', 'unlabeled', 'change_title']);
const REF_ONLY = new Set(['issue_ref', 'cross-reference', 'pull_ref', 'comment_ref']);

const cmd = process.argv[2];
try {
  if (!cmd) throw new Error('缺少子命令：issues | assigned | prs | progress | snapshot');

  if (cmd === 'issues') {
    const raw = getPages(api('/issues?state=open&type=issues'));
    const issues = raw.map(it => ({
      number: it.number, title: it.title,
      updated_at: it.updated_at, created_at: it.created_at,
      comments: it.comments || 0,
      assignees: (it.assignees || []).map(a => a.login),
      creator: (it.user || {}).login || '',
      body: it.body || '',
    }));
    const p = save('issues.json', issues);
    const numbers = issues.map(i => i.number);
    const assigned = issues.filter(i => i.assignees.includes(LOGIN)).map(i => i.number);
    const created = issues.filter(i => i.creator === LOGIN).map(i => i.number);
    console.log(JSON.stringify({ file: p, total: issues.length, assigned_to_me: assigned, created_by_me: created, all_numbers: hasFlag('all') ? numbers : undefined }, null, 2));
  }

  else if (cmd === 'assigned' || cmd === 'progress') {
    let issues = readJson(join(OUT_DIR, 'issues.json'), []);
    if (!issues.length) throw new Error('缺少 issues.json，请先运行 issues 子命令');
    const assigned = issues.filter(i => i.assignees.includes(LOGIN));
    const allPrs = new Set();
    const detail = {};
    let refFiltered = 0;
    for (const it of assigned) {
      const comments = get(api(`/issues/${it.number}/comments?limit=100`));
      const tl = get(api(`/issues/${it.number}/timeline?limit=30`));
      const timeline = Array.isArray(tl) ? tl : [];
      // 对 timeline 的正文/评论抽取 PR 引用
      allPrs.add(...prRefs(it.body));
      for (const c of (Array.isArray(comments) ? comments : [])) allPrs.add(...prRefs(c.body || ''));

      let lastComment = '';
      const cList = Array.isArray(comments) ? comments : [];
      if (cList.length) lastComment = firstNonempty(cList[cList.length - 1].body || '');

      // 从后往前找最新实质事件；引用型跳过；未知类型如实登记
      let latestEvent = '无';
      const unknowns = new Set();
      for (let i = timeline.length - 1; i >= 0; i--) {
        const t = timeline[i].type || '';
        if (REF_ONLY.has(t)) { refFiltered++; continue; }
        if (MEANINGFUL.has(t)) { latestEvent = t; break; }
        if (t) unknowns.add(t);
      }
      if (latestEvent === '无' && unknowns.size) latestEvent = `未知:${[...unknowns].join(',')}`;

      detail[it.number] = {
        title: it.title, assignees: it.assignees,
        updated_at: day(it.updated_at), days_update: daysSince(it.updated_at),
        comments: cList.length, last_comment: lastComment.slice(0, 200),
        latest_event: latestEvent, pr_refs: prRefs([it.body, ...cList.map(c => c.body || '')].join('\n')),
      };
    }
    // PR 状态批量查（以实际为准，防评论滞后）
    const prState = {};
    for (const p of [...allPrs].sort((a, b) => a - b)) {
      try {
        const d = get(api(`/pulls/${p}`));
        prState[p] = { state: d.state, merged: !!d.merged, merged_at: day(d.merged_at), title: (d.title || '').slice(0, 60) };
      } catch { prState[p] = { state: '查询失败' }; }
    }
    const out = { date: DATE, detail, pr_state: prState };
    const f = save('assigned.json', out);

    if (cmd === 'progress') {
      let nums = arg('numbers');
      let targets = nums ? nums.split(',').map(Number) : assigned.map(i => i.number);
      // progress 素材：末评 + PR 实际状态，供人写 ≤80 字
      const progress = {};
      for (const n of targets) {
        const d = detail[n];
        if (!d) continue;
        const prs = d.pr_refs.map(p => {
          const s = prState[p] || {};
          return `PR #${p} ${s.state || '?'}${s.merged ? '已合' : ''}${s.merged_at ? '(' + s.merged_at + ')' : ''}`;
        });
        // 结构化证据块：写进滴答 comment，供人/agent 机读地拒绝二手信号。
        // 注意：这些只是提示，完成判定必须回读 issue 正文完成条件 + 验证证据。
        const last = d.last_comment || '(无评论)';
        progress[n] = {
          title: d.title, days: d.days_update,
          last_comment: last,
          pr_status: prs,
          来源URL: `${SERVER}/${REPO}/issues/${n}`,
          核实时间: new Date().toISOString(),
          PR明细: d.pr_refs.map(p => ({ number: p, ...(prState[p] || { state: '查询失败' }) })),
          // finding=true 表示末评含「发现/复现/待确认/另行推进」等线索——
          // 该 issue 很可能是这个 PR 报告的问题，而非修复的问题，禁止据此关闭。
          finding线索: findingHint(last),
          信号级别: '待核(二手推断)',
          完成判定: false,
          关闭前必读: 'issue 正文完成条件；finding线索=true 时尤其不得据 PR 已合判定完成',
        };
      }
      const pf = save('progress.json', progress);
      console.log(JSON.stringify({ assigned_file: f, progress_file: pf, count: Object.keys(progress).length }, null, 2));
    } else {
      const unknownTypes = [...new Set(Object.values(detail).filter(d => d.latest_event.startsWith('未知:')).map(d => d.latest_event))];
      console.log(JSON.stringify({ file: f, count: Object.keys(detail).length, prs_checked: Object.keys(prState).length, ref_events_filtered: refFiltered, unknown_event_types: unknownTypes }, null, 2));
    }
  }

  else if (cmd === 'prs') {
    const raw = getPages(api('/pulls?state=open'));
    const mine = raw.filter(p => (p.user || {}).login === LOGIN);
    const rows = [];
    for (const p of mine) {
      const n = p.number;
      const d = get(api(`/pulls/${n}`));
      let reviews = get(api(`/pulls/${n}/reviews`));
      if (!Array.isArray(reviews)) reviews = [];
      const reviewSummary = {};
      for (const r of reviews) reviewSummary[r.state] = (reviewSummary[r.state] || 0) + 1;
      let issueCmts = get(api(`/issues/${n}/comments?limit=100`));
      if (!Array.isArray(issueCmts)) issueCmts = [];
      const sha = (p.head || {}).sha || '';
      let ci = {};
      try { ci = get(`/api/v1/repos/${REPO}/commits/${sha}/status`); } catch { ci = { state: '查询失败' }; }
      const checks = (ci.statuses || []).map(c => ({ state: c.state, context: c.context, description: (c.description || '').slice(0, 120) }));
      rows.push({
        number: n, title: p.title,
        created_at: day(p.created_at), updated_at: day(p.updated_at), days_idle: daysSince(p.updated_at),
        base: (p.base || {}).ref || '', head: (p.head || {}).ref || '', draft: !!p.draft,
        mergeable: d.mergeable, merged: !!d.merged,
        reviews: reviewSummary, review_comments: p.review_comments || 0, comments: p.comments || 0,
        commits: p.commits || 0, ci_state: ci.state || '未知', ci_checks: checks,
        last_comments: issueCmts.slice(-5).map(c => ({ author: (c.user || {}).login, at: day(c.created_at), body: firstNonempty(c.body || '').slice(0, 300) })),
      });
    }
    rows.sort((a, b) => b.number - a.number);
    const f = save('my-prs.json', rows);
    console.log(JSON.stringify({ file: f, open_total: raw.length, mine: rows.length,
      summary: rows.map(r => ({ number: r.number, mergeable: r.mergeable, ci: r.ci_state, idle: r.days_idle })) }, null, 2));
  }

  else if (cmd === 'snapshot') {
    const snapFile = arg('snapshot');
    if (!snapFile) throw new Error('snapshot 子命令需要 --snapshot FILE');
    const issues = readJson(join(OUT_DIR, 'issues.json'), []);
    if (!issues.length) throw new Error('缺少 issues.json，请先运行 issues 子命令');
    const old = readJson(snapFile, { date: '', assigned: [], created: [] });
    const oldAssigned = new Map((old.assigned || []).map(x => [x.number, x]));
    const nowAssigned = issues.filter(i => i.assignees.includes(LOGIN));
    const nowSet = new Set(nowAssigned.map(i => i.number));

    const added = nowAssigned.filter(i => !oldAssigned.has(i.number)).map(i => ({ number: i.number, title: i.title, updated_at: day(i.updated_at) }));
    const removed = [...oldAssigned.keys()].filter(n => !nowSet.has(n)).map(n => ({ number: n, title: oldAssigned.get(n).title }));
    const updated = nowAssigned.filter(i => oldAssigned.has(i.number) && day(i.updated_at) !== oldAssigned.get(i.number).updated_at)
      .map(i => ({ number: i.number, title: i.title, from: oldAssigned.get(i.number).updated_at, to: day(i.updated_at) }));
    const unchanged = nowAssigned.length - added.length - updated.length;

    const created = issues.filter(i => i.creator === LOGIN).map(i => ({
      number: i.number, title: i.title,
      assignees: i.assignees.length ? i.assignees.join(', ') : '无指派',
      updated_at: day(i.updated_at),
    }));
    const next = { date: DATE, assigned: nowAssigned.map(i => ({ number: i.number, title: i.title, updated_at: day(i.updated_at) })), created };
    writeFileSync(snapFile, JSON.stringify(next), 'utf8');

    console.log(JSON.stringify({ snapshot: snapFile, date: DATE,
      added, removed, updated, unchanged,
      created_count: created.length, total_assigned: nowAssigned.length }, null, 2));
  }

  else throw new Error('未知子命令：' + cmd);

} catch (e) {
  console.error('[gitea-brief] ' + (e.message || e));
  process.exit(e.networkFailed ? 2 : 1);
}
