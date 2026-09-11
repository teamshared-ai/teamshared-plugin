# TeamShared (Claude Code plugin)

Registers the hosted TeamShared MCP server at `https://teamshared.com/mcp`
and treats Claude Code as a first-class TeamShared client: recall-first
protocol **1.27.0**, SessionStart injection, and chat-capture hooks.

Claude Code has its own native MCP OAuth flow (`/mcp`) — not Cursor's Connect
button, but the same idea: browser login, token stored in your system
keychain. That's the primary way to authenticate the MCP connection itself.
The chat-capture **hooks** are a separate story: they run as standalone
subprocesses with no access to that keychain, so they need their own `tsk_`
org key in `TEAMSHARED_TOKEN` to do anything — without it they simply no-op
(fail-open), and the MCP connection and every-turn workflow still work fine.

This package is Claude Code only. The Cursor plugin at the repo root is
unchanged (email/OTP Connect + Cursor hook event names).

## Install

From Claude Code:

```
/plugin marketplace add teamshared-ai/teamshared-plugin
/plugin install teamshared@teamshared
/reload-plugins
/mcp
```

In `/mcp`, select **teamshared** and choose **Authenticate** — Claude Code
opens a browser to the same email/OTP login as the web console and stores
the token itself. No URL or key to paste.

Equivalent CLI:

```bash
claude plugin marketplace add teamshared-ai/teamshared-plugin
claude plugin install teamshared@teamshared
claude mcp login teamshared   # or --no-browser in a headless environment
```

## Auth

**MCP connection (required):** `/mcp` → teamshared → Authenticate, as above.
After install, confirm MCP tools appear (`memory_recall`, `memory_remember`,
`memory_session_*`, …) and `/mcp` shows `plugin:teamshared:teamshared`
connected.

**Capture hooks (optional, `tsk_` via `TEAMSHARED_TOKEN`):** the hooks below
can't reuse the OAuth token (separate subprocess, no keychain access), so if
you want them capturing chat automatically, mint an org key and export it in
the environment that launches Claude Code:

1. Sign in at [teamshared.com/app](https://teamshared.com/app) (email + one-time code).
2. Mint an org key under `/app/keys`. It starts with `tsk_`.
3. Export it — do not paste it into this plugin's `.mcp.json`.

```bash
export TEAMSHARED_TOKEN=tsk_...
```

Without `TEAMSHARED_TOKEN` set, the hooks fail open silently; everything else
(the MCP connection, `memory_*` tools, the every-turn workflow) is unaffected.

Then:

1. `/reload-plugins` (or start a new session) so `SessionStart` injects protocol 1.27.0.
2. Confirm `/mcp` lists TeamShared tools as connected.
3. `/teamshared:status` — health + `version` (`installed_rule_version` 1.27.0).
4. Work normally. Every turn: `memory_session_ensure` → `memory_recall` → work → `context_commit`.

Durable backup (manual, not this plugin): merge `install/claude/mcp.json` and
replace `__MCP_URL__` / `__TEAMSHARED_TOKEN__` yourself.

## What this package ships

| Component | Purpose |
|---|---|
| `.mcp.json` | Remote HTTP MCP `https://teamshared.com/mcp` — no headers, uses Claude Code's native `/mcp` OAuth |
| `hooks/hooks.json` | Official Claude Code events only (see below); need `TEAMSHARED_TOKEN` to actually write |
| `skills/teamshared-memory/` | Protocol **1.27.0** (same loop as `rules/teamshared.mdc`) |
| `skills/status/` | Slash skill `/teamshared:status` |

## Hooks (official Claude Code events)

Event names come from the [Claude Code hooks reference](https://docs.claude.com/en/docs/claude-code/hooks).
This package does **not** invent Cursor-only names.

| Event | What it does |
|---|---|
| `SessionStart` | Injects protocol 1.27.0 via `additionalContext`; maps Claude `session_id` → `memory_session_ensure` |
| `UserPromptSubmit` | Appends the redacted user prompt (`ensure(user=)`) |
| `Stop` | Appends the redacted assistant text (`last_assistant_message`). Does **not** distill — Stop fires every turn |
| `StopFailure` | Notes API-error turns; does not close the session |
| `SessionEnd` | `memory_session_close` + distill |
| `PostToolUseFailure` | Failed `Bash` / `PowerShell` → short episodic fact (command + error tail) |
| `PreCompact` | Short session summary before compact |

Hook auth is `TEAMSHARED_TOKEN` only — separate from the OAuth-authenticated
MCP connection above. Secrets are scrubbed. Every handler is fail-open (unset
token or MCP down never blocks Claude).

Claude Code's default `SessionEnd` budget is 1.5s; plugin timeouts do not
raise it. To give close+distill more room:

```bash
export CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=10000
```

## Version updates

On the first turn, call `version` with `installed_rule_version` `1.27.0`.
If `update_available: true`, write `rule_markdown` to
`~/.claude/rules/teamshared.md` (or `.claude/rules/teamshared.md` in a repo).
Never invent a version. This is the Claude write path — Cursor still uses
`~/.cursor/rules/teamshared.mdc`.
