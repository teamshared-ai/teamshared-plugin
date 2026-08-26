# Reference MCP snippets (manual setup)

These files are **documentation and copy-paste examples** for non-Cursor
harnesses. Cursor desktop, Cloud, and Grok Bot inherit account-level
**Connect** (Settings → Tools & MCP → teamshared → Connect). The plugin stays
URL-only — do not paste a `tsk_*` key into the plugin `mcp.json` or
`~/.cursor/mcp.json`.

Durable backup for other hosts: one org `tsk_` on the MCP headers
(`Authorization: Bearer tsk_…`).

| Harness | Reference |
|---|---|
| Cursor | ``protocol.md`` + plugin rule ``../rules/teamshared.mdc`` |
| Hermes | ``hermes.config.yaml`` (example URLs) |
| Claude | ``claude-desktop.json`` (remote + local stdio) |
| Codex | ``../install/codex/mcp.toml`` |
| Pi | ``../install/pi/mcp.json`` |
| OpenClaw | ``../../src/teamshared/clients/openclaw.md`` in the repo |

**Memory rule:** ``../rules/teamshared.mdc`` (canonical).

**Agent protocol:** ``protocol.md`` — paste into Hermes SOUL, Claude project
instructions, etc.
