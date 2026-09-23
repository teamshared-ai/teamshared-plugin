#!/usr/bin/env python3
"""Cursor postToolUseFailure — recall prior fixes before the agent retries.

Read-only: remote memory_recall from tool name + truncated error. Injects
hits as additional_context. Never context_commit — failures are already
capture candidates on postToolUse.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_post_tool_use_failure, run_hook


def main() -> int:
    return run_hook(handle_post_tool_use_failure)


if __name__ == "__main__":
    raise SystemExit(main())
