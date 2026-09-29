#!/usr/bin/env python3
"""Fetch verbatim TeamShared constraints for SessionStart / PreCompact (#59).

Calls MCP ``prompts/get`` name ``constraints``, falling back to
``resources/read`` on ``teamshared://constraints``. The server already
token-caps (~1000); this client never paraphrases the preference lines.
Fail-open ≤3s: missing token, timeout, auth error, or empty org → ``""``.

Stdlib only. Auth reuses the plugin capture path (Cursor Connect store,
then ``TEAMSHARED_TOKEN`` / ``TEAMSHARED_STATE_TOKEN``).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

BUDGET_SECONDS = 3.0
DEFAULT_MCP_URL = "https://teamshared.com/mcp"
CONSTRAINTS_PROMPT = "constraints"
CONSTRAINTS_URI = "teamshared://constraints"
# Server caps ~1000 tokens; keep a hard byte ceiling as a second guard.
MAX_CONSTRAINTS_CHARS = 4500
CONSTRAINTS_HEADING = "# TeamShared constraints"

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _parse(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace").strip()
    candidates = [text] if text.startswith("{") else [
        line[5:].strip() for line in text.splitlines() if line.startswith("data:")
    ]
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text.strip()
    return ""


def extract_prompt_text(result: dict[str, Any] | None) -> str:
    """Pull verbatim text from a ``prompts/get`` result. Empty when none."""
    if not isinstance(result, dict):
        return ""
    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        text = _message_text(message.get("content"))
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def extract_resource_text(result: dict[str, Any] | None) -> str:
    """Pull verbatim text from a ``resources/read`` result for constraints."""
    if not isinstance(result, dict):
        return ""
    contents = result.get("contents")
    if not isinstance(contents, list):
        # Some gateways unwrap to the resource body directly.
        text = result.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return ""
    for item in contents:
        if not isinstance(item, dict):
            continue
        raw = item.get("text")
        if not isinstance(raw, str) or not raw.strip():
            continue
        stripped = raw.strip()
        if stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
            except ValueError:
                return stripped
            if isinstance(parsed, dict):
                if parsed.get("empty"):
                    return ""
                inner = parsed.get("text")
                if isinstance(inner, str):
                    return inner.strip()
            return stripped
        return stripped
    return ""


def normalize_constraints_text(text: str) -> str:
    """Pass through server text; enforce heading + hard char cap. No paraphrase."""
    text = (text or "").strip()
    if not text:
        return ""
    if not text.startswith(CONSTRAINTS_HEADING):
        text = f"{CONSTRAINTS_HEADING}\n{text}"
    if len(text) > MAX_CONSTRAINTS_CHARS:
        text = text[: MAX_CONSTRAINTS_CHARS - 1] + "…"
    return text


def mcp_rpc(
    url: str,
    token: str,
    method: str,
    params: dict[str, Any],
    deadline: float,
    *,
    client_name: str = "teamshared-constraints",
) -> dict[str, Any] | None:
    """initialize → notifications/initialized → ``method``, inside ``deadline``."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    def post(body: dict[str, Any], session: str | None) -> tuple[dict[str, Any], str | None]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("hook budget spent")
        req_headers = dict(headers)
        if session:
            req_headers["mcp-session-id"] = session
        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST", headers=req_headers
        )
        with urllib.request.urlopen(request, timeout=remaining) as response:
            return _parse(response.read() or b""), response.headers.get("mcp-session-id") or session

    _, session = post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "1"},
            },
        },
        None,
    )
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    reply, _ = post(
        {"jsonrpc": "2.0", "id": 2, "method": method, "params": params},
        session,
    )
    if reply.get("error"):
        return None
    result = reply.get("result")
    return result if isinstance(result, dict) else None


def _resolve_auth(payload: dict[str, Any]) -> tuple[str | None, str]:
    token: str | None = None
    url = (os.environ.get("TEAMSHARED_MCP_URL") or DEFAULT_MCP_URL).strip()
    try:
        import capture as capture_mod  # type: ignore

        resolve_token: Callable[[], str | None] = getattr(
            capture_mod, "resolve_token", lambda: None
        )
        token = resolve_token()
        resolve_mcp_url = getattr(capture_mod, "resolve_mcp_url", None)
        if callable(resolve_mcp_url):
            resolved = resolve_mcp_url(payload)
            if isinstance(resolved, str) and resolved.strip():
                url = resolved.strip()
    except Exception:
        pass
    if not token:
        for key in ("TEAMSHARED_TOKEN", "TEAMSHARED_STATE_TOKEN"):
            val = os.environ.get(key)
            if isinstance(val, str) and val.strip():
                token = val.strip()
                break
    return token, url


