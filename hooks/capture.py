"""Shared helpers for Cursor hooks that capture Agent Chat into TeamShared.

Stdlib only. Best-effort: never block the agent loop. Writes go through the
hosted TeamShared MCP (memory_session_ensure + memory_session_append +
context_commit + memory_session_close) using the existing Cursor Connect
token when we can find it — not a tsk_ in mcp.json.
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
PLUGIN_VERSION = "0.11.0"
MAX_COMMAND_CHARS = 200
MAX_ERROR_TAIL_CHARS = 800
MAX_SUMMARY_CHARS = 900
MAX_FACT_CHARS = 1000
MAX_TURN_CHARS = 4000
MAX_TOPIC_CHARS = 200
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


def tool_output(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("tool_output", "tool_response", "output"):
        parsed = _as_dict(payload.get(key))
        if parsed:
            return parsed
    return {}


def command_text(payload: dict[str, Any]) -> str:
    inp = tool_input(payload)
    cmd = inp.get("command") or inp.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(str(part) for part in cmd)
    return strip_secrets(str(cmd).strip())


def _exit_code(payload: dict[str, Any]) -> int | None:
    out = tool_output(payload)
    for key in ("exitCode", "exit_code", "status"):
        val = out.get(key)
        if isinstance(val, bool):
            continue
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.strip().lstrip("-").isdigit():
            return int(val)
    raw = payload.get("tool_output") or payload.get("tool_response")
    if isinstance(raw, str) and re.search(r'"exitCode"\s*:\s*([0-9]+)', raw):
        return int(re.search(r'"exitCode"\s*:\s*([0-9]+)', raw).group(1))
    return None


def _combined_output(payload: dict[str, Any]) -> str:
    out = tool_output(payload)
    chunks: list[str] = []
    for key in ("stderr", "stdout", "output", "content"):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            chunks.append(val)
    if not chunks:
        raw = payload.get("tool_output") or payload.get("tool_response") or ""
        if isinstance(raw, str):
            chunks.append(raw)
    return "\n".join(chunks)


def is_shell_tool(payload: dict[str, Any]) -> bool:
    return tool_name(payload).split(":")[-1].lower() in _SHELL_TOOLS


def looks_like_test_or_lint(command: str) -> bool:
    return bool(_TEST_LINT_RE.search(command))


def is_failed_test_lint_shell(payload: dict[str, Any]) -> bool:
    """postToolUse fires after the Shell tool ran; we only keep failures."""
    if not is_shell_tool(payload):
        return False
    command = command_text(payload)
    if not command:
        return False
    code = _exit_code(payload)
    if code == 0:
        return False
    if code is not None and code != 0:
        return True
    output = _combined_output(payload)
    if looks_like_test_or_lint(command) and _FAIL_LINE_RE.search(output):
        return True
    return False


def error_tail(payload: dict[str, Any]) -> str:
    text = strip_secrets(_combined_output(payload))
    if not text:
        err = payload.get("error_message")
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
    body = f"Cursor postToolUse: `{command}` {exit_bit}."
    if tail:
        body = f"{body}\n{tail}"
    return clamp(strip_secrets(body), MAX_FACT_CHARS)


def workspace_cwd(payload: dict[str, Any] | None = None) -> Path:
    payload = payload or {}
    roots = payload.get("workspace_roots")
    first_root = roots[0] if isinstance(roots, list) and roots else None
    for candidate in (
        payload.get("cwd"),
        first_root,
        os.environ.get("CURSOR_PROJECT_DIR"),
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
    pct = payload.get("context_usage_percent")
    tokens = payload.get("context_tokens")
    window = payload.get("context_window_size")
    messages = payload.get("message_count")
    first = payload.get("is_first_compaction")
    parts = [f"Cursor preCompact ({trigger})"]
    if pct is not None:
        parts.append(f"context {pct}%")
    if tokens is not None and window is not None:
        parts.append(f"{tokens}/{window} tokens")
    if messages is not None:
        parts.append(f"{messages} messages")
    if first is True:
        parts.append("first compaction")
    summary = ", ".join(parts) + "."
    extra = _transcript_hint(payload)
    if extra:
        summary = f"{summary} {extra}"
    return clamp(strip_secrets(summary), MAX_SUMMARY_CHARS)


def _transcript_hint(payload: dict[str, Any]) -> str:
    path = payload.get("transcript_path") or os.environ.get("CURSOR_TRANSCRIPT_PATH")
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        data = Path(path).read_text(encoding="utf-8", errors="replace")
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
    """Best-effort last turn from an undocumented transcript_path JSONL file."""
    path = payload.get("transcript_path") or os.environ.get("CURSOR_TRANSCRIPT_PATH")
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        data = Path(path).read_text(encoding="utf-8", errors="replace")
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
    """Cursor conversation id (stable across turns). Not a TeamShared session id."""
    payload = payload or {}
    for key in ("conversation_id", "conversationId"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    # sessionStart / sessionEnd use session_id as an alias of conversation_id.
    val = payload.get("session_id") or payload.get("sessionId")
    if isinstance(val, str) and val.strip():
        return val.strip()
    env = os.environ.get(CONVERSATION_ENV)
    if isinstance(env, str) and env.strip():
        return env.strip()
    return None


def session_topic(cid: str | None) -> str:
    if cid:
        return clamp(f"cursor:{cid}", MAX_TOPIC_CHARS)
    return "cursor"


def session_cache_path() -> Path:
    override = os.environ.get(HOOK_CACHE_ENV)
    if isinstance(override, str) and override.strip():
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME")
    root = Path(xdg) if isinstance(xdg, str) and xdg.strip() else Path.home() / ".cache"
    return root / "teamshared" / "cursor-hook-sessions.json"


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


def _attachment_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    raw = payload.get("attachments")
    if not isinstance(raw, list):
        return names
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = item.get("file_path") or item.get("path") or item.get("name")
        if isinstance(path, str) and path.strip():
            names.append(Path(path).name)
    return names


def user_prompt_text(payload: dict[str, Any]) -> str:
    text = ""
    for key in ("prompt", "user_prompt", "user_message"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            text = strip_secrets(val.strip())
            break
    if not text:
        text = transcript_last_text(payload, role="user")
    names = _attachment_names(payload)
    if names:
        extra = "[attachments: " + ", ".join(names) + "]"
        text = f"{text}\n{extra}" if text else extra
    return clamp(text, MAX_TURN_CHARS)


def assistant_response_text(payload: dict[str, Any]) -> str:
    for key in ("text", "response", "assistant_text", "message"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return clamp(strip_secrets(val.strip()), MAX_TURN_CHARS)
    return clamp(transcript_last_text(payload, role="assistant"), MAX_TURN_CHARS)


def resolve_token() -> str | None:
    """Reuse Cursor Connect when possible. Env token is a silent backup only."""
    token = _token_from_cursor_store()
    if token:
        return token
    for key in ("TEAMSHARED_TOKEN", "TEAMSHARED_STATE_TOKEN"):
        val = os.environ.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _token_from_cursor_store() -> str | None:
    homes = [
        Path.home() / ".config/Cursor/User/globalStorage/state.vscdb",
        Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        homes.append(Path(appdata) / "Cursor/User/globalStorage/state.vscdb")
    for db in homes:
        token = _token_from_vscdb(db)
        if token:
            return token
    return None


def _token_from_vscdb(db: Path) -> str | None:
    if not db.is_file():
        return None
    try:
        import sqlite3
    except ImportError:
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT key, value FROM ItemTable WHERE "
                "lower(key) LIKE '%mcp%' OR lower(key) LIKE '%teamshared%' "
                "OR lower(key) LIKE '%oauth%'"
            ).fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    for key, value in rows:
        blob = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
        if "teamshared.com" not in blob.lower() and "teamshared" not in str(key).lower():
            continue
        token = _access_token_from_blob(blob)
        if token:
            return token
    return None


def _access_token_from_blob(blob: str) -> str | None:
    try:
        data = json.loads(blob)
    except ValueError:
        return None
    return _find_access_token(data)


def _find_access_token(node: Any, depth: int = 0) -> str | None:
    if depth > 6:
        return None
    if isinstance(node, dict):
        for key in ("access_token", "accessToken", "token"):
            val = node.get(key)
            if isinstance(val, str) and len(val) > 12 and " " not in val.strip():
                return val.strip()
        for val in node.values():
            found = _find_access_token(val, depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_access_token(item, depth + 1)
            if found:
                return found
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


def mcp_call(name: str, arguments: dict[str, Any], token: str, url: str = MCP_URL) -> dict[str, Any] | None:
    """JSON-RPC tools/call against the already-connected TeamShared MCP."""
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
        with urllib.request.urlopen(request, timeout=MCP_TIMEOUT_SEC) as response:
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
            "clientInfo": {"name": "teamshared-cursor-hooks", "version": PLUGIN_VERSION},
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
    """Map this Cursor conversation onto a TeamShared working session."""
    token = token if token is not None else resolve_token()
    if not token:
        return None
    payload = payload or {}
    repo, github, cid = _scope_args(payload)
    cached = mapped_session_id(cid)
    if cached and fresh:
        # sessionStart can fire more than once for the same composer id.
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
    """Append one redacted turn via memory_session_append (self-healing)."""
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
    """Close + distill the mapped working session when the composer ends."""
    token = token if token is not None else resolve_token()
    if not token:
        return False
    payload = payload or {}
    cid = conversation_id(payload)
    session_id = mapped_session_id(cid)
    if reason:
        note = clamp(strip_secrets(f"Cursor sessionEnd ({reason})."), MAX_SUMMARY_CHARS)
        append_turn("system", note, payload, token=token)
        session_id = mapped_session_id(cid) or session_id
    if not session_id:
        session_id = ensure_session(payload, token=token, fresh=False)
    if not session_id:
        return False
    result = mcp_call("memory_session_close", {"session_id": session_id, "distill": True}, token)
    drop_mapped_session(cid)
    return result is not None


def ingest(
    summary: str,
    *,
    fact: str | None = None,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> bool:
    """Append to the open session via the normal MCP ingest path."""
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
                "subject": "cursor hook",
                "tags": ["origin:agent", "cursor", "hook"],
            }
        ]
    committed = mcp_call("context_commit", commit_args, token)
    return committed is not None


def handle_session_start(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = ensure_session(payload, fresh=True)
    extra: dict[str, Any] = {}
    env: dict[str, str] = {}
    cid = conversation_id(payload)
    if cid:
        env[CONVERSATION_ENV] = cid
    if session_id:
        env[SESSION_ENV] = session_id
    if env:
        extra["env"] = env
    return extra


def handle_before_submit_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = user_prompt_text(payload)
    if prompt:
        ensure_session(payload, fresh=False, user=prompt)
    return {"continue": True}


def handle_after_agent_response(payload: dict[str, Any]) -> dict[str, Any]:
    text = assistant_response_text(payload)
    if text:
        append_turn("assistant", text, payload)
    return {}


def handle_stop(payload: dict[str, Any]) -> dict[str, Any]:
    """Agent loop ended. Do not distill here — stop fires after every turn."""
    status = str(payload.get("status") or "").strip().lower()
    if status in {"aborted", "error"}:
        append_turn("system", f"Cursor stop: {status}.", payload)
    return {}


def handle_session_end(payload: dict[str, Any]) -> dict[str, Any]:
    reason = payload.get("reason") or payload.get("final_status") or "completed"
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
