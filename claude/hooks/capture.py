"""Shared helpers for Claude Code hooks that capture chat into TeamShared.

Stdlib only. Best-effort: never block the agent loop. Writes go through the
hosted TeamShared MCP (memory_session_ensure + memory_session_append +
context_commit + memory_session_close) using TEAMSHARED_TOKEN (tsk_ bearer).
Claude Code does not inherit Cursor Connect. Fail-open if the token is unset
or MCP is unreachable.
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

MCP_URL = "https://teamshared.com/mcp"
PLUGIN_VERSION = "0.13.0"
PROTOCOL_VERSION = "1.27.0"
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

Unsure which tool? Call `memory_tools_catalog(need="<intent>")`.

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


def repo_slug(cwd: Path | None = None) -> str:
    cwd = cwd or Path.cwd()
    root = cwd
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
            root = Path(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    slug = str(root).lstrip("/").replace("/", "-")
    return slug or "workspace"


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


def precompact_summary(payload: dict[str, Any]) -> str:
    trigger = payload.get("trigger") or "auto"
    parts = [f"Claude PreCompact ({trigger})"]
    extra = payload.get("custom_instructions")
    if isinstance(extra, str) and extra.strip():
        parts.append(clamp(strip_secrets(extra.strip()), 120))
    hint = _transcript_hint(payload)
    summary = ", ".join(parts) + "."
    if hint:
        summary = f"{summary} {hint}"
    return clamp(strip_secrets(summary), MAX_SUMMARY_CHARS)


def _transcript_hint(payload: dict[str, Any]) -> str:
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        data = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = [line.strip() for line in data.splitlines() if line.strip()][-8:]
    snippets: list[str] = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        text = _transcript_text(entry)
        if text:
            snippets.append(clamp(strip_secrets(text), 160))
    if not snippets:
        return ""
    return "Recent: " + " | ".join(snippets[-3:])


def _transcript_text(entry: dict[str, Any]) -> str:
    message = entry.get("message") if isinstance(entry.get("message"), dict) else entry
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        bits: list[str] = []
        for block in content:
            if isinstance(block, str):
                bits.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                bits.append(str(block.get("text") or ""))
        return " ".join(bits).strip()
    return ""


def _transcript_role(entry: dict[str, Any]) -> str:
    for key in ("role", "type"):
        val = entry.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    message = entry.get("message")
    if isinstance(message, dict):
        val = message.get("role")
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    return ""


def transcript_last_text(payload: dict[str, Any], *, role: str | None = None) -> str:
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        data = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    wanted = role.strip().lower() if isinstance(role, str) and role.strip() else None
    last = ""
    for line in data.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        if wanted:
            found = _transcript_role(entry)
            if found and found != wanted and not found.endswith(wanted):
                continue
        text = _transcript_text(entry)
        if text:
            last = text
    return strip_secrets(last)


def conversation_id(payload: dict[str, Any] | None = None) -> str | None:
    """Claude Code session_id (stable across turns). Not a TeamShared session id."""
    payload = payload or {}
    for key in ("session_id", "sessionId"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    env = os.environ.get(CONVERSATION_ENV)
    if isinstance(env, str) and env.strip():
        return env.strip()
    return None


def session_topic(cid: str | None) -> str:
    if cid:
        return clamp(f"claude:{cid}", MAX_TOPIC_CHARS)
    return "claude"


def session_cache_path() -> Path:
    override = os.environ.get(HOOK_CACHE_ENV)
    if isinstance(override, str) and override.strip():
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME")
    root = Path(xdg) if isinstance(xdg, str) and xdg.strip() else Path.home() / ".cache"
    return root / "teamshared" / "claude-hook-sessions.json"


def _load_session_cache() -> dict[str, Any]:
    try:
        data = json.loads(session_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_session_cache(data: dict[str, Any]) -> None:
    path = session_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def mapped_session_id(cid: str | None) -> str | None:
    if cid:
        data = _load_session_cache()
        convos = data.get("conversations")
        if isinstance(convos, dict):
            entry = convos.get(cid)
            if isinstance(entry, dict):
                sid = entry.get("session_id")
                if isinstance(sid, str) and sid.strip():
                    return sid.strip()
            elif isinstance(entry, str) and entry.strip():
                return entry.strip()
        env_cid = os.environ.get(CONVERSATION_ENV)
        env_sid = os.environ.get(SESSION_ENV)
        if isinstance(env_sid, str) and env_sid.strip():
            if not env_cid or env_cid.strip() == cid:
                return env_sid.strip()
        return None
    env = os.environ.get(SESSION_ENV)
    if isinstance(env, str) and env.strip():
        return env.strip()
    return None


def store_mapped_session(cid: str | None, session_id: str | None) -> None:
    if not cid or not session_id:
        return
    data = _load_session_cache()
    convos = data.get("conversations")
    if not isinstance(convos, dict):
        convos = {}
        data["conversations"] = convos
    convos[cid] = {"session_id": session_id}
    _write_session_cache(data)


def drop_mapped_session(cid: str | None) -> None:
    if not cid:
        return
    data = _load_session_cache()
    convos = data.get("conversations")
    if not isinstance(convos, dict) or cid not in convos:
        return
    convos.pop(cid, None)
    _write_session_cache(data)


def user_prompt_text(payload: dict[str, Any]) -> str:
    text = ""
    for key in ("prompt", "user_prompt", "user_message"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            text = strip_secrets(val.strip())
            break
    if not text:
        text = transcript_last_text(payload, role="user")
    return clamp(text, MAX_TURN_CHARS)


def assistant_response_text(payload: dict[str, Any]) -> str:
    for key in ("last_assistant_message", "text", "response", "assistant_text"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return clamp(strip_secrets(val.strip()), MAX_TURN_CHARS)
    return clamp(transcript_last_text(payload, role="assistant"), MAX_TURN_CHARS)


def resolve_token() -> str | None:
    """Claude Code auth is TEAMSHARED_TOKEN only — no Cursor Connect store."""
    for key in ("TEAMSHARED_TOKEN", "TEAMSHARED_STATE_TOKEN"):
        val = os.environ.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _parse_sse_json(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    if text.lstrip().startswith("{"):
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    for line in text.splitlines():
        if line.startswith("data:"):
            payload = line.split(":", 1)[1].strip()
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return {}


def mcp_call(
    name: str,
    arguments: dict[str, Any],
    token: str,
    url: str = MCP_URL,
    timeout: float = MCP_TIMEOUT_SEC,
) -> dict[str, Any] | None:
    """JSON-RPC tools/call against the hosted TeamShared MCP."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    def post(body: dict[str, Any], session: str | None) -> tuple[dict[str, Any], str | None]:
        req_headers = dict(headers)
        if session:
            req_headers["mcp-session-id"] = session
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers=req_headers,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            session_id = response.headers.get("mcp-session-id") or session
            parsed = _parse_sse_json(response.read() or b"")
            return parsed, session_id

    init_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "teamshared-claude-hooks", "version": PLUGIN_VERSION},
        },
    }
    try:
        _, session = post(init_body, None)
        post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
        result, _ = post(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            session,
        )
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    if result.get("error"):
        return None
    inner = result.get("result")
    return inner if isinstance(inner, dict) else result or {}


