# ZCode 动态工作流 UI 高保真视觉与交互规格

> 权威源码：`E:/QedAgent/ZCode-main/packages/ui`。本文所有类名、色值、尺寸均从源码原文提取，
> 行号供回溯。QEDAgent 工作流 UI 对齐时以本文为像素级答案；与本文冲突时以 ZCode 源码为准。
> 语言约定：状态灯（lamp）、药丸（pill）、脊线（spine）、边檐（ledge）、留白（hole）、行进边（march rail）。

---

## 一、视觉 token（styles.css）

### 1.1 字号与排印（styles.css L76, L171-183）

- `--ui-font-size: 14px` 为基准：`text-ui-xl` 18 / `text-ui-lg` 16 / `text-ui-base` 14 /
  `text-ui-caption` 13 / `text-ui-sm` 12 / `text-ui-xs` 10 / `text-ui-2xs` 9（仅限工作流图轴面刻度标签、
  通道码、单位后缀）。
- `--tracking-wf-label: 0.09em`：大写等宽微标签（CAUSALITY GRAPH / TIMEBASE）专用字距。
- 技术值（run 名、runId、模型名、计数、时间）一律 `font-mono` + `tabular-nums`；人话正文用默认字体。

### 1.2 语义色（styles.css L186-336 亮色 / L338-490 暗色）

| token | 亮色 | 暗色 | 用途 |
|---|---|---|---|
| `--color-warning` | `var(--color-yellow-600)` (L295) | `yellow-500` (L449) | 活动色：运行灯、行进光、留白、并发芯片 |
| `--color-success` | `green-600` (L289) | `green-500` (L443) | done 灯、完成词 |
| `--color-destructive` | `red-600` (L293) | `red-500` (L447) | failed 灯、错误面板、删除项 |
| `--color-brand` | `sky-400` (L189) | `sky-500` (L344) | 输入框聚焦描边（不用于运行状态） |
| `--color-foreground` | `neutral-700` 60%/40% 生成 subtle/subtlest (L284-286) | `neutral-200` (L438) | 文字三级 |
| `--color-border` | `neutral-950` 10% 透明 (L205) | `neutral-50` 10% (L356) | 边框；hover 抬到 20%/30% |
| `--color-surface` / `surface-hover` | `neutral-950` 3% / 5% (L212-213) | `white` 5% / 10% (L363-364) | 药丸底 / 悬停底 |
| `--color-menu` | `white` (L274) | `neutral-950` (L424) | 候选面板底 |
| `--color-workflow-rule` | `neutral-950` 5.5% (L199) | `white` 6.5% (L350) | 刻度线、四格数字分隔线 |
| `--color-workflow-trace` / `-strong` | 950 的 30% / 55% (L200-201) | `white` 35% / 60% (L351-352) | 轨道墨 / 已走过墨 |

近似参考值（Tailwind 色板换算）：yellow-600≈#ca8a04、yellow-500≈#eab308、green-600≈#16a34a、
red-600≈#dc2626。暗色主题一律降一号（600→500）。

### 1.3 工作流运动词汇 `.wf-motion`（styles.css L1457-1465）

```
--wf-t-fast: 120ms;  --wf-t-base: 160ms;  --wf-t-enter: 200ms;  --wf-t-ink: 320ms;
--wf-ease: cubic-bezier(0.22, 0.61, 0.36, 1);   --wf-beat: 1.6s;  /* 灯的心跳周期 */
```

关键 keyframes（L2080-2149）：`wf-arrive` from `opacity:0; translateY(4px)`；
`wf-mark` from `scale(0.6)`；`wf-unfold` from `translateY(-3px)`；`wf-swap` from `translateY(3px)`；
`wf-rail-grow` from `scaleX(0)`（origin left）；`wf-slide` from `translateX(var(--wf-slide))`；
`wf-beat`：12% 处 `scale(1.12)`，光晕环从 3px 涨到 8px 淡尽。
`prefers-reduced-motion: reduce` 时全部动画/过渡归零（L2150-2205），循环停在静止帧；
灯只剩常亮光晕（L1822-1826 用 no-preference 包裹动画）。

扫光 `animated-gradient-text`（L856-872）：`background-size: 300%`，强色→弱色→强色五停点线性渐变，
`gradient-flow 4s linear infinite`，`background-clip: text`。运行中卡的种类词用它（见 3.2）；
注意 wf-swap 必须包在扫光**外层**，否则子图层提升后文字透明（WorkflowCardChrome.tsx L177-179）。

### 1.4 交互基础（components/ui/button.tsx L13-38）

Button 基类：`rounded-md text-ui-base transition-colors disabled:opacity-50`。
尺寸：`sm` h-6 px-2（svg 3）/ `default` h-7 px-2（svg 3.5）/ `lg` h-8 px-2.5 rounded-lg（svg 4）/
`icon-sm` size-6 / `icon-md` size-7 rounded-lg / `icon` size-7。
变体：`ghost` hover:bg-hover；`outline` border-border hover:border-border-hover hover:bg-input/50；
焦点环一律 `focus-visible:ring-2 focus-visible:ring-ring/40`。

---

## 二、输入框动作菜单与 /workflow 命令

### 2.1 触发按钮与弹出定位（ChatPromptActionMenu.tsx）

