"""从随 Skill 提供的模板创建 Excel 报告，或检查工作簿结构与冒烟填报。"""

import argparse
from collections import Counter
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "发布测试报告模板.xlsx"
NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
SHEETS = ["发布测试摘要", "发布功能覆盖", "测试自测结论", "PR 证据索引", "测试证据", "证据截图"]
PANES = ["C2", "E2", "C2", "B2", "A3"]
STATES = {"待执行", "通过", "失败", "受阻", "不适用"}


def new_report(output):
    if output.suffix.lower() != ".xlsx":
        raise ValueError("输出文件须使用 .xlsx 扩展名。")
    with TEMPLATE.open("rb") as source, output.open("xb") as destination:
        shutil.copyfileobj(source, destination)


def read_xml(book, member):
    return ET.fromstring(book.read(member))


def workbook_sheets(book):
    index = read_xml(book, "xl/workbook.xml")
    rels = read_xml(book, "xl/_rels/workbook.xml.rels")
    targets = {rel.get("Id"): rel.get("Target") for rel in rels}
    for node in index.findall("s:sheets/s:sheet", NS):
        target = targets.get(node.get(f"{{{NS['r']}}}id"))
        if not target:
            raise ValueError(f"工作表缺少部件关系：{node.get('name')}")
        part = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        if PurePosixPath(part).parts[:2] != ("xl", "worksheets"):
            raise ValueError("工作表部件不在工作簿内部。")
        yield node.get("name"), read_xml(book, part)


def text_nodes(node):
    return "".join(item.text or "" for item in node.iter(f"{{{NS['s']}}}t")) if node is not None else ""


def load_strings(book):
    name = "xl/sharedStrings.xml"
    if name not in book.namelist():
        return []
    return [text_nodes(item) for item in read_xml(book, name)]


def collect_cells(table, shared):
    cells = {}
    for node in table.findall("s:sheetData/s:row/s:c", NS):
        ref = node.get("r", "")
        if node.get("t") == "inlineStr":
            value = text_nodes(node.find("s:is", NS))
        else:
            value = node.findtext("s:v", default="", namespaces=NS)
            if node.get("t") == "s" and value:
                value = shared[int(value)]
        cells[ref] = value.strip()
    return cells


def check_cases(cells, table_end, template_only):
    cols = {value: key[:-1] for key, value in cells.items() if re.fullmatch("[A-Z]+1", key)}
    expected = {"编号", "需求", "主测人", "测试结论", "实际测试结果"}
    if not expected <= cols.keys():
        raise ValueError("冒烟工作表缺字段：" + "、".join(sorted(expected - cols.keys())))
    rows = sorted({int(match[1]) for key, value in cells.items()
                   if value and (match := re.fullmatch("[A-Z]+([0-9]+)", key)) and match[1] != "1"})
    if template_only and rows:
        raise ValueError("空白模板的自测表含已有记录。")
    issues, case_ids = [], {}
    count = Counter()
    for row in rows:
        if row > table_end:
            issues.append(f"第 {row} 行有用例数据，但超出原生冒烟表范围。请扩展表格，确保摘要公式统计到。")
        values = {name: cells.get(f"{cols[name]}{row}", "") for name in expected}
        case_id = values["编号"]
        if not case_id:
            issues.append(f"第 {row} 行有内容，缺少用例编号。")
            continue
        normalized = case_id.casefold()
        if normalized in case_ids:
            issues.append(f"第 {row} 行与第 {case_ids[normalized]} 行用例编号重复：{case_id}")
        case_ids[normalized] = row
        if not values["主测人"]:
            issues.append(f"{case_id} 缺主测人。")
        state = values["测试结论"]
        if state not in STATES:
            issues.append(f"{case_id} 的测试结论为空或不在下拉选项中。")
        else:
            count[state] += 1
        if state in {"通过", "不适用"} and not values["实际测试结果"]:
            issues.append(f"{case_id} 缺实际结果或不适用依据。")
    return issues, count


def check_report(source, template_only):
    with ZipFile(source) as book:
        found = dict(workbook_sheets(book))
        if list(found) != SHEETS:
            raise ValueError("六个工作表的名称或顺序与模板不一致。")
        for sheet_name, expected_pane in zip(SHEETS[1:], PANES):
            view = found[sheet_name].find("s:sheetViews/s:sheetView/s:pane", NS)
            if view is None or view.get("topLeftCell") != expected_pane:
                raise ValueError(f"{sheet_name} 的冻结区域与模板不一致。")

        table_files = [name for name in book.namelist()
                       if name.startswith("xl/tables/") and name.endswith(".xml")]
        tables = [read_xml(book, name) for name in table_files]
        if len(tables) != 4 or any(table.find("s:autoFilter", NS) is None for table in tables):
            raise ValueError("报告应保留四张带筛选的明细数据表。")
        smoke_table = next((table for table in tables if table.get("name") == "ReleaseSmokeCases"), None)
        bounds = re.fullmatch(r"[A-Z]+1:[A-Z]+([0-9]+)", smoke_table.get("ref", "")) if smoke_table is not None else None
        if bounds is None:
            raise ValueError("未找到模板原生冒烟表 ReleaseSmokeCases 或表格范围异常。")
        summary = found["发布测试摘要"]
        for address in ("B3", "B31", "D31", "F31", "H31", "I31"):
            formula = summary.find(f".//s:c[@r='{address}']/s:f", NS)
            if formula is None or not (formula.text or "").strip():
                raise ValueError(f"发布测试摘要 {address} 的计算公式缺失。")
        smoke = found["测试自测结论"]
        if not smoke.findall("s:dataValidations/s:dataValidation", NS):
            raise ValueError("测试自测结论的状态下拉缺失。")
        shared = load_strings(book)
        if template_only:
            if any(name.startswith(("xl/media/", "xl/externalLinks/")) for name in book.namelist()):
                raise ValueError("空白模板含图片或外部工作簿链接。")
            for sheet in SHEETS[1:5]:
                if any(value and not re.fullmatch("[A-Z]+1", cell)
                       for cell, value in collect_cells(found[sheet], shared).items()):
                    raise ValueError(f"空白模板的 {sheet} 含已有记录。")
        return check_cases(collect_cells(smoke, shared), int(bounds[1]), template_only)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="command", required=True)
    create = actions.add_parser("new", help="复制模板，目标文件须不存在")
    create.add_argument("file", type=Path)
    check = actions.add_parser("check", help="检查版式和冒烟用例填报")
    check.add_argument("file", type=Path)
    check.add_argument("--template", action="store_true", help="另检查模板未含已有自测记录和图片")
    args = parser.parse_args()

    try:
        if args.command == "new":
            new_report(args.file)
            print(f"已创建报告：{args.file.resolve()}")
        else:
            issues, states = check_report(args.file, args.template)
            for issue in issues:
                print(issue, file=sys.stderr)
            if issues:
                parser.exit(2, "工作簿检查发现待处理项。\n")
            state_text = "、".join(f"{key} {states[key]}" for key in ("待执行", "通过", "失败", "受阻", "不适用"))
            print("工作簿结构和填报检查通过。" + state_text + "。")
            print("验收结论需按实际正式包结果及证据核对。")
    except FileExistsError:
        parser.exit(2, "目标文件已存在，原文件未被覆盖。\n")
    except (BadZipFile, ET.ParseError, OSError, ValueError, KeyError, IndexError) as error:
        parser.exit(2, f"工作簿检查或创建未完成：{error}\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
