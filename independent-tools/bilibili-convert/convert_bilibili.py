#!/usr/bin/env python3
"""Bilibili m4s -> MP4 batch converter (handles 9-byte obfuscation, supports incremental mode)"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


BLOCK_SIZE = 1024 * 1024  # 1MB
TRACKING_FILE = ".converted.json"


def sanitize_filename(name):
    illegal = r'[<>:"/\\|?*]'
    s = re.sub(illegal, "_", name).strip().rstrip(".")
    return s if s else "untitled"


def get_unique_path(base_dir, filename):
    stem, ext = os.path.splitext(filename)
    if not ext:
        ext = ".mp4"
    path = base_dir / filename
    counter = 2
    while path.exists():
        path = base_dir / f"{stem}_{counter}{ext}"
        counter += 1
    return path


def strip_m4s_header(src_path, dst_path):
    """Remove the 9-byte obfuscation header from bilibili m4s file."""
    with open(src_path, "rb") as fin, open(dst_path, "wb") as fout:
        header = fin.read(16)
        idx = 0
        while idx < len(header) and header[idx] == 0x30:
            idx += 1
        if idx == 0:
            fout.write(header)
        elif idx < len(header):
            fout.write(header[idx:])
        while True:
            chunk = fin.read(BLOCK_SIZE)
            if not chunk:
                break
            fout.write(chunk)


def load_tracking(output_root):
    """Load {cid: output_filename} mapping from tracking file."""
    path = output_root / TRACKING_FILE
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_tracking(output_root, tracking):
    """Save tracking mapping to file."""
    path = output_root / TRACKING_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)


def video_info(video_dir):
    """Read title and group_title from videoInfo.json."""
    json_path = video_dir / "videoInfo.json"
    if not json_path.exists():
        return None, None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            info = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None, None
    return info.get("title", video_dir.name), info.get("groupTitle", "")


def convert_video(video_dir, output_root, temp_dir, tracking):
    """Convert single video, return (ok: bool, msg: str, output_name: str)."""
    title, group_title = video_info(video_dir)
    if title is None:
        return (False, "no json", "")

    m4s_files = list(video_dir.glob("*.m4s"))
    if not m4s_files:
        return (False, "no m4s", "")

    video_file = None
    audio_file = None
    for f in m4s_files:
        name = f.stem
        if "30280" in name:
            video_file = f
        elif "30064" in name or "30080" in name:
            audio_file = f

    if not video_file:
        return (False, "no video track", "")

    if group_title:
        output_dir = output_root / sanitize_filename(group_title)
    else:
        output_dir = output_root
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_title = sanitize_filename(title)
    output_path = get_unique_path(output_dir, f"{safe_title}.mp4")

    clean_video = Path(temp_dir) / f"{video_dir.name}_video.m4s"
    clean_audio = Path(temp_dir) / f"{video_dir.name}_audio.m4s"

    try:
        strip_m4s_header(str(video_file), str(clean_video))
        if audio_file:
            strip_m4s_header(str(audio_file), str(clean_audio))

        cmd = ["ffmpeg", "-i", str(clean_video), "-y"]
        if audio_file:
            cmd.extend(["-i", str(clean_audio)])
        cmd.extend(["-c", "copy", str(output_path)])

        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="gbk", errors="ignore"
        )
        if result.returncode == 0:
            size_mb = output_path.stat().st_size / (1024 * 1024)
            tracking[video_dir.name] = str(output_path.relative_to(output_root))
            return (True, f"OK {size_mb:.1f}MB -> {output_path.name}", output_path.name)
        else:
            lines = result.stderr.strip().split("\n")
            last = lines[-1] if lines else "unknown"
            return (False, f"ffmpeg err: {last[:100]}", "")
    except FileNotFoundError:
        return (False, "FFmpeg not found", "")
    except Exception as e:
        return (False, f"exception: {str(e)[:100]}", "")
    finally:
        for tmp in (clean_video, clean_audio):
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass


def scan_dirs(base_dir):
    """Collect and sort all numeric-named video directories."""
    video_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    if not video_dirs:
        return []
    video_dirs.sort(key=lambda d: int(d.name))
    return video_dirs


def cmd_check(base_dir, output_root):
    """Check mode: show conversion status for all videos."""
    video_dirs = scan_dirs(base_dir)
    if not video_dirs:
        print("No video dirs found")
        return

    tracking = load_tracking(output_root)
    total = len(video_dirs)
    converted = 0
    pending = 0
    missing_meta = 0

    pending_list = []
    missing_list = []

    for d in video_dirs:
        cid = d.name
        if cid in tracking:
            converted += 1
        else:
            title, _ = video_info(d)
            if title is None:
                missing_meta += 1
                missing_list.append(cid)
            else:
                pending += 1
                pending_list.append(f"  [{cid}] {title}")

    print(f"Total: {total}")
    print(f"  Converted: {converted}")
    print(f"  Pending:   {pending}")
    if missing_meta:
        print(f"  No meta:   {missing_meta}")

    if pending_list:
        print(f"\nPending ({pending}):")
        for line in pending_list:
            print(line)

    if missing_list:
        print(f"\nMissing videoInfo.json ({len(missing_list)}):")
        for cid in missing_list:
            print(f"  [{cid}]")


def cmd_convert(base_dir, output_root, force=False):
    """Incremental convert mode: skip already-converted unless --force."""
    video_dirs = scan_dirs(base_dir)
    if not video_dirs:
        print("No video dirs found")
        sys.exit(1)

    tracking = load_tracking(output_root)
    total = len(video_dirs)
    already = sum(1 for d in video_dirs if d.name in tracking)
    todo_count = total - already if not force else total

    if already > 0 and not force:
        print(f"Total: {total}, Already converted: {already}, Pending: {todo_count}\n")
        if todo_count == 0:
            print("All videos already converted. Use --force to re-convert.")
            return
    else:
        print(f"Total: {total} video dirs\n")
        if force and already > 0:
            print(f"(--force: will re-convert {already} already-converted videos)\n")

    with tempfile.TemporaryDirectory(prefix="bili_convert_") as temp_dir:
        temp_dir = Path(temp_dir)
        ok_count = 0
        fail_count = 0
        skip_count = 0
        errors = []

        idx = 0
        for d in video_dirs:
            idx += 1
            cid = d.name
            if not force and cid in tracking:
                skip_count += 1
                continue

            print(f"[{idx}/{total}] {cid} ... ", end="", flush=True)
            ok, msg, out_name = convert_video(d, output_root, temp_dir, tracking)
            print(msg)
            if ok:
                ok_count += 1
            else:
                fail_count += 1
                errors.append((cid, msg))

        save_tracking(output_root, tracking)

        print()
        print(
            f"Done! Success: {ok_count}, Failed: {fail_count}, Skipped: {skip_count}, Total: {total}"
        )
        print(f"Output: {output_root}")

        if errors:
            print("\nErrors:")
            for n, m in errors:
                print(f"  [{n}] {m}")

        if fail_count > 0:
            sys.exit(1)


def print_usage():
    prog = Path(sys.argv[0]).name if sys.argv else "convert_bilibili.py"
    print(f"Usage: python {prog} [TARGET_DIR] [OPTIONS]")
    print()
    print("  TARGET_DIR    Path to bilibili cache directory (default: current dir)")
    print()
    print("Options:")
    print("  --check       Show conversion status: how many converted / pending")
    print("  --force       Re-convert all, including already-converted videos")
    print("  --help        Show this message")
    print()
    print("Default behavior: incremental mode (skip already-converted videos)")


def main():
    # Parse arguments
    check_only = False
    force = False
    target = None

    for arg in sys.argv[1:]:
        if arg == "--check":
            check_only = True
        elif arg == "--force":
            force = True
        elif arg == "--help" or arg == "-h":
            print_usage()
            return
        elif not arg.startswith("-"):
            target = arg
        else:
            print(f"Unknown option: {arg}")
            print_usage()
            sys.exit(1)

    base_dir = Path(target).resolve() if target else Path.cwd()
    output_root = base_dir.parent / f"{base_dir.name}_output"

    if check_only:
        cmd_check(base_dir, output_root)
    else:
        cmd_convert(base_dir, output_root, force=force)


if __name__ == "__main__":
    main()
