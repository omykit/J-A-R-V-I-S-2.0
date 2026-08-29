#!/usr/bin/env python3
"""Quick JARVIS smoke tests for config, syntax, assets, and safe file routing."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _print_result(ok: bool, message: str) -> bool:
    marker = "PASS" if ok else "FAIL"
    print(f"[{marker}] {message}")
    return ok


def test_config() -> bool:
    try:
        config = json.loads((ROOT / "jarvis_config.json").read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return _print_result(False, f"Config JSON failed: {exc}")

    required = ["assistant_name", "owner_name", "voice", "ai", "weather"]
    missing = [key for key in required if key not in config]
    if missing:
        return _print_result(False, f"Config missing keys: {', '.join(missing)}")

    weather_key = str(config.get("weather", {}).get("weather_api_key") or "").strip()
    if weather_key:
        return _print_result(False, "Config still contains inline weather_api_key")

    return _print_result(True, "Config JSON valid and free of inline weather secrets")


def test_python_syntax() -> bool:
    source_files = [
        "jarvis_desktop.py",
        "voice_engine.py",
        "command_handler.py",
        "ai_module.py",
        "memory_module.py",
    ]
    for file_name in source_files:
        try:
            ast.parse((ROOT / file_name).read_text(encoding="utf-8-sig"))
        except SyntaxError as exc:
            return _print_result(False, f"{file_name} syntax error: {exc}")
    return _print_result(True, "Python source syntax OK")


def test_models() -> bool:
    required_paths = [
        "vosk-model-en-us-0.22",
        "vosk-model-small-en-us-0.15",
        "voices/en_US-lessac-medium.onnx",
        "voices/en_US-lessac-medium.onnx.json",
    ]
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    if missing:
        return _print_result(False, f"Missing model assets: {', '.join(missing)}")
    return _print_result(True, "Vosk and Piper assets found")


def test_memory() -> bool:
    try:
        memory = json.loads((ROOT / "memory.json").read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return _print_result(False, f"Memory JSON failed: {exc}")

    if not isinstance(memory.get("memories"), dict):
        return _print_result(False, "Memory store must contain a memories object")
    if not isinstance(memory.get("reminders"), list):
        return _print_result(False, "Memory store must contain a reminders list")
    return _print_result(True, "Memory JSON valid and clean")


def test_safe_file_routing() -> bool:
    sys.path.insert(0, str(ROOT))
    from command_handler import CommandHandler

    config = json.loads((ROOT / "jarvis_config.json").read_text(encoding="utf-8-sig"))
    handler = CommandHandler(config=config, project_dir=ROOT)
    sanitized = handler._sanitize_name("../../dangerous.txt")
    if "/" in sanitized or "\\" in sanitized or ".." in sanitized:
        return _print_result(False, f"Unsafe sanitized filename: {sanitized}")
    if handler.notes_dir != handler.workspace_dir / "notes":
        return _print_result(False, "Notes directory is not isolated under workspace/notes")
    return _print_result(True, "File operation routing is confined to notes directory")


def main() -> int:
    print("JARVIS Smoke Tests\n")
    results = [
        test_config(),
        test_python_syntax(),
        test_models(),
        test_memory(),
        test_safe_file_routing(),
    ]
    print(f"\nPassed: {sum(results)}/{len(results)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
