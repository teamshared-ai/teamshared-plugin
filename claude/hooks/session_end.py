#!/usr/bin/env python3
"""Claude SessionEnd — close and distill the mapped TeamShared session."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_session_end, run_hook


def main() -> int:
    return run_hook(handle_session_end)


if __name__ == "__main__":
    raise SystemExit(main())
