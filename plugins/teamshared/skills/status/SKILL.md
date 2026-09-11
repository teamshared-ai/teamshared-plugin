---
name: status
description: Check TeamShared MCP health, protocol version, and whether this Codex session is captured. Use when the user runs $status / $teamshared-status or asks if TeamShared memory is connected.
---

# TeamShared status

Report whether TeamShared is usable in this Codex session. Do **not**
print OAuth tokens, `TEAMSHARED_TOKEN`, or any secret.

1. Call `health`. If it fails, say MCP is unreachable and stop. Do not probe
   `TEAMSHARED_*` in the shell.
2. Call `version` with `installed_rule_version` `1.24.0`. Report
   `update_available` exactly. Never invent a version. If an update is
   available, tell the user to upgrade this marketplace plugin; you may add
   a short note to `~/.codex/AGENTS.md` (or the repo `AGENTS.md`). Do not
   write Cursor or Claude rule files.
3. Resolve `repo=` (workspace slug, no slashes) and `github=` (`owner/repo`)
   when you can.
4. Optionally `memory_session_ensure(repo=..., topic=..., fresh=false)` and
   report the returned `session_id` plus whether `soul` / `agent_memory` /
   `playbook` came back non-empty. Do not dump those bodies unless asked.
5. Remind the user: this plugin uses MCP OAuth (connect when prompted). Do
   not mix with `install/codex/` (`TEAMSHARED_TOKEN`). Official Codex hooks
   must be reviewed and trusted via `/hooks` before capture writes run.
   SessionStart still injects protocol 1.24.0. Codex has no `StopFailure` or
   `PostToolUseFailure` (Claude-only).

Keep the answer short. Then `context_commit` a one-line summary (`close=false`
unless the user is done).
