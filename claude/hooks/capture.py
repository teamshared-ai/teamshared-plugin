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

# Claude Code shell tools (official names: Bash, PowerShell).
_SHELL_TOOLS = {"bash", "powershell", "shell"}

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

# Injected on SessionStart (official additionalContext). Keep under the
# 10k hook-output cap. Full protocol lives in skills/teamshared-memory.
PROTOCOL_CONTEXT = f"""# TeamShared memory protocol {PROTOCOL_VERSION}

The `teamshared` MCP server is durable memory across sessions and repos.
Auth is a `tsk_` bearer from `TEAMSHARED_TOKEN`. Claude Code does not inherit
Cursor Connect. Do not call `mcp_auth` as the first hop. Never store secrets,
tokens, or credentials. Follow the `teamshared-memory` skill (protocol {PROTOCOL_VERSION})
for fetch/store, CRM, and version updates.

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
`installed_rule_version` `{PROTOCOL_VERSION}`. If `update_available: true`, write
`rule_markdown` verbatim to `~/.claude/rules/teamshared.md` (or
`.claude/rules/teamshared.md` in a repo). Never invent a version.

`memory_recall` may return `degraded: true` with `errors_by_pillar` — treat as
partial. Plugin hooks already capture this chat into TeamShared working memory
(`UserPromptSubmit` / `Stop` / `SessionEnd`). Still recall first; do not
re-append the same user/assistant text in the same turn.
"""


def clamp(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def strip_secrets(text: str) -> str:
    if not text:
        return ""
    text = _URL_USERINFO_RE.sub(r"\1[redacted]:[redacted]@", text)
    for pat in _SECRET_RES:
        text = pat.sub("[redacted]", text)
    return text


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def tool_name(payload: dict[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("tool") or "").strip()


def tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(payload.get("tool_input") or payload.get("input"))


def command_text(payload: dict[str, Any]) -> str:
    inp = tool_input(payload)
    cmd = inp.get("command") or inp.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(str(part) for part in cmd)
    return strip_secrets(str(cmd).strip())


def _exit_code(payload: dict[str, Any]) -> int | None:
    err = payload.get("error")
    if isinstance(err, str):
        match = _EXIT_CODE_RE.search(err)
        if match:
            return int(match.group(1))
    out = _as_dict(payload.get("tool_response") or payload.get("tool_output"))
    for key in ("exitCode", "exit_code", "status"):
        val = out.get(key)
        if isinstance(val, bool):
            continue
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.strip().lstrip("-").isdigit():
            return int(val)
    return None


def _combined_output(payload: dict[str, Any]) -> str:
    err = payload.get("error")
    if isinstance(err, str) and err.strip():
        return err
    out = _as_dict(payload.get("tool_response") or payload.get("tool_output"))
    chunks: list[str] = []
    for key in ("stderr", "stdout", "output", "content"):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            chunks.append(val)
    return "\n".join(chunks)


def is_shell_tool(payload: dict[str, Any]) -> bool:
    return tool_name(payload).split(":")[-1].lower() in _SHELL_TOOLS


def error_tail(payload: dict[str, Any]) -> str:
    text = strip_secrets(_combined_output(payload))
    if not text:
        err = payload.get("error_message") or payload.get("error_details")
        if isinstance(err, str):
            text = strip_secrets(err)
    text = text.strip()
    if len(text) > MAX_ERROR_TAIL_CHARS:
        text = text[-MAX_ERROR_TAIL_CHARS:]
        text = "…" + text.lstrip()
    return text


def failed_tool_fact(payload: dict[str, Any]) -> str:
    command = clamp(command_text(payload), MAX_COMMAND_CHARS)
    code = _exit_code(payload)
    exit_bit = f"exit {code}" if code is not None else "failed"
    tail = error_tail(payload)
    body = f"Claude PostToolUseFailure: `{command}` {exit_bit}."
    if tail:
        body = f"{body}\n{tail}"
    return clamp(strip_secrets(body), MAX_FACT_CHARS)


def workspace_cwd(payload: dict[str, Any] | None = None) -> Path:
    payload = payload or {}
    for candidate in (
        payload.get("cwd"),
        os.environ.get("CLAUDE_PROJECT_DIR"),
        os.getcwd(),
    ):
        if isinstance(candidate, str) and candidate.strip():
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return Path.cwd()


def _git_toplevel(cwd: Path) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def repo_root(cwd: Path | None = None) -> Path:
    cwd = cwd or Path.cwd()
    top = _git_toplevel(cwd)
    return top if top is not None else cwd


def repo_slug(cwd: Path | None = None) -> str:
    slug = str(repo_root(cwd)).lstrip("/").replace("/", "-")
    return slug or "workspace"


def resolve_mcp_url(payload: dict[str, Any] | None = None) -> str:
    """Bound repo → ``/o/{slug}/mcp``; missing or invalid binding → ``/mcp``."""
    return resolve_org_binding(repo_root(workspace_cwd(payload))).url


def github_slug(cwd: Path | None = None) -> str | None:
    cwd = cwd or Path.cwd()
    try:
        out = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0:
            value = out.stdout.strip()
            if value and "/" in value and " " not in value:
                return value
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None
