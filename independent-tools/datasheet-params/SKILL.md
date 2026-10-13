---
name: datasheet-params
description: >
  从器件数据手册（IC datasheet）提取"结构化、可信、可溯源"的器件参数，把中间解析产物 merged.json
  （含 full_markdown + layout blocks）加工为 `*_ai_params.yaml`：每条参数都带 Page / layout_type / Block 证据地址。
  当用户提到"提取器件参数"、"datasheet 参数"、"数据手册参数"、"把数据手册转成 yaml"、
  "merged.json 参数"、"ai_params.yaml"、"器件规格/电特性表结构化"、"芯片参数溯源"、
  "给 PDF 建参数证据"、"MOSFET/MOS/射频合成器/PLL/ADC 的规格参数"，或训练评测里要求
  "不借助 MCP 复现参数提取"、"和 *_ai_params.yaml 基准对齐"时使用。输入可以是 merged.json，
  也可以直接给数据手册 PDF（先解析出合并 JSON）。注意：简单单步"读某个 PDF 摘要"不需要此 Skill。
---

# Datasheet 器件参数提取

## 调用契约与定位

**输入**：`merged.json`（首选，PDF 布局解析产物）或原始数据手册 PDF（需先转成 merged.json）。
**输出**：`<器件型号>_ai_params.yaml`，UTF-8，YAML 块式缩进。
**价值**：参数不是文本摘要，而是可寻址的事实——每个参数/分组必须有 `source: 'Page: N, layout_type: <type>, Block: <id>'`，
`block_id` 必须来自真实数据块，绝不能是数组下标 +1，也绝不能编造页码。

整体链路：`merged.json(理解+寻址) → 按 Schema 匹配读取 → 类别收敛 → 验证(来源/结构) → 交付 yaml`。
`full_markdown` 只用于通读发现；参数落到 layout 里的精确证据用 `layout[]`。

## 前置条件

- 有可读取的输入（merged.json 或 PDF）。PDF 解析失败/无法安装解析依赖时，先向用户要 merged.json，不要硬编。
- 输出目录可写；同名旧 yaml 需用户确认后再覆盖。
- 本 Skill 使用 python 辅助脚本，需 python ≥3.8；如缺 `yaml` 库，运行 `pip install pyyaml` 后再验证。

## 文件结构

| 文件 | 用途 | 何时读 |
|------|------|--------|
| `SKILL.md` | 本流程 | 始终 |
| `references/merged-json-schema.md` | merged.json 字段契约与 PDF 解析方法 | 输入是 PDF 或校验 block 字段时 |
| `references/ai-params-schema.md` | 输出分类/字段/优先级、类别→关键词映射、调度阈值、状态机 | 每次提取前必读 |
| `references/sample-output.yaml` | 完整成品样例（LMX2571，17 大类） | 组织输出结构/不确定字段时 |
| `scripts/dump_layout.py` | 把 merged.json 摊平成按页可读文本（表格转 `|` 行），规避 JSON 长行截断 | 读源前必跑 |
| `scripts/validate_output.py` | 结构 + 来源存在性校验，可选 `--gold` 深对比 | 每轮验证必跑 |

## 铁律速查

| 规则 | 内容 | 违反后果 |
|------|------|---------|
| R0 | 值只从文档读，绝不计算/推导/脑补缺失参数；不改写数值单位 | 产生假数据，交付失败 |
| R1 | 每个参数/分组都必须有真实存在的 `source: 'Page: N, layout_type: T, Block: M'` | validate 来源检查不过 |
| R2 | 多行/多条件共享符号时用 `variants`（条件+min/typ/max），不丢测试条件与脚注号 | 变体数据错位、语义丢失 |
| R3 | 跨页续表合并进同一类别/参数；同一类别全部子表留在同一批处理 | 断点重复或漏参数 |
| R4 | 单元、MIN/TYP/MAX 列对齐以表头为准；空单元格按"无此界"处理，不得填空造值 | 数值串列 |
| R5 | 先结构发现→定点读取→再写 yaml；不凭记忆写 Page/Block | 溯源失真，验证失败 |
| R6 | 验证门禁：通过 ≥95%、80–94% 修复后复验、<80% 判失败向用户如实报告 | 假通过交付错误参数 |

