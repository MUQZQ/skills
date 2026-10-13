#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datasheet-params 输出校验器：结构 + 来源存在性；可选 --gold 深对比。

用法:
    python validate_output.py <merged.json> <输出_ai_params.yaml> [--gold <基准.yaml>]

检查项(任一 FAIL -> 退出码 1)：
  1. 输出可解析为 YAML；
  2. 每个参数叶子(symbol+值域字段)在其祖先链上存在可解析的 source（组级或参数级）；
  3. source 指向 merged.json 中真实存在的 block（同 page_index / layout_type / block_id）；
     table 类若落点本身是 text 块、但同页确有 table 块，记 WARN 不记 FAIL；
  4. 参数叶子缺 symbol/name/值域(min|typ|max|variants|max_ref) 之一记 FAIL；
  5. pin 元素含 num/name/type/desc。

--gold 时做深对比并打印差异路径。
"""
import argparse
import json
import re
import sys

try:
    import yaml
except ImportError:
    print("缺依赖: 请先运行  pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SRC_RE = re.compile(r"^Page: (\d+), layout_type: (text|table|image|formula), Block: (\d+)$")
VALUE_FIELDS = ("min", "typ", "max", "variants", "max_ref")


def load(path: str):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_param_leaf(node) -> bool:
    return isinstance(node, dict) and isinstance(node.get("symbol"), str)


def check_tree(node, path, ancestor_src, failures, warnings, src_map) -> None:
    """ancestor_src: 当前祖先链上已出现 source 字符串；None 表示尚未出现。"""
    if isinstance(node, dict):
        src = node.get("source") if isinstance(node.get("source"), str) else None
        valid_src = None
        if src is not None:
            m = SRC_RE.match(src.strip())
            if not m:
                failures.append(f"{path}.source: 格式非法 {src!r}")
            else:
                page, lt, bid = int(m.group(1)), m.group(2), int(m.group(3))
                hit = [b for b in src_map.get(page, []) if b["block_id"] == bid]
                if not hit:
                    failures.append(f"{path}.source: {src} 不存在该 block")
                elif hit[0].get("layout_type") != lt:
                    if lt == "table" and any(b.get("layout_type") == "table" for b in src_map.get(page, [])):
                        warnings.append(f"{path}.source: {src} 命中 text 块(同页有 table)，WARN")
                    else:
                        failures.append(f"{path}.source: {src} layout_type 不符(实际 {hit[0].get('layout_type')})")
                else:
                    valid_src = src
        cur_src = valid_src or ancestor_src

        if is_param_leaf(node):
            if not cur_src:
                failures.append(f"{path}: 参数缺少可溯源 source")
            if "name" not in node:
                failures.append(f"{path}: 缺 name")
            if not any(k in node for k in VALUE_FIELDS):
                failures.append(f"{path}: 缺值域字段({', '.join(VALUE_FIELDS)})")
            if isinstance(node.get("unit"), str) and not node["unit"].strip():
                failures.append(f"{path}: unit 为空字符串")

        for k, v in node.items():
            if k in ("source",):
                continue
            if isinstance(v, dict):
                check_tree(v, f"{path}.{k}", cur_src, failures, warnings, src_map)
            elif isinstance(v, list):
                for i, it in enumerate(v):
                    check_tree(it, f"{path}.{k}[{i}]", cur_src, failures, warnings, src_map)
    elif isinstance(node, list):
        for i, it in enumerate(node):
            check_tree(it, f"{path}[{i}]", ancestor_src, failures, warnings, src_map)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("merged_json")
    ap.add_argument("output_yaml")
    ap.add_argument("--gold")
    args = ap.parse_args()

    with open(args.merged_json, encoding="utf-8") as f:
        merged = json.load(f)
    src_map = {}
    for b in merged.get("layout", []):
        src_map.setdefault(b.get("page_index"), []).append(b)

    out = load(args.output_yaml)
    if not isinstance(out, dict):
        print("== 结构/来源校验 == FAIL 1  WARN 0")
        print(f"  FAIL: 输出 YAML 顶层必须是映射(dict)，实际为 {type(out).__name__}（空文件或格式错误）")
        sys.exit(1)
    failures, warnings = [], []
    check_tree(out, "root", None, failures, warnings, src_map)

    pins = (out.get("pin_configuration") or {}).get("pins") or []
    for i, p in enumerate(pins):
        for fld in ("num", "name", "type", "desc"):
            if fld not in p:
                failures.append(f"pin_configuration.pins[{i}]: 缺 {fld}")

    print(f"== 结构/来源校验 == FAIL {len(failures)}  WARN {len(warnings)}")
    for w in warnings:
        print("  WARN:", w)
    for f in failures[:60]:
        print("  FAIL:", f)
    if len(failures) > 60:
        print(f"  ... 其余 {len(failures)-60} 条")

    if args.gold:
        gold = load(args.gold)
        if not isinstance(gold, dict):
            print(f"== 与基准深对比 == 跳过：基准 YAML 顶层为 {type(gold).__name__}，不是映射")
        else:
            diff = []
            compared = 0

            def walk(a, b, path=""):
                nonlocal compared
                if type(a) != type(b):
                    diff.append(f"{path}: 类型 {type(a).__name__} vs {type(b).__name__}")
                    compared += 1
                    return
                if isinstance(a, dict):
                    for k in set(a) | set(b):
                        if k not in a:
                            diff.append(f"{path}.{k}: gold 独有")
                            compared += 1
                        elif k not in b:
                            diff.append(f"{path}.{k}: 输出独有")
                            compared += 1
                        else:
                            walk(a[k], b[k], f"{path}.{k}")
                elif isinstance(a, list):
                    if len(a) != len(b):
                        diff.append(f"{path}: 长度 {len(a)} vs {len(b)}")
                    for i, (u, v) in enumerate(zip(a, b)):
                        walk(u, v, f"{path}[{i}]")
                else:
                    compared += 1
                    if a != b:
                        diff.append(f"{path}: {a!r} vs {b!r}")

            walk(gold, out)
            identical = len(diff) == 0
            pct = 100.0 * (compared - len(diff)) / compared if compared else 100.0
            verdict = "完全一致" if identical else f"覆盖率 {pct:.1f}%（R6 门禁: >=95 过 / 80-94 修复 / <80 失败）"
            print(f"== 与基准深对比 == 对比项 {compared}  差异 {len(diff)} 条  ->  {verdict}")
            for d in diff[:20]:
                print("  DIFF:", d)
            if len(diff) > 20:
                print(f"  ... 其余 {len(diff)-20} 条")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