结构树：

```
Popover (open && !disabled)
├─ ControlHintTooltip (title=disabledReason ?? actionMenuTitle)
│  └─ PopoverTrigger asChild → Button variant=ghost size=icon-md
│     className="gap-1 rounded-lg text-ui-base"  → PlusIcon size-4 + sr-only 标签
├─ PopoverAnchor (virtualRef = 输入框容器 getBoundingClientRect)
└─ PopoverContent align="start" side="top" sideOffset={0}
   className="w-(--radix-popover-trigger-width) max-w-[calc(100vw-1rem)]
              gap-0 overflow-visible border-0 bg-transparent p-0 shadow-none"
   └─ MentionPanel (见 2.3)
```

- 快捷命令 `QUICK_COMMANDS`（L29-32）：`goal`（GoalIcon）/ `workflow`（lucide `Workflow` 图标），
  在「添加」分区里排附件之后；条目渲染 `Icon size-4 shrink-0` + `truncate text-ui-base font-medium`。
- 供给条件（L221-239）：仅严格空草稿（`getText() === ""`）；`/goal` 还要求新会话（`sessionId === null`）；
  `/workflow` 要求 CLI slash 命令目录含 `workflow`（插件禁用则不出）。
- 选中即 `buildSlashApplyMentionPayload({ trigger: "/", value: "workflow", label: "/workflow" })`
  插入 mention token（L203-216），焦点归还编辑器。
- 键盘（L285-302）：`ArrowDown/Up` 循环移动并跳过 disabled 项；`Enter/Tab/Space` 选中；
  打开时焦点移到面板（`onOpenAutoFocus` preventDefault 后 `contentRef.focus()`）。
- 面板 footer 快捷键提示（L308-329）：`code.flex.size-5.rounded.bg-tooltip-tag.font-mono` 方块装
  `@ / $` 三个触发符 + Info 图标提示行，`text-ui-sm text-foreground-subtle`。

### 2.2 斜杠候选面板 MentionPanel（mentions/components/MentionPanel.tsx）

- 容器（L254）：`mb-1 overflow-hidden rounded-2xl border border-border bg-menu shadow-xs`。
- 虚拟列表行高（L74-76）：选项 34px、分组头 34px、状态行 40px；滚动层 `max-h-56 overflow-y-auto px-1 py-0.75`，
  外部可传 `listMaxHeight="min(24rem, max(8rem, available-6rem))"`；上下滚动遮罩渐隐。
- 分组头类（L80-81）：`flex h-8 items-center px-3 text-ui-base font-semibold uppercase tracking-wide text-foreground-subtle`。
- 选项行（L393-415）：外层 `py-px`，按钮 `flex h-8 w-full items-center gap-3 rounded-xl px-3 transition-colors`；
  选中 `bg-selected`、悬停 `bg-hover`、禁选 `cursor-not-allowed opacity-50`（可见但不可点，fail closed）。
- 状态行（L336-373）：loading = `LoaderIcon size-3.5 animate-spin` + subtle；error = `bg-destructive
  text-destructive-foreground` 圆角条；empty = `text-foreground-subtlest`。

### 2.3 mention token 染色与命令图标

- token 基类（mentionChip.ts L3-6）：`inline-flex cursor-default items-center gap-1 align-top
  text-ui-base leading-5 font-medium`（align-top 修正与正文基线错位）。
- 命令变体（L15-17）：`text-command-node-foreground capitalize`。命令色 token（styles.css L322-324 亮 /
  L476-478 暗）：底 `slate-500/600` 14% mix，前景亮 `slate-600`≈#475569、暗 `slate-300`。
- 图标 DOM（mentionIconDom.ts）：`WORKFLOW_COMMAND_MENTION_LUCIDE_ICON_NAME = "Workflow"`（L64），
  路径 = rect(3,3,8,8,rx2) + path(M7 11v4a2 2 0 0 0 2 2h4) + rect(13,13,8,8,rx2)（L65-69）；
  `createMentionSvgIcon`（L117-140）：16×16、`stroke="currentColor"`、`stroke-width 1.5`、圆头圆角。
- 图标经 CSS mask 绘制不进选区（promptMentionDecoration.ts L30-39）：`--mention-mask` 装 data-URI SVG；
  styles.css `.prompt-mention::before`（L2208-2216）：`width/height 1rem`、
  `background: var(--mention-icon-color) var(--mention-image) center/contain no-repeat`、
  `mask: var(--mention-mask) center/contain no-repeat`；plugins 类目图标为图片、加 `border-radius: var(--radius-sm)`（L2218-2220）。
- 分类→图标：skills WandSparkles / subagents Bot / sessions MessagesSquare / whiteboards Palette /
  goal Goal / **workflow Workflow** / compact ScrollText / 其余命令 SquareSlash（promptMentionDecoration.ts L84-101）。

---

## 三、工作流运行卡片（对话流内）

### 3.1 运行卡 WorkflowRunDigest（WorkflowRunDigest.tsx L212-303）

