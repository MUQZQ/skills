# ai_params Schema 与类别定位（输出契约）

> 每次提取前通读。结构基准见同目录 `sample-output.yaml`（LMX2571 完整成品，17 大类）。

## 输出文件与顶层类别

输出：`{器件型号}_ai_params.yaml`，UTF-8，块式缩进。顶层类别（TI RF 合成器示例；其他器件类型按本文
"类别定位映射"换成该文档真实章节组织）：

| 顶层类别 | 内容 | 优先级 | 结构要点 |
|---------|------|:---:|---------|
| `device_info` | 型号/厂商/器件类型/系列 | P0 | device_name, manufacturer, device_type, device_family |
| `basic_info` | 一句话概述 + 要点 | P1 | description, highlights[] |
| `features` | 特性清单 | P1 | items[]（逐条原文要点） |
| `electrical_characteristics` | 电特性全表，按表内小标题再分组 | P0 | 组如 current_consumption/oscin_reference/crystal_reference/mult/pll/pll_noise/vco/rf_output/fsk_modulation/digital_interface；每组 source |
| `operating_current` | 电流汇总 | P0 | ICC/IPLL/ICCPD + variants |
| `operating_temperature_range` | 环境/结温 | P0 | TA(T_A) min/max、TJ max |
| `absolute_maximum_ratings` | 绝对最大额定 | P0 | 每行 symbol/name + min 或 max 或 max_ref + unit |
| `thermal_resistance` | 热阻 | P0 | RθJA/ψJT… symbol/name/typ/unit |
| `pin_configuration` | 引脚表 | P0 | pins[]: num/name/type/desc；source 在 pin_configuration |
| `package_info` | 封装 | P0 | type/code/leads |
| `ordering_information` | 主订购型号 | P0 | model/package/pins/package_qty/status/eco_plan/op_temp… |
| `family_info` | 订购表全型号展开 | P1 | models[] 逐行 |
| `device_specific` | 时序等 | P0/P1 | timing 等：min/unit/condition |
| `applications` | 应用清单 | P1 | items[] |
| `applications_information` | 应用章节要点 | P2 | circuits[]: name/components[]/formulas[] |
| `theory_of_operation` | 工作原理摘要 | P2 | principle + architecture |
| `additional_info` | 商标等杂项 | P2 | trademark 等 |

## 类别定位映射（关键词/锚点 → 类别）

三层收敛，不静默丢弃；跨厂商结果未预跑前不要标记为 Observed：
- L1 类别关键词精确/模糊匹配（电特性/absolute maximum/recommended operating/thermal/electrical characteristics/timing/pin…）
- L2 标题核心词 ↔ 注册类别（如 6.5 Electrical Characteristics ↔ electrical_characteristics）
- L3 相邻结构受限推断（续表标题"Electrical Characteristics (continued)"归属同一类别；无标题小表用上方段落定位）
- 三层都失败 → 写 error_log，不放空也不猜类别

定位手法：
- 用 dump 文本里的 `## N.N` 小节锚点（section_number）抓边界；
- 用"小节首行条件句 + 表内首个跨列分类单元格"给长 EC 表分组（如 CURRENT CONSUMPTION / OSCIN REFERENCE INPUT…）。

## 参数字段约定

单条参数允许字段：
`symbol`（源符号）、`name`（名称）、`unit`、`condition`（测试条件，可含脚注号）、
`min`/`typ`/`max`（数值）、`max_ref`（上限为引用量，如 VIO）、`variants`（[{condition|name, min/typ/max}]）。

规则细则：
- 同符号多条件 → `variants`；variant 里各条只放该行出现的界；统一量纲在父级 `unit`。
- 只有一行（如 fPD 只有 max）→ 顶层 max 即可。
- 数值是"上限类"（如第二谐波 -25dBc 属 max）→ max；`typ` 缺省不写 null。
- 无单位量（如 FSK level 档位 2–8）→ 可省略 unit。
- `source` 字符串规范：`'Page: <N>, layout_type: <text|table|image|formula>, Block: <真实id>'`；
  组内同源集中写组级 source，跨表跨页则逐项或逐子节写。

## 数值/单位清洗

- 剥 LaTeX/HTML 残留：`$V_{CC}$`→`VCC`，`^{TM}`→`™`，`Δ-Σ`、`Ω`、`μA`、`μs`、`℃`、`±`、`×` 保留量纲符。
- 拆连写条件：`fOUT=480MHzSE OSCin`→`fOUT=480MHz, SE OSCin`；但**值不重算**。
- OCR 形近词修正以语义为准（如把某行 `VIIL=0V` 判为 `VIL=0V` 仅在上下文确凿时），拿不准写 error_log。

## 提取优先级（P0/P1/P2）

P0 = 电特性、绝对最大、推荐工作、热阻、引脚、封装、订购 → 缺则阻断交付。
P1 = 特性/概述/应用清单/时序/叙述要点。
P2 = theory/notes/附加说明。
叙述类（P2）允许中文摘要但保留英文符号、公式、寄存器与数值。

## 调度阈值

| merged.json | 调度 |
|---|---|
| < 30 KB | 单 Agent 单轮 |
| 30–100 KB | 顺序 3–4 批 |
| ≥ 100 KB | 3 子 Agent 并发（类别亲和） |

类别亲和（同类别子表同一 Agent，避免按页平均切分）：
- Agent A：electrical(电流/DC/AC/limits)、绝对最大/推荐/热阻
- Agent B：thermal/rating/package/pin/ordering/family
- Agent C：applications / theory / notes
并发时各 Agent 只写自己的 temp yaml；主 Agent 计划/收敛/合并/验证/定点修复。
阈值是当前 Skill/模型/样本快照经验值，不是通用规则。

## 长任务状态机

`READY → EXTRACTING → PARTIAL → MERGED → VALIDATING → REPAIRING → PASSED | FAILED`
- 持久状态文件：`progress.json`（completed_batches/categories）、`error_log.json`（工具/Agent/验证/降级错误）、`temp/*.yaml`。
- 只重跑失败类别，禁止全量重来；修复后不再 merge 覆盖已合结果。
- 中断后可依据 progress.json 续跑，不依赖聊天记忆。
