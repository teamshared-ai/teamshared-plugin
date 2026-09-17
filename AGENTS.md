# TeamShared plugin — agent install

Connect once. Bind repos to orgs. Do not add a second TeamShared server.
Unbound `https://teamshared.com/mcp` keeps working (Connect-time org).

This file is for agents working in this plugin repo and for agents that
install TeamShared into a checkout. Human install: [`README.md`](README.md).

## Model

1. **One Connect** — the plugin registers `https://teamshared.com/mcp`.
   Cursor uses Settings → Tools & MCP → teamshared → Connect. Claude Code
   uses `/mcp` → Authenticate. Codex uses plugin OAuth. Cursor Cloud / Grok
   Bot inherit the account-level Cursor Connect.
2. **One org per repo** — `teamshared org bind <slug>` writes
   `.teamshared/org` (`{"v":1,"slug"}`). Capture hooks read that file and
   POST to `https://teamshared.com/o/{slug}/mcp`. The plugin MCP entry stays
   on `/mcp`.
3. **Unbound `/mcp` keeps working** — missing or invalid `.teamshared/org`
   is not an error. Tools and capture stay on the Connect-time org.
4. **No second server** — do not write `.cursor/mcp.json`, project
   `.mcp.json`, or Codex `[mcp_servers.teamshared]` pointing at
   `/o/{slug}/mcp` (or a second `/mcp`). Those load a duplicate TeamShared
   tool set next to the plugin.

## Bind

From an authenticated MCP chat, call `org_list` / `org_context_get`, then
`org_bind(slug=..., scope=conversation|workspace)`. Conversation bind is
this `Mcp-Session-Id` only (else `reason=no_session`). Workspace bind is
account + repo slug. `org_unbind` clears the overlay. Precedence: path
`/o/{slug}/mcp` > conversation > workspace > OAuth/`tsk_` default.
Membership is fail-closed; `tsk_` keys cannot switch; path mounts cannot
be overridden; this is not a global account switch. Do not tell the user
to install the TeamShared CLI. The local CLI is an optional fallback that
writes `.teamshared/org`:

```bash
teamshared org bind <slug> --token "$TEAMSHARED_TOKEN"
teamshared org status
teamshared org unbind
```

`bind` checks membership, then writes only `.teamshared/org`. `status` and
`unbind` are offline. Commit the file. Never store the derived org URL.

## Harnesses

### Cursor

Marketplace install, then Connect. Bind the repo. Hooks reuse the Connect
token on the org path. Do not add a project MCP twin.

### Cursor Cloud

Cloud agents inherit account-level Connect. Bind is the checkout file;
hooks that run in the workspace follow it. Do not treat repo
`.cursor/mcp.json` as the Cloud bind path. Unbound `/mcp` keeps working.

### Claude Code

`/plugin install teamshared@teamshared`, then `/mcp` → Authenticate. Bind
the repo. Do not add a project `.mcp.json` TeamShared server. Capture hooks
need an org-scoped `TEAMSHARED_TOKEN` (seat key); without it they no-op.

### Codex

`codex plugin add teamshared@teamshared`, connect when prompted, trust
`/hooks`. Bind the repo. The first OAuth browser open is the Codex host
(system browser); TeamShared only serves `/oauth/authorize` + redirect.
ChatGPT `@Browser` is not MCP Authenticate. To skip the browser, use
`install/codex/` + `TEAMSHARED_TOKEN` **instead of** the plugin. Do not
install `install/codex/` next to the plugin. Do not add
`[mcp_servers.teamshared]` unless you are on that seat-key path.

## Bots and seat keys

Bots that must stay in one org use a seat key scoped to that org:

```bash
teamshared token mint <agent>
```

Or mint under https://teamshared.com/app/keys. Put `Authorization: Bearer
tsk_…` on the bot's MCP headers (or `TEAMSHARED_TOKEN` for Claude/Codex
hooks). That is not a second TeamShared server.

## Version notes (Codex)

If `version` returns `update_available: true`, upgrade the marketplace
plugin. You may add a short note to `~/.codex/AGENTS.md` or this repo
`AGENTS.md`. Do not write Cursor `~/.cursor/rules/teamshared.mdc` or Claude
`~/.claude/rules/teamshared.md` from the Codex package.
