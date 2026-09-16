# TeamShared for Codex

This native Codex plugin registers the hosted TeamShared MCP server and treats
Codex as a first-class TeamShared client: recall-first protocol **1.30.0**,
SessionStart injection, and official Codex chat-capture hooks.

Authentication uses the MCP OAuth discovery metadata published by
`https://teamshared.com`. This package does not store API keys or headers.

### Browser behavior (expected)

**The first browser open is host-owned.** MCP **Authenticate** /
`codex mcp login` is opened by the **Codex / ChatGPT host**, not by
TeamShared.

| Surface | Who opens the first URL |
|---|---|
| `codex mcp login` (CLI / TUI) | Codex CLI (`webbrowser` on the authorize URL) |
| ChatGPT / Codex **desktop** Authenticate | Desktop app-server returns `authorization_url`; the shell opens it via the **external** link bridge (system default browser, usually Chrome) |
| This plugin | Registers `https://teamshared.com/mcp` only — no browser launcher |
| TeamShared | Serves `/oauth/authorize` (email/OTP) and **redirects** to the client’s `redirect_uri` |

TeamShared does not call `webbrowser`, `open`, or a ChatGPT deep link for
Connect. After OTP it redirects to Codex loopback
(`http://127.0.0.1:<port>/callback/…`) or the hosted ChatGPT connector
callback. There is **no** public “force in-app browser” API for third-party
MCP servers.

**ChatGPT `@Browser` ≠ MCP Authenticate.** The in-app panel
([ChatGPT Browser docs](https://learn.chatgpt.com/docs/browser)) is
Computer Use inside a chat. It is not available in Codex CLI or the Codex
IDE extension, and it is not the MCP OAuth surface. No Settings toggle
routes Connect there. Finish email/OTP in the system browser; the callback
hits Codex’s localhost listener.

**Post-OTP loopback is a second hop.** After a successful OTP, TeamShared
may serve `oauth_loopback.html` for Codex loopback
(`http://127.0.0.1:<port>/callback/<id>`). That page uses **one** auto
handoff (top navigation for ephemeral Codex ports; iframe only for Cursor
`:8787`) plus a **Return to app** button — not iframe and `location.replace`
racing. Hosted `chatgpt.com/connector_platform_oauth_redirect` 302s and
never hits the 8787 interstitial. This still cannot change who opens
`/oauth/authorize` (teamshared PR 540).

**Reliable workaround (skip the OAuth browser):** use
[`install/codex/`](../../install/codex/README.md) with `TEAMSHARED_TOKEN`
and `bearer_token_env_var` instead of this OAuth plugin — not both. See
[#46](https://github.com/teamshared-ai/teamshared-plugin/issues/46).

The Cursor plugin at the repo root is unchanged (email/OTP Connect + Cursor
hook event names). Claude Code lives under `claude/` and uses
`TEAMSHARED_TOKEN` for capture hooks.

**One Connect, one org per repo.** Connect when Codex prompts. From chat,
call MCP `org_list` / `org_bind` when those tools exist.
`teamshared org bind <slug>` is an optional fallback that writes
`.teamshared/org`. Capture follows that file. Do not add a second TeamShared server
(`[mcp_servers.teamshared]` next to this plugin). Unbound `/mcp` keeps working.
Bots that must stay in one org use the manual
[`install/codex/`](../../install/codex/README.md) path with
`teamshared token mint` (org-scoped seat key) — not both.

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
2. Start a new task so `SessionStart` injects protocol 1.30.0.
3. Confirm `/mcp` lists TeamShared tools.
4. `$status` (or `$teamshared-status`) — health + `version`
   (`installed_rule_version` 1.30.0).
5. Work normally. Every turn: `memory_session_ensure` → `memory_recall` →
   work → `context_commit`. You do not need to name TeamShared.

For a manual `config.toml` installation instead, use
[`install/codex/README.md`](../../install/codex/README.md). That alternative
uses `TEAMSHARED_TOKEN` from `teamshared token mint` (org-scoped) and
should not be installed alongside this plugin. Bind either path with
`teamshared org bind <slug>`.

## Package contents

| Component | Purpose |
|---|---|
| `.codex-plugin/plugin.json` | Native Codex plugin manifest, UI metadata, `interface.defaultPrompt`, `interface.logo` / `composerIcon` |
| `assets/logo.png` / `assets/icon.png` | Brand mark for ChatGPT Sources and the Codex plugin directory (paths stay inside this package) |
| `.mcp.json` | Streamable HTTP MCP to `https://teamshared.com/mcp` (OAuth, no headers) |
| `hooks/hooks.json` | Official Codex events only (see below). Auto-discovered; also declared in the manifest |
| `skills/teamshared-memory/` | Protocol **1.30.0** (same loop as `rules/teamshared.mdc`) |
| `skills/status/` | `$status` / `$teamshared-status` health + version check |

## Always-on (without naming TeamShared)

Codex has no Cursor `alwaysApply` rule. This package stacks three supported
mechanisms:

1. **Skill description** + `allow_implicit_invocation` so Codex loads the
   1.30.0 loop when TeamShared MCP tools are present.
2. **`interface.defaultPrompt`** starter chips that ask to recall / continue /
   save without requiring the user to say "TeamShared".
3. **`SessionStart` `additionalContext`** — official Codex hook output that
   injects protocol 1.30.0 at session start (`startup`, `resume`, `clear`,
   `compact`).

## Hooks (official Codex events)

Event names come from the [Codex hooks reference](https://developers.openai.com/codex/hooks).
This package does **not** invent Cursor camelCase names or Claude-only events.

| Event | What it does |
|---|---|
| `SessionStart` | Injects protocol 1.30.0 via `additionalContext`; maps Codex `session_id` → `memory_session_ensure` |
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

On the first turn, call `version` with `installed_rule_version` `1.30.0`.
If `update_available: true`, upgrade this marketplace plugin. You may add a
short note to `~/.codex/AGENTS.md` (or the repo `AGENTS.md`). Do not write
Cursor `~/.cursor/rules/teamshared.mdc` or Claude
`~/.claude/rules/teamshared.md`. Never invent a version.
