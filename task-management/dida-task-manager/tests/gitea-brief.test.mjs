#!/usr/bin/env node
/**
 * gitea-brief 契约测试（纯静态 + 纯函数，不依赖网络/token）。
 * 运行：node --test tests/gitea-brief.test.mjs
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(HERE, '..', 'scripts', 'gitea-brief.mjs');
const source = readFileSync(SCRIPT, 'utf8');

test('脚本只做 Gitea 只读调用，不含写操作端点', () => {
  // 允许的 API 路径都是 GET 语义；不得出现 POST/PATCH/DELETE 或关闭/评论写入
  assert.doesNotMatch(source, /\b(method\s*:\s*['"]POST|method\s*:\s*['"]PATCH|method\s*:\s*['"]DELETE)/i);
  assert.doesNotMatch(source, /\/(issues\/\$\{[^}]+\})\s*\?[^\n]*(state|comments)/i);
  assert.match(source, /\/issues\?state=open&type=issues/);
  assert.match(source, /\/pulls\?state=open/);
});

test('令牌遵循 branch-manager R7：唯一来源 ~/.gitea-token，仓库内无 token 文件', () => {
  assert.match(source, /join\(process\.env\.USERPROFILE \|\| process\.env\.HOME \|\| '', '\.gitea-token'\)/);
  assert.match(source, /process\.env\.GITEA_TOKEN/);
  assert.match(source, /git', \['credential', 'fill'\]/);
  // 不得读同目录任何 token 文件
  assert.doesNotMatch(source, /readFileSync\(join\(HERE,\s*['"][^'"]*token/i);
});

test('日期与输出目录参数化，不硬编码具体日期', () => {
  assert.match(source, /arg\('date'\)/);
  assert.match(source, /arg\('out-dir'\)/);
  assert.doesNotMatch(source, /2026-11-\d{2}/);
});

test('引用型事件被显式过滤，change_title 登记为实质事件', () => {
  assert.match(source, /REF_ONLY\s*=\s*new Set\(\['issue_ref', 'cross-reference', 'pull_ref', 'comment_ref'\]\)/);
  assert.match(source, /MEANINGFUL[^\n]*'change_title'/);
  assert.match(source, /refFiltered\+\+; continue/);
});

test('进度一句话剥 HTML 注释，PR 状态以实际查询为准', () => {
  assert.match(source, /replace\(\/<!--\[\\s\\S\]\*\?-->\/g, ''\)/);
  assert.match(source, /merged:\s*!!d\.merged/);
  assert.match(source, /prStatus|pr_status/);
  // 完成凭证闸门：progress 必须显式标为待核二手信号，不得当完成依据
  assert.match(source, /信号级别:\s*'待核\(二手推断\)'/);
  assert.match(source, /完成判定:\s*false/);
  // 结构化证据块 + finding 线索：让消费端机读地区分「发现的问题」与「修复的问题」
  assert.match(source, /来源URL:/);
  assert.match(source, /核实时间:\s*new Date\(\)/);
  assert.match(source, /finding线索:\s*findingHint\(last\)/);
  assert.match(source, /FINDING_HINT\s*=\s*\//);
});

test('finding 线索正则覆盖文档承诺的发现/待确认措辞', () => {
  const m = source.match(/const FINDING_HINT = \/(.+)\/;/);
  assert.ok(m, '未找到 FINDING_HINT 正则');
  const re = new RegExp(m[1]);
  for (const text of ['发现于 #1234', '发现一个问题', '此项待确认', '仍可复现', '另行推进', '等待本人确认']) {
    assert.match(text, re, `finding 正则应命中：${text}`);
  }
  for (const text of ['已完成修复并合入', 'PR 已合并，验证通过']) {
    assert.doesNotMatch(text, re, `finding 正则不应命中：${text}`);
  }
});

test('snapshot diff 输出新增/移除/更新/未变四类', () => {
  assert.match(source, /const added =/);
  assert.match(source, /const removed =/);
  assert.match(source, /const updated =/);
  assert.match(source, /const unchanged =/);
  assert.match(source, /writeFileSync\(snapFile/);
});

test('网络失败重试三次并区分退出码', () => {
  assert.match(source, /attempts\s*=\s*3/);
  assert.match(source, /3 \* \(i \+ 1\)/);
  assert.match(source, /networkFailed \? 2 : 1/);
});

test('子命令清单完整且与 SKILL.md 文档同步', () => {
  const skill = readFileSync(join(HERE, '..', 'SKILL.md'), 'utf8');
  for (const cmd of ['issues', 'assigned', 'prs', 'progress', 'snapshot']) {
    assert.match(source, new RegExp(`cmd === '${cmd}'`), `脚本缺 ${cmd}`);
    assert.match(skill, new RegExp(`\\b${cmd}\\b`), `SKILL.md 缺 ${cmd} 文档`);
  }
});

test('SKILL.md 固化不对称双向原则与三闸门', () => {
  const skill = readFileSync(join(HERE, '..', 'SKILL.md'), 'utf8');
  assert.match(skill, /不对称双向/);
  assert.match(skill, /正向.*自动/);
  assert.match(skill, /反向.*提议/);
  assert.match(skill, /绝不自动关闭/);
  assert.match(skill, /### 闸门一：完成凭证/);
  assert.match(skill, /### 闸门二：重要度推导/);
  assert.match(skill, /### 闸门三：产能与依赖投影/);
});
