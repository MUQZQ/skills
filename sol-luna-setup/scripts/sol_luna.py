#!/usr/bin/env python3
"""Sol-Luna 控制面：管理开关、模型选择、角色同步与 Claude Code 调用。"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from subprocess import list2cmdline
from typing import Any, Mapping, Sequence, TextIO


DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "auto",
    "model": "auto",
    "flash_model": "deepseek-v4-flash",
    "pro_model": "deepseek-v4-pro",
    "flash_claude_model": "claude-haiku-4-5-20251001",
    "pro_claude_model": "claude-sonnet-4-6",
    "flash_claude_alias": "haiku",
    "pro_claude_alias": "sonnet",
    "max_task_chars": 2000,
    "max_result_chars": 1200,
    "allow_escalation": True,
}
CLAUDE_FLASH_OVERRIDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_PRO_OVERRIDE_MODEL = "claude-sonnet-4-6"
LUNA_FLASH_PROVIDER_MODEL = "deepseek-v4-flash"
LUNA_PRO_PROVIDER_MODEL = "deepseek-v4-pro"
VALID_MODES = {"off", "auto", "force"}
VALID_MODELS = {"auto", "flash", "pro"}
VALID_RISKS = {"normal", "high"}
VALID_ROLES = {"scout", "worker", "critic", "tester"}
READ_ONLY_ROLES = {"scout", "critic", "tester"}


class SolLunaError(RuntimeError):
    """控制面可预期错误。"""


class LunaDisabledError(SolLunaError):
    """Luna 已被当前有效配置禁用。"""


class ModelMismatchError(SolLunaError):
    """Claude Code 实际模型与请求模型不一致。"""


@dataclass(frozen=True)
class ModelRoute:
    """Claude Code 入口模型与网关实际模型的映射。"""

    selection: str
    claude_model: str
    provider_model: str


class EventMonitor:
    """将 Claude stream-json 事件转换为简洁、脱敏的执行状态。"""

    def __init__(self, status_stream: TextIO, quiet: bool) -> None:
        self.status_stream = status_stream
        self.quiet = quiet
        self.failed = False
        self.final_payload: dict[str, Any] | None = None
        self._last_thinking_report = 0.0
        self._seen_content_blocks: set[tuple[str, int]] = set()

    def _emit(self, message: str) -> None:
        if self.quiet:
            return
        print(f"[sol-luna] {message}", file=self.status_stream, flush=True)

    def starting(self, role: str, model: str) -> None:
        self._emit(f"STARTING role={role} model={model}")

    def handle(self, event: Mapping[str, Any]) -> None:
        event_type = event.get("type")
        subtype = event.get("subtype")
        if event_type == "system" and subtype == "init":
            self._emit(
                "RUNNING "
                f"session={event.get('session_id', 'unknown')} "
                f"model={event.get('model', 'unknown')}"
            )
            return
        if event_type == "system" and subtype == "thinking_tokens":
            now = time.monotonic()
            if now - self._last_thinking_report >= 30.0:
                self._emit(
                    f"RUNNING thinking_tokens={event.get('estimated_tokens', 'unknown')}"
                )
                self._last_thinking_report = now
            return
        if event_type == "assistant":
            message = event.get("message")
            content = message.get("content", []) if isinstance(message, dict) else []
            message_id = str(message.get("id", "unknown")) if isinstance(message, dict) else "unknown"
            for index, item in enumerate(content if isinstance(content, list) else []):
                if not isinstance(item, dict):
                    continue
                block_key = (message_id, index)
                if block_key in self._seen_content_blocks:
                    continue
                self._seen_content_blocks.add(block_key)
                if item.get("type") == "tool_use":
                    self._emit(f"TOOL_ACTIVITY tool={item.get('name', 'unknown')}")
                elif item.get("type") == "text":
                    self._emit("FINALIZING assistant_output_received")
            return
        if event_type == "result":
            self.final_payload = dict(event)
            self.failed = bool(event.get("is_error"))
            state = "FAILED" if self.failed else "SUCCEEDED"
            self._emit(
                f"{state} duration_ms={event.get('duration_ms', 'unknown')} "
                f"turns={event.get('num_turns', 'unknown')}"
            )

    def report_quiet(self, elapsed_seconds: float) -> None:
        if self.final_payload is not None:
            return
        self._emit(f"QUIET elapsed_seconds={elapsed_seconds:.0f} process_still_running=true")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SolLunaError(f"无法读取配置 {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SolLunaError(f"配置必须是 JSON 对象: {path}")
    return value


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("mode") not in VALID_MODES:
        raise SolLunaError("mode 必须是 off、auto 或 force")
    if config.get("model") not in VALID_MODELS:
        raise SolLunaError("model 必须是 auto、flash 或 pro")
    for key in (
        "flash_model",
        "pro_model",
        "flash_claude_model",
        "pro_claude_model",
        "flash_claude_alias",
        "pro_claude_alias",
    ):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise SolLunaError(f"{key} 必须是非空模型 ID")
    if not isinstance(config.get("allow_escalation"), bool):
        raise SolLunaError("allow_escalation 必须是布尔值")
    for key in ("max_task_chars", "max_result_chars"):
        if not isinstance(config.get(key), int) or config[key] <= 0:
            raise SolLunaError(f"{key} 必须是正整数")


def config_path(scope: str, project_root: Path, home: Path) -> Path:
    if scope == "project":
        return project_root / ".codex" / "sol-luna.json"
    if scope == "global":
        return home / ".codex" / "sol-luna.json"
    raise SolLunaError("scope 必须是 project 或 global")


def resolve_config(
    project_root: Path,
    home: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """按 默认 < 全局 < 项目 < 环境变量 合并配置。"""
    env = os.environ if environ is None else environ
    resolved = dict(DEFAULT_CONFIG)
    resolved.update(_read_json(config_path("global", project_root, home)))
    resolved.update(_read_json(config_path("project", project_root, home)))

    env_mapping = {
        "SOL_LUNA_MODE": "mode",
        "SOL_LUNA_MODEL": "model",
        "SOL_LUNA_FLASH_MODEL": "flash_model",
        "SOL_LUNA_PRO_MODEL": "pro_model",
        "SOL_LUNA_FLASH_CLAUDE_MODEL": "flash_claude_model",
        "SOL_LUNA_PRO_CLAUDE_MODEL": "pro_claude_model",
        "SOL_LUNA_FLASH_CLAUDE_ALIAS": "flash_claude_alias",
        "SOL_LUNA_PRO_CLAUDE_ALIAS": "pro_claude_alias",
    }
    for env_name, config_name in env_mapping.items():
        value = env.get(env_name)
        if value:
            resolved[config_name] = value.strip()
    _validate_config(resolved)
    return resolved


def update_config(
    scope: str,
    project_root: Path,
    home: Path,
    updates: Mapping[str, Any],
) -> Path:
    path = config_path(scope, project_root, home)
    current = dict(DEFAULT_CONFIG)
    current.update(_read_json(path))
    current.update(updates)
    _validate_config(current)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def resolve_model(
    config: Mapping[str, Any],
    risk: str,
    requested: str | None = None,
) -> ModelRoute:
    if risk not in VALID_RISKS:
        raise SolLunaError("risk 必须是 normal 或 high")
    selection = requested or str(config["model"])
    if selection not in VALID_MODELS:
        raise SolLunaError("请求模型必须是 auto、flash 或 pro")
    if selection == "auto":
        selection = "pro" if risk == "high" else "flash"
    return ModelRoute(
        selection=selection,
        claude_model=str(config[f"{selection}_claude_alias"]),
        provider_model=str(config[f"{selection}_model"]),
    )


def _unique_backup_path(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return path.with_name(f"{path.name}.{timestamp}.bak")


def configure_claude_settings(
    home: Path,
    config: Mapping[str, Any],
) -> dict[str, str | None]:
    """合并 Luna modelOverrides，保留所有其他 Claude 用户配置。"""
    settings_path = home / ".claude" / "settings.json"
    settings = _read_json(settings_path)
    overrides = settings.get("modelOverrides", {})
    if not isinstance(overrides, dict):
        raise SolLunaError(f"modelOverrides 必须是 JSON 对象: {settings_path}")
    desired = {
        CLAUDE_FLASH_OVERRIDE_MODEL: LUNA_FLASH_PROVIDER_MODEL,
        CLAUDE_PRO_OVERRIDE_MODEL: LUNA_PRO_PROVIDER_MODEL,
    }
    legacy_env_values = {
        "ANTHROPIC_MODEL": {LUNA_FLASH_PROVIDER_MODEL, LUNA_PRO_PROVIDER_MODEL},
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": {LUNA_FLASH_PROVIDER_MODEL},
        "ANTHROPIC_DEFAULT_SONNET_MODEL": {LUNA_PRO_PROVIDER_MODEL},
    }
    env = settings.get("env", {})
    if not isinstance(env, dict):
        raise SolLunaError(f"env 必须是 JSON 对象: {settings_path}")
    removable_env_keys = {
        key
        for key, legacy_values in legacy_env_values.items()
        if env.get(key) in legacy_values
    }
    if (
        all(overrides.get(key) == value for key, value in desired.items())
        and not removable_env_keys
    ):
        return {
            "status": "unchanged",
            "path": str(settings_path),
            "backup": None,
        }

    backup: Path | None = None
    if settings_path.exists():
        backup = _unique_backup_path(settings_path)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(settings_path, backup)
    overrides.update(desired)
    settings["modelOverrides"] = overrides
    for key in removable_env_keys:
        env.pop(key, None)
    settings["env"] = env
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = settings_path.with_name(f".{settings_path.name}.sol-luna.tmp")
    temporary_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary_path.replace(settings_path)
    return {
        "status": "updated",
        "path": str(settings_path),
        "backup": str(backup) if backup else None,
    }


def describe_model_routes(config: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    return {
        selection: {
            "claude_model": str(config[f"{selection}_claude_alias"]),
            "override_model": (
                CLAUDE_FLASH_OVERRIDE_MODEL
                if selection == "flash"
                else CLAUDE_PRO_OVERRIDE_MODEL
            ),
            "provider_model": str(config[f"{selection}_model"]),
        }
        for selection in ("flash", "pro")
    }


def build_claude_command(
    role: str,
    model: str,
    prompt: str,
    config: Mapping[str, Any],
) -> list[str]:
    if config["mode"] == "off":
        raise LunaDisabledError("Luna 已关闭；本次任务必须由 Sol 执行")
    if role not in VALID_ROLES:
        raise SolLunaError(f"未知 Luna 角色: {role}")
    if not prompt.strip():
        raise SolLunaError("任务 prompt 不能为空")

    command = [
        "claude",
        "-p",
        "--agent",
        f"luna-{role}",
        "--model",
        model,
    ]
    if role in READ_ONLY_ROLES:
        command.extend(["--permission-mode", "plan"])
    command.extend(
        [
            "--no-session-persistence",
            "--verbose",
            "--output-format",
            "stream-json",
            prompt,
        ]
    )
    return command


def bound_task_prompt(prompt: str, config: Mapping[str, Any]) -> str:
    """限制单次 Luna 委派颗粒，并要求短输出。"""
    max_task_chars = int(config["max_task_chars"])
    if len(prompt) > max_task_chars:
        raise SolLunaError(
            f"Luna 任务颗粒过大：{len(prompt)} 字符，限制 {max_task_chars}；请由 Sol 拆成多个单目标任务"
        )
    max_result_chars = int(config["max_result_chars"])
    return (
        f"{prompt}\n\n"
        "执行契约：只完成一个单一目标；不要顺带扩展范围。"
        f"最终答复不超过 {max_result_chars} 个字符，只给结论、证据和必要的文件路径/命令。"
        "如果当前任务无法形成一次可独立验证的小闭环，停止执行并返回拆分建议，不要自行扩大任务。"
    )


def bound_result(payload: Mapping[str, Any], max_result_chars: int) -> dict[str, Any]:
    bounded = dict(payload)
    result = bounded.get("result")
    if not isinstance(result, str) or len(result) <= max_result_chars:
        return bounded
    bounded["result"] = result[:max_result_chars]
    metadata = bounded.get("_sol_luna", {})
    metadata = dict(metadata) if isinstance(metadata, dict) else {}
    metadata.update(
        {
            "result_truncated": True,
            "original_result_chars": len(result),
        }
    )
    bounded["_sol_luna"] = metadata
    return bounded


def validate_model_usage(payload: Mapping[str, Any], expected_model: str) -> None:
    usage = payload.get("modelUsage")
    actual_models = set(usage) if isinstance(usage, dict) else set()
    if expected_model not in actual_models:
        actual = ", ".join(sorted(actual_models)) or "无"
        raise ModelMismatchError(
            f"模型不一致：请求 {expected_model}，实际 modelUsage 为 {actual}"
        )


def resolve_claude_executable() -> str:
    candidates = (
        ("claude.exe", "claude.cmd", "claude.bat", "claude")
        if os.name == "nt"
        else ("claude",)
    )
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SolLunaError("未找到 claude 命令，请先安装 Claude Code")


def prepare_process_command(command: Sequence[str]) -> tuple[list[str], str]:
    """安全准备进程命令；prompt 通过 stdin 传递，不进入 Windows shell 命令行。"""
    if not command:
        raise SolLunaError("Claude Code 命令不能为空")
    if len(command) < 2:
        raise SolLunaError("Claude Code prompt 缺失")
    prompt = command[-1]
    fixed_command = list(command[:-1])
    executable = Path(fixed_command[0])
    if os.name == "nt" and executable.suffix.lower() in {".cmd", ".bat"}:
        unsafe = set("&|<>^%\r\n")
        if any(any(char in argument for char in unsafe) for argument in fixed_command):
            raise SolLunaError("Windows wrapper 的固定参数包含不允许的 shell 元字符")
        return ["cmd.exe", "/d", "/s", "/c", list2cmdline(fixed_command)], prompt
    return fixed_command, prompt


def _read_process_stream(
    stream: TextIO,
    source: str,
    events: queue.Queue[tuple[str, str | None]],
) -> None:
    try:
        for line in stream:
            events.put((source, line))
    finally:
        events.put((source, None))


def _write_process_input(
    stream: TextIO,
    prompt: str,
    events: queue.Queue[tuple[str, str | None]],
) -> None:
    try:
        stream.write(prompt)
        stream.flush()
    finally:
        stream.close()
        events.put(("stdin", None))


def parse_stream_event(line: str, noise_lines: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        if line.strip():
            noise_lines.append(line.rstrip())
        return None
    return value if isinstance(value, dict) else None


def reject_unknown_model_warning(lines: Sequence[str]) -> None:
    marker = "is not a model this version of Claude Code recognizes"
    if any(marker in line for line in lines):
        raise SolLunaError(
            "检测到 Claude Code 未知模型窗口警告；请运行 configure-claude 并使用 haiku/sonnet 别名路由"
        )


def run_luna(
    role: str,
    prompt: str,
    config: Mapping[str, Any],
    risk: str,
    requested_model: str | None,
    cwd: Path,
    *,
    quiet: bool = False,
    timeout_seconds: float | None = None,
    quiet_interval_seconds: float = 30.0,
) -> dict[str, Any]:
    route = resolve_model(config, risk, requested_model)
    command = build_claude_command(
        role, route.claude_model, bound_task_prompt(prompt, config), config
    )
    command[0] = resolve_claude_executable()
    process_command, stdin_prompt = prepare_process_command(command)
    monitor = EventMonitor(status_stream=sys.stderr, quiet=quiet)
    monitor.starting(role, route.claude_model)
    try:
        process = subprocess.Popen(
            process_command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError) as exc:
        raise SolLunaError(f"无法启动 Claude Code: {command[0]}") from exc

    if process.stdout is None or process.stderr is None:
        process.kill()
        raise SolLunaError("无法读取 Claude Code 输出流")
    if process.stdin is None:
        process.kill()
        raise SolLunaError("无法向 Claude Code 传递 prompt")
    stream_events: queue.Queue[tuple[str, str | None]] = queue.Queue()
    stdout_thread = threading.Thread(
        target=_read_process_stream,
        args=(process.stdout, "stdout", stream_events),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_process_stream,
        args=(process.stderr, "stderr", stream_events),
        daemon=True,
    )
    stdin_thread = threading.Thread(
        target=_write_process_input,
        args=(process.stdin, stdin_prompt, stream_events),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    stdin_thread.start()

    started_at = time.monotonic()
    last_activity_at = started_at
    last_quiet_report_at = started_at
    closed_streams: set[str] = set()
    stderr_lines: list[str] = []
    stdout_noise: list[str] = []
    try:
        while not {"stdout", "stderr"}.issubset(closed_streams) or process.poll() is None:
            now = time.monotonic()
            if timeout_seconds is not None and now - started_at >= timeout_seconds:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise SolLunaError(
                    f"Claude Code 达到显式 timeout={timeout_seconds:g}s，已终止"
                )
            try:
                source, line = stream_events.get(
                    timeout=min(1.0, quiet_interval_seconds)
                )
            except queue.Empty:
                now = time.monotonic()
                if now - last_activity_at >= quiet_interval_seconds and (
                    now - last_quiet_report_at >= quiet_interval_seconds
                ):
                    monitor.report_quiet(now - started_at)
                    last_quiet_report_at = now
                continue
            if line is None:
                closed_streams.add(source)
                continue
            last_activity_at = time.monotonic()
            if source == "stderr":
                stderr_lines.append(line.rstrip())
                continue
            event = parse_stream_event(line, stdout_noise)
            if event is not None:
                monitor.handle(event)
    except KeyboardInterrupt as exc:
        process.terminate()
        raise SolLunaError("Claude Code 调用已由用户取消") from exc
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        stdin_thread.join(timeout=1)

    returncode = process.wait()
    if returncode != 0:
        detail = "\n".join(stderr_lines[-20:]).strip() or "无错误详情"
        raise SolLunaError(f"Claude Code 调用失败，退出码 {returncode}: {detail}")
    payload = monitor.final_payload
    if payload is None:
        quiet_for = time.monotonic() - last_activity_at
        noise = "\n".join(stdout_noise[-10:]).strip()
        detail = f"；stdout 非 JSON 内容: {noise}" if noise else ""
        raise SolLunaError(
            f"Claude Code 正常退出但没有 result 事件；最后活动距今 {quiet_for:.1f}s{detail}"
        )
    reject_unknown_model_warning([*stdout_noise, *stderr_lines])
    validate_model_usage(payload, route.provider_model)
    return bound_result(payload, int(config["max_result_chars"]))


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def role_template_dir() -> Path:
    return _skill_root() / "references" / "project-template" / ".claude" / "agents"


def role_target_dir(scope: str, project_root: Path, home: Path) -> Path:
    if scope == "project":
        return project_root / ".claude" / "agents"
    if scope == "global":
        return home / ".claude" / "agents"
    raise SolLunaError("scope 必须是 project 或 global")


def audit_roles(scope: str, project_root: Path, home: Path) -> list[dict[str, str]]:
    template_dir = role_template_dir()
    target_dir = role_target_dir(scope, project_root, home)
    results: list[dict[str, str]] = []
    for role in sorted(VALID_ROLES):
        filename = f"luna-{role}.md"
        template = template_dir / filename
        target = target_dir / filename
        if not target.exists():
            status = "missing"
        elif target.read_bytes() == template.read_bytes():
            status = "managed"
        else:
            status = "custom"
        results.append({"role": role, "status": status, "path": str(target)})
    return results


def sync_roles(
    scope: str,
    project_root: Path,
    home: Path,
    replace_custom: bool = False,
) -> list[dict[str, str]]:
    template_dir = role_template_dir()
    target_dir = role_target_dir(scope, project_root, home)
    target_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    for role in sorted(VALID_ROLES):
        filename = f"luna-{role}.md"
        source = template_dir / filename
        target = target_dir / filename
        if not target.exists():
            shutil.copyfile(source, target)
            action = "created"
        elif target.read_bytes() == source.read_bytes():
            action = "unchanged"
        elif replace_custom:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = target.with_name(f"{target.name}.{timestamp}.bak")
            shutil.copyfile(target, backup)
            shutil.copyfile(source, target)
            action = f"replaced (backup: {backup})"
        else:
            action = "kept-custom"
        results.append({"role": role, "action": action, "path": str(target)})
    return results


def _scope_from_args(args: argparse.Namespace) -> str:
    return "global" if getattr(args, "global_scope", False) else "project"


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sol-luna", description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="显示最终有效配置和角色状态")
    status.add_argument("--global", dest="global_scope", action="store_true")

    mode = subparsers.add_parser("mode", help="设置 Luna 使用模式")
    mode.add_argument("value", choices=sorted(VALID_MODES))
    mode.add_argument("--global", dest="global_scope", action="store_true")

    model = subparsers.add_parser("model", help="设置 Luna 模型策略")
    model.add_argument("value", choices=sorted(VALID_MODELS))
    model.add_argument("--global", dest="global_scope", action="store_true")

    subparsers.add_parser(
        "configure-claude",
        help="安全合并 Claude modelOverrides，并备份已有 settings.json",
    )

    audit = subparsers.add_parser("audit", help="只读检查四个 Luna 角色")
    audit.add_argument("--global", dest="global_scope", action="store_true")

    sync = subparsers.add_parser("sync", help="同步四个 Luna 角色")
    sync.add_argument("--global", dest="global_scope", action="store_true")
    sync.add_argument("--replace-custom", action="store_true")

    run = subparsers.add_parser("run", help="以指定 Luna 角色执行一次任务")
    run.add_argument("role", choices=sorted(VALID_ROLES))
    run.add_argument("--model", choices=sorted(VALID_MODELS), default=None)
    run.add_argument("--risk", choices=sorted(VALID_RISKS), default="normal")
    run.add_argument("--quiet", action="store_true", help="只输出最终 JSON")
    run.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help="显式硬超时；默认不因静默自动终止",
    )
    run.add_argument("prompt")

    smoke = subparsers.add_parser("smoke", help="验证 Flash 和 Pro 的实际模型解析")
    smoke.add_argument("--model", choices=["flash", "pro", "all"], default="all")
    smoke.add_argument("--ignore-mode", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    project_root = args.project_root.resolve()
    home = args.home.resolve()
    try:
        config = resolve_config(project_root, home)
        if args.command == "status":
            _print_json(
                {
                    "config": config,
                    "model_routes": describe_model_routes(config),
                    "scope": _scope_from_args(args),
                    "roles": audit_roles(_scope_from_args(args), project_root, home),
                }
            )
        elif args.command == "mode":
            path = update_config(
                _scope_from_args(args), project_root, home, {"mode": args.value}
            )
            print(f"Luna mode={args.value} 已写入 {path}")
        elif args.command == "model":
            path = update_config(
                _scope_from_args(args), project_root, home, {"model": args.value}
            )
            print(f"Luna model={args.value} 已写入 {path}")
        elif args.command == "configure-claude":
            _print_json(configure_claude_settings(home, config))
        elif args.command == "audit":
            _print_json(audit_roles(_scope_from_args(args), project_root, home))
        elif args.command == "sync":
            _print_json(
                sync_roles(
                    _scope_from_args(args),
                    project_root,
                    home,
                    replace_custom=args.replace_custom,
                )
            )
        elif args.command == "run":
            payload = run_luna(
                args.role,
                args.prompt,
                config,
                args.risk,
                args.model,
                project_root,
                quiet=args.quiet,
                timeout_seconds=args.timeout,
            )
            _print_json(payload)
        elif args.command == "smoke":
            smoke_config = dict(config)
            if args.ignore_mode:
                smoke_config["mode"] = "auto"
            selections = ["flash", "pro"] if args.model == "all" else [args.model]
            results = []
            for selection in selections:
                payload = run_luna(
                    "scout",
                    f"只回复 LUNA_{selection.upper()}_SMOKE_OK，不读取文件，不调用工具。",
                    smoke_config,
                    "normal",
                    selection,
                    project_root,
                )
                results.append(
                    {
                        "selection": selection,
                        "modelUsage": sorted(payload.get("modelUsage", {})),
                        "result": payload.get("result"),
                    }
                )
            _print_json(results)
        return 0
    except SolLunaError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
