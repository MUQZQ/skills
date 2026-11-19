#!/usr/bin/env node
'use strict';

/**
 * switch-automation.js — 读写 ZCode 定时任务（automations）的模型/套餐设置。
 *
 * 数据位置：~/.zcode/v2/tasks-index.sqlite 的 automations 表。
 * 只修改 model、model_selection、thought_level、updated_at 四个字段，
 * 不改 cron、启用状态、下次运行时间和运行历史。
 *
 * Node.js >= 22（依赖内置 node:sqlite）。
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const PRESETS = {
  'start-plan': {
    providerId: 'account:bigmodel-start-plan',
    modelId: 'GLM-5.3-Flash',
    reasoningLevel: 'max',
  },
  'individual-coding-plan': {
    providerId: 'account:bigmodel-individual-coding-plan',
    modelId: 'GLM-5.3-Flash',
    reasoningLevel: 'max',
  },
};

const EXIT_OK = 0;
const EXIT_ERROR = 1;
const EXIT_USAGE = 2;

function usage(message) {
  const lines = [
    message ? `错误：${message}` : null,
    '',
    '用法：',
    '  node switch-automation.js --list [--db <路径>] [--json]',
    '  node switch-automation.js --title <标题> --to <预设> [--dry-run] [--json]',
    '  node switch-automation.js --all --to <预设> [--dry-run] [--json]',
    '  node switch-automation.js --id <automation_id> --provider <id> --model <id> [--reasoning <级别>] [--dry-run]',
    '  node switch-automation.js --restore <备份文件> [--db <路径>] [--dry-run]',
    '  node switch-automation.js --history <automation_id> [--limit <N>] [--session-db <路径>] [--json]',
    '',
    '预设：' + Object.keys(PRESETS).join(', '),
    '默认数据库：~/.zcode/v2/tasks-index.sqlite',
    '默认备份目录：<系统临时目录>/zcode-plan-switch-backups',
  ].filter((line) => line !== null);
  console.error(lines.join('\n'));
  process.exit(message ? EXIT_USAGE : EXIT_OK);
}

function parseArgs(argv) {
  const options = {
    list: false,
    all: false,
    json: false,
    dryRun: false,
    db: undefined,
    title: undefined,
    id: undefined,
    to: undefined,
    provider: undefined,
    model: undefined,
    reasoning: undefined,
    restore: undefined,
    history: undefined,
    limit: undefined,
    sessionDb: undefined,
    help: false,
  };
  const valued = new Set([
    'db',
    'session-db',
    'title',
    'id',
    'to',
    'provider',
    'model',
    'reasoning',
    'restore',
    'history',
    'limit',
  ]);
  const flags = new Set(['list', 'all', 'json', 'dry-run', 'help']);

  for (let index = 0; index < argv.length; index += 1) {
    const raw = argv[index];
    if (!raw.startsWith('--')) {
      throw new Error(`无法识别的参数：${raw}`);
    }
    const name = raw.slice(2);
    if (flags.has(name)) {
      if (name === 'dry-run') options.dryRun = true;
      else options[name] = true;
      continue;
    }
    if (!valued.has(name)) {
      throw new Error(`未知选项：--${name}`);
    }
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) {
      throw new Error(`选项 --${name} 缺少取值`);
    }
    const key = name.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    options[key] = value;
    index += 1;
  }
  return options;
}

function resolveDbPath(value) {
  const dbPath = value
    ? path.resolve(value)
    : path.join(os.homedir(), '.zcode', 'v2', 'tasks-index.sqlite');
  if (!fs.existsSync(dbPath)) {
    throw new Error(`数据库不存在：${dbPath}`);
  }
  return dbPath;
}

function resolveSessionDbPath(value) {
  const dbPath = value
    ? path.resolve(value)
    : path.join(os.homedir(), '.zcode', 'cli', 'db', 'db.sqlite');
  return fs.existsSync(dbPath) ? dbPath : null;
}

function openDatabase(dbPath, readOnly) {
  const db = new DatabaseSync(dbPath, readOnly ? { readOnly: true } : {});
  db.exec('PRAGMA busy_timeout = 5000');
  return db;
}

function readSelection(row) {
  try {
    const parsed = JSON.parse(row.model_selection || 'null');
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch (error) {
    return { invalid: String(row.model_selection), error: error.message };
  }
}

function describeRow(row) {
  return {
    automation_id: row.automation_id,
    title: row.title,
    cron_expr: row.cron_expr,
    model: row.model,
    model_selection: readSelection(row),
    thought_level: row.thought_level,
    enabled: row.enabled,
    lifecycle_status: row.lifecycle_status,
    next_run_at: row.next_run_at ? new Date(row.next_run_at).toISOString() : null,
    last_run_at: row.last_run_at ? new Date(row.last_run_at).toISOString() : null,
  };
}

function listAutomations(db) {
  return db
    .prepare(
      'select automation_id, title, cron_expr, model, model_selection, thought_level, ' +
        'enabled, lifecycle_status, next_run_at, last_run_at from automations ' +
        'order by coalesce(next_run_at, 0) asc'
    )
    .all()
    .map(describeRow);
}

function readJson(value) {
  try {
    return JSON.parse(value || 'null');
  } catch (error) {
    return { invalid: String(value), error: error.message };
  }
}

function automationHistory(db, sessionDb, automationId, limit) {
  const runs = db
    .prepare(
      'select run_id, scheduled_at, dispatch_status, outcome, session_id, error, model_selection, updated_at ' +
        'from automation_runs where automation_id = ? order by scheduled_at desc limit ?'
    )
    .all(automationId, limit);

  let usageError = null;
  let usageStatement = null;
  if (sessionDb) {
    try {
      usageStatement = sessionDb.prepare(
        'select provider_id, model_id, status, started_at from model_usage ' +
          'where session_id = ? order by started_at desc limit 3'
      );
    } catch (error) {
      usageError = `无法查询 model_usage：${error.message}`;
    }
  } else {
    usageError = '未找到会话数据库，跳过实际请求用量';
  }

  return {
    usageError,
    runs: runs.map((run) => {
      const usage = usageStatement && run.session_id
        ? usageStatement
            .all(run.session_id)
            .map((item) => ({ ...item, started_at: new Date(item.started_at).toISOString() }))
        : [];
      return {
        run_id: run.run_id,
        scheduled_at: new Date(run.scheduled_at).toISOString(),
        dispatch_status: run.dispatch_status,
        outcome: run.outcome,
        session_id: run.session_id,
        error: run.error,
        model_selection: readJson(run.model_selection),
        usage,
      };
    }),
  };
}

function findAutomationRows(db, options) {
  if (options.all) {
    return db.prepare('select * from automations order by title').all();
  }
  return [findAutomation(db, options)];
}

function findAutomation(db, options) {
  if (options.id) {
    const row = db.prepare('select * from automations where automation_id = ?').get(options.id);
    if (!row) throw new Error(`找不到 automation_id：${options.id}`);
    return row;
  }
  const rows = db.prepare('select * from automations where title = ?').all(options.title);
  if (rows.length === 0) throw new Error(`找不到标题为「${options.title}」的定时任务`);
  if (rows.length > 1) {
    const ids = rows.map((row) => row.automation_id).join(', ');
    throw new Error(`标题「${options.title}」匹配到 ${rows.length} 个定时任务，请改用 --id：${ids}`);
  }
  return rows[0];
}

function buildPlan(options) {
  let providerId = options.provider;
  let modelId = options.model;
  let reasoningLevel = options.reasoning;

  if (options.to) {
    const preset = PRESETS[options.to];
    if (!preset) {
      throw new Error(`未知预设「${options.to}」，可用：${Object.keys(PRESETS).join(', ')}`);
    }
    if (providerId || modelId) {
      throw new Error('--to 不能与 --provider/--model 同时使用');
    }
    providerId = preset.providerId;
    modelId = preset.modelId;
    reasoningLevel = reasoningLevel || preset.reasoningLevel;
  }

  if (!providerId || !modelId) {
    throw new Error('必须提供 --to 预设，或同时提供 --provider 与 --model');
  }

  const selection = { providerId, modelId };
  if (reasoningLevel) {
    selection.options = { reasoningLevel };
  }

  return {
    model: `${providerId}/${modelId}`,
    modelSelection: JSON.stringify(selection),
    thoughtLevel: null,
  };
}

function sanitizeFileName(value) {
  return value.replace(/[\\/:*?"<>|\s]+/g, '-').replace(/^-+|-+$/g, '') || 'automation';
}

function backupRow(row, plan) {
  const backupDir =
    process.env.ZCODE_PLAN_SWITCH_BACKUP_DIR ||
    path.join(os.tmpdir(), 'zcode-plan-switch-backups');
  fs.mkdirSync(backupDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filePath = path.join(backupDir, `automation-${sanitizeFileName(row.title)}-${stamp}.json`);
  const payload = {
    schemaVersion: 1,
    createdAt: new Date().toISOString(),
    automation: describeRow(row),
    planned: {
      model: plan.model,
      model_selection: JSON.parse(plan.modelSelection),
      thought_level: plan.thoughtLevel,
    },
  };
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  return filePath;
}

function applyPlan(db, row, plan) {
  const now = Date.now();
  db.exec('BEGIN IMMEDIATE');
  try {
    const info = db
      .prepare(
        'update automations set model = ?, model_selection = ?, thought_level = ?, updated_at = ? ' +
          'where automation_id = ?'
      )
      .run(plan.model, plan.modelSelection, plan.thoughtLevel, now, row.automation_id);
    if (info.changes !== 1) {
      throw new Error(`预期更新 1 行，实际 ${info.changes} 行`);
    }
    db.exec('COMMIT');
  } catch (error) {
    db.exec('ROLLBACK');
    throw error;
  }
  return describeRow(
    db.prepare('select * from automations where automation_id = ?').get(row.automation_id)
  );
}

function restoreFromBackup(db, backupPath, dryRun) {
  const resolved = path.resolve(backupPath);
  if (!fs.existsSync(resolved)) {
    throw new Error(`备份文件不存在：${resolved}`);
  }
  const payload = JSON.parse(fs.readFileSync(resolved, 'utf8'));
  const saved = payload.automation;
  if (!saved || !saved.automation_id) {
    throw new Error('备份文件缺少 automation.automation_id');
  }
  const current = db
    .prepare('select * from automations where automation_id = ?')
    .get(saved.automation_id);
  if (!current) {
    throw new Error(`数据库中已不存在该定时任务：${saved.automation_id}`);
  }

  const selection = saved.model_selection === null ? null : JSON.stringify(saved.model_selection);
  const before = describeRow(current);
  if (dryRun) {
    return { dryRun: true, before, restored: { ...before, model: saved.model, model_selection: saved.model_selection, thought_level: saved.thought_level } };
  }

  db.exec('BEGIN IMMEDIATE');
  try {
    const info = db
      .prepare('update automations set model = ?, model_selection = ?, thought_level = ?, updated_at = ? where automation_id = ?')
      .run(saved.model ?? null, selection, saved.thought_level ?? null, Date.now(), saved.automation_id);
    if (info.changes !== 1) {
      throw new Error(`预期更新 1 行，实际 ${info.changes} 行`);
    }
    db.exec('COMMIT');
  } catch (error) {
    db.exec('ROLLBACK');
    throw error;
  }
  const after = describeRow(
    db.prepare('select * from automations where automation_id = ?').get(saved.automation_id)
  );
  return { before, after, backup: resolved };
}

function printHumanList(rows) {
  if (rows.length === 0) {
    console.log('没有定时任务。');
    return;
  }
  for (const row of rows) {
    const selection = row.model_selection ? JSON.stringify(row.model_selection) : 'null';
    console.log(`${row.title}  [${row.automation_id}]`);
    console.log(`  cron: ${row.cron_expr}  enabled: ${row.enabled}  next: ${row.next_run_at || 'null'}`);
    console.log(`  model: ${row.model || 'null'}`);
    console.log(`  selection: ${selection}`);
  }
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    usage(error.message);
  }
  if (options.help) usage();
  if (options.list && (options.all || options.title || options.id || options.to || options.restore || options.history)) {
    usage('--list 不能与其他操作同时使用');
  }
  if (options.all && (options.title || options.id || options.restore || options.history)) {
    usage('--all 不能与 --title/--id/--restore/--history 同时使用');
  }
  if (options.history && (options.all || options.title || options.id || options.to || options.restore)) {
    usage('--history 不能与其他操作同时使用');
  }
  if (!options.list && !options.all && !options.restore && !options.history && !options.title && !options.id) {
    usage('必须指定 --list、--all、--history、--title/--id 或 --restore');
  }

  const dbPath = resolveDbPath(options.db);
  const readOnly = options.list || options.dryRun;

  if (options.list) {
    const db = openDatabase(dbPath, true);
    try {
      const rows = listAutomations(db);
      if (options.json) console.log(JSON.stringify({ db: dbPath, automations: rows }, null, 2));
      else printHumanList(rows);
    } finally {
      db.close();
    }
    return;
  }

  if (options.history) {
    const limit = options.limit === undefined ? 5 : Number.parseInt(options.limit, 10);
    if (!Number.isInteger(limit) || limit <= 0 || limit > 100) {
      throw new Error('--limit 必须是 1 到 100 的整数');
    }
    const sessionDbPath = resolveSessionDbPath(options.sessionDb);
    const sessionDb = sessionDbPath ? openDatabase(sessionDbPath, true) : null;
    const db = openDatabase(dbPath, true);
    try {
      const history = automationHistory(db, sessionDb, options.history, limit);
      if (options.json) {
        console.log(
          JSON.stringify(
            {
              db: dbPath,
              session_db: sessionDbPath,
              automation_id: options.history,
              usage_error: history.usageError,
              runs: history.runs,
            },
            null,
            2
          )
        );
      } else if (history.runs.length === 0) {
        console.log(`暂无运行记录：${options.history}`);
      } else {
        if (history.usageError) console.log(`注意：${history.usageError}`);
        for (const run of history.runs) {
          console.log(`${run.scheduled_at}  ${run.outcome}  ${run.dispatch_status}  ${run.run_id}`);
          console.log(`  selection: ${JSON.stringify(run.model_selection)}`);
          for (const item of run.usage) {
            console.log(`  usage: ${item.provider_id}/${item.model_id} ${item.status} ${item.started_at}`);
          }
          if (run.error) console.log(`  error: ${run.error}`);
        }
      }
    } finally {
      db.close();
      if (sessionDb) sessionDb.close();
    }
    return;
  }

  if (options.restore) {
    const db = openDatabase(dbPath, readOnly);
    try {
      const result = restoreFromBackup(db, options.restore, options.dryRun);
      if (options.json) console.log(JSON.stringify({ db: dbPath, ...result }, null, 2));
      else {
        console.log(`数据库：${dbPath}`);
        console.log(`恢复来源：${options.restore}`);
        console.log(`恢复前：${JSON.stringify(result.before.model_selection)} (model=${result.before.model})`);
        if (result.after) {
          console.log(`恢复后：${JSON.stringify(result.after.model_selection)} (model=${result.after.model})`);
        } else {
          console.log('dry-run：未写入');
        }
      }
    } finally {
      db.close();
    }
    return;
  }

  const plan = buildPlan(options);
  const db = openDatabase(dbPath, readOnly);
  try {
    const rows = findAutomationRows(db, options);
    if (rows.length === 0) {
      throw new Error('数据库中没有定时任务，--all 无可操作对象');
    }
    const results = rows.map((row) => {
      const before = describeRow(row);
      const backup = options.dryRun ? null : backupRow(row, plan);
      const after = options.dryRun ? null : applyPlan(db, row, plan);
      return {
        automation_id: row.automation_id,
        title: row.title,
        before,
        after,
        backup,
      };
    });

    if (options.json) {
      console.log(
        JSON.stringify(
          {
            db: dbPath,
            dryRun: options.dryRun,
            planned: {
              model: plan.model,
              model_selection: JSON.parse(plan.modelSelection),
              thought_level: plan.thoughtLevel,
            },
            count: results.length,
            results,
          },
          null,
          2
        )
      );
    } else {
      console.log(`数据库：${dbPath}`);
      console.log(`目标：${plan.modelSelection} (model=${plan.model})`);
      console.log(`任务数：${results.length}${options.all ? '（--all 自动发现）' : ''}`);
      for (const result of results) {
        console.log(`--- ${result.title} [${result.automation_id}]`);
        console.log(`  切换前：${JSON.stringify(result.before.model_selection)} (model=${result.before.model})`);
        if (options.dryRun) {
          console.log('  dry-run：未写入');
        } else {
          console.log(`  切换后：${JSON.stringify(result.after.model_selection)} (model=${result.after.model})`);
          console.log(`  备份：${result.backup}`);
        }
      }
      if (!options.dryRun) {
        console.log('提示：请在下次调度运行后，用 model_usage 核对实际使用的 provider_id。');
      }
    }
  } finally {
    db.close();
  }
}

try {
  main();
} catch (error) {
  console.error(`错误：${error.message}`);
  process.exit(EXIT_ERROR);
}