## 实战反例

| Agent 可能产生的想法 | 实际现实 | 违反规则 | 实际后果 |
|--------------------|---------|:------:|---------|
| "两个表数值一样，只留一个省事" | 续表可能含主表没有的行 | R3 | 漏参数 |
| "这个符号刚才见过，直接沿用上次 Page/Block" | 不同 block 数值不同 | R5 | 溯源错误 |
| "VIH 的 max 填 VIO"（当表格里是 VIO 引用） | 那是"上限=VIO"，应记 `max_ref` | R0/R4 | 单位错 |
| "从上下文补齐 KPD 的 min/typ/max 位置" | 行列错位全靠表头语义 | R4 | 串列 |
| "README 说 2500 卷带，直接抄到两个型号" | 同一器件不同订购码 qty 不同 | R0 | 假事实 |
| "先 dump 一次，后续凭全文 markdown 写 source" | source 必须对应真实 block | R5/R1 | 校验失败 |

## 工作流

### 步骤 0：输入获取（PDF 或 merged.json）
1. 输入已是 merged.json → 跳到步骤 1。
2. 输入是 PDF → 见 `references/merged-json-schema.md` 的解析方法生成 conformant merged.json；
   解析质量差（扫描页、表格错位）或依赖不可用 → 明确告诉用户并索要 merged.json。
- [ ] 输入确定且可读

### 步骤 1：结构发现
1. 跑 `python "<本 Skill 目录>/scripts/dump_layout.py" <merged.json> [输出 txt]` 生成按页摊平文本
   （表格已转管道行），分段通读，规避 JSON 2000 字符长行截断。
2. 建立"页→block、heading 锚点(sec 号)、表格块"索引；把每类目标参数的候选 block 记下来（真实 block_id）。
3. 通读 `full_markdown`（用于发现与交叉验证，不用于写 source）。
- [ ] 已掌握各目标类别所在页与候选 block

### 步骤 2：Schema 与类别定位
1. 读 `references/ai-params-schema.md`，按 `类别→关键词/锚点` 映射表定位 17 大类。
2. 器件类型不同时（MOSFET/ADC/混频器…）以样例结构为基准、按该文档真实章节组织类别，
   参数一律用 `symbol/name/min/typ/max/unit/condition/variants/max_ref + source` 字段。
3. 标记 P0（电特性/极限/推荐/热阻等硬参数，缺失即阻断）与 P1/P2（说明/应用等叙述类）。
- [ ] 类别与优先级已定，且全部来自真实结构

### 步骤 3：调度（按 merged.json 大小）
| merged.json 大小 | 调度 |
|---|---|
| < 30 KB | 单 Agent 单轮顺序 |
| 30–100 KB | 顺序 3–4 批，一批一类别族 |
| ≥ 100 KB | 3 子 Agent 并发，按**类别亲和**切（electrical/DC+AC+limits 一起；thermal/ratings/package 一起；applications/theory/notes 一起），各自写独立 temp yaml |

同一类别的全部子表必须留在同一批；写入隔离（temp 目录），不共享文件。
- [ ] 批次划分不与业务类别交叉

### 步骤 4：分类别提取
**表格类（电特性/极限/推荐/热阻/引脚/时序/订购）**：
1. 表格长行转结构化：先剥 HTML 标签得到单元格，再按表头 `PARAMETER|TEST CONDITIONS|MIN|TYP|MAX|UNIT`
   语义对齐；留意 rowspan/colspan 折叠导致的"参数块"纵向合并。
2. 同符号多条件→`variants`（参考样例 electrical_characteristics.current_consumption.ICC 或 pll.KPD 写法）。
3. 引用型上限（如 `VIO`、`VCC+0.3`）记 `max_ref`，不填 unit 数值。
4. 条件文本保留脚注号（如 `Configuration A(1)`），脚注解释自然留在条件里可读化。
5. unit 从末列取，符号去残留 LaTeX（`$V_{CC}$`→`VCC` 等），保留 Ω/μ/±/Δ/° 等量纲符号。
6. 数值逐字抄录，仅去除空格/换行排版；含义无损时把连写（如 `fOUT=480MHzSE OSCin`）拆成可读条件。

