#!/usr/bin/env python3
"""Claude UserPromptSubmit — append the redacted user prompt (fail-open)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import handle_user_prompt_submit, run_hook


def main() -> int:
    return run_hook(handle_user_prompt_submit)


if __name__ == "__main__":
    raise SystemExit(main())
