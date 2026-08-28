#!/usr/bin/env python3
"""Cursor postToolUse hook — failed test/lint/shell only.

Stores a short episodic fact (command + error tail) on the open TeamShared
session. Secrets stripped. Full transcript is never sent.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import (
    emit_ok,
    failed_tool_fact,
    ingest,
    is_failed_test_lint_shell,
    read_stdin_json,
)


def main() -> int:
    try:
        payload = read_stdin_json()
        if not is_failed_test_lint_shell(payload):
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
