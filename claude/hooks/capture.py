"""Shared helpers for Claude Code hooks that capture chat into TeamShared.

Stdlib only. Best-effort: never block the agent loop. Writes go through the
hosted TeamShared MCP (memory_session_ensure + memory_session_append +
context_commit + memory_session_close) using the org-scoped TEAMSHARED_TOKEN
or Claude Code's native /mcp OAuth. Fail-open if the token is unset or MCP
is unreachable.

Capture POSTs to the org URL from ``.teamshared/org`` (D1 resolver).
Unbound / invalid → ``/mcp``. Does not register a second TeamShared server.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_HOOKS_DIR = Path(__file__).resolve().parent
for _org_dir in (
    _HOOKS_DIR,
    _HOOKS_DIR.parent / "scripts",
    _HOOKS_DIR.parent.parent / "scripts",
    _HOOKS_DIR.parent.parent.parent / "scripts",
):
    if (_org_dir / "org_binding.py").is_file():
        if str(_org_dir) not in sys.path:
            sys.path.insert(0, str(_org_dir))
        break

from org_binding import DEFAULT_MCP_URL, resolve_org_binding

MCP_URL = DEFAULT_MCP_URL  # unbound fallback; live calls use resolve_mcp_url()
PLUGIN_VERSION = "0.13.0"
PROTOCOL_VERSION = "1.29.0"
MAX_COMMAND_CHARS = 200
MAX_ERROR_TAIL_CHARS = 800
MAX_SUMMARY_CHARS = 900
MAX_FACT_CHARS = 1000
MAX_TURN_CHARS = 4000
MAX_TOPIC_CHARS = 200
MCP_TIMEOUT_SEC = 6
SESSION_END_MCP_TIMEOUT_SEC = 1.2
HOOK_CACHE_ENV = "TEAMSHARED_CLAUDE_HOOK_CACHE"
SESSION_ENV = "TEAMSHARED_SESSION_ID"
CONVERSATION_ENV = "TEAMSHARED_CONVERSATION_ID"
