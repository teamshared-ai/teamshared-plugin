#!/usr/bin/env python3
"""Claude StopFailure — note API-error turns; do not distill."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_stop_failure, run_hook


def main() -> int:
    return run_hook(handle_stop_failure)


if __name__ == "__main__":
    raise SystemExit(main())
