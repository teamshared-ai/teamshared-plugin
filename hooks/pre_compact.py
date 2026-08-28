#!/usr/bin/env python3
"""Cursor preCompact hook — short session summary on the normal ingest path."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import emit_ok, ingest, precompact_summary, read_stdin_json


def main() -> int:
    try:
        payload = read_stdin_json()
        summary = precompact_summary(payload)
        if summary:
            ingest(summary, payload=payload)
    except Exception:
        pass
    emit_ok()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
