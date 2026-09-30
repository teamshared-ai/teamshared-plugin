#!/usr/bin/env python3
"""Cursor preCompact — summary ingest + durable-facts nudge (#63).

Composes with #59 constraints re-attach when ``constraints_attach`` is
importable (same ``user_message`` channel). Fail-open.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from durable_facts_nudge import run_precompact_with_nudge


def main() -> int:
    return run_precompact_with_nudge(host="cursor")


if __name__ == "__main__":
    raise SystemExit(main())
