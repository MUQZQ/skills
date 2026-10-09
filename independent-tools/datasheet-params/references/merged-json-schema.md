# merged.json 输入契约与 PDF 解析方法

## merged.json 字段契约

顶层两个键：

- `full_markdown`：整份数据手册 markdown（含页眉 `===` 分段、标题 `##`、表格 HTML、图片引用）。只用于通读发现。
- `layout`：逐块数组，每块字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `block_content` | str | 内容：正文 markdown 文本，或 `<table border="1">…</table>` HTML，或图片引用 `![Image](image_splits/split_N_M.png)` |
| `bbox` | [x1,y1,x2,y2] | 页面坐标，用于版式/页面对齐校验 |
| `block_id` | int | **真实块 id**（全局唯一）。source 必须用它，绝不是数组下标+1 |
| `page_index` | int | 1 起始页码 |
| `layout_type` | text/table/image/formula | 块类型（可能还有 caption 类文本块） |
| `heading_level` | int/null | 标题级别（2≈章节标题），`section_number` 给 `N` 或 `N.N` 小节号 |
| `image_summary`/`image_caption`/`image_type`/`image_data`/`image_error` |  | 图片块视觉解析结果；`image_error: "API 返回空结果"` 表示视觉模型未返回内容 |

表格块 `block_content` 是带 `<tr><td rowspan=… colspan=…>` 的 HTML，必须按单元格语义解析。

## source 规范

`source: 'Page: <N>, layout_type: <T>, Block: <M>'`，其中 M 必须能在 merged.json 里查到：
同一页(page_index=N)存在 block_id=M 且 layout_type=T 的块。这是验证脚本的第 1 类事实检查。

## 关键坑（读取期）

- `block_content` 可能单行超长（数千字符）；直接 Read 会在 2000 字符截断——先用
  `scripts/dump_layout.py` 摊平成按页文本（表格转 `|` 管道行）再分段读，避免错读丢行。
- 跨页续表：标题常为 "X (continued)" 且无 section_number；用上方锚点块归属到原类别。
- 同一 device 的 layout 全在一个 merged.json；多器件批量会各自出文件。

## 从 PDF 生成 merged.json（可选 Stage 0）

数据手册多数为原生文本 PDF。无专用解析器时按下面方法尽力生成，产出必须满足上述字段契约：

1. 依赖：`pip install pymupdf`（文本层+几何布局）。如不可安装或页面为扫描图 → 停止并索要 merged.json。
2. 逐页用 `page.get_text("dict")` 取块（block type 0 文本 / 1 图像），给 bbox、page_index、自增 block_id；
   标题块按字号/加粗与页首特征标 heading_level 与 section_number。
3. 表格：优先把规则网格的文本块判为 table 并输出为单行 `<table>…</table>` HTML（行/列由几何对齐聚类）；
   识别不了规则的表格仍按文本块保留并记 error_log——提取阶段会对文本行做表格语义重建。
4. 图片块写 `![Image](image_splits/split_{page}_{block}.png)`，若环境能看图则填 image_summary/caption。
5. 拼接 `full_markdown`：按页顺序输出标题（`#`/`##`）与块文本、表格 HTML、图片引用。
6. 自检：`block_id` 连续且每块字段齐全；抽样页文本与 PDF 肉眼一致。
7. 若解析质量可疑（表格错乱、整页缺失），降级向用户要官方解析产物 merged.json，并把解析问题写入 error_log。

> 解析器质量决定 source 可信度；**提取阶段的正确性不依赖解析器同源**——只要 merged.json 满足字段契约，
> 每条 source 指向真实 block 即可。评测对齐基准时建议使用与基准同源的 merged.json。
