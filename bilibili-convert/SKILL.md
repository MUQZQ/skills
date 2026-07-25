---
name: bilibili-convert
description: 将 Bilibili 客户端下载的分离音视频 m4s 文件无损合并为通用 MP4 格式
license: MIT
compatibility: opencode
metadata:
  audience: general
  category: media-conversion
  tags: bilibili,m4s,ffmpeg,video,convert,mp4
---

# Bilibili 视频格式转换

## 概述

Bilibili PC 客户端下载的视频将音频轨和视频轨分离存储为 `.m4s` 文件，无法直接在普通播放器中播放。此 Skill 使用 FFmpeg 将音视频流无损合并为标准 MP4 文件，支持批量处理。

## 文件结构说明

Bilibili 客户端下载的视频目录结构：

```
bilibili/
  {cid}/                     # 视频目录，以 cid 命名
    {cid}-1-30064.m4s        # 音频轨 (低码率)
    {cid}-1-30080.m4s        # 音频轨 (高码率)
    {cid}-1-30280.m4s        # 视频轨
    {cid}_p1-1-30080.m4s     # 多 P 视频音频轨
    {cid}_p1-1-30280.m4s     # 多 P 视频视频轨
    videoInfo.json           # 视频元数据 (标题、UP主、分组等)
    image.png/jpg            # 封面图
    group.png/jpg            # 分组封面图
    .playurl                 # 播放地址
    .videoInfo               # 视频信息
    dm1 / dm2                # 弹幕数据
    view                     # 观看数据
```

关键字段：
- `30064` / `30080` = 音频轨编码标识
- `30280` = 视频轨编码标识
- `videoInfo.json` 中的 `title` = 视频标题，`groupTitle` = 合集/分组标题

## 工作流程

```
检查 FFmpeg 安装状态
       ↓
  已安装? ──否──> 安装 FFmpeg (winget)
       ↓
      是
       ↓
遍历数字命名子目录
       ↓
读取 videoInfo.json 获取 title、groupTitle
       ↓
glob 匹配视频 m4s 和音频 m4s
       ↓
sanitize 文件名 (去除 Windows 非法字符)
       ↓
按 groupTitle 归类输出目录
       ↓
调用 ffmpeg -c copy 无损合并
       ↓
输出统计: 成功/失败/跳过数量
```

## 执行步骤

### 步骤 1: 检查 FFmpeg

必须先确认 FFmpeg 可用。

**检查命令**:

```powershell
ffmpeg -version
```

**安装（如未安装）**:

```powershell
winget install FFmpeg
```

安装后需重启终端或刷新 PATH 环境变量。

**手动安装备选方案** (winget 不可用时):

1. 访问 https://ffmpeg.org/download.html
2. 下载 Windows 版本 (gyan.dev 或 BtbN 构建)
3. 解压到 `C:\ffmpeg\`
4. 将 `C:\ffmpeg\bin` 添加到系统 PATH
5. 重启终端

注意：使用国内镜像下载更快：
- https://mirrors.tuna.tsinghua.edu.cn/ffmpeg/

### 步骤 2: 确认目录结构

确认目标目录 `bilibili/` 存在且包含数字命名的子目录，每个子目录中有 `videoInfo.json` 和 `.m4s` 文件。

### 步骤 3: 运行转换

脚本已内置在 skill 目录中，直接运行即可：

```powershell
python "C:\Users\Admin\.config\opencode\skills\bilibili-convert\convert_bilibili.py" "目标目录路径"
```

不指定路径则使用当前工作目录。

### 增量模式（默认行为）

脚本默认只转换 **尚未转换过** 的视频，已转换的自动跳过。

```powershell
# 只转换新增的
python convert_bilibili.py "目标目录"

# 查看状态：哪些已转，哪些待转
python convert_bilibili.py "目标目录" --check

# 强制全部重转
python convert_bilibili.py "目标目录" --force
```

输出路径为 `{源目录}_output`，位于源目录的上一层。

### 步骤 4: 验证结果

检查 `bilibili/output/` 目录下的 MP4 文件数量和大小。确认所有文件可正常播放。

## AI 执行流程

当用户触发此 Skill 时，AI 应按以下流程执行：

1. **检查 FFmpeg**: 运行 `ffmpeg -version` 确认已安装；未安装则执行 `winget install FFmpeg`
2. **确认目标目录**: 询问或自动识别 bilibili 视频缓存目录（默认 `C:\Users\Admin\Videos\bilibili`）
3. **先查状态**: 运行 `--check` 查看待转数量
4. **增量转换**: 默认运行（自动跳过已转），有需要时加 `--force` 全量重转
5. **输出报告**: 汇总成功/失败/跳过数量、输出路径、文件大小

## Bilibili 文件混淆处理

Bilibili PC 客户端下载的 m4s 文件并非标准 MP4 容器，而是在文件头部**插入了 9 个 `0x30` (ASCII "0") 字节**作为混淆。因此直接用 FFmpeg 打开会报错：

```
Error opening input files: Invalid data found when processing input
```

**解决方案**：在合并前先去掉文件开头的 9 个 `0x30` 字节。

文件头部十六进制对比：

| 类型 | 头部 |
|------|------|
| Bilibili m4s | `30 30 30 30 30 30 30 30 30` + `00 00 00 24 ftypisom...` |
| 标准 MP4 | `00 00 00 24 ftypisom...` |

脚本内置了自动识别和清理逻辑：读取文件头部，跳过所有连续 `0x30` 字节后再写入临时文件供 FFmpeg 处理。

## 注意事项

1. **无损合并**：`-c copy` 直接复制流，不重新编码，速度快且不损失画质
2. **codecid=7**：B 站使用 H.264/HEVC 编码，MP4 容器完美兼容
3. **文件大小**：合并后大小 = 视频轨大小 + 音频轨大小（几乎无变化）
4. **处理速度**：每个文件约 1-3 秒（取决于磁盘速度）
5. **多 P 视频**：如 `_p1`、`_p2` 等会自动生成独立 MP4 文件
6. **无音频视频**：如目录中只有视频轨没有音频轨，脚本自动跳过音频输入
7. **文件名安全**：Windows 非法字符 `<>:"/\|?*` 会被自动替换为下划线
8. **重复标题**：重名标题自动追加 `_2`、`_3` 后缀
9. **不修改原始文件**：只在临时目录清理文件头，原始 m4s 保持不变

