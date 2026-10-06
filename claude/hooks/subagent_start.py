#!/usr/bin/env python3
"""Claude SubagentStart — inject protocol 1.31.0 + the parent's cached recall.

Local only (no network). Fail-open: any error still exits 0 so the subagent
starts normally (#66).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    try:
        from capture import handle_subagent_start, run_hook
    except Exception:
        sys.stdout.write("{}\n")
        return 0
    return run_hook(handle_subagent_start)


if __name__ == "__main__":
    raise SystemExit(main())
