# teamshared (Cursor, Claude Code, and Codex plugins)

Registers the teamshared MCP server. The **Cursor** plugin also ships the
recall-first memory rule and Cursor hooks that capture Agent Chat into
TeamShared (`sessionStart`, `beforeSubmitPrompt`, `afterAgentResponse`,
`stop`, `sessionEnd`) plus `postToolUse` (failed test/lint/shell) and
`preCompact`. The Cursor plugin still has no skills, slash commands, or
extra agents.

This repo also ships a **Claude Code** marketplace plugin under `claude/`
(remote MCP via Claude Code's native `/mcp` OAuth, `TEAMSHARED_TOKEN` for the
optional capture hooks, protocol 1.27.0, SessionStart injection, and official
Claude Code capture hooks).

The native **Codex** package under `plugins/teamshared/` uses the server's MCP
OAuth discovery flow and treats Codex as a first-class client: protocol 1.27.0,
SessionStart injection, and official Codex capture hooks. A manual Codex TOML
setup remains available under `install/codex/` (`TEAMSHARED_TOKEN`; do not mix).

The MCP server itself lives in [`teamshared-ai/teamshared`](https://github.com/teamshared-ai/teamshared)
and is hosted at [teamshared.com](https://teamshared.com).

| Component | Purpose |
|---|---|
| `mcp.json` | Registers `https://teamshared.com/mcp` (URL only; Cursor OAuth Connect) |
| `rules/teamshared.mdc` | Lean always-on fetch/store loop (`alwaysApply`); tool encyclopedia lives in `memory_tools_catalog` |
| `hooks/` | Cursor hooks: Agent Chat capture plus `postToolUse` (failed test/lint/shell) and `preCompact` |
| `claude/` | Claude Code plugin (remote MCP via native `/mcp` OAuth + protocol 1.27.0 + capture hooks needing `TEAMSHARED_TOKEN`) |
| `.claude-plugin/marketplace.json` | Claude Code marketplace catalog (`/plugin marketplace add teamshared-ai/teamshared-plugin`) |
| `.agents/plugins/marketplace.json` | Codex marketplace catalog (`codex plugin marketplace add teamshared-ai/teamshared-plugin`) |
| `plugins/teamshared/` | Native Codex plugin (OAuth MCP + protocol 1.27.0 + official capture hooks) |
| `clients/` | Copy-paste protocol + MCP examples for non-Cursor harnesses (not loaded by Cursor) |

## Install

### From git marketplace (recommended)

1. **Settings → Plugins → Add marketplace** → paste `https://github.com/teamshared-ai/teamshared-plugin`
2. Run **`/add-plugin teamshared`** or enable **teamshared** under Settings → Plugins
3. **Settings → Tools & MCP → teamshared → Connect** (email + one-time code, same as the console)

Cloud and Grok Bot agents inherit that account-level Connect. Installing the
plugin registers `https://teamshared.com/mcp` — you only click **Connect**.
Do not paste a URL or token into the plugin `mcp.json`.

See [MARKETPLACE.md](MARKETPLACE.md) for the official Marketplace publish checklist.

### Claude Code (marketplace)

```
/plugin marketplace add teamshared-ai/teamshared-plugin
/plugin install teamshared@teamshared
/reload-plugins
/mcp
```

In `/mcp`, select **teamshared** and choose **Authenticate** — Claude Code's
own native OAuth flow, same email/OTP login as the web console, token stored
in your system keychain. Confirm tools appear under `/mcp` as
`plugin:teamshared:teamshared` connected.

The chat-capture hooks are a separate subprocess with no access to that
keychain, so if you also want them capturing chat automatically, mint a
`tsk_` org key and export it — never commit it:

```bash
export TEAMSHARED_TOKEN=tsk_...   # mint under https://teamshared.com/app/keys
```

Without it the hooks just no-op; the MCP connection and every-turn workflow
work fine either way. `SessionStart` injects protocol 1.27.0;
`/teamshared:status` checks health + version. Details:
[`claude/README.md`](claude/README.md).

### Codex (native plugin marketplace)

The native Codex package uses TeamShared's MCP OAuth discovery flow, so it does
not require `TEAMSHARED_TOKEN` or store an authorization header.

```bash
codex plugin marketplace add teamshared-ai/teamshared-plugin
codex plugin add teamshared@teamshared
```

Restart the Codex app, start a new task, and connect TeamShared when prompted.
Then review and trust plugin hooks with `/hooks` so capture writes run.
`SessionStart` injects protocol 1.27.0; `$status` checks health + version.
The package lives under [`plugins/teamshared/`](plugins/teamshared/) and is
cataloged by [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json).
Details: [`plugins/teamshared/README.md`](plugins/teamshared/README.md).

### cursor.directory listing

Submit **this** repo at [cursor.directory/plugins/new](https://cursor.directory/plugins/new):

```
https://github.com/teamshared-ai/teamshared-plugin
```

Do not submit the old `xhad/teamshared-cursor` redirect. Root `plugin.json` and
`.mcp.json` are the Open Plugins / directory discovery files; Cursor install
still uses `.cursor-plugin/` and `mcp.json`.

Ready-to-paste listing description:

```
TeamShared is hosted MCP plus the recall-first memory rule and Cursor
hooks that capture Agent Chat (plus failed test/lint/shell + preCompact).
No skills, slash commands, or extra agents.

Install in Cursor:
1. Settings → Plugins → Add marketplace
2. Paste https://github.com/teamshared-ai/teamshared-plugin
3. /add-plugin teamshared
4. Settings → Tools & MCP → teamshared → Connect (email + one-time code)

Cloud and Grok Bot agents inherit that Connect.
```

### From this repo (folder or symlink)

**Add plugins from folder** needs a marketplace catalog in the selected
directory. Select **this repo root** (it ships `.cursor-plugin/marketplace.json`
with `"source": "./"`).

Then enable the plugin, reload the window, and **Connect**.

For local iteration without the folder picker:

```bash
ln -sf "$(pwd)" ~/.cursor/plugins/local/teamshared
```

## Setup

1. **Connect with email/OTP** — **Settings → Tools & MCP → teamshared → Connect**.
   Cursor opens a browser; sign in with the same email + one-time code as the
   web console (`/app`). The plugin already shipped the server URL; do not add
   headers or a `tsk_*` token to the plugin `mcp.json`.
2. **Cloud / Grok Bot** — they inherit that account-level Cursor Connect. After
   the one-time Connect, every cloud agent for that user gets TeamShared.
3. **Developer: Reload Window** — confirm **Settings → MCP** shows `teamshared` enabled.

If you previously added `https://teamshared.com/mcp` by hand, remove that
manual entry so you do not get two `teamshared` servers.

Durable backup: one org `tsk_` on the MCP headers (`Authorization: Bearer tsk_…`)
for CI and other harnesses — not in the plugin `mcp.json`. Mint keys under
`/app/keys`.

## What you get

- **MCP tools**: `memory_recall`, `memory_remember`, `memory_session_*`, etc.
  (registered by `mcp.json` when the plugin is installed).
- **Rule**: injects the recall-first protocol on every agent turn, and points
  teammates to the web console (`/app`) for human actions.
- **Cursor hooks**: Agent Chat turns are appended to TeamShared in
  near-real-time without waiting for the agent to call
  `memory_session_ensure` / `context_commit`. `sessionStart` maps
  `conversation_id` onto a working session; `beforeSubmitPrompt` and
  `afterAgentResponse` append redacted user/assistant text; `sessionEnd`
  closes and distills. `stop` only notes aborted/error loops (it fires
  after every turn, so it does not distill). `postToolUse` still appends a
  short episodic fact when a Shell test/lint/command fails (command +
  error tail, secrets stripped). `preCompact` writes a short session
  summary. All reuse the existing Connect session — no `tsk_` in
  `mcp.json`. Fail-open if MCP is unreachable. Cloud agents may skip
  `sessionStart` / `sessionEnd`; prompt/response hooks still capture turns.
  Agents still recall first and may commit curated facts; hooks store the
  transcript.

The Cursor plugin still has no skills, slash commands, or extra agents.
The Claude Code package ships protocol **1.27.0** (`teamshared-memory`),
`/teamshared:status`, and official Claude Code capture hooks. The Codex
package ships the same 1.27.0 loop plus official Codex hooks (`SessionStart`,
`UserPromptSubmit`, `Stop`, `Interrupt`, `SessionEnd`, `PostToolUse` on failed
`Bash`, `PreCompact`). `SessionEnd` closes through one bounded commit;
`Interrupt` covers Cursor abort parity. Codex has no `StopFailure` or
`PostToolUseFailure`.

## Other clients

See [`clients/`](clients/) for Hermes, Claude Desktop, and protocol markdown.
Claude Code and Codex should use their marketplace plugins above unless you are
debugging a manual client configuration.

### Codex (manual TOML alternative)

For manual MCP registration without the native plugin, Codex uses TOML rather
than Cursor's JSON `mcp.json`. Mint a `tsk_` key at
[teamshared.com/app/keys](https://teamshared.com/app/keys), export it, then
register the hosted MCP (Codex sends `Authorization: Bearer tsk_…`):

```bash
export TEAMSHARED_TOKEN=tsk_...   # from /app/keys — never commit this
codex mcp add teamshared \
  --url https://teamshared.com/mcp \
  --bearer-token-env-var TEAMSHARED_TOKEN
```

Or merge [`install/codex/mcp.toml`](install/codex/mcp.toml) into project-local
`.codex/config.toml` and run Codex from that trusted repo root. Full steps:
[`install/codex/README.md`](install/codex/README.md).

Use either the native marketplace plugin or the manual TOML entry, not both.

Cursor desktop, Cloud, and Grok Bot still use **Connect** — do not add this
`tsk_` block to the plugin `mcp.json`.

## License

MIT — see [LICENSE](LICENSE).
