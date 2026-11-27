#!/usr/bin/env node
/**
 * 按分支维护 QEDAgent 桌面交付版本，并在打包前同步四处版本字段。
 *
 * 规则：
 * - 版本记录属于项目，保存到仓库 `scripts/desktop-release-version.json`
 *   （`{ "branch": "<当前分支>", "version": "x.y.z.n" }`），随分支提交、可评审；
 * - 记录里的 branch 与当前分支不一致（新分支继承了旧文件）或文件不存在时，
 *   视为“未记录”，停止并要求先与用户确认初始版本，再用 --init <x.y.z.n> 重跑；
 * - 已有记录：第四段构建号 +1（2.2609.2.0 → 2.2609.2.1）；
 * - 本脚本不猜测初始版本。
 *
 * 用法：
 *   node <skill>/scripts/bump-build-version.mjs --dry-run [工作树根目录]
 *   node <skill>/scripts/bump-build-version.mjs [工作树根目录]
 *   node <skill>/scripts/bump-build-version.mjs --init 2.2609.2.0 [工作树根目录]
 *
 * 修改五处：
 * - scripts/desktop-release-version.json  分支与版本记录
 * - electron-builder.yml  buildVersion（Windows FileVersion，四段数字）
 * - electron-builder.yml  win.artifactName（安装包文件名，...-<ver>.HND-...）
 * - electron-builder.yml  nsis.uninstallDisplayName（卸载显示名）
 * - resources/sch-extension/manifest.json  version / version_name
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

const args = process.argv.slice(2);
let initVersion;
let dryRun = false;
const positional = [];
for (let index = 0; index < args.length; index += 1) {
  const argument = args[index];
  if (argument === '--init') initVersion = args[++index];
  else if (argument === '--dry-run') dryRun = true;
  else positional.push(argument);
}
const root = resolve(positional[0] ?? process.cwd());

const git = (...command) => execFileSync('git', ['-C', root, ...command], { encoding: 'utf8' }).trim();
let branch;
try {
  branch = git('rev-parse', '--abbrev-ref', 'HEAD');
} catch {
  throw new Error(`无法读取 git 分支：${root}`);
}
if (branch === 'HEAD') throw new Error('当前处于 detached HEAD，无法按分支维护版本；请先检出交付分支。');

const recordPath = join(root, 'scripts', 'desktop-release-version.json');
let record;
try {
  const stored = JSON.parse(readFileSync(recordPath, 'utf8'));
  // 新分支从旧分支继承了文件时 branch 不一致，按“未记录”处理，避免沿用他分支版本。
  if (stored && stored.branch === branch && typeof stored.version === 'string') record = stored;
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}

if (record === undefined) {
  if (initVersion === undefined) {
    process.stderr.write(
      `分支 ${branch} 没有版本记录（${recordPath}）。\n`
      + '请先与用户确认初始版本（例 2.2609.2.0），再用 --init <x.y.z.n> 重跑；本脚本不猜测初始版本。\n',
    );
    process.exit(2);
  }
  if (!/^\d+\.\d+\.\d+\.\d+$/u.test(initVersion)) {
    throw new Error(`初始版本必须是四段数字（x.y.z.n）：${initVersion}`);
  }
} else if (initVersion !== undefined) {
  throw new Error(`分支 ${branch} 已有版本记录 ${record.version}；要重置请先修改 ${recordPath}。`);
}

const builderPath = join(root, 'electron-builder.yml');
const manifestPath = join(root, 'resources', 'sch-extension', 'manifest.json');
const builder = readFileSync(builderPath, 'utf8');
const ymlVersion = builder.match(/^buildVersion:\s*(\d+)\.(\d+)\.(\d+)\.(\d+)\s*$/mu);
if (!ymlVersion) throw new Error(`未找到 buildVersion（四段数字）：${builderPath}`);

let version;
if (record === undefined) {
  // 首次建立记录：用户确认的版本原样使用，不额外 +1。
  version = initVersion;
  const [major, minor, patch] = version.split('.');
  if (`${major}.${minor}.${patch}` !== `${ymlVersion[1]}.${ymlVersion[2]}.${ymlVersion[3]}`) {
    throw new Error(
      `初始版本 ${version} 与 electron-builder.yml 的 ${ymlVersion[1]}.${ymlVersion[2]}.${ymlVersion[3]} 前三段不一致，`
      + '请先对齐配置或重新确认初始版本。',
    );
  }
} else {
  const [major, minor, patch, build] = record.version.split('.').map(Number);
  version = `${major}.${minor}.${patch}.${build + 1}`;
}

let updated = builder
  .replace(/^buildVersion:\s*\d+\.\d+\.\d+\.\d+\s*$/mu, `buildVersion: ${version}`)
  .replace(/artifactName:\s*'([^']*?)\d+\.\d+\.\d+(?:\.\d+)?\.HND([^']*)'/u,
    (_m, head, tail) => `artifactName: '${head}${version}.HND${tail}'`)
  .replace(/^(\s*uninstallDisplayName:\s*QEDAgent\s*)\d+\.\d+\.\d+(?:\.\d+)?\.HND\s*$/mu,
    `$1${version}.HND`);
if (!updated.includes(`buildVersion: ${version}`) || !updated.includes(`Setup-${version}.HND-`)) {
  throw new Error('electron-builder.yml 版本字段未全部更新，请检查 artifactName/uninstallDisplayName 格式');
}
if (dryRun) {
  process.stdout.write(
    `[dry-run] 分支 ${branch}：${record?.version ?? '(未记录)'} → ${version}（显示 ${version}.HND）\n`
    + `记录将写入 ${recordPath}；未写入任何文件，向用户确认后再去掉 --dry-run 执行。\n`,
  );
  process.exit(0);
}
writeFileSync(builderPath, updated);

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
manifest.version = version;
manifest.version_name = `${version}.HND`;
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

writeFileSync(recordPath, `${JSON.stringify({
  branch,
  version,
  updatedAt: new Date().toISOString(),
}, null, 2)}\n`);

process.stdout.write(`分支 ${branch} 版本：${version}（显示 ${version}.HND）\n`);
process.stdout.write(`  ${builderPath}\n  ${manifestPath}\n  记录 ${recordPath}\n`);
