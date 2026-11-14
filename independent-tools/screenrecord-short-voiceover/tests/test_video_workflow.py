"""验证计划兼容性、画面边界与真实 FFmpeg 渲染。"""

import asyncio
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "video_workflow.py"
SPEC = importlib.util.spec_from_file_location("video_workflow", SCRIPT)
video = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = video
SPEC.loader.exec_module(video)


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.gettempdir()).resolve()
        self.plan = {
            "source": "input.mp4",
            "output": "demo.mp4",
            "limit_seconds": 5,
            "segments": [{"start": 0, "end": 8, "duration": 4}],
            "narration": [
                {"start": 0, "end": 4, "text": "正式文稿", "spoken_text": "合成发音"}
            ],
        }
        self.media = patch.object(
            video,
            "media_info",
            return_value={"duration": 8, "width": 640, "height": 360},
            create=True,
        )
        self.media.start()
        self.probe = patch.object(
            video, "probe", return_value=(8, "Video: h264, 640x360")
        )
        self.probe.start()
        self.addCleanup(self.media.stop)
        self.addCleanup(self.probe.stop)

    def test_legacy_full_recording(self):
        prepared = video.validate(self.plan, self.base)
        self.assertEqual(prepared.total, 4)
        self.assertEqual(prepared.canvas, (640, 360))
        self.assertEqual(prepared.segments[0]["source"], "default")
        self.assertEqual(prepared.captions, [])

    def test_small_legacy_video_does_not_require_subtitle_space(self):
        with patch.object(
            video, "media_info", return_value={"duration": 8, "width": 64, "height": 32}
        ):
            self.assertEqual(video.validate(self.plan, self.base).canvas, (64, 32))

    def test_verify_rejects_invalid_duration_limit(self):
        for value in [float("nan"), float("inf"), -1]:
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "limit_seconds"),
            ):
                video.verify(self.base / "demo.mp4", limit=value)

    def test_multisource_and_explicit_reorder(self):
        del self.plan["source"]
        self.plan.update(sources={"a": "first.mp4", "b": "second.mp4"}, allow_cuts=True)
        self.plan["segments"] = [
            {"source": "a", "start": 4, "end": 8, "duration": 1},
            {"source": "b", "start": 0, "end": 3, "duration": 2},
            {"source": "a", "start": 0, "end": 2, "duration": 1},
        ]
        with self.assertRaisesRegex(ValueError, "allow_reorder"):
            video.validate(self.plan, self.base)
        self.plan["allow_reorder"] = True
        prepared = video.validate(self.plan, self.base)
        self.assertEqual([s["source"] for s in prepared.segments], ["a", "b", "a"])

    def test_subtitles_use_formal_text(self):
        self.plan["subtitles"] = True
        prepared = video.validate(self.plan, self.base)
        self.assertEqual(
            prepared.captions, [{"start": 0.0, "end": 4.0, "text": "正式文稿"}]
        )

    def test_reject_invalid_numbers_and_subtitle_overlap(self):
        for field, value in [
            ("limit_seconds", float("inf")),
            ("max_voice_speed", 0),
            ("subtitles", "yes"),
        ]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                video.validate({**self.plan, field: value}, self.base)
        for value in [True, float("nan"), -1]:
            invalid = copy.deepcopy(self.plan)
            invalid["segments"][0]["duration"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                video.validate(invalid, self.base)
        self.plan["captions"] = [
            {"start": 0, "end": 3, "text": "甲"},
            {"start": 2, "end": 4, "text": "乙"},
        ]
        with self.assertRaises(ValueError):
            video.validate(self.plan, self.base)

    def test_protect_all_input_files(self):
        del self.plan["source"]
        self.plan.update(sources={"a": "first.mp4", "b": "demo.mp4"})
        self.plan["segments"][0]["source"] = "a"
        with self.assertRaises(ValueError):
            video.validate(self.plan, self.base)
        self.plan = {**self.plan, "sources": {"a": "first.mp4"}}
        self.plan["narration"][0]["audio_file"] = "demo.mp4"
        with self.assertRaises(ValueError):
            video.validate(self.plan, self.base)

    def test_crop_and_highlight_must_fit_source(self):
        self.plan["segments"][0].update(
            crop=[100, 40, 400, 240], highlight=[120, 80, 100, 60]
        )
        self.assertEqual(
            video.validate(self.plan, self.base).segments[0]["crop"],
            [100, 40, 400, 240],
        )
        for field, value in [
            ("crop", [400, 0, 400, 360]),
            ("highlight", [0, 0, 50, 50]),
            ("crop", [0, 0, 639, 360]),
        ]:
            invalid = copy.deepcopy(self.plan)
            invalid["segments"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                video.validate(invalid, self.base)

    def test_gaps_still_require_explicit_cuts(self):
        self.plan["segments"][0]["start"] = 1
        with self.assertRaises(ValueError):
            video.validate(self.plan, self.base)
        self.plan["allow_cuts"] = True
        self.assertEqual(video.validate(self.plan, self.base).total, 4)

    def test_unknown_source_and_conflicting_input_modes(self):
        self.plan["sources"] = {"a": "a.mp4"}
        with self.assertRaises(ValueError):
            video.validate(self.plan, self.base)
        del self.plan["source"]
        self.plan["segments"][0]["source"] = "unknown"
        with self.assertRaisesRegex(ValueError, "未知片段"):
            video.validate(self.plan, self.base)

    def test_subtitle_overflow_is_reported_without_truncation(self):
        with self.assertRaisesRegex(ValueError, "两行"):
            video.wrap_caption("这是不能被静默截断的字幕" * 10, 12)
        escaped = video.wrap_caption(r"文字{\pos(0,0)}", 40)
        self.assertNotIn("{", escaped)
        self.assertNotIn("\\pos", escaped)

    def test_render_rejects_input_in_its_own_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.plan["source"] = ".video-work/plan/input.mp4"
            path = base / "plan.json"
            path.write_text(json.dumps(self.plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "工作缓存"):
                asyncio.run(video.render(path))


class CacheTest(unittest.TestCase):
    def test_same_size_and_mtime_replacement_changes_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"old-content")
            original = source.stat()
            first = video.source_identity(source)
            source.write_bytes(b"new-content")
            os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))
            self.assertNotEqual(first, video.source_identity(source))


