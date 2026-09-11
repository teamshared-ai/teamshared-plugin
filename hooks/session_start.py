#!/usr/bin/env python3
"""Cursor sessionStart — map conversation_id → TeamShared working session."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_session_start, run_hook


def main() -> int:
    return run_hook(handle_session_start)


if __name__ == "__main__":
    raise SystemExit(main())
