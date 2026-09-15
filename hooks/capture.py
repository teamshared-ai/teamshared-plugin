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