```
section.wf-motion.wf-arrive.flex.w-full.min-w-0.flex-col.gap-1
  .rounded-xl.border.border-border/70.bg-card/70.px-3.5.pb-2.pt-1.5
│ data-workflow-run-status / data-expanded / role=button(有轨道时) tabIndex=0
│ 有轨道时 cursor-pointer + focus-visible:ring-2 ring-ring/40；点空白或 Enter/Space 折叠
├─ WorkflowCardHeader（见 3.2）
├─ div.wf-digest-plot.overflow-hidden  height = timelineHeight(model)+8
│  └─ WorkflowTimeline className="py-1"（站/药丸/弧，见 3.3-3.5）
├─ WorkflowTruncatedNotice（「仅展示 n/m 步的详情」）
└─ WorkflowArtifactStrip（产物药丸条，pb-0.5 pt-0.5）
```

- 收起时只清空各站药丸、保留阶段线（L111-120）；折叠过渡 `wf-digest-plot: transition height 320ms var(--wf-ease)`（styles.css L1776-1778）。
- 待答问题芯片（L151-170）：`wf-arrive flex shrink-0 items-center gap-1 rounded-full
  bg-[color-mix(in_oklab,var(--color-warning)_12%,transparent)] py-0.5 pl-1.5 pr-2
  text-ui-xs font-medium text-warning`，图标 `MessageCircleQuestion size-3`；可点时 hover 底抬到 20%。
- 「{n} 处留白待补全」芯片同面孔，图标换 `PenIcon size-3`（WorkflowHoleParts.tsx L62-101），两枚可并存于表头 leading 槽。
- Resume（outline default 钮 + `RotateCcw size-3.5`）与 Stop（ghost icon-md + `Square size-3.5 fill-current`）
  互斥占同一表头位（L184-205）；Stop 按下进入 disabled「正在停止…」，按 status 键控重挂复位。

### 3.2 卡表头 WorkflowCardHeader（WorkflowCardChrome.tsx L171-244）

```
div.flex.min-w-0.items-center.gap-2.text-ui-base   [data-testid=workflow-card-header]
├─ Workflow 图标 size-4 shrink-0 text-foreground-subtle        (L24)
├─ 种类词 span.shrink-0.font-medium → 内层 .wf-swap(key=文案) → live 时 .animated-gradient-text
├─ 名称 span.min-w-0.flex-1.truncate.text-foreground-subtle (title=全名)
└─ 右簇 span.flex.min-w-0.items-center.gap-2 (min-w-0 是压缩关键，细节串先让位)
   ├─ leading（问题/留白芯片）
   ├─ status = WorkflowRunStatus（灯+状态词，见 五）
   ├─ 细节串 .min-w-0.truncate.text-ui-base.tabular-nums.text-foreground-subtlest
   ├─ trailing（Configure / Resume|Stop）
   ├─ ⤢ Button ghost icon-md → Maximize2Icon size-3.5（开详情）
   └─ chevron Button ghost icon-md → ChevronRightIcon size-4，expanded 时 rotate-90
```

页脚变体 WorkflowCardFooter（L259-285）：`flex-wrap items-center gap-x-2 text-ui-sm text-foreground-subtle`
+ `ListIcon size-3.5` + 各段以 `·`（text-foreground-subtlest）分隔 + tabular-nums。

### 3.3 横向时间线几何（timeline-geometry.ts）

常量（与设计画布逐字相同）：`STATION_WIDTH 168`、`STATION_GAP 24`（`STATION_PITCH 192`，五站 936 装进
960 会话列）、灯心 `MARK_X 17`、`RAIL_ROW 24`、弧道 `ARC_LANE 14`、最低弧道 `ARC_BASE 26`、
弧端槽距 `TERMINAL_PITCH 10`、`PILL_HEIGHT 32`、`PILL_GAP 6`、站台行 `PLATFORM_ROW 24`、
站台名左缘 `CAPTION_X 12`、分叉回退 `FORK_BACK 16`、汇合回退 `MERGE_BACK 10`、`TAIL 4 / STUB 6`、
补全头行 `HEAD_ROW 24`、尾留白 `TAIL_STUB 40`。
药丸入场 `PILL_STAGGER_MS = 30`（WorkflowTimeline.tsx L101），逐枚 30ms 错位、`animationFillMode: backwards`。
总高 `timelineHeight = pillsTop + max(站药丸列高) + 8`（底部 8px 是 2px 滚动条的家）。

### 3.4 站头与轨道（WorkflowTimelineStation.tsx）

- 站头（L51-93）：`wf-station flex h-6 min-w-0 shrink items-center gap-2 rounded-md`；可点时加
  `wf-station-open cursor-pointer hover:text-foreground focus-visible:ring-2`。
  灯 `stationLampClass`（WorkflowTimelineLedge.tsx L29-51）：普通 `wf-lamp size-2.5 rounded-full + STATUS_DOT`，
  running 加 `wf-lamp-running`；留白站 `wf-lamp-hole size-2.5 rounded-full border-[1.5px] border-dashed
  bg-transparent`，waiting 加 `wf-lamp-hole-waiting border-warning`，open 用 `border-foreground-subtlest`。
  站名 `truncate text-ui-caption font-medium`，pending 时 `text-foreground-subtle` 否则 `text-foreground`。
