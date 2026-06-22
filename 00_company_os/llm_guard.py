#!/usr/bin/env python3
"""
LLM Guard — pure helper, stdlib only.
Provides assert_llm_allowed() and log_llm_call() to prevent accidental
LLM token burn from idle/heartbeat/cron ticks without a real work item.

Used by:
- kanban-auto-execute.sh (via inline python3) before every `hermes -z` spawn
- any future Python LLM call site in the NofiTech-Ind repo

Author: forge (task MC-LLM-BURN-FIX-1, 2026-06-22)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

LOG_DIR = Path("/home/nofidofi/NofiTech-Ind/00_company_os/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "llm-calls.jsonl"

BLOCKED_REASONS = {"tick", "heartbeat", "idle_check", "keepalive", "scheduled_noop", ""}


def _now_iso_dubai() -> str:
    """ISO8601 timestamp in Asia/Dubai (UTC+4) — matches the rest of the OS."""
    # Use UTC time then offset; avoids depending on host TZ being set.
    return time.strftime("%Y-%m-%dT%H:%M:%S+04:00", time.gmtime(time.time() + 4 * 3600))


def assert_llm_allowed(context: dict) -> bool:
    """
    Raises ValueError if the LLM call should be blocked.
    Returns True when the call is permitted.

    Required semantics:
    - Missing context → block
    - reason in BLOCKED_REASONS → block
    - No card_id/job_id/user_message_id attached → block
    - trigger == "cron" without card_id or job_id → block
    """
    if not context or not isinstance(context, dict):
        raise ValueError("LLM call blocked: missing or invalid context.")

    reason = context.get("reason")
    trigger = context.get("trigger")

    if reason in BLOCKED_REASONS:
        raise ValueError(f"LLM call blocked: invalid idle reason: {reason!r}")

    has_work_item = any(
        context.get(k) for k in ("card_id", "job_id", "user_message_id")
    )
    if not has_work_item:
        raise ValueError("LLM call blocked: no real work item attached (need card_id, job_id, or user_message_id).")

    if trigger == "cron" and not (context.get("card_id") or context.get("job_id")):
        raise ValueError("LLM call blocked: cron trigger without real card_id or job_id.")

    return True


def log_llm_call(entry: dict) -> None:
    """Append one JSONL row to logs/llm-calls.jsonl. Never raises — best-effort."""
    try:
        row = {"timestamp": _now_iso_dubai(), **entry}
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception as exc:  # pragma: no cover — audit must never break callers
        sys.stderr.write(f"[llm_guard] log_llm_call failed: {exc}\n")


# CLI entry points for shell callers ----------------------------------------

def _cli_check() -> int:
    """Read JSON context from stdin, call assert_llm_allowed, exit 0 ok / 1 blocked."""
    try:
        raw = sys.stdin.read()
        ctx = json.loads(raw) if raw.strip() else {}
        assert_llm_allowed(ctx)
        print(json.dumps({"ok": True, "context": ctx}))
        return 0
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"unexpected: {e}"}), file=sys.stderr)
        return 2


def _cli_log() -> int:
    """Read JSON entry from stdin, append to llm-calls.jsonl."""
    try:
        raw = sys.stdin.read()
        entry = json.loads(raw) if raw.strip() else {}
        log_llm_call(entry)
        print(json.dumps({"ok": True, "logged": True}))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        sys.exit(_cli_check())
    elif cmd == "log":
        sys.exit(_cli_log())
    elif cmd == "path":
        print(str(LOG_FILE))
    else:
        print(f"usage: {sys.argv[0]} [check|log|path]", file=sys.stderr)
        sys.exit(2)