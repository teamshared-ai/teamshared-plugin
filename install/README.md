# Reference harness snippets

Optional MCP config examples for **non-Cursor** clients (Codex, Hermes, Claude
Desktop, Pi). Cursor desktop, Cursor Cloud, and Grok Bot inherit account-level
Connect (Settings → Tools & MCP → teamshared → Connect) — do not paste these
into `~/.cursor/mcp.json` or the plugin `mcp.json`.

**One Connect, one org per repo.** The plugin / Connect server stays
`https://teamshared.com/mcp`. Bind the checkout with
`teamshared org bind <slug>` (writes `.teamshared/org`). Capture follows that
file. Do not add a second TeamShared server. Unbound `/mcp` keeps working
(Connect-time org). See [`../AGENTS.md`](../AGENTS.md) and the root
[`README.md`](../README.md).

These snippets are the durable backup for bots that must stay in one org:
`teamshared token mint` (org-scoped seat key) or a `tsk_` from
[teamshared.com/app/keys](https://teamshared.com/app/keys) on the MCP headers
(`Authorization: Bearer tsk_…`). Still one server.

**Codex** is a first-class package: [`codex/README.md`](codex/README.md)
(`codex mcp add` or project-local `.codex/config.toml`). Use that manual
`TEAMSHARED_TOKEN` path **or** the native marketplace plugin, not both.
The seat-key path skips the host-owned OAuth system browser (ChatGPT
`@Browser` is not MCP Authenticate). See
[#46](https://github.com/teamshared-ai/teamshared-plugin/issues/46).

**Claude Code** should install the marketplace plugin in `claude/` instead of
hand-merging `install/claude/mcp.json`. Auth is Claude's native `/mcp`
Authenticate flow; `TEAMSHARED_TOKEN` is only for capture hooks.

The curl installer that used to fetch these from `/install/assets/*` is retired.
