#!/usr/bin/env python3
"""PreCompact durable-facts nudge — call memory_remember for 0–3 facts (#63).

After existing summary ingest (kept fail-open), inject a short host message
telling the agent to store at most 0–3 durable facts via MCP
``memory_remember`` before continuing past compaction.

Same channels as #59 / PR #61 constraints re-attach:
- Cursor ``preCompact`` → ``user_message``
- Claude ``PreCompact`` → ``systemMessage``

Compose with constraints by passing both blocks into ``precompact_extra``
(do not replace constraints). Skip when unbound / no token. Cap length.
Stdlib only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

MAX_NUDGE_CHARS = 520
NUDGE_BODY = (
    "# TeamShared durable facts\n"
    "Before continuing after compaction, call MCP `memory_remember` for at "
    "most 0–3 durable facts (15–50 words each) that would still help a cold "
    "agent next week. Skip trivia. Prefer `kind=preference` / `note` / "
    "decision wording the server already accepts. Do not paraphrase org "
    "constraints (those re-attach from the constraints prompt)."
)

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def nudge_text() -> str:
    """Return the capped durable-facts nudge (never empty)."""
    text = NUDGE_BODY.strip()
    if len(text) > MAX_NUDGE_CHARS:
        text = text[: MAX_NUDGE_CHARS - 1] + "…"
    return text


def should_emit_nudge(*, token: str | None) -> bool:
    """True when auth is available (bound session / token). Fail-open skip otherwise."""
    return bool(isinstance(token, str) and token.strip())


def compose_blocks(*blocks: str) -> str:
    """Join non-empty blocks for a single user_message / systemMessage."""
    parts = [b.strip() for b in blocks if isinstance(b, str) and b.strip()]
    return "\n\n".join(parts)


def precompact_extra(host: str, *blocks: str) -> dict[str, Any]:
    """Host-shaped PreCompact payload from composed blocks.

    ``host`` is ``cursor`` or ``claude``. Empty blocks → ``{}``.
    """
    message = compose_blocks(*blocks)
    if not message:
        return {}
    if host == "claude":
        return {"systemMessage": message}
    return {"user_message": message}


def resolve_auth_token(payload: dict[str, Any] | None = None) -> str | None:
    """Reuse capture Connect / env token resolution. ``None`` when unbound."""
    try:
        import capture as capture_mod  # type: ignore

        resolve_token: Callable[[], str | None] = getattr(
            capture_mod, "resolve_token", lambda: None
        )
        token = resolve_token()
        if isinstance(token, str) and token.strip():
            return token.strip()
    except Exception:
        pass
    for key in ("TEAMSHARED_TOKEN", "TEAMSHARED_STATE_TOKEN"):
        val = os.environ.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def build_precompact_extra(
    host: str,
    payload: dict[str, Any] | None = None,
    *,
    token: str | None = None,
    constraints: str = "",
) -> dict[str, Any]:
    """Compose optional constraints (#59) + durable-facts nudge (#63).

    Summary ingest is the caller's job (keep fail-open capture). This only
    builds the inject payload. Skip nudge when no token.
    """
    if token is None:
        token = resolve_auth_token(payload)
    nudge = nudge_text() if should_emit_nudge(token=token) else ""
    return precompact_extra(host, constraints or "", nudge)


def run_precompact_with_nudge(*, host: str) -> int:
    """Shared PreCompact entry: summary ingest + durable-facts nudge.

    Always fail-open; exit 0. When ``constraints_attach`` is present (e.g.
    after #59 merges), also re-attach verbatim constraints and compose.
    """
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

        constraints = ""
        try:
            import constraints_attach as ca  # type: ignore

            fetch = getattr(ca, "fetch_constraints_text", None)
            if callable(fetch):
                constraints = fetch(payload) or ""
        except Exception:
            constraints = ""

        extra = build_precompact_extra(host, payload, constraints=constraints)
        capture_mod.emit_ok(extra)
    except Exception:
        try:
            sys.stdout.write("{}\n")
            sys.stdout.flush()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(run_precompact_with_nudge(host="cursor"))
