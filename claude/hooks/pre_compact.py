#!/usr/bin/env python3
"""Claude PreCompact — ingest summary + re-attach verbatim constraints (#59).

Claude ``PreCompact`` does not accept ``hookSpecificOutput.additionalContext``.
Non-empty constraints are emitted as top-level ``systemMessage``. Post-compact
re-attach also happens on ``SessionStart`` with ``source=compact``. Fail-open ≤3s.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from constraints_attach import run_precompact_main


def main() -> int:
    return run_precompact_main(host="claude")


if __name__ == "__main__":
    raise SystemExit(main())