class AuditTest(unittest.TestCase):
    def test_silent_audio_and_unreadable_measurement_are_distinct(self):
        log = "Video: h264, 640x360\nAudio: aac"
        decoded = subprocess.CompletedProcess([], 0, b"", b"")
        silent = subprocess.CompletedProcess([], 0, b"", b"max_volume: -inf dB")
        with (
            patch.object(video, "probe", return_value=(2, log)),
            patch.object(video, "command", side_effect=[decoded, silent]),
        ):
            self.assertIsNone(
                video.verify(Path("silent.mp4"), allow_silent=True, emit=False)[
                    "peak_db"
                ]
            )
        with (
            patch.object(video, "probe", return_value=(2, log)),
            patch.object(video, "command", side_effect=[decoded, silent]),
            self.assertRaisesRegex(ValueError, "silent"),
        ):
            video.verify(Path("silent.mp4"), emit=False)
        with (
            patch.object(video, "probe", return_value=(2, log)),
            patch.object(video, "command", return_value=decoded),
            self.assertRaisesRegex(ValueError, "无法读取音轨峰值"),
        ):
            video.verify(Path("broken.mp4"), allow_silent=True, emit=False)

    def test_clipping_never_gets_technical_pass(self):
        info = {
            "duration": 2,
            "width": 640,
            "height": 360,
            "peak_db": 0,
            "has_audio": True,
        }
        with (
            patch.object(video, "verify", return_value=info),
            patch.object(
                video,
                "command",
                return_value=subprocess.CompletedProcess([], 0, b"", b""),
            ),
        ):
            result = video.audit(Path("clip.mp4"))
        self.assertEqual(result["technical_status"], "WARN")
        self.assertEqual(result["observations"][0]["code"], "clipping_risk")

    def test_mismatched_plan_cannot_supply_timing_hints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text("{}", encoding="utf-8")
            prepared = video.PreparedPlan(
                {}, Path(directory) / "different.mp4", 2, (640, 360), [], [], []
            )
            with (
                patch.object(video, "validate", return_value=prepared),
                self.assertRaisesRegex(ValueError, "output 不同"),
            ):
                video.audit(Path(directory) / "sample.mp4", plan_path=path)

    def test_silence_including_unclosed_tail_has_time_ranges(self):
        log = "silence_start: 1.25\nsilence_end: 3.0 | silence_duration: 1.75\nsilence_start: 8.5"
        self.assertEqual(video.silence_ranges(log, 12), [(1.25, 3.0), (8.5, 12)])

    def test_plan_flags_slow_motion_padding_and_wide_highlight(self):
        prepared = video.PreparedPlan(
            {"default": Path("input.mp4")},
            Path("out.mp4"),
            6,
            (1280, 720),
            [
                {
                    "source": "default",
                    "start": 60,
                    "end": 62,
                    "duration": 6,
                    "crop": [0, 0, 1000, 400],
                    "highlight": [0, 0, 850, 80],
                }
            ],
            [],
            [],
        )
        warnings = video.plan_observations(prepared)
        self.assertEqual(
            {row["code"] for row in warnings},
            {"slow_motion", "large_padding", "wide_highlight"},
        )
        self.assertTrue(all(row["start"] == 0 and row["end"] == 6 for row in warnings))

    def test_no_warnings_never_equals_editorial_approval(self):
        info = {
            "duration": 12,
            "width": 1280,
            "height": 720,
            "peak_db": -3,
            "has_audio": True,
        }
        with (
            patch.object(video, "verify", return_value=info),
            patch.object(
                video,
                "command",
                return_value=subprocess.CompletedProcess([], 0, b"", b""),
            ),
        ):
            report = video.audit(Path("sample.mp4"))
        self.assertEqual(report["technical_status"], "PASS")
        self.assertEqual(report["editorial_status"], "PENDING")
        self.assertEqual(report["observations"], [])

    def test_authorized_silent_version_is_not_an_audio_failure(self):
        log = "Video: h264, 640x360"
        with (
            patch.object(video, "probe", return_value=(2, log)),
            patch.object(
                video,
                "command",
                return_value=subprocess.CompletedProcess([], 0, b"", b""),
            ),
        ):
            info = video.verify(Path("silent.mp4"), allow_silent=True, emit=False)
            self.assertFalse(info["has_audio"])
            with self.assertRaises(ValueError):
                video.verify(Path("silent.mp4"), emit=False)

    def test_invalid_silence_threshold_fails_before_decoding(self):
        for value in [0, -1, float("nan"), float("inf")]:
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "silence_seconds"),
            ):
                video.audit(Path("sample.mp4"), silence_seconds=value)