def _session_id_from_result(result: dict[str, Any] | None) -> str | None:
    if not result:
        return None
    for key in ("session_id", "sessionId"):
        val = result.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        for key in ("session_id", "sessionId"):
            val = structured.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    for item in result.get("content") or []:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            parsed = json.loads(text)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            val = parsed.get("session_id") or parsed.get("sessionId")
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def _scope_args(payload: dict[str, Any] | None) -> tuple[str, str | None, str | None]:
    cwd = workspace_cwd(payload)
    github = github_slug(cwd)
    return repo_slug(cwd), github, conversation_id(payload)


def ensure_session(
    payload: dict[str, Any] | None = None,
    *,
    fresh: bool = False,
    user: str | None = None,
    token: str | None = None,
) -> str | None:
    """Map this Claude Code session onto a TeamShared working session."""
    token = token if token is not None else resolve_token()
    if not token:
        return None
    payload = payload or {}
    repo, github, cid = _scope_args(payload)
    cached = mapped_session_id(cid)
    if cached and fresh:
        # SessionStart also fires on resume / compact / clear.
        fresh = False
    ensure_args: dict[str, Any] = {
        "repo": repo,
        "topic": session_topic(cid),
        "fresh": fresh,
    }
    if github:
        ensure_args["github"] = github
    if user:
        ensure_args["user"] = clamp(strip_secrets(user), MAX_TURN_CHARS)
    ensured = mcp_call("memory_session_ensure", ensure_args, token)
    session_id = _session_id_from_result(ensured) or (cached if not fresh else None)
    if session_id:
        store_mapped_session(cid, session_id)
    return session_id


