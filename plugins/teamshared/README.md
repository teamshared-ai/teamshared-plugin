# TeamShared for Codex

This native Codex plugin registers the hosted TeamShared MCP server and adds a
recall-first memory skill. It does not include the Cursor-only hooks.

## Install from the repository marketplace

```bash
codex plugin marketplace add teamshared-ai/teamshared-plugin
codex plugin add teamshared@teamshared
```

Restart the Codex app, start a new task, and connect TeamShared when prompted.
Authentication uses the MCP OAuth discovery metadata published by
`https://teamshared.com`; no token belongs in this package.

For a manual `config.toml` installation instead, use
[`install/codex/README.md`](../../install/codex/README.md). That alternative
uses `TEAMSHARED_TOKEN` and should not be installed alongside this plugin.

## Package contents

| Component | Purpose |
|---|---|
| `.codex-plugin/plugin.json` | Native Codex plugin manifest and UI metadata |
| `.mcp.json` | Streamable HTTP MCP connection to `https://teamshared.com/mcp` |
| `skills/teamshared-memory/` | Recall-first session, fetch, and commit workflow |