@unittest.skipUnless(
    os.environ.get("VIDEO_WORKFLOW_SMOKE") == "1",
    "设置 VIDEO_WORKFLOW_SMOKE=1 运行真实渲染",
)
class RenderTest(unittest.TestCase):
    def test_audit_cli_reports_long_tail_and_allows_silent_export(self):
        with tempfile.TemporaryDirectory(prefix="video-audit-") as directory:
            base = Path(directory)
            output = base / "sample.mp4"
            video.command(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "color=blue:s=320x180:r=30:d=4",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=1",
                    "-af",
                    "adelay=300,apad=whole_dur=4",
                    "-t",
                    "4",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    output,
                ]
            )
            before = video.source_identity(output)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "audit", str(output)],
                check=True,
                capture_output=True,
                timeout=60,
                env={**os.environ, "PYTHONIOENCODING": "gbk", "PYTHONUTF8": "0"},
            )
            report = json.loads(result.stdout)
            silence = [r for r in report["observations"] if r["code"] == "long_silence"]
            self.assertEqual(len(silence), 1)
            self.assertAlmostEqual(silence[0]["start"], 1.3, delta=0.1)
            self.assertAlmostEqual(silence[0]["end"], 4, delta=0.1)
            self.assertEqual(report["editorial_status"], "PENDING")
            self.assertEqual(before, video.source_identity(output))
            silent = base / "silent.mp4"
            video.command(["-i", output, "-an", "-c:v", "copy", silent])
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "audit", str(silent), "--allow-silent"],
                check=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(json.loads(result.stdout)["technical_status"], "PASS")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "audit", str(silent)],
                check=False,
                capture_output=True,
                timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_multisource_captions_cache_and_legacy_cli(self):
        with tempfile.TemporaryDirectory(prefix="video-smoke-") as directory:
            base = Path(directory)
            for name, color, size in [
                ("a", "red", "640x360"),
                ("b", "blue", "320x240"),
            ]:
                video.command(
                    [
                        "-f",
                        "lavfi",
                        "-i",
                        f"color={color}:s={size}:r=30",
                        "-t",
                        "2",
                        "-c:v",
                        "libx264",
                        base / f"{name}.mp4",
                    ]
                )
            video.command(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=0.8",
                    base / "voice.wav",
                ]
            )
            plan = {
                "sources": {"a": "a.mp4", "b": "b.mp4"},
                "output": "out.mp4",
                "limit_seconds": 5,
                "canvas": {"width": 640, "height": 360},
                "subtitles": True,
                "segments": [
                    {
                        "source": "a",
                        "start": 0,
                        "end": 2,
                        "duration": 1.05,
                        "crop": [40, 20, 560, 300],
                        "highlight": [80, 60, 100, 60],
                    },
                    {"source": "b", "start": 0, "end": 2, "duration": 2.95},
                ],
                "narration": [
                    {
                        "start": 0,
                        "end": 1,
                        "text": "参数提取",
                        "audio_file": "voice.wav",
                    },
                    {
                        "start": 2,
                        "end": 3,
                        "text": "知识库查询",
                        "audio_file": "voice.wav",
                    },
                ],
            }
            path = base / "plan.json"

            def render():
                path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "render", str(path)],
                    check=False,
                    capture_output=True,
                    timeout=120,
                )
                self.assertEqual(
                    result.returncode, 0, result.stderr.decode(errors="replace")
                )

            render()
            report = json.loads((base / "out.timing.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(report["verification"]["duration"], 4, delta=0.05)
            self.assertEqual(report["verification"]["width"], 640)
            self.assertEqual(report["verification"]["height"], 360)
            self.assertEqual(report["segments"][0]["output_end"], 32 / 30)
            self.assertEqual(report["segments"][1]["output_start"], 32 / 30)
            self.assertIn("知识库查询", (base / "out.srt").read_text(encoding="utf-8"))
            frame = video.command(
                [
                    "-ss",
                    "2.5",
                    "-i",
                    base / "out.mp4",
                    "-frames:v",
                    "1",
                    "-vf",
                    "crop=2:2:320:180",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ]
            ).stdout
            self.assertGreater(frame[2], frame[0] + 100)
            cache = base / ".video-work" / "plan"
            before = {
                p.name: p.stat().st_mtime_ns
                for p in cache.glob("*.mp4")
                if "pending" not in p.name
            }
            video.command(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=660:duration=0.8",
                    base / "voice.wav",
                ]
            )
            render()
            after = {
                p.name: p.stat().st_mtime_ns
                for p in cache.glob("*.mp4")
                if "pending" not in p.name
            }
            self.assertEqual(before, after, "只改音频不得重编画面")
            video.command(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "color=green:s=320x240:r=30",
                    "-t",
                    "2",
                    "-c:v",
                    "libx264",
                    base / "b.mp4",
                ]
            )
            render()
            frame = video.command(
                [
                    "-ss",
                    "2.5",
                    "-i",
                    base / "out.mp4",
                    "-frames:v",
                    "1",
                    "-vf",
                    "crop=2:2:320:180",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ]
            ).stdout
            self.assertGreater(frame[1], frame[2] + 50)
            plan = {
                "source": "a.mp4",
                "output": "legacy.mp4",
                "limit_seconds": 3,
                "segments": [{"start": 0, "end": 2, "duration": 2}],
                "narration": [{"start": 0, "end": 1, "audio_file": "voice.wav"}],
            }
            render()
            self.assertAlmostEqual(video.probe(base / "legacy.mp4")[0], 2, delta=0.05)


if __name__ == "__main__":
    unittest.main()
