# teamshared (Cursor plugin)

Registers the teamshared MCP server and ships the recall-first memory rule.
Nothing else — no skills, slash commands, hooks, or continual-learning agent.

The MCP server itself lives in [`xhad/teamshared`](https://github.com/xhad/teamshared)
and is hosted at [teamshared.com](https://teamshared.com).

| Component | Purpose |
|---|---|
| `mcp.json` | Registers `https://teamshared.com/mcp` (URL only; Cursor OAuth Connect) |
| `rules/teamshared.mdc` | Lean always-on fetch/store loop (`alwaysApply`); tool encyclopedia lives in `memory_tools_catalog` |
| `clients/` | Copy-paste protocol + MCP examples for non-Cursor harnesses (not loaded by Cursor) |

## Install

### From marketplace (recommended)

1. **Settings → Plugins → Add marketplace** → `https://github.com/teamshared-ai/teamshared-plugin`
2. Run **`/add-plugin teamshared`** or enable it under Settings → Plugins
3. **Settings → Tools & MCP → teamshared → Connect** (email + one-time code, same as the console)

For [cursor.directory](https://cursor.directory/plugins/new), submit this same repo URL. Root `plugin.json` and `.mcp.json` are the Open Plugins / directory discovery files; Cursor install still uses `.cursor-plugin/` and `mcp.json`.

Installing the plugin registers the MCP server. You only click **Connect** —
do not paste a URL or `tsk_*` token into the plugin `mcp.json`. Cloud and
Grok Bot agents inherit that account-level Cursor Connect.

See [MARKETPLACE.md](MARKETPLACE.md) for publish/submission checklist.

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

Session logging and context compression live in the MCP tools and the rule —
not in Cursor hooks.

## Other clients

See [`clients/`](clients/) for Hermes, Claude Desktop, and protocol markdown.

## License

MIT — see [LICENSE](LICENSE).