- 站头元数据 StationMeta（WorkflowStationMeta.tsx L10-32）：`font-mono text-ui-xs tabular-nums
  text-foreground-subtlest gap-1.5`；轮次 `⟳ n`（`Repeat2Icon size-2.5`）+ `·` + 步数分数 `a/b`（text-ui-sm）。
- 轨道段（L207-233）：`wf-ink h-0 flex-1 rounded-full border-t border-foreground-subtlest`，
  `marginLeft:10 / marginRight:-6`；行进段加 `wf-rail-march`（::after 叠 1.5px 渐变光
  `linear-gradient(90deg, transparent, var(--color-warning) 80%)`，右端越界 4px 贴向光晕，styles.css L1380-1389）；
  流轨加 `wf-rail-stream min-w-[42px]`（border 变透明，::before 在正中留 22px 缺口画线，
  L1400-1417），缺口里 `StreamChevronsBox` 站三枚 chevron：每枚 2.6×6.4、间距 5、描边 1.35 圆头；
  墨 faint=workflow-trace / strong=workflow-trace-strong / march=warning 且三枚沿流向依次亮
  （`wf-stream-flow 1.2s`、相隔 0.15s，styles.css L1418-1431）。触到开着的留白的段 `border-dashed`。
- 尾巴留白（L234-241）：`wf-tail-stub` 40px 虚线残段 + `mask-image: linear-gradient(90deg,#000,transparent)` 向右淡出。
- SVG 行进光 MarchLight（WorkflowMarchLight.tsx L21-47）：`.wf-lit` 路径 `stroke-width 1.5` 圆头，
  `userSpaceOnUse` 线性渐变 stop0 警示色 opacity 0 → stop 0.8 满色——光在灯那头最亮、向控制流来向淡去，**不动**。
- 边檐与滚动条（styles.css L1782-1821）：原生滚动条隐藏（`.wf-scroller`）；折到檐上的灯 hover/focus
  `scale(1.25)`；自绘滚动条 `opacity 0→1`（hover 时间线或滚动/拖拽中），高度 2px、hover/拖拽 4px；
  轨道带在檐旁 40px 渐隐，药丸只在视口真边界渐隐；镜头把运行站滚居中，草稿期贴右缘跟随笔，飞行中目标站不折。

### 3.5 子代理药丸 WorkflowAgentPill（WorkflowAgentPill.tsx L104-218）

```
Root = span|button  class 基底: "wf-pill wf-agent-pill wf-arrive flex rounded-full min-w-0 items-center text-ui-sm"
  md(卡上/站下): h-8 gap-2 bg-surface pl-2 pr-2.5        avatar size-4
  row(侧栏名单): h-6 gap-1.5 pl-1 pr-1.5                 avatar size-3.5
├─ LaneGlyph：agent 车道 = WorkflowAgentFace 瓦片脸；workspace=TerminalIcon / 未解析=CircleHelpIcon
│   class: shrink-0 + tinted ? "text-[var(--wf-avatar)]" : "text-foreground-subtle"
├─ 名字 .wf-pill-name.min-w-0.flex-1.truncate  settled→text-foreground，否则 text-foreground-subtle
├─ children（侧栏行的计数与模型名）
└─ 尾槽 .wf-pill-tail.grid.size-3.5.place-items-center（状态标记与 ↗ 同格叠放）
   ├─ PillStatusMark：running=LoaderCircle spin / done=CircleCheck / failed=CircleX，size-3.5
   │   running、done 用 text-foreground-subtle（正常加载不读作警告），failed 用 text-destructive
   └─ ↗ .wf-pill-go size-3.5（初始 opacity:0 scale(0.6)，悬停进场；wf-pill-go-rest 常驻给门行）
```

交互态（styles.css L1466-1556）：`.wf-pill-open:hover/:focus-visible` → 底色 `surface-hover` +
`inset 0 0 0 1px color-mix(--wf-avatar 35%)` 内描边；头像 `scale(1.08)` + 底色 mix 30%；名字转
`text-foreground`；↗ 进场。`:active` 整枚 `scale(0.985)`。代理胶囊 `wf-agent-pill:hover` 强制
`box-shadow:none`（只用底色反馈，不让彩色描边抢状态层级）。

瓦片脸 WorkflowAgentFace（WorkflowAgentFace.tsx）：SVG `viewBox 0 0 20 20`，机身 rect 20×20 `rx 7`
填 `--wf-face-body`，眼白 `--wf-face-eye: #ffffff`；六种表情 pill/happy/sleepy/focused/sad/confused
按 status 映射；动作 blink(230ms×2)/morph/hop/float/shake/dots-wave 只动眼不动机身；身份色见 五.2。

「还有 n 个」门行 WorkflowMoreRow（WorkflowMoreRow.tsx L61-140）：与药丸同高 32px、同底色（卡上
`bg-surface`、侧栏开门态 `bg-surface-hover`）、`rounded-full pl-2 pr-2.5`；三张脸一叠
（`wf-more-deck` 相邻 `margin-left:-5px`，hover 扇开到 -2px；每张 `wf-more-face border-radius:35% +
box-shadow 0 0 0 1.5px var(--color-background)`）；藏失败时 `✕ n`（`text-destructive font-mono`）；
卡上尾槽 ↗ 常驻（`wf-pill-go-rest`），侧栏门行换 ChevronDown 开时 rotate-180。

