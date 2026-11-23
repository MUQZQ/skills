#!/usr/bin/env python3
"""Render base/head/diff PNGs for every .drawio changed between two git refs.

For each `.drawio` that differs between `--base` and `--head`, exports the
base and head pages as PNGs via the draw.io CLI, and — for files present on
both sides — chains `drawiodiff.py` -> `autolayout.py` -> CLI export into a
third colour-coded diff PNG. Added/removed files just get the one side that
exists. Emits a Markdown report with one section per changed file (status +
image links) and a summary count for the target repository’s PR or CI report.

  python3 prdiff.py --base origin/main --head HEAD -o drawio-pr/report.md

Missing draw.io CLI degrades gracefully: the Markdown still lists every
changed file, just without images (a review comment listing the files is
still useful). Missing git, or `--repo` not a git repository, is fatal.

Usage: python3 prdiff.py --base <ref> [--head <ref>] [--repo <dir>] [--drawio <exe>] [--out-dir <dir>] [-o report.md]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def changed_drawios(base, head, repo):
    """List of (path, status) for .drawio files that differ between base and head.

    status is "added", "removed", or "modified" (renames/copies count as
    modified, keyed on the new path). Shells to `git diff --name-status`.
    """
    try:
        r = subprocess.run(
            ["git", "-C", repo, "diff", "--name-status", f"{base}..{head}", "--", "*.drawio"],
            capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("error: not a git repo / git not found (git not on PATH)")
    if r.returncode != 0:
        sys.exit(f"error: not a git repo / git not found: {r.stderr.strip()}")
    entries = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        code, path = parts[0], parts[-1]
        status = "added" if code.startswith("A") else "removed" if code.startswith("D") else "modified"
        entries.append((path, status))
    return entries


def git_show_file(repo, ref, path, dest):
    """Write the blob at ref:path (in repo) to dest. False if it doesn't exist there."""
    r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True)
    if r.returncode != 0:
        return False
    with open(dest, "wb") as f:
        f.write(r.stdout)
    return True


def export_png(drawio_executable, src_drawio, out_png):
    """将输入图表的首页导出为 PNG。"""
    command = [drawio_executable, "-x", "-f", "png", "--page-index", "1", "-o", out_png, src_drawio]
    try:
        result = subprocess.run(command, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        sys.stderr.write(f"警告：导出 {out_png} 失败（{error}）\n")
        return False
    if result.returncode != 0 or not os.path.isfile(out_png):
        sys.stderr.write(f"警告：导出 {out_png} 失败（退出码 {result.returncode}）\n")
        return False
    return True


def export_diff_png(drawio_executable, base_drawio, head_drawio, out_png, tmp):
    """drawiodiff.py -> autolayout.py -> CLI export a coloured diff PNG. True on success."""
    diff_json = os.path.join(tmp, "diff.json")
    diff_drawio = os.path.join(tmp, "diff.drawio")
    r1 = subprocess.run([sys.executable, os.path.join(HERE, "drawiodiff.py"),
                        base_drawio, head_drawio, "-o", diff_json], capture_output=True)
    if r1.returncode != 0 or not os.path.exists(diff_json):
        return False
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "autolayout.py"),
                        diff_json, "-o", diff_drawio], capture_output=True)
    if r2.returncode != 0 or not os.path.exists(diff_drawio):
        return False
    return export_png(drawio_executable, diff_drawio, out_png)


