# TeamShared (Claude Code plugin)

Registers the hosted TeamShared MCP server at `https://teamshared.com/mcp`
and treats Claude Code as a first-class TeamShared client: recall-first
protocol **1.24.0**, SessionStart injection, and chat-capture hooks.

Claude Code does **not** inherit Cursor Connect. Authenticate with a `tsk_`
org key in `TEAMSHARED_TOKEN`. Never commit that value.

This package is Claude Code only. The Cursor plugin at the repo root is
unchanged (email/OTP Connect + Cursor hook event names).

## Install

From Claude Code:

```
/plugin marketplace add teamshared-ai/teamshared-plugin
/plugin install teamshared@teamshared
/reload-plugins
```

Equivalent CLI:

```bash
claude plugin marketplace add teamshared-ai/teamshared-plugin
claude plugin install teamshared@teamshared
```

## Auth (`tsk_` via `TEAMSHARED_TOKEN`)

1. Sign in at [teamshared.com/app](https://teamshared.com/app) (email + one-time code).
2. Mint an org key under `/app/keys`. It starts with `tsk_`.
3. Export it in the environment that launches Claude Code. Do not paste the
   key into this plugin's `.mcp.json`.

```bash
export TEAMSHARED_TOKEN=tsk_...
```

The plugin's `.mcp.json` sends `Authorization: Bearer ${TEAMSHARED_TOKEN}`
(same placeholder idea as `install/claude/mcp.json`). Claude Code expands the
variable at load time.

After install, confirm MCP tools appear (`memory_recall`, `memory_remember`,
`memory_session_*`, …). If they are missing, `/mcp` should show
`plugin:teamshared:teamshared` — usually `TEAMSHARED_TOKEN` is unset.

Then:

1. `/reload-plugins` (or start a new session) so `SessionStart` injects protocol 1.24.0.
2. Confirm `/mcp` lists TeamShared tools.
3. `/teamshared:status` — health + `version` (`installed_rule_version` 1.24.0).
4. Work normally. Every turn: `memory_session_ensure` → `memory_recall` → work → `context_commit`.

Durable backup (manual, not this plugin): merge `install/claude/mcp.json` and
replace `__MCP_URL__` / `__TEAMSHARED_TOKEN__` yourself.

## What this package ships

| Component | Purpose |
|---|---|
| `.mcp.json` | Remote HTTP MCP `https://teamshared.com/mcp` + `TEAMSHARED_TOKEN` header |
| `hooks/hooks.json` | Official Claude Code events only (see below) |
| `skills/teamshared-memory/` | Protocol **1.24.0** (same loop as `rules/teamshared.mdc`) |
| `skills/status/` | Slash skill `/teamshared:status` |

## Hooks (official Claude Code events)

Event names come from the [Claude Code hooks reference](https://docs.claude.com/en/docs/claude-code/hooks).
This package does **not** invent Cursor-only names.

| Event | What it does |
|---|---|
| `SessionStart` | Injects protocol 1.24.0 via `additionalContext`; maps Claude `session_id` → `memory_session_ensure` |
| `UserPromptSubmit` | Appends the redacted user prompt (`ensure(user=)`) |
| `Stop` | Appends the redacted assistant text (`last_assistant_message`). Does **not** distill — Stop fires every turn |
| `StopFailure` | Notes API-error turns; does not close the session |
| `SessionEnd` | `memory_session_close` + distill |
| `PostToolUseFailure` | Failed `Bash` / `PowerShell` → short episodic fact (command + error tail) |
| `PreCompact` | Short session summary before compact |

Auth is `TEAMSHARED_TOKEN` only. Secrets are scrubbed. Every handler is
fail-open (unset token or MCP down never blocks Claude).

Claude Code's default `SessionEnd` budget is 1.5s; plugin timeouts do not
raise it. To give close+distill more room:

```bash
export CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=10000
```

## Version updates

On the first turn, call `version` with `installed_rule_version` `1.24.0`.
If `update_available: true`, write `rule_markdown` to
`~/.claude/rules/teamshared.md` (or `.claude/rules/teamshared.md` in a repo).
Never invent a version. This is the Claude write path — Cursor still uses
`~/.cursor/rules/teamshared.mdc`.