### 3.6 完成卡 WorkflowCompletionCard（WorkflowCompletionCard.tsx L204-268）

```
section.wf-motion.wf-arrive.@container/wf-card.flex.w-full.min-w-0.flex-col.gap-2.5
  .rounded-xl.border.border-border/70.bg-card/70.px-3.5.pb-3.pt-1.5
├─ WorkflowCardHeader（kind=completed + WorkflowRunStatus completed + headerLeading/headerTrailing 槽）
├─ WorkflowCompletionArtifacts（交付物行 + 产物索引，收据式细线分隔）
└─ 四格数字 grid.grid-cols-4.gap-x-3.border-t.border-[var(--color-workflow-rule)].pt-2.5
   └─ Figure：值 .font-mono.text-ui-lg.tabular-nums.font-medium.text-foreground（单位 text-ui-sm
      font-normal subtle）；拿不到写「—」text-foreground-subtlest；标签 .truncate.text-ui-sm.subtle
```

数字 640ms 内 easeOutCubic 从 0 翻起（首帧即终值，reduced-motion 直接终值）；延迟 =
`PILL_STAGGER_MS × (产物格数 + 1)` 起排、每格再错 30ms。tokens 紧凑写法：<1k 原值、k 一位小数、M 两位小数。

---

## 四、运行详情侧栏（app-shell）

### 4.1 面板骨架（WorkflowRunSidePane.tsx L342-436）

`div.flex.h-full.min-h-0.flex-col.bg-background`（data-workflow-run-id / -status）→
状态头（含保存槽）→ Provenance（中枢启动来龙去脉）→ 结果区 → 阶段脊线（图不可得时一句
「图不可用」`px-4 py-3 text-ui-xs text-foreground-subtle`）→ 产物区（无则整区缺席）。

### 4.2 状态头（WorkflowRunSidePaneSections.tsx L141-371）

```
div.shrink-0.border-b.border-border.px-4.py-3
├─ 行1 flex.items-center.gap-2：run名 .min-w-0.flex-1.truncate.font-mono.text-ui-base.font-medium
│  + Configure( outline sm + SlidersHorizontal size-3.5 ) + Resume( outline sm + RotateCcw size-3.5 )
│  + 「保存/再次运行」saveVerb + Stop( outline sm + Square size-3.5 fill-current )
├─ 行2 .mt-1.5.flex.min-w-0.flex-wrap.items-center.gap-2
│  ├─ WorkflowRunStatus（灯 size-2 + 状态词 text-ui-sm + 原因词「· …」+「· 可恢复」，原因/resumable
│  │   均 text-ui-sm text-foreground-subtlest）
│  ├─ RunHolesWaitingChip / 已保存芯片
│  └─ 并发芯片 .rounded-xs.border.border-warning/60.px-1.5.py-0.5.font-mono.text-ui-xs.text-warning
│      （「最大并发数 N · 冷却 hh:mm:ss」；与状态徽标同形但用活动色——运行时调节不是故障）
├─ 被拒提示 .mt-1.5.text-ui-xs.text-warning（warning 非 destructive：什么都没发生）；诊断 pre mono max-h-24
├─ lineage 行 .mt-1.5.text-ui-xs.text-foreground-subtlest：「调整自/已被替代」+ mono 值 truncate；
│  supersededBy 可点时是按钮 hover:text-foreground + ArrowUpRight size-3
├─ 摘要行 .mt-2.flex-wrap.gap-x-2.text-ui-sm.text-foreground-subtle：ListIcon size-3.5 + 各段 tabular-nums
│  以「·」分隔；第一段=子代理模型，可配置时是按钮 underline-offset-2 hover:underline（开配置弹层）
│  退化为用量行：标签 text-ui-xs subtle + 值 .font-mono.text-ui-xs.tabular-nums.text-foreground
└─ WorkflowTruncatedNotice .mt-1.5
```

终态区（L374-462）：absent 提示 / completed 结果（`pre max-h-40 mono text-ui-xs` 预览）/
errored+stopped 错误面板（`border-b border-destructive/40`，标题 `text-ui-xs font-medium text-destructive`
+ stopped 时追加原因词，正文 `text-ui-base text-foreground` 按人话排版不用 mono）。

### 4.3 脊线阶段清单（WorkflowRunPhaseList.tsx + workflowRunSpine.ts + WorkflowRunSpineParts.tsx）

布局参数：主轨 x=`SPINE_TRACK_X 21`（中心），接头行高 `SPINE_JOINT_PX 16`；轨距
`widest-1 ≤ 4 ? 12 : 8`；文字列整根共用 `paddingLeft: 39 + gutter`（gutter = pitch×(T−1)）——
轨道与文字不共列。轨道段拆节画：`above`（top:0 h-3）/ `below`（bottom:0 top-6）/ `full`（inset-y-0）；
普通墨 `w-px bg-foreground-subtlest`，行进墨 `w-[1.5px] + wf-spine-march` 按 `data-rail-position`
选渐变（styles.css L1436-1452）：below 透明→70% warning、above 70%→满色（一直亮进灯里）、full 平 70%。
流轨两半在节边界让出 `SPINE_STREAM_GAP_PX 7` 缺口，站两枚朝下 chevron（z-index 1）。
开口接头（无前驱的分叉/无汇合的汇合）主轨向行外伸出 `SPINE_STUB_PX 4` 收圆头——一个根/一个汇点；
接头 SVG 曲线底墨 `stroke: var(--color-foreground-subtlest) strokeWidth 1` 圆头，march 再叠 MarchLight。