## 触发示例

用户可以使用以下方式触发此 Skill：

```
如何将这些bilibili视频格式转为通用格式
```

或

```
bilibili 视频转 MP4
```

或

```
转换 b 站下载的视频
```

或

```
/convert-bilibili
```

或

```
m4s 转 mp4 批量
```

## 验证清单

完成后检查：

- [ ] FFmpeg 已安装且 PATH 可访问
- [ ] `convert_bilibili.py` 已生成在 bilibili 根目录
- [ ] `output/` 目录已创建且包含 MP4 文件
- [ ] MP4 文件数量与源目录数量一致
- [ ] 随机抽查 2-3 个 MP4 可正常播放
- [ ] 源目录完好无损（脚本不删除原始文件）

---

## 附录: convert_bilibili.py 完整脚本

以下脚本在用户确认后直接写入 `convert_bilibili.py`：

```python
#!/usr/bin/env python3
"""Bilibili m4s -> MP4 batch converter (handles 9-byte obfuscation)"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


BLOCK_SIZE = 1024 * 1024  # 1MB


def sanitize_filename(name):
    illegal = r'[<>:"/\\|?*]'
    s = re.sub(illegal, '_', name).strip().rstrip('.')
    return s if s else 'untitled'


def get_unique_path(base_dir, filename):
    stem, ext = os.path.splitext(filename)
    if not ext:
        ext = '.mp4'
    path = base_dir / filename
    counter = 2
    while path.exists():
        path = base_dir / f"{stem}_{counter}{ext}"
        counter += 1
    return path


def strip_m4s_header(src_path, dst_path):
    """Remove the 9-byte obfuscation header from bilibili m4s file."""
    with open(src_path, 'rb') as fin, open(dst_path, 'wb') as fout:
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


def convert_video(video_dir, output_root, temp_dir):
    json_path = video_dir / 'videoInfo.json'
    if not json_path.exists():
        return False, 'no json'

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
    except json.JSONDecodeError:
        return False, 'bad json'

    title = info.get('title', video_dir.name)
    group_title = info.get('groupTitle', '')

    m4s_files = list(video_dir.glob('*.m4s'))
    if not m4s_files:
        return False, 'no m4s'

    video_file = None
    audio_file = None
    for f in m4s_files:
        name = f.stem
        if '30280' in name:
            video_file = f
        elif '30064' in name or '30080' in name:
            audio_file = f

    if not video_file:
        return False, 'no video track'

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

        cmd = ['ffmpeg', '-i', str(clean_video), '-y']
        if audio_file:
            cmd.extend(['-i', str(clean_audio)])
        cmd.extend(['-c', 'copy', str(output_path)])

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='gbk', errors='ignore'
        )
        if result.returncode == 0:
            size_mb = output_path.stat().st_size / (1024 * 1024)
            return True, f"OK {size_mb:.1f}MB -> {output_path.name}"
        else:
            lines = result.stderr.strip().split('\n')
            last = lines[-1] if lines else 'unknown'
            return False, f"ffmpeg err: {last[:100]}"
    except FileNotFoundError:
        return False, 'FFmpeg not found'
    except Exception as e:
        return False, f"exception: {str(e)[:100]}"
    finally:
        for tmp in (clean_video, clean_audio):
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass


def main():
    base_dir = Path(__file__).resolve().parent
    output_root = base_dir / 'output'

    with tempfile.TemporaryDirectory(prefix='bili_convert_') as temp_dir:
        temp_dir = Path(temp_dir)

        video_dirs = []
        for d in base_dir.iterdir():
            if d.is_dir() and d.name.isdigit():
                video_dirs.append(d)

        if not video_dirs:
            print('No video dirs found')
            sys.exit(1)

        video_dirs.sort(key=lambda d: int(d.name))
        total = len(video_dirs)
        print(f"Found {total} video dirs\n")

        ok_count = 0
        fail_count = 0
        errors = []

        for idx, d in enumerate(video_dirs, 1):
            print(f"[{idx}/{total}] {d.name} ... ", end='', flush=True)
            ok, msg = convert_video(d, output_root, temp_dir)
            print(msg)
            if ok:
                ok_count += 1
            else:
                fail_count += 1
                errors.append((d.name, msg))

        print()
        print(f"Done! Success: {ok_count}, Failed: {fail_count}, Total: {total}")
        print(f"Output: {output_root}")

        if errors:
            print("\nErrors:")
            for n, m in errors:
                print(f"  [{n}] {m}")

        if fail_count > 0:
            sys.exit(1)


if __name__ == '__main__':
    main()
```
