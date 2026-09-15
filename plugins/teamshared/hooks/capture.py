"""Shared helpers for Codex hooks that capture chat into TeamShared.

Stdlib only. Best-effort: never block the agent loop. Writes go through the
hosted TeamShared MCP (memory_session_ensure + memory_session_append +
context_commit + memory_session_close).

Auth for hook subprocesses (they cannot see Codex's in-process OAuth):
1. Codex MCP OAuth file store at ``$CODEX_HOME/.credentials.json``
   (default ``~/.codex/.credentials.json``) — documented file fallback.
2. ``TEAMSHARED_TOKEN`` / ``TEAMSHARED_STATE_TOKEN`` last resort for the
   subprocess only. Native ``.mcp.json`` stays OAuth-only; do not mix the
   ``install/codex/`` TOML path with this plugin.

Keyring-only OAuth (no file fallback) is a documented gap: SessionStart still
injects protocol 1.29.0; capture writes fail-open. Codex has no StopFailure
or PostToolUseFailure events.

Capture POSTs to the org URL from ``.teamshared/org`` (D1 resolver).
Unbound / invalid → ``/mcp``. Does not register a second TeamShared server.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
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
SESSION_END_MCP_TIMEOUT_SEC = 2.0
HOOK_CACHE_ENV = "TEAMSHARED_CODEX_HOOK_CACHE"
SESSION_ENV = "TEAMSHARED_SESSION_ID"
CONVERSATION_ENV = "TEAMSHARED_CONVERSATION_ID"
CODEX_HOME_ENV = "CODEX_HOME"
CREDENTIALS_FILENAME = ".credentials.json"

# Codex shell tools (official hook name: Bash; exec_command also matches Bash).
_SHELL_TOOLS = {"bash", "shell"}

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
_EXIT_CODE_RE = re.compile(r"(?i)exit code\s+(\d+)")

# Injected on SessionStart (official additionalContext). Keep under Codex's
# ~2,500-token hook-output cap. Full protocol lives in skills/teamshared-memory.
PROTOCOL_CONTEXT = f"""# TeamShared memory protocol {PROTOCOL_VERSION}

The `teamshared` MCP server is durable memory across sessions and repos.
This Codex plugin authenticates with MCP OAuth discovery — connect when
prompted. `.mcp.json` stores no tokens. Do not mix with `install/codex/`
(`TEAMSHARED_TOKEN`). Do not call `mcp_auth` as the first hop. Never store
secrets, tokens, or credentials. Follow the `teamshared-memory` skill
(protocol {PROTOCOL_VERSION}) for fetch/store, CRM, and version updates.

Unsure which tool? Call `memory_tools_catalog(need=\"<intent>\")`.

## Every turn

1. `memory_session_ensure(repo=..., topic=..., fresh=<first turn>, user=<request>)`
   Bound work → `work_id=`; named playbook → `playbook_slug=`. Omit both when
   unbound. Adopt non-empty `soul`, `agent_memory`, and `playbook` from ensure.
2. `memory_recall(...)` for keywords. Resume handoff: `memory_changes_since(cursor=...)`.
   Named playbook/skill/entity → `memory_playbook_get` / `memory_skill_get` / `memory_entity_view`.
3. Do the work.
4. `context_commit(summary=..., facts=[...], repo=..., github=..., close=<done?>)`
   — last MCP call of the turn.

On the first turn (or when asked about versions), call `version` with
`installed_rule_version` `{PROTOCOL_VERSION}`. If `update_available: true`, tell the
user to upgrade this plugin. You may add a short note to `~/.codex/AGENTS.md`
(or the repo `AGENTS.md`). Do not write Cursor or Claude rule files. Never
invent a version.

`memory_recall` may return `degraded: true` with `errors_by_pillar` — treat as
partial. Plugin hooks already capture this chat into TeamShared working memory
(`UserPromptSubmit` / `Stop` / `SessionEnd`) once trusted via `/hooks`.
Still recall first; do not re-append the same user/assistant text in the
same turn. Codex has no `StopFailure` or `PostToolUseFailure`.
"""
