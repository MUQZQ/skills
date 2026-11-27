---
name: qeda-desktop-packaging
description: >
  QEDAgent 旧桌面架构（1030 交付线）的 Windows 安装包构建、版本号调整与交付核验工作流。
  当用户提到「打包」「出包」「重新打包」「打个包」「安装包」「NSIS」「electron-builder」
  「发行包」「交付包」「版本号改成 X」「客户工具随包」「隐藏入口交付」时使用。
  覆盖 desktop:build、目录包、真机验收、VC++/PCB 客户工具暂存、NSIS 生成，
  以及 asar/模型/帮助/端口/版本号/载荷的逐字节核验。
---

# QEDAgent 桌面打包

本 Skill 只负责 QEDAgent 旧桌面架构（`1030release-bugfix` / `release1030package`）的
Windows 安装包构建与交付核验。DSH/新架构打包、CI 发布、代码评审不在本范围。

权威背景在项目 `docs/development/desktop-distribution.md`；本 Skill 提供可执行的顺序、
真实命令、坑位和验收清单，不复制该文档的完整论述。

## 前置条件

- 工作树：打包通常在 `E:/worktrees/QEDAgent/QEDAgent_user-guide-pilot`，分支 `release1030package`。
- 工作区必须干净（只允许既有未跟踪的 `resources/sch-extension.zip`）；有并行写者先确认归属。
- 资源就绪：
  - 帮助图片：`QEDA_HELP_ASSET_ROOT='C:\Users\30960\Desktop\QEDAgent-help-assets'`
  - 客户工具：`QEDA_CUST_TOOLS_BUNDLE_DIR='E:\QedAgent\cust-tools-bundle-2610.6\dist'`
  - VC++ 缓存：`E:/QedAgent/handoff/vc-cache-14.52.37029.0/`（官方下载超时时复用）
- 打包前清空帮助残留：`frontend/public/help/assets`、`frontend/public/help/guide.json`、
  `.desktop-package/resources/sch-extension.zip`。

## 场景路由

| 用户意图 | 走法 |
|---|---|
| 首次/常规打包 | 主流程五步 |
| 重新拉代码后打包 | 先按 `branch-manager` 合入 upstream → 再走主流程 |
| 只改版本号/显示名 | 先改三层版本（见下），再走主流程 |
| 打包中断/失败 | 按「错误处理」恢复，不从头盲目重跑 |
| 包已生成，只做核验 | 直接按 `references/verification.md` |

## 铁律

| 规则 | 内容 | 违反后果 |
|---|---|---|
| R1 | electron-builder 必须带 `--projectDir .desktop-package --config ../electron-builder.yml`，输出用 `--config.directories.output=../release/package-profile` | 漏 `--projectDir` 会扫描工作区 `node_modules`，命中循环软链 `ELOOP` |
| R2 | `release1030package` 含裁剪/隐藏/客户工具定制，**默认不推送**；推送需用户逐次明确 | 泄露定制交付内容 |
| R3 | 版本号分三层：内部 semver（`package.json`）、显示名/文件名（artifactName、`uninstallDisplayName`、扩展 `version_name`）、Windows FileVersion（`buildVersion` 四段数字） | 字母版本写进 semver/manifest 会被构建或浏览器拒绝 |
| R4 | 交付结论必须来自逐字节比对（asar 哈希、载荷 SHA、模型 SHA），不能只看日志 | 打出旧包/错包 |
| R5 | 不删除、不覆盖用户手工产物（如 `resources/sch-extension.zip`）；要改先备份到 `E:/QedAgent/handoff/` | 丢失用户交付物 |
| R6 | NSIS 阶段默认使用 `electron-builder.yml` 的 `nsis.include` 链（VC++ + 客户工具）；单独 include VC 会触发 6001 或漏客户工具 | 安装器缺前置或编译失败 |
| R7 | 打包前必须与用户确认：当前分支、当前版本 → 目标版本、安装包文件名；未确认不得启动 bump 或构建 | 打出用户不认可的版本 |

## 主流程

0. **版本准备与确认**（每次交付打包都执行）：
   1. 先干跑：`node <skill>/scripts/bump-build-version.mjs --dry-run <工作树根目录>`。
   2. 若脚本报「分支没有版本记录」，**停止并向用户确认初始版本**（例 `2.2609.2.0`），
      再用 `--init <初始版本>` 重跑；不要自行假定。
   3. 把「分支、当前版本 → 目标版本、安装包文件名」展示给用户，取得明确确认。
   4. 用户确认后去掉 `--dry-run` 执行，脚本会同步 `buildVersion`、`artifactName`、
      `uninstallDisplayName` 与扩展 manifest，并把版本记录写入项目仓库的
      `scripts/desktop-release-version.json`（随分支提交，不属于 Skill）。
   用户明确说「沿用上一版版本重打」时才跳过本步。

环境变量（每个新 shell 都要导出）：

```bash
export QEDA_DESKTOP_UI_MASK='{"hiddenPluginPackages":["@qedagent/plugin-project-workspace-web","@qedagent/plugin-design-review-web","@qedagent/plugin-library-sync-web","@qedagent/plugin-plugin-manager-web","@qedagent/plugin-auth-web"],"hideCbb":true}'
export QEDA_HELP_ASSET_ROOT='C:\Users\30960\Desktop\QEDAgent-help-assets'
export ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
export QEDA_CUST_TOOLS_BUNDLE_DIR='E:\QedAgent\cust-tools-bundle-2610.6\dist'
```

