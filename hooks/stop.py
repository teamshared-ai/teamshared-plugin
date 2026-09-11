#!/usr/bin/env python3
"""Cursor stop — note aborted/error loops; do not distill after every turn."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_stop, run_hook


def main() -> int:
    return run_hook(handle_stop)


if __name__ == "__main__":
    raise SystemExit(main())