def build_entry(repo, base, head, path, status, out_dir, drawio_executable):
    """One render_markdown entry: fetch both sides, export whatever PNGs it can."""
    entry = {"path": path, "status": status}
    if drawio_executable is None:
        entry["skipped"] = True
        return entry
    slug = path.replace("/", "__")
    with tempfile.TemporaryDirectory() as tmp:
        base_drawio = os.path.join(tmp, "base.drawio")
        head_drawio = os.path.join(tmp, "head.drawio")
        have_base = git_show_file(repo, base, path, base_drawio)
        have_head = git_show_file(repo, head, path, head_drawio)
        if have_base:
            p = os.path.join(out_dir, f"{slug}.base.png")
            if export_png(drawio_executable, base_drawio, p):
                entry["base_png"] = p
        if have_head:
            p = os.path.join(out_dir, f"{slug}.head.png")
            if export_png(drawio_executable, head_drawio, p):
                entry["head_png"] = p
        if have_base and have_head:
            p = os.path.join(out_dir, f"{slug}.diff.png")
            if export_diff_png(drawio_executable, base_drawio, head_drawio, p, tmp):
                entry["diff_png"] = p
    return entry


def render_markdown(entries, out_dir):
    """Pure: Markdown PR report from prdiff entries. No I/O, no CLI.

    entries: list of {"path", "status", "base_png"?, "head_png"?, "diff_png"?,
    "skipped"?} — image paths (if any) are made relative to out_dir for the
    Markdown links. "skipped" means the draw.io CLI was unavailable.
    """
    counts = {"added": 0, "removed": 0, "modified": 0}
    for e in entries:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    lines = [
        "# draw.io diagram changes",
        "",
        f"{len(entries)} file(s) changed: +{counts.get('added', 0)} added, "
        f"-{counts.get('removed', 0)} removed, ~{counts.get('modified', 0)} modified",
    ]
    if not entries:
        lines.append("")
        lines.append("No `.drawio` files changed.")
        return "\n".join(lines) + "\n"

    def rel(png):
        return os.path.relpath(png, out_dir).replace(os.sep, "/") if png else None

    for e in entries:
        lines.append("")
        lines.append(f"## {e['path']} ({e['status']})")
        if e.get("skipped"):
            lines.append("")
            lines.append("_draw.io CLI not available — images skipped._")
            continue
        base_r, head_r, diff_r = rel(e.get("base_png")), rel(e.get("head_png")), rel(e.get("diff_png"))
        lines.append("")
        if base_r:
            lines.append(f"![base]({base_r})")
        if head_r:
            lines.append(f"![head]({head_r})")
        if diff_r:
            lines.append(f"![diff]({diff_r})")
        if not (base_r or head_r or diff_r):
            lines.append("_no image produced._")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Render PNGs + a Markdown report for .drawio files "
                                              "changed between two git refs.")
    ap.add_argument("--base", required=True, help="base git ref/sha")
    ap.add_argument("--head", default="HEAD", help="head git ref/sha (default HEAD)")
    ap.add_argument("--repo", default=".", help="path to the git repo (default: current directory)")
    ap.add_argument("--out-dir", default="drawio-pr", help="directory for exported PNGs (default: ./drawio-pr)")
    ap.add_argument("-o", "--output", help="write the Markdown report here (default: stdout)")
    ap.add_argument("--drawio", metavar="EXE", help="draw.io 的可执行文件路径或命令名")
    args = ap.parse_args()

    if args.drawio:
        drawio_executable = shutil.which(args.drawio)
        if drawio_executable is None:
            ap.error(f"找不到 --drawio 指定的可执行文件：{args.drawio}")
    else:
        drawio_executable = shutil.which("drawio") or shutil.which("draw.io")

    changed = changed_drawios(args.base, args.head, args.repo)
    if not changed:
        sys.stderr.write("no .drawio files changed\n")

    if drawio_executable is None and changed:
        sys.stderr.write("警告：PATH 中找不到 draw.io，报告将保留文件清单。"
                         "已安装时可用 --drawio 指定可执行文件路径。\n")
    os.makedirs(args.out_dir, exist_ok=True)

    entries = [build_entry(args.repo, args.base, args.head, path, status, args.out_dir, drawio_executable)
               for path, status in changed]
    report = render_markdown(entries, args.out_dir)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        sys.stderr.write(f"wrote {args.output}\n")
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()
