"""Shared helpers for Cursor hooks that capture Agent Chat into TeamShared.

Stdlib only. Best-effort: never block the agent loop. Writes go through the
hosted TeamShared MCP (memory_session_ensure + memory_session_append +
context_commit + memory_session_close) using the existing Cursor Connect
token when we can find it — not a tsk_ in mcp.json.

sessionStart also injects a capped additional_context block from the
ensure payload (soul / playbook header / optional profile) when useful.

Capture POSTs to the org URL from ``.teamshared/org`` (D1 resolver) and
reuses the Cursor Connect token. Unbound / invalid → ``/mcp``. Does not
register a second TeamShared MCP server.
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
MAX_BOOTSTRAP_CHARS = 3500
MAX_PLAYBOOK_HEADER_CHARS = 1200
MAX_PROFILE_CHARS = 800
MCP_TIMEOUT_SEC = 8
HOOK_CACHE_ENV = "TEAMSHARED_HOOK_CACHE"
SESSION_ENV = "TEAMSHARED_SESSION_ID"
CONVERSATION_ENV = "TEAMSHARED_CONVERSATION_ID"

# Failed test / lint / generic shell — not every successful tool turn.
_SHELL_TOOLS = {"shell", "bash"}
_TEST_LINT_RE = re.compile(
    r"(?i)\b("
    r"pytest|py\.test|unittest|nosetests|"
    r"npm\s+test|npx\s+.*test|pnpm\s+test|yarn\s+test|"
    r"vitest|jest|mocha|ava\b|"
    r"eslint|prettier|ruff|mypy|flake8|pylint|black\b|"
    r"cargo\s+test|go\s+test|phpunit|rspec|"
    r"lint(?:er|ing)?|tsc\b"
    r")\b"
)
_FAIL_LINE_RE = re.compile(
    r"(?i)(\bFAILED\b|\bERROR\b|\bFAIL(?:ED)?\b|Traceback \(most recent call last\)|"
    r"error\[E\d+\]|panic:|FATAL:|Command failed|exit status |exit code |"
    r"npm ERR!|ELIFECYCLE|AssertionError)"
)

_SECRET_RES = [
    re.compile(r"tsk_[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    re.compile(
        r"(?i)\b(authorization|api[_-]?key|access[_-]?token|secret|password|passwd|pwd)"
        r"\s*[:=]\s*\S+"
    ),
]
_URL_USERINFO_RE = re.compile(r"(https?://)([^/@:\s]+):([^@/\s]+)@")