def append_turn(
    role: str,
    content: str,
    payload: dict[str, Any] | None = None,
    *,
    token: str | None = None,
) -> bool:
    token = token if token is not None else resolve_token()
    if not token:
        return False
    payload = payload or {}
    content = clamp(strip_secrets(content), MAX_TURN_CHARS)
    if not content:
        return False
    repo, github, cid = _scope_args(payload)
    session_id = mapped_session_id(cid) or ensure_session(payload, token=token, fresh=False)
    if not session_id:
        return False
    args: dict[str, Any] = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "repo": repo,
        "topic": session_topic(cid),
    }
    if github:
        args["github"] = github
    result = mcp_call("memory_session_append", args, token)
    new_id = _session_id_from_result(result)
    if new_id:
        store_mapped_session(cid, new_id)
    return result is not None


def close_session(
    payload: dict[str, Any] | None = None,
    *,
    reason: str | None = None,
    token: str | None = None,
) -> bool:
    token = token if token is not None else resolve_token()
    if not token:
        return False
    payload = payload or {}
    cid = conversation_id(payload)
    session_id = mapped_session_id(cid)
    if reason:
        note = clamp(strip_secrets(f"Claude sessionEnd ({reason})."), MAX_SUMMARY_CHARS)
        append_turn("system", note, payload, token=token)
        session_id = mapped_session_id(cid) or session_id
    if not session_id:
        session_id = ensure_session(payload, token=token, fresh=False)
    if not session_id:
        return False
    result = mcp_call(
        "memory_session_close",
        {"session_id": session_id, "distill": True},
        token,
        timeout=SESSION_END_MCP_TIMEOUT_SEC,
    )
    drop_mapped_session(cid)
    return result is not None


def ingest(
    summary: str,
    *,
    fact: str | None = None,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> bool:
    token = token if token is not None else resolve_token()
    if not token:
        return False
    payload = payload or {}
    repo, github, _cid = _scope_args(payload)
    summary = clamp(strip_secrets(summary), MAX_SUMMARY_CHARS)
    session_id = ensure_session(payload, token=token, fresh=False)
    commit_args: dict[str, Any] = {
        "summary": summary,
        "repo": repo,
        "close": False,
    }
    if github:
        commit_args["github"] = github
    if session_id:
        commit_args["session_id"] = session_id
    if fact:
        commit_args["facts"] = [
            {
                "content": clamp(strip_secrets(fact), MAX_FACT_CHARS),
                "kind": "event",
                "subject": "claude hook",
                "tags": ["origin:agent", "claude", "hook"],
            }
        ]
    committed = mcp_call("context_commit", commit_args, token)
    return committed is not None


def _session_start_fresh(payload: dict[str, Any]) -> bool:
    source = str(payload.get("source") or "startup").strip().lower()
    return source in {"startup", "clear", "fork"}


def handle_session_start(payload: dict[str, Any]) -> dict[str, Any]:
    source = str(payload.get("source") or "startup").strip().lower()
    if source == "clear":
        drop_mapped_session(conversation_id(payload))
    ensure_session(payload, fresh=_session_start_fresh(payload))
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": PROTOCOL_CONTEXT,
        }
    }


def handle_user_prompt_submit(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = user_prompt_text(payload)
    if prompt:
        ensure_session(payload, fresh=False, user=prompt)
    return {}


def handle_stop(payload: dict[str, Any]) -> dict[str, Any]:
    """Claude finished responding. Do not distill — Stop fires after every turn."""
    text = assistant_response_text(payload)
    if text:
        append_turn("assistant", text, payload)
    return {}


def handle_stop_failure(payload: dict[str, Any]) -> dict[str, Any]:
    err = payload.get("error") or "unknown"
    details = payload.get("error_details")
    note = f"Claude StopFailure: {err}."
    if isinstance(details, str) and details.strip():
        note = f"{note} {strip_secrets(details.strip())}"
    append_turn("system", clamp(note, MAX_SUMMARY_CHARS), payload)
    return {}


def handle_session_end(payload: dict[str, Any]) -> dict[str, Any]:
    reason = payload.get("reason") or "other"
    close_session(payload, reason=str(reason))
    return {}


def emit_ok(extra: dict[str, Any] | None = None) -> None:
    sys.stdout.write(json.dumps(extra or {}) + "\n")


def run_hook(handler: Any) -> int:
    extra: dict[str, Any] = {}
    try:
        result = handler(read_stdin_json())
        if isinstance(result, dict):
            extra = result
    except Exception:
        extra = {}
    emit_ok(extra)
    return 0
