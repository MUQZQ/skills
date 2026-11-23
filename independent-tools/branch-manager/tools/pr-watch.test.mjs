import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { copyFile, mkdtemp, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { promisify } from 'node:util';

const exec = promisify(execFile);
const head = 'a'.repeat(40);
const base = 'b'.repeat(40);
const currentTime = '2026-11-22T07:55:42Z';
const repo = 'sample/project';
const root = '/api/v1/repos/' + repo;
const pullPath = root + '/pulls/7';
const commentsPath = root + '/issues/7/comments';

async function fixture(t) {
  const directory = await mkdtemp(join(tmpdir(), 'ccs-pr-watch-'));
  const script = join(directory, 'pr-watch.mjs');
  t.after(() => rm(directory, { recursive: true, force: true }));
  const watchSource = process.env.CCS_TEST_PR_WATCH_SOURCE ?? new URL('./pr-watch.mjs', import.meta.url);
  await copyFile(watchSource, script);

  const pull = {
    state: 'open', title: '样例 PR', mergeable: true, draft: false,
    head: { sha: head }, base: { sha: base, ref: 'develop', repo: { full_name: 'upstream/project' } },
  };
  const comments = Array.from({ length: 51 }, (_, index) =>
    ({ id: index + 1, created_at: currentTime, updated_at: currentTime, body: '评论 ' + (index + 1) }));
  const checks = [
    { context: 'CI / desktop', status: 'failure', id: 1, updated_at: currentTime },
    { context: 'CI / desktop', status: 'success', id: 2, updated_at: currentTime },
    { context: 'typecheck', status: 'success', id: 3 },
  ];
  const reviews = [];
  const config = { reviewError: 0, commentError: 0, driftAtSecondPull: false };
  let pullReads = 0;
  const server = createServer((request, response) => {
    assert.equal(request.method, 'GET');
    const url = new URL(request.url, 'http://localhost');
    const { pathname, searchParams } = url;
    const limit = Number(searchParams.get('limit')) || 50;
    const index = ((Number(searchParams.get('page')) || 1) - 1) * limit;
    let body;
    if (pathname === pullPath) {
      pullReads++;
      body = config.driftAtSecondPull && pullReads === 2
        ? { ...pull, base: { ...pull.base, sha: 'd'.repeat(40) } } : pull;
    } else if (pathname === commentsPath) {
      response.statusCode = config.commentError || 200;
      body = config.commentError ? { message: '评论端点错误' } : comments.slice(index, index + limit);
    } else if (pathname === pullPath + '/reviews') {
      response.statusCode = config.reviewError || 200;
      body = config.reviewError ? { message: '评审不可读' } : reviews.slice(index, index + limit);
    } else if (pathname === root + '/commits/' + head + '/status') {
      const statuses = checks.slice(index, index + limit);
      body = { sha: head, total_count: statuses.length, statuses };
    } else {
      response.statusCode = 404;
      body = { message: '样例中没有此端点' };
    }
    response.setHeader('Content-Type', 'application/json');
    response.end(JSON.stringify(body));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));

  const env = {
    ...process.env,
    USERPROFILE: directory,
    HOME: directory,
    GITEA_SERVER: 'http://127.0.0.1:' + server.address().port,
    GITEA_REPO: repo,
    GITEA_TOKEN: 'local-fixture',
  };
  async function watch() {
    pullReads = 0;
    const options = { env, cwd: directory, timeout: 10_000 };
    try {
      const output = await exec(process.execPath, [script, '7'], options);
      return { code: 0, ...output };
    } catch (error) {
      if (typeof error.code !== 'number') throw error;
      return { code: error.code, stdout: error.stdout, stderr: error.stderr };
    }
  }
  return { pull, comments, checks, reviews, config, watch, state: () => readFile(join(directory, 'pr-watch.state.json'), 'utf8') };
}

test('检测历史评论编辑、目标分支推进及正式评审变化', async t => {
  const { pull, comments, reviews, watch, state } = await fixture(t);
  const initial = await watch();
  assert.equal(initial.code, 0, initial.stderr);
  assert.match(initial.stdout, /评论 51/);
  assert.match(initial.stdout, /develop@bbbbbbbbb/);
  assert.equal((await watch()).stdout, '');

  comments[0].body = '旧评论已更新';
  pull.base.sha = 'c'.repeat(40);
  pull.draft = true;
  reviews.push(
    { id: 1, state: 'APPROVED', commit_id: base, user: { id: 10 } },
    { id: 2, state: 'APPROVED', commit_id: head, user: { id: 20 } },
    { id: 3, state: 'REQUEST_CHANGES', commit_id: head, user: { id: 20 } },
    { id: 4, state: 'APPROVED', commit_id: head, user: { id: 30 } },
    { id: 5, state: 'COMMENT', commit_id: head, user: { id: 30 } },
  );
  const next = await watch();
  assert.equal(next.code, 0, next.stderr);
  assert.match(next.stdout, /目标分支 develop@bbbbbbbbb → develop@ccccccccc/);
  assert.match(next.stdout, /草稿状态变化/);
  assert.match(next.stdout, /评论有新增、编辑或移除/);
  assert.match(next.stdout, /正式评审记录变化/);
  assert.match(next.stdout, /当前提交正式批准记录 1/);
  assert.doesNotMatch(await state(), /旧评论已更新/);
});

test('报告最新回执、同状态新作业以及消失的 CI', async t => {
  const { checks, watch } = await fixture(t);
  const initial = await watch();
  assert.equal(initial.code, 0, initial.stderr);
  assert.match(initial.stdout, /CI \/ desktop=success/);

  for (let i = 0; i < 50; i++) checks.push({ context: '检查 ' + i, status: 'success', id: 10 + i });
  const url = 'https://ci.example.test/runs/42';
  checks.push({ context: 'CI / desktop', status: 'failure', id: 4, target_url: url, updated_at: currentTime });
  checks.splice(2, 1);
  const failed = await watch();
  assert.equal(failed.code, 0, failed.stderr);
  assert.match(failed.stdout, /typecheck：success → 未回报/);
  assert.ok(failed.stdout.includes('失败作业 CI / desktop ' + url + '\n'));

  checks.push({ context: 'CI / desktop', status: 'failure', id: 5, target_url: url + '0', updated_at: currentTime });
  const retried = await watch();
  assert.equal(retried.code, 0, retried.stderr);
  assert.match(retried.stdout, /failure，作业回执变化/);
});

test('API 异常或候选读取中变化时保留可靠快照', async t => {
  const { config, watch, state } = await fixture(t);
  const initial = await watch();
  assert.equal(initial.code, 0, initial.stderr);
  const baseline = await state();
  config.commentError = 500;
  const failure = await watch();
  assert.equal(failure.code, 1);
  assert.match(failure.stderr, /HTTP 500/);
  assert.equal(await state(), baseline);

  config.commentError = 0;
  config.driftAtSecondPull = true;
  const drift = await watch();
  assert.equal(drift.code, 1);
  assert.match(drift.stderr, /本次快照未保存/);
  assert.equal(await state(), baseline);
});

test('读取不到正式评审时明确显示不可读，关闭后返回终止状态', async t => {
  const { pull, config, watch } = await fixture(t);
  config.reviewError = 403;
  const initial = await watch();
  assert.equal(initial.code, 0, initial.stderr);
  assert.match(initial.stdout, /当前提交正式批准记录 不可读/);
  pull.state = 'closed';
  pull.merged = true;
  delete pull.head;
  const closed = await watch();
  assert.equal(closed.code, 2, closed.stderr);
  assert.match(closed.stdout, /所有监控的 PR 均已关闭或合并/);
});
