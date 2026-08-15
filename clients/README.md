# Reference MCP snippets (manual setup)

These files are **documentation and copy-paste examples** for non-Cursor
harnesses. Cursor installs MCP from this plugin's `mcp.json` (URL only) and
authenticates with **Connect** — do not paste bearer tokens into
`~/.cursor/mcp.json`.

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