```
根 .wf-motion.relative.flex-1.overflow-auto.pb-3.pt-2.5
├─ FillHeadingRow…（补全标题行）
├─ section.relative [data-phase-id/status/open/track/landed]
│  ├─ SpinePieces（竖轨两截/full + chevron）
│  ├─ 节头 button.wf-station-open.flex.h-9.w-full.items-center.gap-2.pl-[39px].pr-3
│  │   hover:bg-surface focus-visible:ring-2；落点时 wf-landed（亮 400ms 退 800ms，一次）+ key 重挂
│  │   ├─ SpineLamp：absolute left-4 top-[13px] size-2.5 rounded-full + STATUS_DOT；pending 加 bg-background
│  │   ├─ 名 .min-w-0.flex-1.truncate.text-ui-base（pending→subtle，否则 font-medium foreground）
│  │   └─ 右簇 .font-mono.text-ui-xs.tabular-nums.text-foreground-subtlest.gap-2.5：
│  │       折叠时 AvatarCluster（≤3 枚 LaneGlyph size-4 + 「+n」ml-1）或 RosterMeter mini；分数 a/b；
│  │       Rounds（Repeat2 size-[11px] gap-[3px]）；ChevronRight size-3.5 expanded→rotate-90
│  └─ 节体（展开）.wf-unfold.flex.flex-col.gap-1.5.pb-3.pl-[39px].pr-3.pt-0.5
│     ├─ 留白等待体 / 药丸列（每行外层 .flex.min-w-0.flex-col 使药丸拉满列宽）
│     ├─ 问题行 WorkflowRunQuestionRow className="ml-[26px]" 挂提问者下再退一步
│     └─ 名册：钉 5 枚 + 门行（door 开合）+ WorkflowRoll 两列 row 药丸；asking 行插 ? CircleHelp
│         size-3 text-warning；名单末尾淡字交代界上列不出的差额
└─ 孤儿问题块 .pl-[39px].pr-3.pt-2（标题 text-ui-xs font-medium subtle + 问题行）
```

交互：正在运行的站与等待补全的站**自动展开**（带内多个同时开）；折叠只收节体；落点 =
展开 + 开门 + scrollIntoView + `wf-landed` 亮一下（`LANDING_MS 1200`，键含 openedAt 可重落）；
等待时长 30s tick 自走（等答案的 run 不发事件）。

### 4.4 升级问题行（WorkflowRunQuestionRow.tsx L33-72）

`mt-1 flex items-start gap-2 rounded-lg bg-[var(--color-interaction-confirmation-surface)]
px-2 py-1.5 text-ui-sm text-[var(--color-interaction-confirmation-foreground)]`；
图标 `MessageCircleQuestion size-3.5 mt-0.5`；提问者 `font-mono text-ui-xs font-medium mr-2`；
正文 pre-wrap break-words；context `text-ui-xs opacity-80`；右侧 `font-mono text-ui-xs`：等待时长 +
`qid opacity-70`。等待时长**刻意不**用 warning（长等待是设计内状态，不是告警）。

### 4.5 产物区（WorkflowRunArtifactsSection.tsx L91-188）

```
section.wf-motion.shrink-0.border-t.border-border/60 [data-artifacts-open]
├─ 节头 button.flex.h-9.w-full.items-center.gap-2.px-3 hover:bg-surface
│   标题 text-ui-base font-medium foreground + 件数 .font-mono.text-ui-xs.tabular-nums.subtlest
│   （收起时也在场）+ 收起时「· 交付物名」text-ui-sm subtle + ChevronRight ml-auto size-3.5 subtlest
└─ 节体 .wf-unfold.max-h-[50vh].overflow-auto.px-3.pb-3.pt-0.5  @container/wf-artifacts
   ├─ 有交付物：WorkflowArtifactRow（预览框 160×100，容器 <380px 收 136×85）+ 细线下索引
   │   WorkflowArtifactIndex columns="one"（单列、不封顶；卡上六行封顶）
   └─ 无交付物：画廊 grid-cols-[repeat(auto-fill,minmax(130px,180px))].gap-3，一件一张瓦片
```

默认展开（与阶段节相反）；失败/取消的 run 照常渲染。产物瓦片悬停语法与药丸一致（styles.css
L1561-1633）：框边抬 border-hover、kind 瓦片转前景、尾槽 ↗ 顶替版本号、`:active` 框 scale(0.99)、
焦点环画在容器（`:has()` 读兄弟按钮状态）。

---

## 五、状态语义专节

### 5.1 状态灯五形五色（run-status-presentation.ts L12-50）

