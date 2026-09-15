# Claude Code — blocked in this VM

`command -v claude` is absent. We cannot run `claude mcp list` or
`/plugin` here.

## Docs used

- https://code.claude.com/docs/en/mcp-servers
  - Plugin servers register as `plugin:<plugin>:<server>`
    (`plugin:teamshared:teamshared`).
  - `${VAR}` / `${VAR:-default}` expand in plugin and project `url`.
  - Project `.mcp.json` is a separate manual server (needs trust/approval).
  - Changelog 2.1.71: plugin server is skipped only when it duplicates a
    manual server's **command or URL**. Same-URL copy-and-tweak replaces;
    a different org URL does not.
- https://github.com/anthropics/claude-code/issues/31682 — dedup is
  undocumented in the main MCP page; suppressions show in `/plugin`.
- https://code.claude.com/docs/en/settings — committed
  `.claude/settings.json` `env` applies after workspace trust, including
  Claude Code cloud sessions.

## How to verify

1. `/plugin install teamshared@teamshared` and Authenticate. Confirm
   `plugin:teamshared:teamshared` at `https://teamshared.com/mcp`.
2. Add project `.mcp.json` with `https://teamshared.com/o/YOUR_SLUG/mcp`
   under `mcpServers.teamshared`.
3. `claude mcp list` — expect **both** servers (URLs differ).
4. `/plugin` — plugin copy is not suppressed.
5. Remove the project entry. One server remains.
6. After C2 only: change the **plugin** `url` to
   `${TEAMSHARED_MCP_URL:-https://teamshared.com/mcp}` and set
   `TEAMSHARED_MCP_URL` in trusted project settings. Expect still one
   server, now on the org path.
