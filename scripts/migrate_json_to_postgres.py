#!/usr/bin/env python3
"""One-time migration: import memory.json and jarvis_config.json into the Memory Service.

Usage:
    python scripts/migrate_json_to_postgres.py [--memory-service-url URL]

Requires the memory service to be running.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_JSON = ROOT / "memory.json"
CONFIG_JSON = ROOT / "jarvis_config.json"


def _post(base_url: str, path: str, data: dict) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _put(base_url: str, path: str, data: dict) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def migrate_memories(base_url: str) -> int:
    if not MEMORY_JSON.exists():
        print(f"[SKIP] {MEMORY_JSON} not found")
        return 0

    data = json.loads(MEMORY_JSON.read_text(encoding="utf-8"))
    count = 0

    # Migrate memories
    memories = data.get("memories", {})
    for key, value in memories.items():
        if not value:  # skip empty values
            continue
        try:
            _post(base_url, "/memories", {"key": key, "value": value})
            print(f"  [OK] memory: {key}")
            count += 1
        except urllib.error.HTTPError as exc:
            print(f"  [ERR] memory {key}: HTTP {exc.code}")

    # Migrate reminders
    reminders = data.get("reminders", [])
    for reminder in reminders:
        if not isinstance(reminder, dict) or reminder.get("triggered"):
            continue
        try:
            _post(base_url, "/reminders", {
                "text": reminder.get("text", ""),
                "scheduled_at": reminder.get("time", ""),
            })
            print(f"  [OK] reminder: {reminder.get('text', '')}")
            count += 1
        except urllib.error.HTTPError as exc:
            print(f"  [ERR] reminder: HTTP {exc.code}")

    return count


def migrate_config(base_url: str) -> int:
    if not CONFIG_JSON.exists():
        print(f"[SKIP] {CONFIG_JSON} not found")
        return 0

    data = json.loads(CONFIG_JSON.read_text(encoding="utf-8-sig"))
    count = 0

    # Store each top-level config section
    for section_key, section_value in data.items():
        try:
            _put(base_url, f"/config/{section_key}", {
                "key": section_key,
                "value": section_value,
            })
            print(f"  [OK] config: {section_key}")
            count += 1
        except urllib.error.HTTPError as exc:
            print(f"  [ERR] config {section_key}: HTTP {exc.code}")

    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate JSON files to Memory Service")
    parser.add_argument(
        "--memory-service-url",
        default="http://localhost:8001",
        help="Base URL of the running Memory Service",
    )
    args = parser.parse_args()

    print(f"Migrating to: {args.memory_service_url}\n")

    # Check health
    try:
        urllib.request.urlopen(f"{args.memory_service_url}/health", timeout=5)
    except Exception as exc:
        print(f"[FATAL] Cannot reach memory service: {exc}")
        return 1

    print("[1/2] Migrating memory.json...")
    memory_count = migrate_memories(args.memory_service_url)
    print(f"  Migrated {memory_count} entries\n")

    print("[2/2] Migrating jarvis_config.json...")
    config_count = migrate_config(args.memory_service_url)
    print(f"  Migrated {config_count} entries\n")

    total = memory_count + config_count
    print(f"Done! Total entries migrated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
