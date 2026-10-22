---
name: prhelp-review-to-guide
description: >
  从 PrHelp（patodo PR 检视平台）提取检视记录全文、场景验证步骤与实机截图，并产出带图的操作指导
  文档（Markdown / Word）。当用户说「读某 PR 的检视/评审全文」「PrHelp 上有什么」「把检视里的截图
  步骤整理成文档」「基于检视写操作指导/操作手册」「取检视验证截图」「总结某 PR 的实机验证步骤」，
  或给出 qedai PrHelp 页面链接（#/pr/数字）要求取证或成文时使用。覆盖 PrHelp API 直连认证、
  检视正文/截图提取、已归档规格与源码文案核对、docx 生产与视觉验收全链。仅读某条评论的短摘要
  不需要本 Skill。
---

# PrHelp 检视取证 → 操作指导文档

把 PR 检视记录（轮次列表 → 正文全文 → 场景验证表 → 实机截图）加工成一份图文可溯的操作指导文档。
方法论源自 PR #423 CMS 归档实例：检视摘要只是索引，全文才有场景表；截图只覆盖「实机 UI 验证过且
需要视觉证据」的场景，缺图是素材事实不是遗漏，禁止用原型图或模拟图充数。

整体链路：`取证（API 直连）→ 权威核对（规格+源码）→ 成文（Markdown 先行）→ Word 生产 → 双层验收`。

## 前置条件

- 目标 PR 号或 PrHelp 页面 URL（`https://qedai.df2cloud.com:60008/patodo/pr-help/#/pr/<N>`）。
- API key：`C:\Users\30960\AppData\Roaming\localapp\profiles.json` 的 `profiles.default.apiKey`
  （与页面同域的服务地址也在该文件的 `serverUrl`）。
- 产出 Word 时需 `documents:docx` skill 与 node/bun；渲染验收需 LibreOffice（本机坑见阶段 4）。

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|---------|
| R0 | 认证一律用 `X-API-Key: <apiKey>` 请求头；页面弹出的账号密码登录框与此无关，不要尝试填它 | 认证绕路浪费时间；Bearer/query 参数均为未登录态 |
| R1 | 检视查询一律 POST JSON `{"params":{...}}`；列表参数名是 `prNumber`（不是 pr） | 404/Unknown param 空转 |
| R2 | 截图必须真实可溯：只嵌入检视正文实际引用的图片，每张标注来源轮次与 head 提交 | 文档可信度崩塌 |
| R3 | 行为描述以已归档 OpenSpec 规格为权威、界面文案与源码逐条核对；检视摘要只当索引用 | 文档与实际界面措辞漂移 |
| R4 | Word 交付前必须 postcheck 0 错误 + 独立视觉验收 agent 全量 PASS；修复后同一复核上下文全量复检 | 带版式缺陷交付 |
| R5 | 评审结论对应的是「评审提交」时点；处置引用前先 `git show <commit>` 确认真实内容 | 引用已过时的快照结论 |

## 工作流

### 阶段 1：API 直连取证

BASE = `<serverUrl>/serve/patodo/pr-help/api`。连续快速请求会触发 nginx 502，逐个请求加 3~10s 间隔。

1. **轮次列表**：`POST {BASE}/queries/$pr_reviews.byPr`，body `{"params":{"prNumber":<N>,"limit":50,"offset":0}}`。
   返回 `data.rows[]`（id / head_sha / verdict / summary / reviewed_at）。Git Bash 中 URL 里的 `$`
   必须转义（`\$pr_reviews.byPr`）或用单引号。
2. **筛选相关轮**：按 summary 关键词（如功能名、模块名）定位目标轮次的 id。轮次 id 是时间正序的
   数字，最新轮最大。
3. **拉全文**：`POST {BASE}/queries/$pr_reviews.bodyById`，body `{"params":{"id":<id>}}` →
   `data.rows[0].body_md`。正文含「场景验证」表与「验证截图」段。
4. **取截图**：正文中 `![图N](/serve/patodo/pr-help/api/content/<hash>.png)`，同域名加同一
   `X-API-Key` 头直接 GET 下载。python 读 JSON 时注意 Git Bash 的 `/tmp` 路径要过 `cygpath -w`。
5. 页面若打不开/认证异常，可下载 SPA bundle（页面 resource list 里的
   `/serve/patodo/pr-help/assets/index-*.js`）grep 查询名与参数——查询契约以代码为准。
- [ ] 拿到目标轮全文 + 全部相关截图落盘 → 下一步

### 阶段 2：权威核对

