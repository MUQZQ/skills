"""检查录屏，制作多素材、分段变速、字幕与同音色配音的短片。"""

import argparse
import array
import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

CACHE_VERSION = 2
RATE = 48000


def ffmpeg():
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def command(args, timeout=300, cwd=None):
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-y", *map(str, args)],
        check=False,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
    )
    if r.returncode:
        raise RuntimeError(r.stderr.decode("utf-8", errors="replace")[-5000:])
    return r


def probe(path):
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-i", str(path)],
        check=False,
        capture_output=True,
        timeout=30,
    )
    log = r.stderr.decode("utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    if not m:
        raise ValueError(f"Cannot read media duration: {path}\n{log[-1500:]}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), log


def media_info(path):
    duration, log = probe(path)
    line = next((line for line in log.splitlines() if "Video:" in line), "")
    match = re.search(r"\b(\d{2,6})x(\d{2,6})\b", line)
    if not match:
        raise ValueError(f"无法读取视频尺寸：{path}")
    width, height = map(int, match.groups())
    rotation = re.search(r"rotation of ([-\d.]+) degrees", log)
    if rotation and round(float(rotation[1])) % 180 == 90:
        width, height = height, width
    return {"duration": duration, "width": width, "height": height}


def source_identity(path):
    """按内容失效缓存，识别原路径替换而大小和修改时间不变的文件。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return [str(path), digest.hexdigest()]


def key(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:24]


def resolve(base, value):
    return (base / value).resolve()


def verify(
    path,
    limit=None,
    expected=None,
    expected_size=None,
    *,
    allow_silent=False,
    emit=True,
):
    if limit is not None and number(limit, "limit_seconds") <= 0:
        raise ValueError("limit_seconds 必须大于 0")
    duration, log = probe(path)
    if limit is not None and duration >= limit:
        raise ValueError(f"Duration {duration} must be less than {limit}")
    if expected is not None and abs(duration - expected) > 0.15:
        raise ValueError(f"Unexpected duration {duration}; planned {expected}")
    has_audio = "Audio:" in log
    if "Video:" not in log or (not has_audio and not allow_silent):
        raise ValueError("Both video and audio are required")
    r = command(["-v", "error", "-i", path, "-f", "null", "-"])
    if r.stderr.strip():
        raise RuntimeError(r.stderr.decode(errors="replace"))
    peak = None
    if has_audio:
        r = command(["-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"])
        m = re.search(rb"max_volume: ([-\d.]+) dB", r.stderr)
        if m:
            peak = float(m[1])
        elif b"max_volume: -inf dB" not in r.stderr:
            raise ValueError("无法读取音轨峰值，不能判定已验证")
        if (peak is None or peak < -60) and not allow_silent:
            raise ValueError("Audio appears silent")
    info = media_info(path)
    if expected_size and (info["width"], info["height"]) != tuple(expected_size):
        raise ValueError(f"成片尺寸不符：{info}")
    report = {**info, "peak_db": peak, "has_audio": has_audio}
    if emit:
        print(
            json.dumps(
                {
                    "file": str(path),
                    **report,
                    "clipping_risk": peak is not None and peak >= -0.1,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return report


def silence_ranges(log, duration):
    """保留完整时间区间，包括 FFmpeg 未输出 end 的片尾静音。"""
    result, start = [], None
    for event, value in re.findall(r"silence_(start|end):\s*([-+\d.eE]+)", log):
        point = max(0.0, min(float(value), duration))
        if event == "start":
            start = point
        elif start is not None:
            result.append((start, point))
            start = None
    if start is not None:
        result.append((start, duration))
    return result


def plan_observations(prepared):
    """按计划给出待审看线索；不声称已从成片识别到结果或构图。"""
    observations, metadata, offset = [], {}, 0.0
    cw, ch = prepared.canvas
    for index, row in enumerate(prepared.segments):
        a, b = offset, offset + row["duration"]
        common = {"segment": index + 1, "start": a, "end": b, "basis": "plan"}
        speed = (row["end"] - row["start"]) / row["duration"]
        if speed < 1:
            observations.append(
                {
                    **common,
                    "code": "slow_motion",
                    "speed": speed,
                    "reason": "确认慢放是否帮助看清动作，或只是拉长等待/设置页",
                }
            )
        if "crop" in row:
            width, height = row["crop"][2:]
        else:
            source = row["source"]
            if source not in metadata:
                metadata[source] = media_info(prepared.sources[source])
            width, height = metadata[source]["width"], metadata[source]["height"]
        scale = min(cw / width, ch / height)
        padding = max(0.0, 1 - width * height * scale * scale / (cw * ch))
        if padding >= 0.25:
            observations.append(
                {
                    **common,
                    "code": "large_padding",
                    "estimated_padding_ratio": round(padding, 4),
                    "reason": "核对留边用途、实际字号与上下文，不能为消除留边拉伸界面",
                }
            )
        if "highlight" in row and row["highlight"][2] / width >= 0.8:
            observations.append(
                {
                    **common,
                    "code": "wide_highlight",
                    "width_ratio": row["highlight"][2] / width,
                    "reason": "核对是否确需标注整行，避免框住大半页面却没有明确目标",
                }
            )
        offset = b
    return observations


def audit(path, plan_path=None, silence_seconds=1.5, allow_silent=False):
    """只诊断、不修改视频；自动检测永不授予成片审看通过。"""
    if number(silence_seconds, "silence_seconds") <= 0:
        raise ValueError("silence_seconds 必须大于 0")
    prepared, plan = None, None
    if plan_path is not None:
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        prepared = validate(plan, plan_path.resolve().parent)
        if prepared.output != path.resolve():
            raise ValueError("被审看视频与计划 output 不同，不能套用该计划的时间点")
    info = verify(
        path,
        limit=plan["limit_seconds"] if plan else None,
        expected=prepared.total if prepared else None,
        expected_size=prepared.canvas if prepared else None,
        allow_silent=allow_silent,
        emit=False,
    )
    observations = plan_observations(prepared) if prepared else []
    if info["has_audio"]:
        result = command(
            [
                "-i",
                path,
                "-vn",
                "-af",
                f"silencedetect=noise=-40dB:d={silence_seconds}",
                "-f",
                "null",
                "-",
            ]
        )
        for start, end in silence_ranges(
            result.stderr.decode("utf-8", errors="replace"), info["duration"]
        ):
            if end - start >= silence_seconds:
                observations.append(
                    {
                        "code": "long_silence",
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "duration": round(end - start, 3),
                        "basis": "audio",
                        "reason": "回看是否承载阅读、对比或行动指引；不机械删除留白",
                    }
                )
    else:
        observations.append(
            {
                "code": "intentional_silent",
                "start": 0,
                "end": info["duration"],
                "basis": "audio",
                "reason": "已允许静音版；仍须核对静音理解与循环衔接",
            }
        )
    clipping = info["peak_db"] is not None and info["peak_db"] >= -0.1
    if clipping:
        observations.append(
            {
                "code": "clipping_risk",
                "basis": "audio",
                "reason": "峰值接近满幅，调整后复核声音",
            }
        )
    return {
        "file": str(path.resolve()),
        "technical_status": "WARN" if clipping else "PASS",
        "editorial_status": "PENDING",
        "media": info,
        "observations": observations,
        "plan_binding": "仅核对路径、总时长和尺寸，计划提示不证明当前成片内容与计划一致"
        if prepared
        else "未提供计划，未检查慢放/计划留边/高亮宽度",
        "thresholds": {
            "silence_seconds": silence_seconds,
            "noise_db": -40,
            "padding_ratio": 0.25,
            "highlight_width_ratio": 0.8,
        },
        "manual_checks": [
            "真实价值与结果证据",
            "目标观看尺寸下的阅读与构图",
            "切点、字幕与留白目的",
            "试听自然度与发音（静音版不适用）",
            "与完整片或局部样片范围相符的产品识别与下一步",
        ],
    }


def inspect(path, out, step):
    from PIL import Image, ImageDraw

    if step <= 0:
        raise ValueError("step must be positive")
    duration, log = probe(path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "media.txt").write_text(log, encoding="utf-8")
    count = math.ceil(duration / step)
    for page in range(math.ceil(count / 12)):
        sheet = Image.new("RGB", (1440, 4 * 328), "#dddddd")
        draw = ImageDraw.Draw(sheet)
        for cell in range(12):
            t = (page * 12 + cell) * step
            if t >= duration:
                break
            frame = out / f"frame-{page * 12 + cell:05d}.jpg"
            command(
                [
                    "-ss",
                    t,
                    "-i",
                    path,
                    "-frames:v",
                    1,
                    "-vf",
                    "scale=480:300:force_original_aspect_ratio=decrease,pad=480:300:(ow-iw)/2:(oh-ih)/2",
                    frame,
                ]
            )
            with Image.open(frame) as im:
                sheet.paste(im, (cell % 3 * 480, cell // 3 * 328))
            draw.text(
                (cell % 3 * 480 + 8, cell // 3 * 328 + 304), f"{t:.2f}s", fill="black"
            )
        sheet.save(out / f"contact-{page:03d}.jpg")
    print(f"Inspected {duration:.2f}s: {out}", flush=True)


@dataclass
class PreparedPlan:
    sources: dict
    output: Path
    total: float
    canvas: tuple
    segments: list
    narration: list
    captions: list


def number(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} 必须是有限数值")
    return float(value)


def rectangle(value, bounds, name, even=False):
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(type(v) is not int for v in value)
    ):
        raise ValueError(f"{name} 必须是整数 [x, y, width, height]")
    x, y, width, height = value
    bx, by, bw, bh = bounds
    if (
        x < bx
        or y < by
        or width <= 0
        or height <= 0
        or x + width > bx + bw
        or y + height > by + bh
    ):
        raise ValueError(f"{name} 超出画面范围")
    if even and any(v % 2 for v in value):
        raise ValueError(f"{name} 的四个值须为偶数，以免色度采样改变裁剪位置")
    return value


def timed_rows(rows, total, name, require_text=False):
    if not isinstance(rows, list):
        raise TypeError(f"{name} 必须是数组")
    result, previous = [], 0.0
    for row in rows:
        a, b = number(row["start"], name), number(row["end"], name)
        if a < previous or b <= a or b > total:
            raise ValueError(f"{name} 时间越界或重叠")
        if require_text and (
            not isinstance(row.get("text"), str) or not row["text"].strip()
        ):
            raise ValueError(f"{name} 需要正式 text 文稿")
        result.append({**row, "start": a, "end": b})
        previous = b
    return result


def validate(plan, base):
    if ("source" in plan) == ("sources" in plan):
        raise ValueError("source 与 sources 必须且只能提供一种")
    source_paths = {"default": plan["source"]} if "source" in plan else plan["sources"]
    if not isinstance(source_paths, dict) or not source_paths:
        raise ValueError("sources 必须是非空名称到路径的映射")
    if any(
        not isinstance(k, str) or not k or not isinstance(v, str) or not v
        for k, v in source_paths.items()
    ):
        raise ValueError("素材名称和路径须是非空字符串")
    sources = {k: resolve(base, v) for k, v in source_paths.items()}
    output = resolve(base, plan["output"])
    if output.suffix.lower() != ".mp4":
        raise ValueError("输出须使用 .mp4 扩展名")
    input_paths = list(sources.values()) + [
        resolve(base, n["audio_file"])
        for n in plan.get("narration", [])
        if n.get("audio_file")
    ]
    targets = [output, output.with_suffix(".timing.json"), output.with_suffix(".srt")]
    if any(
        target == source
        or (target.exists() and source.exists() and os.path.samefile(target, source))
        for target in targets
        for source in input_paths
    ):
        raise ValueError("输出或附属文件不得覆盖输入素材")
    for field in ("allow_cuts", "allow_reorder", "subtitles"):
        if type(plan.get(field, False)) is not bool:
            raise ValueError(f"{field} 必须是布尔值")
    if plan.get("allow_reorder") and not plan.get("allow_cuts"):
        raise ValueError("allow_reorder 需要同时设置 allow_cuts")
    limit = number(plan["limit_seconds"], "limit_seconds")
    if number(plan.get("max_voice_speed", 1.3), "max_voice_speed") < 1:
        raise ValueError("max_voice_speed 不得小于 1")
    metadata = {k: media_info(v) for k, v in sources.items()}
    first = next(iter(metadata.values()))
    canvas = plan.get(
        "canvas", {"width": first["width"] // 2 * 2, "height": first["height"] // 2 * 2}
    )
    size = (canvas["width"], canvas["height"])
    if any(type(v) is not int or not 2 <= v <= 7680 or v % 2 for v in size):
        raise ValueError("canvas 宽高须为 2 到 7680 之间的偶数")
    font = plan.get(
        "subtitle_font", "Microsoft YaHei" if os.name == "nt" else "sans-serif"
    )
    if not isinstance(font, str) or not font.strip() or any(c in font for c in ",\r\n"):
        raise ValueError("subtitle_font 不是有效字体名称")
    if (plan.get("captions") or plan.get("subtitles") or "subtitle_size" in plan) and (
        not 8
        <= number(
            plan.get("subtitle_size", max(18, round(size[1] * 0.04))), "subtitle_size"
        )
        <= size[1] / 4
    ):
        raise ValueError("subtitle_size 超出可读范围")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", plan.get("highlight_color", "#FFD166")):
        raise ValueError("highlight_color 须为 #RRGGBB")
    if (
        not isinstance(plan.get("segments"), list)
        or not plan["segments"]
        or not plan.get("narration")
    ):
        raise ValueError("需要非空 segments 和 narration")
    total, previous, segments = 0.0, dict.fromkeys(sources, 0.0), []
    for row in plan["segments"]:
        source = row.get("source", "default")
        if source not in sources:
            raise ValueError(f"未知片段 source：{source}")
        info = metadata[source]
        a, b, d = (number(row[k], k) for k in ("start", "end", "duration"))
        if a < 0 or b <= a or d < 1 / 30 or b > info["duration"] + 0.05:
            raise ValueError("片段时间越界或不足一帧")
        if not plan.get("allow_reorder") and a < previous[source] - 0.02:
            raise ValueError("倒序或复用素材需要 allow_reorder")
        if not plan.get("allow_cuts") and abs(a - previous[source]) > 0.02:
            raise ValueError("素材删减需要 allow_cuts")
        bounds = [0, 0, info["width"], info["height"]]
        if "crop" in row:
            bounds = rectangle(row["crop"], bounds, "crop", even=True)
        if "highlight" in row:
            rectangle(row["highlight"], bounds, "highlight")
        segments.append({**row, "source": source, "start": a, "end": b, "duration": d})
        total += d
        previous[source] = b
    if not plan.get("allow_cuts") and any(
        abs(previous[k] - info["duration"]) > 0.05 for k, info in metadata.items()
    ):
        raise ValueError("素材未完整覆盖，需要 allow_cuts")
    if not 0 < total < limit or total > 3600:
        raise ValueError("计划总时长必须小于上限，且不超过一小时")
    narration = timed_rows(plan["narration"], total, "narration")
    for row in narration:
        if not row.get("audio_file") and not (
            isinstance(row.get("text"), str) and row["text"].strip()
        ):
            raise ValueError("配音需要 text 或 audio_file")
        if "spoken_text" in row and (
            not isinstance(row["spoken_text"], str) or not row["spoken_text"].strip()
        ):
            raise ValueError("spoken_text 必须是非空字符串")
    captions = plan.get(
        "captions",
        [{k: n[k] for k in ("start", "end", "text") if k in n} for n in narration]
        if plan.get("subtitles")
        else [],
    )
    captions = timed_rows(captions, total, "captions", require_text=True)
    return PreparedPlan(sources, output, total, size, segments, narration, captions)


def subtitle_time(seconds, srt=False):
    units = 1000 if srt else 100
    value = round(seconds * units)
    hours, value = divmod(value, 3600 * units)
    minutes, value = divmod(value, 60 * units)
    seconds, fraction = divmod(value, units)
    return (
        f"{hours:02}:{minutes:02}:{seconds:02},{fraction:03}"
        if srt
        else f"{hours}:{minutes:02}:{seconds:02}.{fraction:02}"
    )


def wrap_caption(text, capacity):
    """限制两行，保留完整文案；过长时要求改稿而不截字。"""
    lines, current, width = [], "", 0.0
    for char in text.replace("\r", ""):
        cost = 1 if ord(char) > 255 else 0.55
        if char == "\n" or (width + cost > capacity and current):
            lines.append(current)
            current, width = "", 0.0
        if char != "\n":
            current += char
            width += cost
    if current:
        lines.append(current)
    if len(lines) > 2:
        raise ValueError("字幕超过两行，请拆分字幕时间槽或缩短文稿")
    return "\\N".join(
        line.replace("\\", "＼").replace("{", "｛").replace("}", "｝") for line in lines
    )


def subtitle_files(prepared, plan, work):
    width, height = prepared.canvas
    font = plan.get(
        "subtitle_font", "Microsoft YaHei" if os.name == "nt" else "sans-serif"
    )
    size = plan.get("subtitle_size", max(18, round(height * 0.04)))
    margin = max(12, round(height * 0.05))
    ass = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,{margin},{margin},{margin},1",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    srt = []
    for i, row in enumerate(prepared.captions, 1):
        text = wrap_caption(row["text"], (width - 2 * margin) / size * 0.85)
        ass.append(
            f"Dialogue: 0,{subtitle_time(row['start'])},{subtitle_time(row['end'])},Default,,0,0,0,,{text}"
        )
        srt.append(
            f"{i}\n{subtitle_time(row['start'], True)} --> {subtitle_time(row['end'], True)}\n{row['text']}\n"
        )
    content = "\n".join(ass) + "\n"
    path = work / f"captions-{key(content)}.ass"
    path.write_text(content, encoding="utf-8", newline="")
    return path, "\n".join(srt)


def segment_filters(row, size, color):
    filters = [
        f"setpts=(PTS-STARTPTS)/{(row['end'] - row['start']) / row['duration']:.12f}"
    ]
    cx, cy = 0, 0
    if "crop" in row:
        cx, cy, cw, ch = row["crop"]
        filters.append(f"crop={cw}:{ch}:{cx}:{cy}")
    if "highlight" in row:
        x, y, width, height = row["highlight"]
        filters.append(
            f"drawbox=x={x - cx}:y={y - cy}:w={width}:h={height}:color=0x{color[1:]}:t=3"
        )
    width, height = size
    filters.extend(
        [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "setsar=1",
            "fps=30",
            f"tpad=stop_mode=clone:stop_duration={row['duration']}",
        ]
    )
    return ",".join(filters)


async def render(plan_path):
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    base = plan_path.resolve().parent
    prepared = validate(plan, base)
    output, total = prepared.output, prepared.total
    work = output.parent / ".video-work" / plan_path.stem
    inputs = [
        *prepared.sources.values(),
        plan_path.resolve(),
        *(
            resolve(base, n["audio_file"])
            for n in prepared.narration
            if n.get("audio_file")
        ),
    ]
    if any(path.is_relative_to(work) for path in inputs):
        raise ValueError("输入文件不得位于本计划的工作缓存目录内")
    if plan_path.resolve() in (
        output.with_suffix(".timing.json"),
        output.with_suffix(".srt"),
    ):
        raise ValueError("附属文件不得覆盖计划文件")
    work.mkdir(parents=True, exist_ok=True)
    ass, srt = subtitle_files(prepared, plan, work)
    voice = plan.get("voice", "zh-CN-YunxiNeural")
    rate = plan.get("rate", "+0%")
    pcm = array.array("h", [0]) * round(total * RATE)
    narration_report = []
    for n in prepared.narration:
        spoken = n.get("spoken_text", n.get("text", ""))
        if n.get("audio_file"):
            audio = resolve(base, n["audio_file"])
        else:
            import edge_tts

            audio = work / (key([spoken, voice, rate, CACHE_VERSION]) + ".mp3")
            if not audio.exists():
                temp = audio.with_suffix(".pending.mp3")
                for attempt in range(3):
                    try:
                        await asyncio.wait_for(
                            edge_tts.Communicate(spoken, voice, rate=rate).save(
                                str(temp)
                            ),
                            35,
                        )
                        probe(temp)
                        os.replace(temp, audio)
                        break
                    except Exception:
                        temp.unlink(missing_ok=True)
                        if attempt == 2:
                            raise
        duration, _ = probe(audio)
        slot = n["end"] - n["start"]
        speed = max(1.0, duration / slot)
        if speed > float(plan.get("max_voice_speed", 1.3)):
            raise ValueError(
                f"Voice at {n['start']}s needs {speed:.2f}x; shorten text or extend slot"
            )
        # 有限 PCM 缓冲；检查解码器尾部，防止悄悄截断语句。
        r = command(
            [
                "-i",
                audio,
                "-af",
                f"asetpts=PTS-STARTPTS,atempo={speed:.9f}",
                "-t",
                slot + 0.1,
                "-f",
                "s16le",
                "-ac",
                1,
                "-ar",
                RATE,
                "-",
            ],
            timeout=45,
        )
        data = array.array("h")
        data.frombytes(r.stdout)
        if os.sys.byteorder != "little":
            data.byteswap()
        if not data or max(map(abs, data)) < 40:
            raise ValueError("Narration is silent")
        size = round(slot * RATE)
        if len(data) > size and max(map(abs, data[size:]), default=0) > 100:
            raise ValueError(
                "Speech extends beyond slot; adjust timing instead of truncating"
            )
        data = data[:size]
        start = round(n["start"] * RATE)
        pcm[start : start + len(data)] = data
        narration_report.append(
            {
                **n,
                "spoken_text": spoken,
                "voice": voice if not n.get("audio_file") else "external",
                "speed": speed,
            }
        )
    wav = work / "narration.wav"
    if os.sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    source_ids = {k: source_identity(v) for k, v in prepared.sources.items()}
    clips, rows, offset = [], [], 0.0
    for s in prepared.segments:
        source = prepared.sources[s["source"]]
        a, b, d = s["start"], s["end"], s["duration"]
        speed = (b - a) / d
        frame_start, frame_end = round(offset * 30), round((offset + d) * 30)
        filters = segment_filters(
            s, prepared.canvas, plan.get("highlight_color", "#FFD166")
        )
        clip = work / (
            key(
                [
                    source_ids[s["source"]],
                    a,
                    b,
                    d,
                    filters,
                    frame_end - frame_start,
                    CACHE_VERSION,
                ]
            )
            + ".mp4"
        )
        if not clip.exists():
            tmp = clip.with_suffix(".pending.mp4")
            print(f"Rendering {a}–{b}s at {speed:.2f}x", flush=True)
            command(
                [
                    "-ss",
                    a,
                    "-t",
                    b - a,
                    "-i",
                    source,
                    "-an",
                    "-vf",
                    filters,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    20,
                    "-threads",
                    6,
                    "-pix_fmt",
                    "yuv420p",
                    "-frames:v",
                    frame_end - frame_start,
                    tmp,
                ],
                timeout=600,
            )
            os.replace(tmp, clip)
        clips.append(clip)
        rows.append(
            {
                **s,
                "output_start": frame_start / 30,
                "output_end": frame_end / 30,
                "speed": speed,
            }
        )
        offset += d
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in clips), encoding="utf-8")
    video_input = ["-f", "concat", "-safe", 0, "-i", listing]
    if prepared.captions:
        visual = work / (
            "visual-"
            + key(
                [list(map(str, clips)), ass.read_text(encoding="utf-8"), CACHE_VERSION]
            )
            + ".mp4"
        )
        if not visual.exists():
            tmp = visual.with_suffix(".pending.mp4")
            command(
                [
                    *video_input,
                    "-an",
                    "-vf",
                    f"ass={ass.name}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    20,
                    "-threads",
                    6,
                    "-pix_fmt",
                    "yuv420p",
                    tmp,
                ],
                timeout=600,
                cwd=work,
            )
            os.replace(tmp, visual)
        video_input = ["-i", visual]
    pending = work / "final.pending.mp4"
    command(
        [
            *video_input,
            "-i",
            wav,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            total,
            "-movflags",
            "+faststart",
            pending,
        ]
    )
    report = verify(pending, float(plan["limit_seconds"]), total, prepared.canvas)
    if report["peak_db"] >= -0.1:
        raise ValueError("Audio may clip; reduce gain before delivery")
    os.replace(pending, output)
    output.with_suffix(".srt").write_text(srt, encoding="utf-8", newline="")
    output.with_suffix(".timing.json").write_text(
        json.dumps(
            {
                "sources": source_ids,
                "segments": rows,
                "narration": narration_report,
                "captions": prepared.captions,
                "verification": report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Created {output}", flush=True)


def main():
    # 命令行输出统一为 UTF-8，保证中文 JSON 在重定向和子进程中可读取。
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("inspect")
    p.add_argument("source", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--step", type=float, default=5)
    p = sub.add_parser("render")
    p.add_argument("plan", type=Path)
    p = sub.add_parser("verify")
    p.add_argument("video", type=Path)
    p.add_argument("--limit-seconds", type=float)
    p = sub.add_parser("audit")
    p.add_argument("video", type=Path)
    p.add_argument("--plan", type=Path)
    p.add_argument("--silence-seconds", type=float, default=1.5)
    p.add_argument("--allow-silent", action="store_true")
    args = parser.parse_args()
    if args.action == "inspect":
        inspect(args.source, args.out, args.step)
    elif args.action == "render":
        asyncio.run(render(args.plan))
    elif args.action == "audit":
        print(
            json.dumps(
                audit(args.video, args.plan, args.silence_seconds, args.allow_silent),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        verify(args.video, limit=args.limit_seconds)


if __name__ == "__main__":
    main()
