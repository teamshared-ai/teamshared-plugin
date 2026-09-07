# teamshared (Cursor plugin + Claude Code marketplace)

Registers the teamshared MCP server. The **Cursor** plugin also ships the
recall-first memory rule and two Cursor hooks (`postToolUse` for failed
test/lint/shell, `preCompact` for a short session summary). The Cursor
plugin still has no skills, slash commands, extra hooks, or extra agents.

This repo also ships a **Claude Code** marketplace plugin under `claude/`
(remote MCP + `TEAMSHARED_TOKEN` auth). Claude Code does not inherit Cursor Connect.

The MCP server itself lives in [`xhad/teamshared`](https://github.com/xhad/teamshared)
and is hosted at [teamshared.com](https://teamshared.com).

| Component | Purpose |
|---|---|
| `mcp.json` | Registers `https://teamshared.com/mcp` (URL only; Cursor OAuth Connect) |
| `rules/teamshared.mdc` | Lean always-on fetch/store loop (`alwaysApply`); tool encyclopedia lives in `memory_tools_catalog` |
| `hooks/` | Two Cursor hooks only: `postToolUse` (failed test/lint/shell) and `preCompact` |
| `claude/` | Claude Code plugin (remote MCP + `TEAMSHARED_TOKEN`; no Cursor hooks) |
| `.claude-plugin/marketplace.json` | Claude Code marketplace catalog (`/plugin marketplace add teamshared-ai/teamshared-plugin`) |
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

Claude Code does not inherit Cursor Connect. Use a `tsk_` org key in
`TEAMSHARED_TOKEN` — never commit it.

```
/plugin marketplace add teamshared-ai/teamshared-plugin
/plugin install teamshared@teamshared
/reload-plugins
```

Then export the key in the environment that launches Claude Code:

```bash
export TEAMSHARED_TOKEN=tsk_...   # mint under https://teamshared.com/app/keys
```

The Claude package registers `https://teamshared.com/mcp` with
`Authorization: Bearer ${TEAMSHARED_TOKEN}` (same placeholder idea as
`install/claude/mcp.json`). Confirm tools appear under `/mcp` as
`plugin:teamshared:teamshared`. Details: [`claude/README.md`](claude/README.md).

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
TeamShared is hosted MCP plus the recall-first memory rule and two Cursor
hooks (failed test/lint/shell + preCompact). No skills, slash commands, or
extra agents.

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
- **Two hooks only**: `postToolUse` appends a short episodic fact when a
  Shell test/lint/command fails (command + error tail, secrets stripped).
  `preCompact` writes a short session summary through `context_commit`.
  Both reuse the existing Connect session — no `tsk_` in `mcp.json`.

The Cursor plugin still has no skills, slash commands, extra agents, or extra
hooks. The Claude Code package adds only a thin `teamshared-memory` skill.

## Other clients

See [`clients/`](clients/) for Hermes, Claude Desktop, and protocol markdown.
Claude Code should use the marketplace plugin above, not a hand-merged
`~/.claude.json`, unless you are debugging.

### Codex

Codex is TOML, not Cursor's JSON `mcp.json`. Mint a `tsk_` key at
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

Cursor desktop, Cloud, and Grok Bot still use **Connect** — do not add this
`tsk_` block to the plugin `mcp.json`.

## License

MIT — see [LICENSE](LICENSE).
