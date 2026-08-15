#!/usr/bin/env python3
"""Sol-Luna 控制面：管理开关、用户模型列表、角色同步与 Codex/Claude 调用。"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
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
    "max_task_chars": 2000,
    "max_result_chars": 1200,
    "allow_escalation": True,
}
VALID_MODES = {"off", "auto", "force"}
VALID_RISKS = {"normal", "high"}
VALID_ROLES = {"scout", "worker", "critic", "tester"}
PLAN_ONLY_ROLES = {"scout", "critic"}
CODEX_ROLE_INSTRUCTIONS = {
    "scout": "保持只读；探索代码、依赖和文档，引用路径与符号，不修改文件。",
    "worker": "只实现有界任务，保持最小 diff；不得 commit、push、建 PR 或部署。",
    "critic": "保持只读；对正确性、安全、回归风险和测试缺口做对抗审查。",
    "tester": "只运行任务卡指定的测试并报告证据；不得顺带修改产品行为。",
}
TASK_BRIEF_FIELDS = (
    "目标",
    "允许范围",
    "禁止范围",
    "约束",
    "预期输出",
    "验证证据",
)
GROUP_STATUSES = {
    "DONE",
    "DONE_WITH_CONCERNS",
    "NEEDS_CONTEXT",
    "NEEDS_COORDINATION",
    "BLOCKED",
}
TASK_STATUSES = {"SATISFIED", "UNSATISFIED", "BLOCKED"}


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
    backend: str
    provider_model: str
    claude_model: str | None
    reasoning_effort: str | None


@dataclass(frozen=True)
class LunaModel:
    """用户维护的单个 Luna 模型路由。"""

    id: str
    label: str
    backend: str
    provider_model: str
    claude_model: str | None
    override_model: str | None
    reasoning_effort: str | None
    aliases: tuple[str, ...]


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
    if not isinstance(config.get("model"), str) or not config["model"].strip():
        raise SolLunaError("model 必须是 auto、default、模型 ID 或模型别名")
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


def luna_model_list_path() -> Path:
    return _skill_root() / "luna-models.json"


def luna_result_schema_path() -> Path:
    return _skill_root() / "references" / "result-schema.json"


def _required_model_text(value: Mapping[str, Any], key: str, index: int) -> str:
    field = value.get(key)
    if not isinstance(field, str) or not field.strip():
        raise SolLunaError(f"Luna 模型列表第 {index + 1} 项的 {key} 必须是非空字符串")
    return field.strip()


def load_luna_models(path: Path | None = None) -> tuple[LunaModel, ...]:
    """读取用户维护的有序模型列表；第一项是默认 Luna。"""
    model_path = path or luna_model_list_path()
    if not model_path.exists():
        raise SolLunaError(f"Luna 模型列表不存在: {model_path}")
    try:
        raw = json.loads(model_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SolLunaError(f"无法读取 Luna 模型列表 {model_path}: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise SolLunaError("Luna 模型列表必须是非空 JSON 数组，第一项作为默认模型")

    models: list[LunaModel] = []
    selectors: dict[str, str] = {}
    override_models: set[str] = set()
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise SolLunaError(f"Luna 模型列表第 {index + 1} 项必须是 JSON 对象")
        aliases_value = value.get("aliases", [])
        if not isinstance(aliases_value, list) or any(
            not isinstance(alias, str) or not alias.strip() for alias in aliases_value
        ):
            raise SolLunaError(
                f"Luna 模型列表第 {index + 1} 项的 aliases 必须是非空字符串数组"
            )
        backend_value = value.get("backend", "claude")
        if not isinstance(backend_value, str) or backend_value not in {
            "claude",
            "codex",
        }:
            raise SolLunaError(
                f"Luna 模型列表第 {index + 1} 项的 backend 必须是 claude 或 codex"
            )
        model = LunaModel(
            id=_required_model_text(value, "id", index),
            label=_required_model_text(value, "label", index),
            backend=backend_value,
            provider_model=_required_model_text(value, "provider_model", index),
            claude_model=(
                _required_model_text(value, "claude_model", index)
                if backend_value == "claude"
                else None
            ),
            override_model=(
                _required_model_text(value, "override_model", index)
                if backend_value == "claude"
                else None
            ),
            reasoning_effort=(
                _required_model_text(value, "reasoning_effort", index)
                if backend_value == "codex"
                else None
            ),
            aliases=tuple(alias.strip() for alias in aliases_value),
        )
        if model.override_model is not None and model.override_model in override_models:
            raise SolLunaError(f"Luna 模型列表存在重复 override_model: {model.override_model}")
        if model.override_model is not None:
            override_models.add(model.override_model)
        for selector in {model.id, model.provider_model, *model.aliases}:
            owner = selectors.get(selector)
            if owner is not None and owner != model.id:
                raise SolLunaError(f"Luna 模型选择名重复: {selector}")
            selectors[selector] = model.id
        models.append(model)
    return tuple(models)


def resolve_model(
    config: Mapping[str, Any],
    risk: str,
    requested: str | None = None,
    *,
    models: Sequence[LunaModel] | None = None,
) -> ModelRoute:
    if risk not in VALID_RISKS:
        raise SolLunaError("risk 必须是 normal 或 high")
    model_list = tuple(models or load_luna_models())
    selection = requested or str(config["model"])
    if selection in {"auto", "default"}:
        selected = model_list[0]
    else:
        selected = next(
            (
                model
                for model in model_list
                if selection in {model.id, model.provider_model, *model.aliases}
            ),
            None,
        )
        if selected is None:
            available = ", ".join(model.id for model in model_list)
            raise SolLunaError(f"未知 Luna 模型 {selection!r}；可选: {available}")
    return ModelRoute(
        selection=selected.id,
        backend=selected.backend,
        provider_model=selected.provider_model,
        claude_model=selected.claude_model,
        reasoning_effort=selected.reasoning_effort,
    )


def _unique_backup_path(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return path.with_name(f"{path.name}.{timestamp}.bak")


def configure_claude_settings(
    home: Path,
    config: Mapping[str, Any],
    models: Sequence[LunaModel] | None = None,
) -> dict[str, str | None]:
    """合并 Luna modelOverrides，保留所有其他 Claude 用户配置。"""
    _ = config
    model_list = tuple(models or load_luna_models())
    settings_path = home / ".claude" / "settings.json"
    settings = _read_json(settings_path)
    overrides = settings.get("modelOverrides", {})
    if not isinstance(overrides, dict):
        raise SolLunaError(f"modelOverrides 必须是 JSON 对象: {settings_path}")
    claude_models = [model for model in model_list if model.backend == "claude"]
    desired = {
        model.override_model: model.provider_model
        for model in claude_models
        if model.override_model is not None
    }
    provider_models = {model.provider_model for model in claude_models}
    legacy_env_values = {
        "ANTHROPIC_MODEL": provider_models,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": {
            model.provider_model for model in claude_models if model.claude_model == "haiku"
        },
        "ANTHROPIC_DEFAULT_SONNET_MODEL": {
            model.provider_model for model in claude_models if model.claude_model == "sonnet"
        },
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


def describe_model_routes(
    config: Mapping[str, Any], models: Sequence[LunaModel] | None = None
) -> list[dict[str, Any]]:
    _ = config
    model_list = tuple(models or load_luna_models())
    routes: list[dict[str, Any]] = []
    for index, model in enumerate(model_list):
        route: dict[str, Any] = {
            "id": model.id,
            "label": model.label,
            "default": index == 0,
            "backend": model.backend,
            "aliases": list(model.aliases),
            "provider_model": model.provider_model,
        }
        if model.backend == "codex":
            route["reasoning_effort"] = model.reasoning_effort
        else:
            route["claude_model"] = model.claude_model
            route["override_model"] = model.override_model
        routes.append(route)
    return routes


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
    if role in PLAN_ONLY_ROLES:
        command.extend(["--permission-mode", "plan"])
    elif role == "tester":
        command.extend(
            ["--permission-mode", "dontAsk", "--allowedTools", "Bash"]
        )
    else:
        command.extend(
            ["--permission-mode", "acceptEdits", "--allowedTools", "Bash"]
        )
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


def build_codex_command(
    role: str,
    model: str,
    reasoning_effort: str,
    cwd: Path,
) -> list[str]:
    if role not in VALID_ROLES:
        raise SolLunaError(f"未知 Luna 角色: {role}")
    sandbox = "read-only" if role in PLAN_ONLY_ROLES else "workspace-write"
    return [
        "codex",
        "exec",
        "--model",
        model,
        "--cd",
        str(cwd),
        "--sandbox",
        sandbox,
        "--ephemeral",
        "--json",
        "--output-schema",
        str(luna_result_schema_path()),
        "--ignore-user-config",
        "--disable",
        "multi_agent",
        "--config",
        "sandbox_workspace_write.network_access=false",
        "--config",
        "mcp_servers={}",
        "--config",
        f'model_reasoning_effort="{reasoning_effort}"',
        "-",
    ]


def bound_task_prompt(prompt: str, config: Mapping[str, Any]) -> str:
    """限制单次 Luna 委派颗粒，并要求短输出。"""
    max_task_chars = int(config["max_task_chars"])
    if len(prompt) > max_task_chars:
        raise SolLunaError(
            f"Luna 任务颗粒过大：{len(prompt)} 字符，限制 {max_task_chars}；请由 Sol 拆成多个单目标任务"
        )
    missing_fields = [
        field
        for field in TASK_BRIEF_FIELDS
        if re.search(
            rf"(?m)^[ \t]*(?:[-*][ \t]*)?{re.escape(field)}[ \t]*[:：][ \t]*\S[^\r\n]*\r?$",
            prompt,
        )
        is None
    ]
    if missing_fields:
        raise SolLunaError(
            f"Luna 任务卡缺少非空字段：{', '.join(missing_fields)}；Sol 必须先明确目标与边界"
        )
    max_result_chars = int(config["max_result_chars"])
    return (
        f"{prompt}\n\n"
        "Sol 委派前置：原始任务必须明确单一目标、允许范围、禁止范围、约束、预期输出和验证证据；"
        "任何一项缺失时停止并返回缺失项，不得猜测或自行扩展。"
        "执行契约：只完成该单一目标，不要顺带扩展范围。"
        f"最终答复的 result 不超过 {max_result_chars} 个字符。"
        "最终只输出一个 JSON 对象，字段必须是 result、group_status、task_results、files_changed、"
        "verification、concerns、coordination；task_results 的每项必须包含非空 task、status 和 evidence。"
        "group_status 只可取 DONE、DONE_WITH_CONCERNS、NEEDS_CONTEXT、NEEDS_COORDINATION、BLOCKED；"
        "task status 只可取 SATISFIED、UNSATISFIED、BLOCKED。DONE 或 DONE_WITH_CONCERNS 时所有 task 必须 SATISFIED。"
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


def resolve_cli_executable(
    command: str,
    disallowed_root: Path | None = None,
) -> str:
    suffixes = (".cmd", ".bat", ".exe", "") if os.name == "nt" else ("",)
    candidates = tuple(f"{command}{suffix}" for suffix in suffixes)
    disallowed_roots = {Path.cwd().resolve()}
    if disallowed_root is not None:
        disallowed_roots.add(disallowed_root.resolve())
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            resolved_path = Path(resolved).resolve()
            if any(resolved_path.is_relative_to(root) for root in disallowed_roots):
                continue
            return resolved
    display_name = "Claude Code" if command == "claude" else "Codex CLI"
    raise SolLunaError(f"未找到 {command} 命令，请先安装 {display_name}")


def resolve_claude_executable(disallowed_root: Path | None = None) -> str:
    return resolve_cli_executable("claude", disallowed_root)


def resolve_codex_executable(disallowed_root: Path | None = None) -> str:
    return resolve_cli_executable("codex", disallowed_root)


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """终止 CLI 及其派生进程，避免 Windows wrapper 在 timeout 后残留。"""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            process.wait(timeout=5)
            return
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            pass
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def prepare_process_command(command: Sequence[str]) -> tuple[list[str], str]:
    """安全准备进程命令；prompt 通过 stdin 传递，不进入 Windows shell 命令行。"""
    if not command:
        raise SolLunaError("执行命令不能为空")
    if len(command) < 2:
        raise SolLunaError("执行 prompt 缺失")
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


def parse_codex_output(stdout: str, route: ModelRoute) -> dict[str, Any]:
    result: str | None = None
    usage: Mapping[str, Any] = {}
    noise: list[str] = []
    for line in stdout.splitlines():
        event = parse_stream_event(line, noise)
        if event is None:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str):
                    result = text
        elif event.get("type") == "turn.completed":
            event_usage = event.get("usage")
            if isinstance(event_usage, dict):
                usage = event_usage
        elif event.get("type") in {"turn.failed", "item.failed", "error"}:
            error = event.get("error")
            if isinstance(error, dict):
                detail = error.get("message") or json.dumps(error, ensure_ascii=False)
            else:
                detail = error or event.get("message") or event.get("type")
            raise SolLunaError(f"Codex JSONL 报告执行失败: {detail}")
    if result is None:
        detail = f"；非 JSON 输出: {' | '.join(noise[-5:])}" if noise else ""
        raise SolLunaError(f"Codex 正常退出但没有 agent_message{detail}")
    structured = parse_structured_result(result, "Codex")
    payload = dict(structured)
    payload.update(
        {
            "requestedModel": route.provider_model,
            "usage": dict(usage),
            "_sol_luna": {
                "backend": "codex",
                "model_verification": "command_only",
            },
        }
    )
    return payload


def validate_result_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "result": str,
        "group_status": str,
        "task_results": list,
        "files_changed": list,
        "verification": list,
        "concerns": list,
        "coordination": list,
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != set(required)
        or any(
            not isinstance(payload.get(key), expected_type)
            for key, expected_type in required.items()
        )
    ):
        raise SolLunaError("最终结果不符合结构化返回契约")
    if not payload["result"].strip() or payload["group_status"] not in GROUP_STATUSES:
        raise SolLunaError("最终结果不符合结构化返回契约")
    for field in ("files_changed", "verification", "concerns", "coordination"):
        if any(
            not isinstance(value, str) or not value.strip()
            for value in payload[field]
        ):
            raise SolLunaError("最终结果不符合结构化返回契约")
    if not payload["verification"] or not payload["task_results"]:
        raise SolLunaError("最终结果不符合结构化返回契约")
    for task_result in payload["task_results"]:
        if not isinstance(task_result, dict) or set(task_result) != {
            "task",
            "status",
            "evidence",
        }:
            raise SolLunaError("最终结果不符合结构化返回契约")
        task = task_result.get("task")
        status = task_result.get("status")
        evidence = task_result.get("evidence")
        if (
            not isinstance(task, str)
            or not task.strip()
            or status not in TASK_STATUSES
            or not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) or not item.strip() for item in evidence)
        ):
            raise SolLunaError("最终结果不符合结构化返回契约")
    if payload["group_status"] in {"DONE", "DONE_WITH_CONCERNS"} and any(
        task_result["status"] != "SATISFIED"
        for task_result in payload["task_results"]
    ):
        raise SolLunaError("组状态与 task 状态矛盾")
    if (
        payload["group_status"] == "DONE" and payload["concerns"]
    ) or (
        payload["group_status"] == "DONE_WITH_CONCERNS"
        and not payload["concerns"]
    ):
        raise SolLunaError("完成态与 concerns 矛盾")
    return dict(payload)


def parse_structured_result(result: str, source: str) -> dict[str, Any]:
    try:
        structured = json.loads(result)
    except json.JSONDecodeError as exc:
        raise SolLunaError(f"{source} 最终结果不符合结构化返回契约") from exc
    try:
        return validate_result_contract(structured)
    except SolLunaError as exc:
        raise SolLunaError(f"{source} {exc}") from exc


def parse_claude_output(
    raw_payload: Mapping[str, Any], route: ModelRoute
) -> dict[str, Any]:
    validate_model_usage(raw_payload, route.provider_model)
    result = raw_payload.get("result")
    if not isinstance(result, str):
        raise SolLunaError("Claude Code 最终结果不符合结构化返回契约")
    payload = parse_structured_result(result, "Claude Code")
    payload.update(
        {
            "requestedModel": route.provider_model,
            "modelUsage": dict(raw_payload.get("modelUsage", {})),
            "_sol_luna": {
                "backend": "claude",
                "model_verification": "verified",
            },
        }
    )
    return payload


def run_codex_luna(
    role: str,
    prompt: str,
    config: Mapping[str, Any],
    route: ModelRoute,
    cwd: Path,
    *,
    quiet: bool = False,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    if route.reasoning_effort is None:
        raise SolLunaError(f"Codex 模型 {route.selection} 缺少 reasoning_effort")
    command = build_codex_command(
        role, route.provider_model, route.reasoning_effort, cwd
    )
    command[0] = resolve_codex_executable(cwd)
    task_prompt = (
        f"你是 luna-{role}。{CODEX_ROLE_INSTRUCTIONS[role]}"
        "不得递归调用 auto-code-generator、Sol-Luna provider 或其他子代理；不得访问网络。"
        "遇到歧义、越界或低置信度时停止并升级给 Sol。\n\n"
        f"{bound_task_prompt(prompt, config)}"
    )
    process_command, stdin_prompt = prepare_process_command([*command, task_prompt])
    if not quiet:
        print(
            f"[sol-luna] STARTING role={role} backend=codex model={route.provider_model}",
            file=sys.stderr,
            flush=True,
        )
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
        stdout, stderr = process.communicate(
            input=stdin_prompt,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        terminate_process_tree(process)
        raise SolLunaError(
            f"Codex 达到显式 timeout={timeout_seconds:g}s，已终止"
        ) from exc
    except (FileNotFoundError, OSError) as exc:
        raise SolLunaError(f"无法启动 Codex CLI: {command[0]}") from exc
    if process.returncode != 0:
        detail = "\n".join(stderr.splitlines()[-20:]).strip() or "无错误详情"
        raise SolLunaError(f"Codex 调用失败，退出码 {process.returncode}: {detail}")
    return bound_result(
        parse_codex_output(stdout, route), int(config["max_result_chars"])
    )


def run_claude_luna(
    role: str,
    prompt: str,
    config: Mapping[str, Any],
    route: ModelRoute,
    cwd: Path,
    *,
    quiet: bool = False,
    timeout_seconds: float | None = None,
    quiet_interval_seconds: float = 30.0,
) -> dict[str, Any]:
    if route.claude_model is None:
        raise SolLunaError(f"Claude 模型 {route.selection} 缺少 claude_model")
    command = build_claude_command(
        role, route.claude_model, bound_task_prompt(prompt, config), config
    )
    command[0] = resolve_claude_executable(cwd)
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
                terminate_process_tree(process)
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
        terminate_process_tree(process)
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
    normalized_payload = parse_claude_output(payload, route)
    return bound_result(normalized_payload, int(config["max_result_chars"]))


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
    if config["mode"] == "off":
        raise LunaDisabledError("Luna 已关闭；本次任务必须由 Sol 执行")
    route = resolve_model(config, risk, requested_model)
    if route.backend == "codex":
        return run_codex_luna(
            role,
            prompt,
            config,
            route,
            cwd,
            quiet=quiet,
            timeout_seconds=timeout_seconds,
        )
    if route.backend == "claude":
        return run_claude_luna(
            role,
            prompt,
            config,
            route,
            cwd,
            quiet=quiet,
            timeout_seconds=timeout_seconds,
            quiet_interval_seconds=quiet_interval_seconds,
        )
    raise SolLunaError(f"不支持的 Luna backend: {route.backend}")


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


def execution_config(
    config: Mapping[str, Any], user_triggered: bool
) -> dict[str, Any]:
    effective = dict(config)
    if effective["mode"] == "off":
        if not user_triggered:
            raise LunaDisabledError(
                "Luna 已显式关闭；如需本次使用，请传 --user-triggered 单次开启"
            )
        effective["mode"] = "auto"
    return effective


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sol-luna", description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="显示最终有效配置和角色状态")
    status.add_argument("--global", dest="global_scope", action="store_true")

    subparsers.add_parser("models", help="列出用户维护的 Luna 模型；第一项为默认")

    mode = subparsers.add_parser("mode", help="设置 Luna 委派策略；off 显式关闭")
    mode.add_argument("value", choices=sorted(VALID_MODES))
    mode.add_argument("--global", dest="global_scope", action="store_true")

    model = subparsers.add_parser("model", help="设置 Luna 模型策略")
    model.add_argument("value", help="auto、default、模型 ID 或模型别名")
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
    run.add_argument(
        "--user-triggered",
        action="store_true",
        help="仅当有效 mode=off 时单次开启；不写配置",
    )
    run.add_argument("--model", default=None, help="模型 ID、别名、auto 或 default")
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

    smoke = subparsers.add_parser("smoke", help="验证用户模型列表的执行路由")
    smoke.add_argument(
        "--user-triggered",
        action="store_true",
        help="仅当有效 mode=off 时单次开启；不写配置",
    )
    smoke.add_argument(
        "--model", default="default", help="模型 ID、别名或 all；默认只验证第一项"
    )
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
            models = load_luna_models()
            _print_json(
                {
                    "config": config,
                    "model_routes": describe_model_routes(config, models),
                    "scope": _scope_from_args(args),
                    "roles": audit_roles(_scope_from_args(args), project_root, home),
                }
            )
        elif args.command == "models":
            _print_json(describe_model_routes(config))
        elif args.command == "mode":
            path = update_config(
                _scope_from_args(args), project_root, home, {"mode": args.value}
            )
            print(f"Luna mode={args.value} 已写入 {path}")
        elif args.command == "model":
            resolve_model(config, "normal", args.value)
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
            run_config = execution_config(config, args.user_triggered)
            payload = run_luna(
                args.role,
                args.prompt,
                run_config,
                args.risk,
                args.model,
                project_root,
                quiet=args.quiet,
                timeout_seconds=args.timeout,
            )
            _print_json(payload)
        elif args.command == "smoke":
            smoke_config = execution_config(config, args.user_triggered)
            model_list = load_luna_models()
            selections = (
                [model.id for model in model_list]
                if args.model == "all"
                else [args.model]
            )
            results = []
            for selection in selections:
                marker = re.sub(r"[^A-Z0-9]+", "_", selection.upper()).strip("_")
                expected_result = f"LUNA_{marker}_SMOKE_OK"
                smoke_task = "\n".join(
                    [
                        f"目标：验证 {selection} 模型并让 result 字段返回 {expected_result}",
                        "允许范围：仅执行无工具的模型响应",
                        "禁止范围：不读取文件，不调用工具，不修改任何状态",
                        f"约束：严格使用统一 JSON 返回契约，result 只含 {expected_result}",
                        f"预期输出：结构化结果中的 result 为 {expected_result}",
                        "验证证据：最终 JSON 的 result 与后端对应的模型验证证据",
                    ]
                )
                payload = run_luna(
                    "scout",
                    smoke_task,
                    smoke_config,
                    "normal",
                    selection,
                    project_root,
                )
                actual_result = payload.get("result")
                if actual_result != expected_result:
                    raise SolLunaError(
                        f"{selection} 冒烟标记不匹配：期望 {expected_result}，实际 {actual_result!r}"
                    )
                results.append(
                    {
                        "selection": selection,
                        "requestedModel": payload.get("requestedModel"),
                        "modelUsage": sorted(payload.get("modelUsage", {})),
                        "modelVerification": payload.get("_sol_luna", {}).get(
                            "model_verification"
                        ),
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
