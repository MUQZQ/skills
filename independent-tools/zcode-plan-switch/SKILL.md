---
name: zcode-plan-switch
description: 切换 ZCode 定时任务（automations）的模型与套餐：读取并备份 tasks-index.sqlite，按 Start Plan 或指定供应商写入，支持 dry-run、运行历史回读和回滚。适用于 ZCode 套餐额度用尽、夜间切免费 Start Plan、定时任务模型调整、automations 供应商切换。
---

# ZCode 套餐切换

## 职责边界

- 只修改 ZCode **定时任务**（`automations` 表）的模型与套餐设置。
- 不切换桌面端已经打开的活跃会话：每个会话由桌面主进程独占 `app-server --stdio`，外部没有受支持的切换接口；需要时在 ZCode 界面里手动切换。
- 不创建、删除、启停定时任务，不改 `cron_expr`、`next_run_at` 和运行历史。
- 脚本不读取 API key、token 或其他凭据。

## 前置条件

- ZCode 桌面端已安装并至少登录过一次；目标套餐在该账号下有权益。
- Node.js >= 22（依赖内置 `node:sqlite`）。
- 默认数据位置：
  - 定时任务库：`~/.zcode/v2/tasks-index.sqlite`
  - 会话用量库：`~/.zcode/cli/db/db.sqlite`

## 场景路由

| 用户意图 | 操作 |
|---|---|
| 查看当前定时任务用什么模型 | `--list` |
| 把某个任务切到免费 Start Plan | `--title <标题> --to start-plan --dry-run`，确认后去掉 `--dry-run` |
| 把全部定时任务切到 Start Plan | `--all --to start-plan --dry-run`，确认后去掉 `--dry-run`（自动从数据库发现全部任务，无需列举标题或 ID） |
| 切到付费个人套餐 | `--to individual-coding-plan` |
| 使用自定义供应商/模型 | `--provider <providerId> --model <modelId> --reasoning <级别>` |
| 核对下一次运行是否真的用了新套餐 | `--history <automation_id>` |
| 撤销某次切换 | `--restore <备份文件>` |

## 铁律

| 规则 | 内容 | 违反后果 |
|---|---|---|
| R0 | 先 `--list` 和 `--dry-run`，确认标题和当前值 | 改错任务或覆盖别人的设置 |
| R1 | 正式写入前必须生成备份文件 | 无法回滚 |
| R2 | 只改 `model`、`model_selection`、`thought_level`、`updated_at` | 触发时间、启用状态被破坏 |
| R3 | 写入后回读并核对，不把“执行成功”当“设置正确” | 静默写入失败 |
| R4 | 配置证据不等于运行证据：下一次调度后必须查 `--history` | 套餐无权益时仍报告成功 |

## 工作流

### 1. 列出任务

```bash
node scripts/switch-automation.js --list
```

记录目标任务的 `automation_id`、`cron_expr`、当前 `model_selection` 和 `next_run_at`。

### 2. 预览切换

```bash
node scripts/switch-automation.js --title "定期检视" --to start-plan --dry-run --json
```

检查输出的 `before` 与 `planned`。标题必须唯一；重名时改用 `--id`。

### 3. 写入并备份

```bash
node scripts/switch-automation.js --title "定期检视" --to start-plan
```

脚本会在 `<系统临时目录>/zcode-plan-switch-backups/` 生成备份，返回切换前后的值。可用环境变量 `ZCODE_PLAN_SWITCH_BACKUP_DIR` 指定备份目录。

### 4. 运行后核对

等下一次调度完成（看 `next_run_at`），执行：

```bash
node scripts/switch-automation.js --history <automation_id> --limit 3
```

判定标准，三项都要满足：

- `automation_runs.model_selection` 等于目标供应商/模型；
- `model_usage.provider_id` 与 `model_id` 等于目标（实际请求证据）；
- `outcome` 不是失败；若为 `model_rate_limited`、`not_authenticated` 等，说明套餐无权益或已限额，切回或换套餐。

### 5. 回滚

```bash
node scripts/switch-automation.js --restore <备份文件路径>
```

备份文件逐任务生成，恢复前会回读并打印切换前后的值；`--dry-run` 可先预览。

## 命令参数

| 参数 | 说明 |
|---|---|
| `--list` | 列出全部定时任务 |
| `--all` | 自动发现并操作全部定时任务，与 `--title`/`--id` 互斥；不可与 `--list`/`--history`/`--restore` 同用 |
| `--title <标题>` / `--id <automation_id>` | 指定目标任务（二选一，与 `--all` 三选一） |
| `--to <预设>` | `start-plan` 或 `individual-coding-plan` |
| `--provider` / `--model` / `--reasoning` | 自定义供应商、模型和推理级别 |
| `--dry-run` | 只预览，不写库 |
| `--history <id>` / `--limit <N>` | 查看最近运行记录与 `model_usage` |
| `--restore <文件>` | 从备份恢复 |
| `--db <路径>` | 覆盖定时任务库路径 |
| `--session-db <路径>` | 覆盖会话用量库路径 |
| `--json` | 输出结构化 JSON |

预设内容：

- `start-plan`：`account:bigmodel-start-plan / GLM-5.3-Flash`，`reasoningLevel=max`
- `individual-coding-plan`：`account:bigmodel-individual-coding-plan / GLM-5.3-Flash`，`reasoningLevel=max`

## 错误处理

| 场景 | 处理 |
|---|---|
| 数据库不存在 | 确认 ZCode 桌面端已安装；用 `--db` 指定实际路径 |
| 标题匹配到多个任务 | 改用 `--id` |
| 数据库被占用 | 脚本已设置 5 秒 `busy_timeout`；仍失败时稍后重试，不要强杀进程 |
| 下一次运行失败 | 用 `--history` 看错误；确认账号有该套餐权益，必要时 `--restore` |
| 表结构变化（升级后） | 先 `--list` 验证；失败则停止写入并更新本 Skill |

## 限制

- 免费 Start Plan 与付费套餐的可用性由 ZCode 桌面端权益决定；写入配置正确不等于供应商一定接受请求。
- 活跃会话无法通过本工具切换，只能改定时任务的后续运行。
- 不要把本工具用于绕过计费或账号限制；它只调整本机定时任务的模型选择。
