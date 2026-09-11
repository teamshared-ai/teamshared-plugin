# teamshared (Cursor + Claude Code plugin)

Registers the teamshared MCP server, the recall-first memory rule/skill, and
two hooks (`postToolUse`/`PostToolUse` for failed test/lint/shell,
`preCompact`/`PreCompact` for a short session summary). Nothing else — no
slash commands or extra agents. This one repo ships **two** plugin
manifests side by side:

- `.cursor-plugin/` — the Cursor plugin (rule, no skills)
- `.claude-plugin/` — the Claude Code plugin (skill instead of a rule, since
  Claude Code has no `alwaysApply` rule concept)

Both point at the same hosted MCP server and reuse the same two hook scripts
under `hooks/`.

The MCP server itself lives in [`xhad/teamshared`](https://github.com/xhad/teamshared)
and is hosted at [teamshared.com](https://teamshared.com).

| Component | Purpose |
|---|---|
| `mcp.json` | Registers `https://teamshared.com/mcp`, shared by both plugins |
| `rules/teamshared.mdc` | Cursor: lean always-on fetch/store loop (`alwaysApply`); tool encyclopedia lives in `memory_tools_catalog` |
| `skills/teamshared/` | Claude Code: the same fetch/store loop as a Skill (relevance-triggered, not always-on) |
| `hooks/` | `capture.py` + `post_tool_use.py` + `pre_compact.py` shared by both; `hooks.cursor.json` wires them for Cursor, `hooks.claude.json` for Claude Code (named `hooks.cursor.json` rather than the default `hooks.json` so Claude Code's plugin loader doesn't also merge it in) |
| `clients/` | Copy-paste protocol + MCP examples for other harnesses (not loaded by either plugin) |

## Install (Claude Code)

1. `/plugin marketplace add teamshared-ai/teamshared-plugin`
2. `/plugin install teamshared`
3. `/mcp` → **teamshared** → **Authenticate** — Claude Code auto-detects that
   the server needs OAuth, opens a browser to the same email/OTP login as the
   web console, and stores the token in your system keychain. This is the
   same one-time step as Cursor's Settings → Connect; plugin-registered MCP
   servers use the identical OAuth flow as manually added ones.
4. Confirm `/mcp` shows `teamshared` connected, and the `teamshared` skill
   shows up in `/skills` (or ask "what skills do I have").

The plugin registers `https://teamshared.com/mcp` (`mcpServers` in
`.claude-plugin/plugin.json`, pointing at the shared root `mcp.json`) — no URL
or token to paste. If `/mcp` isn't available (a non-interactive run) and a
`teamshared` call comes back unauthenticated, Claude falls back to calling the
`authenticate` tool with your email, then `complete_authentication` with the
one-time code you receive. For fully non-interactive contexts (CI, or the two
hooks below), set `TEAMSHARED_TOKEN` to an org `tsk_` key minted under
`/app/keys`.

Unlike the Cursor rule, the Claude Code skill (`skills/teamshared/SKILL.md`)
is relevance-triggered, not always-on — Claude Code has no `alwaysApply`
mechanism for skills. It's written to trigger on most non-trivial coding/work
requests, not just explicit "remember this" asks.

## Install (Cursor)

### From git marketplace (recommended)

1. **Settings → Plugins → Add marketplace** → paste `https://github.com/teamshared-ai/teamshared-plugin`
2. Run **`/add-plugin teamshared`** or enable **teamshared** under Settings → Plugins
3. **Settings → Tools & MCP → teamshared → Connect** (email + one-time code, same as the console)

Cloud and Grok Bot agents inherit that account-level Connect. Installing the
plugin registers `https://teamshared.com/mcp` — you only click **Connect**.
Do not paste a URL or token into the plugin `mcp.json`.

See [MARKETPLACE.md](MARKETPLACE.md) for the official Marketplace publish checklist.

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

## Setup (Cursor)

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

## What you get (Cursor)

- **MCP tools**: `memory_recall`, `memory_remember`, `memory_session_*`, etc.
  (registered by `mcp.json` when the plugin is installed).
- **Rule**: injects the recall-first protocol on every agent turn, and points
  teammates to the web console (`/app`) for human actions.
- **Two hooks only**: `postToolUse` appends a short episodic fact when a
  Shell test/lint/command fails (command + error tail, secrets stripped).
  `preCompact` writes a short session summary through `context_commit`.
  Both reuse the existing Connect session — no `tsk_` in `mcp.json`.

Still no skills, slash commands, extra agents, or extra hooks in the Cursor
plugin.

## What you get (Claude Code)

- **MCP tools**: the same `memory_recall`, `memory_remember`,
  `memory_session_*`, etc., registered from the shared `mcp.json`.
- **Skill**: `skills/teamshared/SKILL.md` carries the same recall-first
  protocol as the Cursor rule, pointing the user at `/mcp` → Authenticate as
  the normal login path (Claude Code's own OAuth flow — same email/OTP login,
  same keychain storage, same UX as Cursor's Connect) and falling back to the
  `authenticate` / `complete_authentication` MCP tools only when `/mcp` isn't
  available. The skill is relevance-triggered (Claude Code has no
  `alwaysApply`), so it's written to match most non-trivial coding/work
  requests.
- **Two hooks only**: `PostToolUse` (matcher `Bash`) and `PreCompact`, wired
  in `hooks/hooks.claude.json` to the same `post_tool_use.py` / `pre_compact.py`
  scripts the Cursor plugin uses. They authenticate with an org `tsk_` key from
  `TEAMSHARED_TOKEN` (set it in your shell profile or `.claude/settings.json`
  `env`) — Claude Code has no client-side Connect token store for a hook
  subprocess to reuse, so without that env var the hooks no-op silently.

No slash commands or extra agents in the Claude Code plugin either.

## Other clients

See [`clients/`](clients/) for Hermes, Claude Desktop, and protocol markdown.

## License

MIT — see [LICENSE](LICENSE).
