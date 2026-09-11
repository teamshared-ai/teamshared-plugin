---
name: status
description: Check TeamShared MCP health, protocol version, and whether this Claude Code session is captured. Use when the user runs /teamshared:status or asks if TeamShared memory is connected.
---

# TeamShared status

Report whether TeamShared is usable in this Claude Code session. Do **not**
print `TEAMSHARED_TOKEN` or any secret.

1. Call `health`. If it fails, say MCP is unreachable and stop. Do not probe
   `TEAMSHARED_*` in the shell.
2. Call `version` with `installed_rule_version` `1.24.0`. Report
   `update_available` exactly. Never invent a version. If an update is
   available, offer to write `rule_markdown` to `~/.claude/rules/teamshared.md`
   (or `.claude/rules/teamshared.md`).
3. Resolve `repo=` (workspace slug, no slashes) and `github=` (`owner/repo`)
   when you can.
4. Optionally `memory_session_ensure(repo=..., topic=..., fresh=false)` and
   report the returned `session_id` plus whether `soul` / `agent_memory` /
   `playbook` came back non-empty. Do not dump those bodies unless asked.
5. Remind the user: Claude Code uses `TEAMSHARED_TOKEN` (`tsk_` minted at
   `/app/keys`); it does not inherit Cursor Connect. Slash skill
   `/teamshared:status`. Capture hooks are fail-open.

Keep the answer short. Then `context_commit` a one-line summary (`close=false`
unless the user is done).