```ts
STATUS_DOT = {
  done:     "bg-success",                                            // 绿实点
  failed:   "bg-destructive ring-2 ring-destructive/30",             // 红实点 + 30% 外环
  pending:  "border-[1.5px] border-foreground-subtlest bg-transparent", // 空心环
  running:  "animate-pulse bg-warning motion-reduce:animate-none",   // 琥珀实点 + 脉冲
};
RUN_STATUS_DOT = { pending: 空心, running: 琥珀, completed: 绿, errored: 红, stopped: 空心(同 pending) };
RUN_STATUS_TEXT = { pending: subtle, running: text-warning, completed: text-success,
                    errored: text-destructive, stopped: text-foreground-subtle };
```

- 站灯/卡灯再叠形：running 加 `.wf-lamp-running`——常亮 `0 0 0 3px color-mix(warning 20%)` 光晕 +
  1.6s 心跳（scale 1.12 + 环涨到 8px 淡尽，styles.css L1660-1664, L2130-2149）；脊线灯与卡灯同类同拍。
- 留白灯是第五形：1.5px 虚线空心；waiting 时描边换 warning + 3px 常亮光晕**不搏动**
  （styles.css L1668-1670；WorkflowTimelineLedge.tsx L38-44）——那里没有东西在跑。
- 站灯悬停光环（styles.css L1720-1728）：pending→foreground 10%、done→success 18%、failed→destructive 18%。
- **灯 + 词永远成对**（不变式，WorkflowCardChrome.tsx L56-57）：状态词按值换词播 `wf-swap`（key 重挂）；
  stopped 追加原因词（user/model/provider/interrupted/superseded，L56-64）、resumable 追加「可恢复」。
- 药丸状态标记（WorkflowAgentPill.tsx L62-94）：running/done 用中性 `text-foreground-subtle`
  （正常加载不被读成警告），仅 failed 用 `text-destructive`——图内微观状态与 run 级语义色分两档。

### 5.2 九色板（WorkflowAgentFace.tsx L18-28）

```ts
FACE_COLORS = ["#54B9A6","#F19D38","#6464EF","#885CF5","#3C82F6","#ED712E","#EB4699","#5BC67A","#EA4045"]
```

代理身份色，按 `avatarIndex` 取（第十个起循环 `((i % 9) + 9) % 9`）；无编号退回名字散列
（31 进制 mod 360 再 mod 9，L31-35）。用途：药丸头像机身、药丸悬停内描边（35% mix）与头像底
（30% mix）经 `--wf-avatar` 共享。身份色不随表情/状态改变；工作区车道无身份、不染色。

### 5.3 活动色 vs 强调色的判断（run-status-presentation.ts L8-11）

running 用 **warning（活动色）** 而不是 primary：primary 跨主题反色（亮色下近黑 neutral-950），
读作「强调」而非「在动」；活动色让给真正在动的东西——灯、行进光、流轨 chevron、转圈。
因此运行中的词/灯/并发芯片/「运行中」徽标统一琥珀，主按钮（强调）保持黑白体系。

### 5.4 stopped 中性色的理由（run-status-presentation.ts L30-41）

`stopped` 走中性色（空心环 + subtle 词）而不是 destructive：停下（用户取消、进程亡故、模型侧错误）
是**可恢复的状态**，不是脚本故障；只有 `errored` 才配红色。同理错误面板对 stopped 只列原因词不染红底
（WorkflowRunSidePaneSections.tsx L420-460）；「停止」提示主动说「停止后可以随时恢复，已完成的步骤会保留」。
被修订替代（superseded）的 run：灯仍是 stopped 中性空心环，差别在种类词「已被替代」+ 指向后继的链接
（L60-64；WorkflowCardChrome.tsx L40-54）。编译反馈行同理：open=warning 空心、settled=pending，绝不 destructive（L23-27）。

---

## 六、工作流中枢与启动对话框（settings/saved-workflows）

### 6.1 中枢列表页（SavedWorkflowsSection.tsx L263-360）

- 页头 `mt-8 flex items-center justify-between`：左 `h2 text-ui-base font-medium text-foreground-subtle`
  （组标题 + 总数 subtlest）；右侧「工作流设置」ghost lg（含当前模式词）+ 刷新 outline icon（size-7）。
- 组序：全局组恒置顶，其下按已打开项目分组；首屏 `h-40` 居中 Spinner。
- 空态卡（L316-340）：`mt-8 h-[226px] w-full rounded-2xl border border-card-border bg-background`，
  内部标题/提示 `text-ui-base text-foreground-subtlest`（提示 max-w 420px）+ 「通过对话创建」default lg 钮。
- 工作流卡 SavedWorkflowCard（SavedWorkflowCard.tsx L125-241）：

```
div.group.relative.flex.h-full.cursor-pointer.gap-3.overflow-hidden.rounded-xl
  .border.border-card-border.bg-background.p-3  hover:bg-hover focus ring(input-border-focused)
├─ 主列 flex-col.gap-3：名字 truncate pr-28 text-ui-base font-medium leading-5
│  描述 line-clamp-2 h-10 leading-5 text-foreground-subtle
│  底栏 mt-auto h-6：上次运行徽标 ←→ 实参芯片（≤3 枚 rounded-xs border px-1.5 py-0.5
│    font-mono text-ui-xs subtlest +「+N」）
└─ 右上 absolute right-3 top-3：「运行」outline sm（AutomationRunNowIcon size-3）+ ⋯ ghost icon-sm
   菜单：打开/修订/复制路径/提升为全局(或移到项目)/删除（删除项 text-destructive focus:text-destructive）
```

