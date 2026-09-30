#!/usr/bin/env python3
"""PreToolUse Write|Edit: block local MEMORY.md / .claude/memory (#62).

Fail-closed **only** for matching paths. Non-matching paths and parse
errors stay fail-open (allow). Redirects the agent to MCP
``memory_remember`` (or ``context_commit`` for session distill).

Wired for Cursor ``preToolUse`` (matcher Write|Edit|MultiEdit) and Claude
``PreToolUse`` (matcher Write|Edit|MultiEdit). Stdlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

WRITE_TOOLS = {
    "write",
    "edit",
    "multiedit",
    "write_file",
    "search_replace",
    "create",
    "strreplace",
}

DENY_GUIDANCE = (
    "Do not write local memory files (MEMORY.md / .claude/memory). "
    "Use MCP `memory_remember` for durable facts, or `context_commit` "
    "for session distill."
)


def _norm_posix(path: str) -> str:
    return path.replace("\\", "/").strip()


def is_blocked_path(path: str | None) -> bool:
    """True when ``path`` matches the short deny list (POSIX, case-sensitive).

    Patterns (in spirit of Mem0 ``block_memory_write``):
    - ``**/MEMORY.md`` (basename exactly ``MEMORY.md``)
    - ``**/.claude/memory/**`` (any file under a ``.claude/memory`` dir)
    - ``**/.claude/**/MEMORY.md`` (covered by basename rule)
    - ``**/.cursor/**/MEMORY.md`` (covered by basename rule; kept short)
    """
    if not isinstance(path, str) or not path.strip():
        return False
    p = _norm_posix(path)
    # Strip trailing slash for directory-ish forms; keep basename logic.
    trimmed = p.rstrip("/")
    name = Path(trimmed).name
    if name == "MEMORY.md":
        return True
    # Segment check: .../.claude/memory or .../.claude/memory/...
    parts = trimmed.split("/")
    for i, part in enumerate(parts):
        if part == ".claude" and i + 1 < len(parts) and parts[i + 1] == "memory":
            return True
    return False


def extract_file_path(payload: dict[str, Any]) -> str | None:
    """Pull ``file_path`` / ``path`` from PreToolUse tool input."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "path", "target_file"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    # MultiEdit sometimes nests paths under edits[].
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            for key in ("file_path", "path", "target_file"):
                val = edit.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return None


def tool_name(payload: dict[str, Any]) -> str:
    raw = str(payload.get("tool_name") or payload.get("tool") or "")
    return raw.split("__")[-1].strip().lower()


def is_write_tool(payload: dict[str, Any]) -> bool:
    return tool_name(payload) in WRITE_TOOLS


def is_claude_payload(payload: dict[str, Any]) -> bool:
    name = str(payload.get("hook_event_name") or payload.get("hookEventName") or "")
    return name.lower() == "pretooluse" and (
        "claude" in str(payload.get("session_id") or "").lower()
        or payload.get("hook_event_name") == "PreToolUse"
        or payload.get("hookEventName") == "PreToolUse"
    )


def deny_payload(payload: dict[str, Any], path: str) -> dict[str, Any]:
    """Host-shaped deny response (Cursor permission / Claude HSO)."""
    reason = f"{DENY_GUIDANCE} Blocked path: {path}"
    # Claude PreToolUse uses PascalCase hook_event_name.
    event = payload.get("hook_event_name") or payload.get("hookEventName") or ""
    if str(event) == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    # Cursor preToolUse
    return {"permission": "deny", "agent_message": reason}


def allow_payload(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("hook_event_name") or payload.get("hookEventName") or ""
    if str(event) == "PreToolUse":
        # Empty allow — do not force permissionDecision allow (host default).
        return {}
    return {"permission": "allow"}


def decide(payload: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """Return ``(stdout_json, denied)``. Fail-open → allow on any miss."""
    if not isinstance(payload, dict):
        return {}, False
    try:
        if not is_write_tool(payload):
            return allow_payload(payload), False
        path = extract_file_path(payload)
        if not is_blocked_path(path):
            return allow_payload(payload), False
        assert path is not None
        return deny_payload(payload, path), True
    except Exception:
        return allow_payload(payload) if isinstance(payload, dict) else {}, False


def main() -> int:
    denied = False
    out: dict[str, Any] = {}
    try:
        raw = sys.stdin.read()
        payload: dict[str, Any] = {}
        if raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    payload = parsed
            except ValueError:
                payload = {}
        out, denied = decide(payload)
    except Exception:
        out, denied = {}, False
    try:
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    if denied:
        try:
            sys.stderr.write(DENY_GUIDANCE + "\n")
            sys.stderr.flush()
        except Exception:
            pass
        # Claude: exit 2 is a documented block signal; Cursor ignores non-zero
        # when JSON deny is present. Prefer exit 2 only for Claude PreToolUse.
        event = ""
        try:
            event = str(out.get("hookSpecificOutput", {}).get("hookEventName") or "")
        except Exception:
            event = ""
        if event == "PreToolUse":
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
