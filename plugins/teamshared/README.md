# TeamShared for Codex

This native Codex plugin registers the hosted TeamShared MCP server and treats
Codex as a first-class TeamShared client: recall-first protocol **1.24.0**,
SessionStart injection, and official Codex chat-capture hooks.

Authentication uses the MCP OAuth discovery metadata published by
`https://teamshared.com`. This package does not store API keys or headers.

The Cursor plugin at the repo root is unchanged (email/OTP Connect + Cursor
hook event names). Claude Code lives under `claude/` and uses
`TEAMSHARED_TOKEN`.

## Install from the repository marketplace

```bash
codex plugin marketplace add teamshared-ai/teamshared-plugin
codex plugin add teamshared@teamshared
```

Restart the Codex app, start a new task, and connect TeamShared when prompted.

Then:

1. `/hooks` — review and **trust** the TeamShared plugin hooks. Codex skips
   plugin-bundled hooks until you trust the current definition
   ([hooks reference](https://developers.openai.com/codex/hooks)).
2. Start a new task so `SessionStart` injects protocol 1.24.0.
3. Confirm `/mcp` lists TeamShared tools.
4. `$status` (or `$teamshared-status`) — health + `version`
   (`installed_rule_version` 1.24.0).
5. Work normally. Every turn: `memory_session_ensure` → `memory_recall` →
   work → `context_commit`. You do not need to name TeamShared.

For a manual `config.toml` installation instead, use
[`install/codex/README.md`](../../install/codex/README.md). That alternative
uses `TEAMSHARED_TOKEN` and should not be installed alongside this plugin.

## Package contents

| Component | Purpose |
|---|---|
| `.codex-plugin/plugin.json` | Native Codex plugin manifest, UI metadata, `interface.defaultPrompt` |
| `.mcp.json` | Streamable HTTP MCP to `https://teamshared.com/mcp` (OAuth, no headers) |
| `hooks/hooks.json` | Official Codex events only (see below). Auto-discovered; also declared in the manifest |
| `skills/teamshared-memory/` | Protocol **1.24.0** (same loop as `rules/teamshared.mdc`) |
| `skills/status/` | `$status` / `$teamshared-status` health + version check |

## Always-on (without naming TeamShared)

Codex has no Cursor `alwaysApply` rule. This package stacks three supported
mechanisms:

1. **Skill description** + `allow_implicit_invocation` so Codex loads the
   1.24.0 loop when TeamShared MCP tools are present.
2. **`interface.defaultPrompt`** starter chips that ask to recall / continue /
   save without requiring the user to say "TeamShared".
3. **`SessionStart` `additionalContext`** — official Codex hook output that
   injects protocol 1.24.0 at session start (`startup`, `resume`, `clear`,
   `compact`).

## Hooks (official Codex events)

Event names come from the [Codex hooks reference](https://developers.openai.com/codex/hooks).
This package does **not** invent Cursor camelCase names or Claude-only events.

| Event | What it does |
|---|---|
| `SessionStart` | Injects protocol 1.24.0 via `additionalContext`; maps Codex `session_id` → `memory_session_ensure` |
| `UserPromptSubmit` | Appends the redacted user prompt (`ensure(user=)`) |
| `Stop` | Appends the redacted assistant text (`last_assistant_message`). Does **not** distill — Stop fires every turn |
| `SessionEnd` | `memory_session_close` + distill (timeout capped at Codex's 3s maximum) |
| `PostToolUse` (`Bash`) | Failed shell only → short episodic fact (command + error tail). Codex has no `PostToolUseFailure` |
| `PreCompact` | Short session summary before compact |

### What Codex cannot capture vs Claude

| Claude Code | Codex (this package) |
|---|---|
| `StopFailure` (API-error system note) | **None** — Codex does not document `StopFailure` |
| `PostToolUseFailure` on `Bash\|PowerShell` | Approximated with official `PostToolUse` + exit-code check on `Bash` |
| Hook writes via `TEAMSHARED_TOKEN` (same env the MCP client uses) | MCP chat tools use **in-process OAuth**. Hook subprocesses read `$CODEX_HOME/.credentials.json` (Codex file fallback), then `TEAMSHARED_TOKEN` as last resort. **keyring-only** OAuth is a gap: SessionStart still injects; capture writes fail-open |

Secrets are scrubbed. Every handler is fail-open (no token or MCP down never
blocks Codex). Do not return `decision: "block"` from `Stop` (that continues
the turn) or `PostToolUse` (that replaces the tool result).

## Version updates

On the first turn, call `version` with `installed_rule_version` `1.24.0`.
If `update_available: true`, upgrade this marketplace plugin. You may add a
short note to `~/.codex/AGENTS.md` (or the repo `AGENTS.md`). Do not write
Cursor `~/.cursor/rules/teamshared.mdc` or Claude
`~/.claude/rules/teamshared.md`. Never invent a version.