上次运行徽标四态（L33-86，沿用定时任务卡形状：20px 图标槽 size-5 + rounded-lg）：
completed `bg-success/10 text-success` CircleCheck / errored `text-destructive` TriangleAlert /
running `bg-warning/10 text-warning` Loader2 spin / stopped `text-foreground-subtle` Ban /
never 纯字 subtlest；图标 `strokeWidth 1.33`。

### 6.2 启动对话框 SavedWorkflowLaunchDialog（SavedWorkflowLaunchDialog.tsx L161-326）

```
DialogContent sm:max-w-[480px]
├─ DialogTitle flex.items-center.gap-2：Workflow size-4 subtle + 名字 truncate font-mono
│  + 作用域徽标 .rounded-sm.border.border-border.px-1.5.py-0.5.text-ui-xs.subtlest
│  说明 text-ui-sm text-foreground-subtle
├─ form.flex.flex-col.gap-4
│  ├─ 「运行于」Select（仅全局工作流）：标签 text-ui-base font-medium；无本地项目时提示并禁用提交
│  ├─ 实参字段 × n（flex-col gap-1.5）
│  │  ├─ 行头：字段名 label.font-mono.text-ui-base.font-medium +「必填」徽标（同作用域徽标样式）
│  │  │   右侧 boolean 型放 Switch；描述 text-ui-sm subtle
│  │  ├─ 控件：json→Textarea min-h-20 font-mono；number/text→Input font-mono；校验失败 border-destructive
│  │  └─ 字段错误 text-ui-sm text-destructive
│  ├─ 说明条 .rounded-lg.bg-surface.px-3.py-2.5.text-ui-base.subtle + Info size-4
│  │   「将立即在 {project} 的新会话中运行」
│  ├─ 行内错误区 .rounded-lg.border.border-destructive/40.px-3.py-2.5（标题 destructive + mono 详情）
│  └─ DialogFooter：取消 outline lg ｜ 运行 default lg（AutomationRunNowIcon size-4；pending 时
│      Spinner size-4 + 整窗按钮禁用防重复提交）
```

### 6.3 启动交互流 useSavedWorkflowLauncher（useSavedWorkflowLauncher.ts）

`launch = createSession(空会话) → startSavedWorkflow{name,scope,args} → accepted 则 onNavigate 切新会话`；
被拒/抛错则 `deleteSession` 收回空会话并回结构化错误（reason 词表/unsupported/generic → i18n key）。
`pendingRef` 同帧防重入；「失败在会话存在之前」：createSession 被拒不发 start、不留会话。
无实参的项目档**不弹窗**直接启动；「再次运行」预填该 run 上次的实参（声明外的键忽略）。

---

## 七、运行目录页（WorkflowRunDirectorySidePane.tsx）

```
div.flex.size-full.min-h-0.flex-col.bg-background
├─ 页头 .border-b.border-border.px-4.py-3：h2 text-ui-base font-semibold text-foreground
└─ 列表 .min-h-0.flex-1.overflow-y-auto.px-2.py-3
   ├─ section「运行中」：h3 .px-3.pb-1.5.text-ui-sm.font-medium.text-foreground-subtlest（标题 · 计数）
   ├─ section「已结束」.mt-5：同头
   ├─ 行 button（L73-111）.flex.w-full.min-w-0.items-start.gap-3.rounded-lg.px-3.py-2.5
   │   hover:bg-surface-hover focus ring(input-border-focused)
   │   ├─ 灯 .mt-2.size-1.5.rounded-full + RUN_STATUS_DOT（圆点只是冗余通道，状态永远有词）
   │   ├─ 主列：名 .block.truncate.font-medium.text-foreground
   │   │        次行 .mt-0.5.flex-wrap.gap-x-2.text-ui-sm：状态词(RUN_STATUS_TEXT 着色)
   │   │        + stopped 原因词/errored failureCode（· 前缀，text-foreground-subtle）
   │   ├─ 相对时间 .shrink-0.text-ui-sm.text-foreground-subtlest
   │   └─ ChevronRight size-4 shrink-0 subtlest
   ├─ 空态/不可用 .px-3.py-3.text-ui-base.text-foreground-subtlest（不写报错语气）
   └─ 截断说明 .px-3.pt-4.text-ui-sm.text-foreground-subtlest（一页取满必须明写）
```

---

## 附：对齐实施要点

1. 动画四时长一曲线：120/160/200/320ms + `cubic-bezier(0.22,0.61,0.36,1)`，灯心跳 1.6s；只动
   opacity/transform/background-color，从不动布局属性；`prefers-reduced-motion` 全量降级。
2. 悬停语法统一「三件事」：底色抬一级、身份色内描边（或名字转前景）、尾槽 ↗ 顶替状态标记；
   门行（还有 n 个）的 ↗ 不等悬停就在。
3. 源码遗留注意：`@keyframes wf-land` 在 styles.css 定义了两次（L1842 背景色版、L2119 缩放版），
   后者按 CSS 级联胜出；`.wf-landed`（落点亮一下）预期的是 L1842 版行为，移植时需裁决为两个名字。
4. 所有状态必须「灯 + 词」双通道；颜色永不作为唯一信息载体。