def fetch_constraints_text(
    payload: dict[str, Any] | None = None,
    *,
    token: str | None = None,
    url: str | None = None,
    deadline: float | None = None,
) -> str:
    """Return verbatim constraints markdown, or ``""`` on any miss/failure."""
    payload = payload if isinstance(payload, dict) else {}
    if deadline is None:
        deadline = time.monotonic() + BUDGET_SECONDS - 0.15
    if token is None or url is None:
        resolved_token, resolved_url = _resolve_auth(payload)
        token = token if token is not None else resolved_token
        url = url if url is not None else resolved_url
    if not token or not url:
        return ""
    try:
        prompt = mcp_rpc(
            url,
            token,
            "prompts/get",
            {"name": CONSTRAINTS_PROMPT},
            deadline,
        )
        text = extract_prompt_text(prompt)
        if not text:
            resource = mcp_rpc(
                url,
                token,
                "resources/read",
                {"uri": CONSTRAINTS_URI},
                deadline,
            )
            text = extract_resource_text(resource)
        return normalize_constraints_text(text)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return ""
    except Exception:
        return ""


def append_constraints(existing: str, constraints: str) -> str:
    """Append constraints after bootstrap context. Empty stays empty."""
    constraints = (constraints or "").strip()
    existing = (existing or "").rstrip()
    if not constraints:
        return existing
    if not existing:
        return constraints
    return f"{existing}\n\n{constraints}"


def cursor_session_extra(constraints: str) -> dict[str, Any]:
    """Cursor ``sessionStart`` / inject shape (``additional_context``)."""
    constraints = (constraints or "").strip()
    if not constraints:
        return {}
    return {"additional_context": constraints}


def cursor_precompact_extra(constraints: str) -> dict[str, Any]:
    """Cursor ``preCompact`` only supports ``user_message`` (observational).

    Host limitation: Cursor docs do not accept ``additional_context`` on
    ``preCompact``. Emitting ``user_message`` puts the verbatim list into the
    chat so compaction can see it (Honcho / Mem0 pattern). Claude re-attaches
    primarily via SessionStart ``source=compact``.
    """
    constraints = (constraints or "").strip()
    if not constraints:
        return {}
    return {"user_message": constraints}


def claude_session_extra(constraints: str, base_context: str) -> dict[str, Any]:
    """Claude ``SessionStart`` ``hookSpecificOutput.additionalContext``."""
    merged = append_constraints(base_context, constraints)
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": merged,
        }
    }


def claude_precompact_extra(constraints: str) -> dict[str, Any]:
    """Claude ``PreCompact`` accepts top-level ``systemMessage`` (not HSO)."""
    constraints = (constraints or "").strip()
    if not constraints:
        return {}
    return {"systemMessage": constraints}


def _watchdog_emit_empty() -> None:
    sys.stdout.write("{}\n")
    sys.stdout.flush()
    os._exit(0)


def run_precompact_main(*, host: str) -> int:
    """Shared PreCompact entry: ingest summary + re-attach constraints.

    ``host`` is ``cursor`` or ``claude``. Always fail-open; exit 0.
    """
    started = time.monotonic()
    watchdog = threading.Timer(BUDGET_SECONDS, _watchdog_emit_empty)
    watchdog.daemon = True
    watchdog.start()
    extra: dict[str, Any] = {}
    try:
        import capture as capture_mod  # type: ignore

        payload = capture_mod.read_stdin_json()
        try:
            summary = capture_mod.precompact_summary(payload)
            if summary:
                capture_mod.ingest(summary, payload=payload)
        except Exception:
            pass
        constraints = fetch_constraints_text(
            payload, deadline=started + BUDGET_SECONDS - 0.2
        )
        if host == "claude":
            extra = claude_precompact_extra(constraints)
        else:
            extra = cursor_precompact_extra(constraints)
        capture_mod.emit_ok(extra)
    except Exception:
        try:
            sys.stdout.write("{}\n")
            sys.stdout.flush()
        except Exception:
            pass
    finally:
        watchdog.cancel()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_precompact_main(host="cursor"))
