"""Shared helpers for Claude Code hooks that capture chat into TeamShared.

Stdlib only. Best-effort: never block the agent loop. Writes go through the
hosted TeamShared MCP (memory_session_ensure + memory_session_append +
context_commit + memory_session_close) using the org-scoped TEAMSHARED_TOKEN
or Claude Code's native /mcp OAuth. Fail-open if the token is unset or MCP
is unreachable.

Capture POSTs to the org URL from ``.teamshared/org`` (D1 resolver).
Unbound / invalid → ``/mcp``. Does not register a second TeamShared server.
"""
