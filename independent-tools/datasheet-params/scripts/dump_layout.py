#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 merged.json 摊平成按页可读文本（表格转 | 管道行），规避单行 2000 字符截断。

用法:
    python dump_layout.py <merged.json> [输出.txt]

输出默认 {输入名}_dump.txt，与 merged.json 同目录。脚本只做展示，不改输入。
"""
import json
import re
import sys
import os


def html_to_text(h: str) -> str:
    rows = re.findall(r"<tr>(.*?)</tr>", h, re.S)
    if rows:
        out = []
        for r in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            out.append(" | ".join(cells))
        return "TABLE_HTML\n" + "\n".join(out)
    return re.sub(r"<[^>]+>", "", h).strip()


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    lay = data.get("layout", [])
    pages = {}
    for b in lay:
        pages.setdefault(b.get("page_index"), []).append(b)

    lines = []
    for pg in sorted(pages):
        lines.append("=" * 100)
        lines.append(f"===== PAGE {pg} =====")
        for b in sorted(pages[pg], key=lambda x: x.get("block_id", 0)):
            bid, lt, hl, sn = (
                b.get("block_id"),
                b.get("layout_type"),
                b.get("heading_level"),
                b.get("section_number"),
            )
            lines.append(f"--- B{bid} [{lt}] heading={hl} sec={sn}")
            if lt == "image":
                lines.append("IMG cap=%r err=%r" % (b.get("image_caption"), b.get("image_error")))
            else:
                lines.append(clean(html_to_text(b.get("block_content") or "")))

    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "_dump.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {len(lines)} lines -> {out}")


if __name__ == "__main__":
    main()
