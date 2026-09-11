#!/usr/bin/env python3
"""Cursor afterAgentResponse — append the redacted assistant text."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_after_agent_response, run_hook


def main() -> int:
    return run_hook(handle_after_agent_response)


if __name__ == "__main__":
    raise SystemExit(main())