**文本类（特性/应用/概述）**：逐条列出原文要点，做最小清洗（补全括号、去编号噪声），不新增原文没有的能力。

**叙述类（theory_of_operation / applications_information 等）**：用简洁摘要归纳该章节 prose；工程叙事可用中文，
但符号/公式/寄存器名保留原文；分 circuit 列组件与公式，公式值必须与文档一致。

**订购/封装**：优先"Orderable Device/PACKAGING INFORMATION"表（页尾），逐行逐列；同一表格里多个型号展开成
`family_info.models`，并单独挑主型号填 `ordering_information`。

**来源规则**：某分组内多条参数同源同表 → 组级写一次 source；跨表/跨页不同 → 参数或小节级各自写 source。

- [ ] 已产出结构化 yaml 草稿（可含 temp 分段）

### 步骤 5：合并
1. 无并发：单文件顺序写。有并发：把各子 Agent 独立 temp yaml 按类别合并为最终文件，合并后**不得**再被 merge 覆盖。
2. 文件命名 `{器件型号}_ai_params.yaml`，与输入同目录（用户另指定则服从）。
- [ ] 合并完成，无类别重叠/遗漏

### 步骤 6：验证与门禁
运行 `python "<本 Skill 目录>/scripts/validate_output.py" <merged.json> <输出的 yaml> [--gold <基准 yaml>]`
- 结构校验（必过）：yaml 可解析；必要顶层/分组带 `source`；`source` 格式与存在性（页内确有该 layout_type 的真实 block）；
  pin 元素字段齐全。
- 有 `--gold` 时做深对比并给出差异路径清单；把它当作"基准对齐"门禁（训练/评测模式）。
- 覆盖率门禁：R6 表。
- [ ] 无 FAIL；覆盖率达标或已如实上报

### 步骤 7：定点修复（最多三轮）
1. 只重跑失败类别（P0 优先），不看全量重来；修复后重新 `validate`。
2. 每轮记录到 `progress.json` / `error_log.json`（批号、类别、错误），支持中断续跑。
3. 修复不覆盖已 merge 结果；第三轮后仍失败 → 按 R6 判失败，向用户如实汇报缺口与原因。
- [ ] 修复闭环或显式 FAILED 上报

### 步骤 8：交付
- 给用户文件路径、参数总数、覆盖率与验证结果；把可信/缺口分开说明。
- 展示按大类的汇总表（类别 / 条目数 / 状态），数值类问题突出标注。

## 错误处理

| 环节 | 失败条件 | 处理方式 |
|------|---------|---------|
| 步骤 0 | 无法解析 PDF / 无依赖 | 请求 merged.json；不硬造 layout |
| 步骤 1 | JSON 超大读不全 | 用 dump_layout.py 摊平后分段读 |
| 步骤 4 | 表格行列严重错位 | 以表头+相邻段落双重核对；仍存疑按条件拆分 variants 并在 error_log 记录 |
| 步骤 6 | yaml 语法/来源 FAIL | 进入步骤 7 定点修复 |
| 步骤 6 | 覆盖率 <80% | 判失败，如实报告，不假通过 |

## 输出质量指标

| 指标 | 目标值 | 检查方法 |
|------|--------|---------|
| 结构/source 校验 | 0 FAIL | validate_output.py |
| 覆盖率（对 gold 的深对比一致项） | ≥95% 通过 / 80–94% 修复 / <80% 失败 | validate_output.py --gold |
| 数值与源一致 | 逐字一致，无重算 | R0 + 抽样复核 |
| 修复轮次 | ≤3 | error_log.json |

## 参考文档索引

| 文档 | 何时读 |
|------|--------|
| `references/merged-json-schema.md` | PDF 输入或核对 merged.json 字段时 |
| `references/ai-params-schema.md` | 每次提取前（类别/字段/优先级/调度/状态） |
| `references/sample-output.yaml` | 组织结构与疑难字段写法 |
| `scripts/dump_layout.py` / `validate_output.py` | 步骤 1 / 步骤 6 |
