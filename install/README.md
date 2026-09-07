# Reference harness snippets

Optional MCP config examples for **non-Cursor** clients (Codex, Hermes, Claude
Desktop, Pi). Cursor desktop, Cloud, and Grok Bot inherit account-level Connect
(Settings → Tools & MCP → teamshared → Connect) — do not paste these into
`~/.cursor/mcp.json` or the plugin `mcp.json`. These snippets are the durable
backup: one org `tsk_` on the MCP headers (`Authorization: Bearer tsk_…`).

**Codex** is a first-class package: [`codex/README.md`](codex/README.md)
(`codex mcp add` or project-local `.codex/config.toml`). Mint keys at
[teamshared.com/app/keys](https://teamshared.com/app/keys).

**Claude Code** should install the marketplace plugin in `claude/` instead of
hand-merging `install/claude/mcp.json`. Same `TEAMSHARED_TOKEN` / `tsk_`
auth — Claude Code does not inherit Cursor Connect.

The curl installer that used to fetch these from `/install/assets/*` is retired.