1. **构建暂存**：`pnpm desktop:build`（含 help、SCH 资源、前端、依赖部署与裁剪）。
2. **目录包**：
   `pnpm exec electron-builder --projectDir .desktop-package --config ../electron-builder.yml --win --dir --config.directories.output=../release/package-profile`
3. **真机验收**：
   `QEDA_PROFILE_DISTRIBUTION_EXE="$(pwd)/release/package-profile/win-unpacked/QEDAgent.exe" pnpm exec vitest run frontend/e2e/package-profile-native.spec.ts`
4. **前置暂存**：
   `pnpm exec jiti scripts/stage-windows-vc-runtime.ts`
   `pnpm exec jiti scripts/stage-windows-cust-tools.ts`
5. **NSIS**：
   `pnpm exec electron-builder --projectDir .desktop-package --config ../electron-builder.yml --win nsis --config.directories.output=../release/package-profile`

第 4 步 VC++ 下载超时时，从 `E:/QedAgent/handoff/vc-cache-14.52.37029.0/` 复制
`vc_redist.x64.exe`、`vc-runtime-version.nsh`、`vc-runtime.json` 到
`.desktop-package/installer/`，再单独执行客户工具暂存和第 5 步。

## 版本号三层

- 内部版本：根 `package.json` 的 `version`，必须是合法 semver（例：`2.2609.2`），不随每次打包变化。
- 构建号：`electron-builder.yml` 的 `buildVersion` 四段数字，**每次交付打包前 +1**
  （`2.2609.2.0 → 2.2609.2.1`），映射到 Windows FileVersion。
- 安装包显示：`win.artifactName` 与 `nsis.uninstallDisplayName` 使用
  `<三段>.<构建号>.HND`（例 `QEDAgent-Setup-2.2609.2.1.HND-x64.exe`、`QEDAgent 2.2609.2.1.HND`）。
- 扩展版本：manifest `version` 使用同一四段数字（例 `2.2609.2.1`），`version_name` 用
  `<三段>.<构建号>.HND`；字母只能放在 `version_name`，`version` 必须是数字段。

打包前运行 Skill 自带脚本一次性同步四处：

```bash
node <skill>/scripts/bump-build-version.mjs --dry-run <QEDAgent 工作树根目录>
node <skill>/scripts/bump-build-version.mjs <QEDAgent 工作树根目录>
```

- **按分支维护，记录在项目里**：版本记录保存到目标工作树的
  `scripts/desktop-release-version.json`（`{ branch, version, updatedAt }`），随分支提交、
  可 diff 可追溯。记录里的 `branch` 与当前分支不一致（新分支继承了旧文件）或文件不存在时，
  视为未记录。Skill 只提供方法与脚本，不持有版本状态。
- **未记录分支**：脚本退出码 2，要求先与用户确认初始版本；确认后用
  `--init <x.y.z.n>` 建立记录，不猜初始值。
- **打包前确认**：先 `--dry-run` 得到「当前 → 目标」版本与安装包文件名，交用户确认后再正式执行。
- 脚本会校验 `buildVersion`、`artifactName`、`uninstallDisplayName`、
  `resources/sch-extension/manifest.json` 都更新到新版本；任一格式不匹配即报错，不静默。
- 用户明确要求「沿用当前版本号重打」时才跳过本步。

## 错误处理

| 现象 | 根因 | 处理 |
|---|---|---|
| `ELOOP: too many symbolic links` | 漏 `--projectDir .desktop-package`，扫描工作区 node_modules | 按 R1 重跑第 2 步 |
| `UND_ERR_CONNECT_TIMEOUT`（VC++） | `aka.ms` 下载超时 | 复用本机已验签缓存（见上），不要改脚本硬编码 |
| `Lock file is already being held` | 上次被杀进程留下 `%TEMP%\eb-dl-*.lock.lock` | 确认无 electron-builder 进程后删除该锁目录再重跑 |
| electron 下载 0.5%/分钟 | 未走镜像 | 固定 `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/` |
| 真机验收 `guide.articles` 失败 | 帮助包降级 `{unavailable:true}`（旧哈希图片残留） | 打包前清空 `frontend/public/help/{assets,guide.json}` |
| `Missing deployed runtime dependency`（如 `@noble/hashes`） | 生产代码引用但声明在 devDependencies | 移到 dependencies 并更新 lockfile |
| NSIS `warning 6001` | 单独 include VC nsh 未插入宏 | 用默认 `windows-installer.nsh` 链（R6） |
| 安装包内 asar 与目录包不一致 | NSIS 阶段重新打包或源被改 | 以哈希比对为准重打 |

## 验收

运行 `references/verification.md` 的清单：安装包 SHA256/签名、安装包内 asar 与已验收
目录包一致、模型/onnx 原生绑定、帮助文章数、扩展与 PCB QML 端口、客户载荷 SHA、
版本号三层、可执行文件 FileVersion。

结论必须写到具体文件和哈希；不要用「日志显示成功」代替核验。

## 参考

- 项目文档：`docs/development/desktop-distribution.md`、`docs/development/windows-cust-tools-verification.md`
- 打包脚本：`scripts/stage-desktop-package.ts`、`scripts/stage-windows-vc-runtime.ts`、`scripts/stage-windows-cust-tools.ts`
- 验收用例：`frontend/e2e/package-profile-native.spec.ts`
