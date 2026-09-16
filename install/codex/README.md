# Codex → TeamShared MCP

Few-step setup for [OpenAI Codex](https://developers.openai.com/codex/mcp)
against the hosted TeamShared server at `https://teamshared.com/mcp`.

Codex config is **TOML** (`[mcp_servers.teamshared]`), not the JSON
`mcpServers` object Cursor and Claude use. The CLI, IDE extension, and
desktop app share the same files.


> **OAuth vs this package:** The native marketplace plugin
> ([`plugins/teamshared/`](../../plugins/teamshared/README.md)) uses MCP OAuth and
> opens your **system browser** (host-owned). This TOML path uses
> `TEAMSHARED_TOKEN` and skips that browser step. Prefer one path, not both.
> Details: [#46](https://github.com/teamshared-ai/teamshared-plugin/issues/46).

This package does **not** change the Cursor plugin. Cursor desktop, Cursor
Cloud, and Grok Bot stay on account-level **Connect** (Settings → Tools & MCP →
teamshared → Connect). Do not paste a `tsk_` key into the plugin `mcp.json`.

**One Connect, one org per repo.** Prefer the native Codex marketplace plugin
([`plugins/teamshared/`](../../plugins/teamshared/README.md)). This TOML path
is the seat-key fallback for bots that must stay in one org
(`teamshared token mint` scoped to that org). Use the plugin **or** this
manual entry, not both. Do not add a second TeamShared server. Bind the
checkout with `teamshared org bind <slug>` (writes `.teamshared/org`).
Unbound `/mcp` keeps working.

## 1. Mint a `tsk_` key

1. Sign in at [teamshared.com/app](https://teamshared.com/app) (email + one-time code).
2. Mint an org-scoped seat key: `teamshared token mint <agent>`, or open
   [**/app/keys**](https://teamshared.com/app/keys) and mint an org API key.
3. The value starts with `tsk_`. Keep it out of git. Bind the repo with
   `teamshared org bind <slug>` so capture follows the org. Do not add a second TeamShared server.

```bash
export TEAMSHARED_TOKEN=tsk_...   # shell that launches Codex; never commit this
```

Codex reads `TEAMSHARED_TOKEN` and sends `Authorization: Bearer tsk_…` on
every MCP request. That is the durable-backup auth path for non-Cursor hosts.

## 2. Register the server

### Option A — `codex mcp add` (user-wide)

Writes `[mcp_servers.teamshared]` into `~/.codex/config.toml` (created on
first use). Same config is shared across Codex CLI, IDE, and desktop.

```bash
codex mcp add teamshared \
  --url https://teamshared.com/mcp \
  --bearer-token-env-var TEAMSHARED_TOKEN
```

### Option B — project-local `.codex/config.toml`

Merge the table from [`mcp.toml`](mcp.toml) into **`.codex/config.toml` at
the repo root** you run Codex from. Codex loads project-scoped config only
for **trusted** projects; user `~/.codex/config.toml` still wins on conflicts.

If the project has no Codex config yet:

```bash
mkdir -p .codex
cp path/to/teamshared-plugin/install/codex/mcp.toml .codex/config.toml
```

If `.codex/config.toml` already exists, append the `[mcp_servers.teamshared]`
table (do not nest it under another table):

```toml
[mcp_servers.teamshared]
url = "https://teamshared.com/mcp"
bearer_token_env_var = "TEAMSHARED_TOKEN"
enabled = true
```

Then launch Codex from that repo root.

Prefer the env var. The equivalent explicit header form (still no secret in
git) is `env_http_headers = { Authorization = "TEAMSHARED_AUTHORIZATION" }`
with `export TEAMSHARED_AUTHORIZATION="Bearer tsk_..."`. Do not commit a
literal `tsk_` value in `http_headers`.

## 3. Confirm

```bash
codex mcp list
codex mcp get teamshared
```

In a Codex session, `/mcp` lists connected servers and their tools. You
should see `teamshared` and memory tools (`memory_recall`, `memory_remember`,
…). A 401 usually means `TEAMSHARED_TOKEN` was not exported in the shell
that started Codex.

On **Codex Cloud**, set `TEAMSHARED_TOKEN` as an **environment variable**
(not a Secret). Secrets are wiped before the agent phase; MCP auth happens
on every tool call, so a Secret-only key will 401 after setup.

## Memory protocol

MCP wiring alone does not make the model call memory tools on every turn.
Paste [`clients/protocol.md`](../../clients/protocol.md) into project
instructions (`AGENTS.md`, etc.) if you want the recall-first loop.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server ignored | Config must be TOML `[mcp_servers.teamshared]`, not JSON `mcpServers`. |
| Project file does nothing | Trust the directory, or merge into `~/.codex/config.toml` instead. |
| 401 / no tools | `echo "$TEAMSHARED_TOKEN"` in the same shell; key must start with `tsk_`. |
| Duplicate `teamshared` | One entry only — CLI **or** file merge, not both targeting the same layer. Do not add this TOML next to the native marketplace plugin. |
| OAuth opens Chrome / system browser | Expected. Codex opens the authorize URL externally; ChatGPT in-app `@Browser` is not used for MCP Authenticate. Use this `TEAMSHARED_TOKEN` path to skip the browser, or finish OTP in Chrome. [#46](https://github.com/teamshared-ai/teamshared-plugin/issues/46). |
| Want a second org | `teamshared org bind <slug>` — do not add a second TeamShared server. Unbound `/mcp` keeps working. |

Official field reference: [Codex MCP](https://developers.openai.com/codex/mcp)
(`url`, `bearer_token_env_var`, `http_headers`, `env_http_headers`).
