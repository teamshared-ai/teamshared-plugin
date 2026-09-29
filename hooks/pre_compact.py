#!/usr/bin/env python3
"""Cursor preCompact — ingest summary + re-attach verbatim constraints (#59).

Cursor ``preCompact`` is observational: it cannot inject ``additional_context``.
When constraints are non-empty we emit them as ``user_message`` so the
standing rules enter the chat before compaction (host limitation documented
in ``constraints_attach.cursor_precompact_extra``). Fail-open ≤3s.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from constraints_attach import run_precompact_main


def main() -> int:
    return run_precompact_main(host="cursor")


if __name__ == "__main__":
    raise SystemExit(main())