1. 从 git 导出正文引用的已归档规格：检视正文里的
   `openspec/changes/archive/<变更>/specs/...` 路径若当前分支没有，用
   `git show <PR线提交>:<路径>` 直接导出（`git log --all --diff-filter=A -- "<路径>"` 定位提交）。
2. 界面文案（按钮名、提示句、状态句）与源码逐条核对（grep 源文件字面量），文档中引用界面原话时
   必须与源码一致。
3. 检视的处置结论若引用了具体提交，按 R5 先 `git show` 核对。
- [ ] 文档涉及的每条行为都有规格或源码出处 → 下一步

### 阶段 3：成文（Markdown 先行）

- 截图入 `docs/assets/<主题>/`，文档用相对路径引用。
- 结构：功能定位 → 入口与前提（表）→ 按界面分区/步骤逐段展开（编号步骤 + 界面原话 + 提示块）→
  常见提示速查表（提示｜含义｜处理）→ 依据与来源（截图出处、规格清单、核对源码）。
- 无截图的步骤如实留白并在依据节说明截图覆盖范围，不配假图。
- [ ] 用户确认 Markdown 内容 → 下一步（用户只要 md 到此为止）

### 阶段 4：Word 生产

加载 `documents:docx` skill 按其路由执行（Create 路由）。本机已踩实的坑：

| 环节 | 坑 | 处理 |
|------|-----|------|
| LibreOffice 安装 | MSI 静默安装 1603（要管理员），per-user 同样失败 | `msiexec /a <msi> /qn TARGETDIR=<目录>` 管理解包（免管理员），直接跑 `<TARGETDIR>/program/soffice.exe --headless --convert-to pdf`，加 `-env:UserInstallation=...` 隔离配置 |
| 多节结构 | LibreOffice 把「段落内嵌 sectPr」的节尾段整体推到新页 → 节尾放实质内容必成近空白页 | 目录提示等实质内容放节首；节尾只留 docx-js 自动生成的空 sectPr 段 |
| TOC 占位脚本 | `add_toc_placeholders.py` 把第一条目并进域起始段 → 目录首条重复且缺页码 | 后处理正则剥离域起始段内的 hyperlink（保留 begin/instrText/separate 三个 run） |
| TOC 高度 | 20 条目即占满一页，提示被挤到下页 | 压 TOC1/TOC2 样式间距（toc1 before 20 after 0 / toc2 0 0）+ 缩目录标题间距 |
| 渲染验收 | pdftoppm 无 pymupdf 稳 | `pip install pymupdf` 渲染页 PNG |

其他按 docx skill 既定规则：封面配方（tech 类 R1+DM-1）、三节页码架构（封面无页码/目录 ROMAN/正文
arabic 起 1）、页脚 instrText 后处理（`\* ROMAN` / `\* arabic`）、移除空 `<w:pgNumType/>`、表格
`tableHeader+cantSplit+keepNext`、标题 `keepNext` 防孤行、中文字符串禁弯引号。

### 阶段 5：双层验收

1. `postcheck.py` 必须 0 错误（警告逐条确认是否配方豁免）。
2. soffice 转 PDF → pymupdf 渲染全部页 PNG → 派独立视觉验收 agent（documents:visual-judge）
   全量逐页评审（空白页/溢出/裁剪/重叠/表格跨页/图片变形/页码/乱码/markdown 残留）。
3. 有 fail 项：修复 → 重渲染 → **同一 agent 同一标准全量复检**，直到 overall pass。
- [ ] overall pass → 交付（按 docx skill 的 citation 规范引用最终文件恰好一次）

## 错误处理

| 环节 | 失败条件 | 处理方式 |
|------|---------|---------|
| API | HTTP 502（连续请求限流） | 间隔 3~10s 逐个重试，不要并发 |
| API | `Unknown param` / Not found | 参数名以 SPA bundle 代码为准，勿猜 |
| 取证 | 页面 Authentication required | 用 X-API-Key 直连接口，不走页面登录框 |
| Word | postcheck 报 blank-pages | 检查「节尾 PageBreak + NEXT_PAGE 双重分页」与「节尾 sectPr 实质段」两类根因 |
| 验收 | 渲染字体替换（SimHei 缺失等） | 不影响可读性不计缺陷，向验收 agent 预先声明豁免口径 |

## 输出建议

- 取证类任务：以表列出「轮次 id｜head｜结论｜关键发现」，附截图路径清单。
- 成文类任务：交付 md + docx 两个产物，说明截图覆盖范围与验收结论（postcheck + 视觉验收页数/PASS 数）。
