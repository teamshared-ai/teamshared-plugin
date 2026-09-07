# TeamShared (Claude Code plugin)

Registers the hosted TeamShared MCP server at `https://teamshared.com/mcp`.
This package is Claude Code only — no Cursor hooks.

Claude Code does **not** inherit Cursor Connect. Authenticate with a `tsk_`
org key in `TEAMSHARED_TOKEN`. Never commit that value.

## Install

From Claude Code:

```
/plugin marketplace add teamshared-ai/teamshared-plugin
/plugin install teamshared@teamshared
/reload-plugins
```

Equivalent CLI:

```bash
claude plugin marketplace add teamshared-ai/teamshared-plugin
claude plugin install teamshared@teamshared
```

## Auth (`tsk_` via `TEAMSHARED_TOKEN`)

1. Sign in at [teamshared.com/app](https://teamshared.com/app) (email + one-time code).
2. Mint an org key under `/app/keys`. It starts with `tsk_`.
3. Export it in the environment that launches Claude Code. Do not paste the
   key into this plugin's `.mcp.json`.

```bash
export TEAMSHARED_TOKEN=tsk_...
```

The plugin's `.mcp.json` sends `Authorization: Bearer ${TEAMSHARED_TOKEN}`
(same placeholder idea as `install/claude/mcp.json`). Claude Code expands the
variable at load time.

After install, confirm MCP tools appear (`memory_recall`, `memory_remember`,
`memory_session_*`, …). If they are missing, `/mcp` should show
`plugin:teamshared:teamshared` — usually `TEAMSHARED_TOKEN` is unset.

Durable backup (manual, not this plugin): merge `install/claude/mcp.json` and
replace `__MCP_URL__` / `__TEAMSHARED_TOKEN__` yourself.

## What this package ships

| Component | Purpose |
|---|---|
| `.mcp.json` | Remote HTTP MCP `https://teamshared.com/mcp` + `TEAMSHARED_TOKEN` header |
| `skills/teamshared-memory/` | Thin Claude-shaped pointer to the recall-first loop |

No Cursor hooks, slash-command extras, or agents. The Cursor plugin at the
repo root is unchanged and still uses email/OTP Connect.
