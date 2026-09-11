#!/usr/bin/env python3
"""Codex PostToolUse — failed Bash only (Codex has no PostToolUseFailure).

Stores a short episodic fact (command + error tail) on the open TeamShared
session. Secrets stripped. Successful commands are ignored.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import (
    emit_ok,
    failed_tool_fact,
    ingest,
    is_shell_tool,
    read_stdin_json,
    tool_failed,
)


def main() -> int:
    try:
        payload = read_stdin_json()
        if not is_shell_tool(payload) or not tool_failed(payload):
            emit_ok()
            return 0
        fact = failed_tool_fact(payload)
        ingest(fact, fact=fact, payload=payload)
    except Exception:  # never block the agent
        pass
    emit_ok()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
