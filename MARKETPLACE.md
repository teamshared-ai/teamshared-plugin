# Marketplace install & publish

How to install **teamshared** from this repo, and how to submit to the
[Cursor Marketplace](https://cursor.com/marketplace).

The **Cursor** plugin is **MCP + the recall rule + Cursor hooks** that
capture Agent Chat (`sessionStart`, `beforeSubmitPrompt`,
`afterAgentResponse`, `stop`, `sessionEnd`) plus `postToolUse`,
`postToolUseFailure` (read-only recall), and `preCompact`. Still no
skills, agents, or commands.

Claude Code installs from the same GitHub URL via
`.claude-plugin/marketplace.json` (separate first-class package under
`claude/`: MCP + protocol 1.31.0 + official Claude Code capture hooks).
Official Anthropic marketplace submit is out of scope.

Codex installs from `.agents/plugins/marketplace.json` (package under
`plugins/teamshared/`: OAuth MCP + protocol 1.31.0 + official Codex capture
hooks). Keep that OAuth path separate from `install/codex/` (`tsk_`).

## Install (team / git marketplace)

1. In Cursor: **Settings → Plugins → Add marketplace**
2. Paste the repository URL:

   ```
   https://github.com/teamshared-ai/teamshared-plugin
   ```

3. Install the plugin:

   ```
   /add-plugin teamshared
   ```

   Or use **Settings → Plugins** and enable **teamshared**. This registers
   `https://teamshared.com/mcp` from the plugin's `mcp.json`.

4. **Settings → Tools & MCP → teamshared → Connect** and sign in with email +
   one-time code (same as the web console). Cloud and Grok Bot agents inherit
   that account-level Connect. No URL or bearer token to paste, and do not put
   a key in the plugin `mcp.json`. Then `teamshared org bind <slug>`
   (`.teamshared/org`). Do not add a second TeamShared server. Unbound `/mcp` keeps working.

5. **Developer: Reload Window** — confirm **Settings → MCP** shows `teamshared`.

### Local folder (Add plugins from folder)

Cursor's folder picker looks for a **marketplace catalog**
(`.cursor-plugin/marketplace.json`) in the directory you select — not a plugin
manifest. Select **this repo root**.

Then enable **teamshared** under **Settings → Plugins**, **Developer: Reload
Window**, and **Connect** under **Settings → Tools & MCP**.

### Local dev (symlink)

```bash
ln -sf "$(pwd)" ~/.cursor/plugins/local/teamshared
```

Symlink load uses `.cursor-plugin/plugin.json` only; no catalog is required.

## Prerequisites for users

| Requirement | Why |
|---|---|
| teamshared server | MCP tools at [teamshared.com](https://teamshared.com) |
| MCP OAuth Connect | One-time **Settings → Tools & MCP → teamshared → Connect** (email/OTP). Cloud / Grok Bot inherit it. No API key in the plugin. |

Sign-in is self-service: any email + a one-time passcode (first sign-in creates
your own org). After Connect, every cloud agent for that user gets TeamShared.
Bind each repo with `teamshared org bind <slug>` (`.teamshared/org`). Do not
add a second TeamShared server. Unbound `/mcp` keeps working. Bots that must
stay in one org: `teamshared token mint` (org-scoped seat key) or `/app/keys`
on the MCP headers (`Authorization: Bearer tsk_…`) — not in the plugin
`mcp.json`.

## Publish to Cursor Marketplace (official listing)

Cursor reviews all marketplace plugins manually. Checklist before submitting at
[cursor.com/marketplace/publish](https://cursor.com/marketplace/publish):

- [ ] Repository is **public** and open source (MIT)
- [ ] `.cursor-plugin/marketplace.json` lists `teamshared` with `"source": "./"`
- [ ] `.cursor-plugin/plugin.json` is valid JSON with kebab-case `name`, `version`, `description`, `author`, `license`, `logo`, `mcpServers`
- [ ] `mcp.json` registers `https://teamshared.com/mcp` with no `headers`
- [ ] Plugin ships `rules/teamshared.mdc` and Cursor hooks in `hooks/` (chat capture + `postToolUse` + `postToolUseFailure` + `preCompact`; no `skills/`, `agents/`, or `commands/`)
- [ ] `README.md` covers install, MCP config, and what the plugin does
- [ ] `LICENSE` and `CHANGELOG.md` present
- [ ] Logo committed at `assets/logo.png` (512×512 brand mark) and `assets/logo.svg`; both Cursor `plugin.json` and `marketplace.json` reference `assets/logo.png` (relative path, not a remote URL)
- [ ] Codex package logos live inside `plugins/teamshared/assets/` (`logo.png` 512×512, `icon.png` 128×128); `.codex-plugin/plugin.json` sets `interface.logo` / `logoDark` → `./assets/logo.png` and `interface.composerIcon` → `./assets/icon.png`
- [ ] Test locally: symlink to `~/.cursor/plugins/local/teamshared`, reload, verify MCP + rule

### Validate locally

```bash
./scripts/validate.sh
```

### Submission notes

- Manifest `author.name` is **Loreum Labs Ltd** in both `plugin.json` and
  `.cursor-plugin/plugin.json`. Marketplace `owner.name` matches.
- In the submission description, mention: requires the hosted teamshared MCP
  (`https://teamshared.com/mcp`) and email/OTP Connect (no API key in the
  plugin). Cloud / Grok Bot inherit that account-level Connect. Ships the
  recall-first rule plus Cursor hooks that capture Agent Chat (and
  `postToolUse` / `preCompact`) — no skills, agents, or commands. Do not
  mention a `tsk_` key or `mcp_auth` in the marketplace description.
- Alternative first step: list on [cursor.directory](https://cursor.directory/plugins/new) while waiting for official marketplace review. Submit `https://github.com/teamshared-ai/teamshared-plugin` (not the old `xhad/teamshared-cursor` redirect). Root `plugin.json` and `.mcp.json` are the Open Plugins / Agent Plugins discovery files; Cursor install still uses `.cursor-plugin/` and `mcp.json`.

### Ready-to-paste marketplace description

Use this on [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).
Do not add a `tsk_` key or `mcp_auth` steps.

```
TeamShared registers the hosted TeamShared MCP (https://teamshared.com/mcp)
and ships the recall-first memory rule plus Cursor hooks that capture
Agent Chat in near-real-time, plus postToolUse (failed test/lint/shell),
postToolUseFailure (read-only recall of prior fixes), and preCompact
(short session summary). Still no skills, slash commands, or extra agents.

After install, connect with email and a one-time code under Settings →
Tools & MCP → teamshared → Connect (same as the web console). Cloud and
Grok Bot agents inherit that account-level Connect. Bind each repo with
`teamshared org bind` (`.teamshared/org`). Do not add a second TeamShared
server. Unbound `/mcp` keeps working. Bots that must stay in one org use
`teamshared token mint`. The hooks reuse that Connect session — do not
paste a key into the plugin.
```

## Claude Code marketplace

Users add this repo as a Claude Code marketplace (catalog at
`.claude-plugin/marketplace.json`), then install the `claude/` package:

```
/plugin marketplace add teamshared-ai/teamshared-plugin
/plugin install teamshared@teamshared
```

Auth is Claude Code's native `/mcp` → Authenticate (email/OTP). Capture
hooks optionally use `TEAMSHARED_TOKEN` from `teamshared token mint` (org-scoped
seat key) or `/app/keys`. Never commit the key. Bind the checkout with
`teamshared org bind <slug>` (`.teamshared/org`). Do not add a second TeamShared server.
Unbound `/mcp` keeps working. After install, `/reload-plugins`, confirm `/mcp`,
then `/teamshared:status`. See [`claude/README.md`](claude/README.md).

## Codex marketplace

Users add this repo as a Codex marketplace (catalog at
`.agents/plugins/marketplace.json`), then install the `plugins/teamshared/`
package:

```bash
codex plugin marketplace add teamshared-ai/teamshared-plugin
codex plugin add teamshared@teamshared
```

Auth is MCP OAuth discovery (no token in `.mcp.json`). After install, connect
when prompted, trust hooks with `/hooks`, bind with `teamshared org bind <slug>`
(`.teamshared/org`), then `$status`. Do not add a second TeamShared server.
Unbound `/mcp` keeps working. Codex has no
`StopFailure` or `PostToolUseFailure`. See
[`plugins/teamshared/README.md`](plugins/teamshared/README.md). Do not also
install [`install/codex/`](install/codex/README.md).

## Repo layout

```
teamshared-plugin/
├── .cursor-plugin/
│   ├── marketplace.json   # Cursor git marketplace + folder picker: source ./
│   └── plugin.json
├── .claude-plugin/
│   └── marketplace.json   # Claude Code catalog: source ./claude
├── claude/                # Claude Code plugin (MCP + 1.30 protocol + capture hooks)
├── plugin.json            # Agent Plugins 1.0.0 / cursor.directory discovery
├── .mcp.json              # Open Plugins MCP config (streamable-http)
├── mcp.json               # Cursor-native HTTP MCP (OAuth Connect, no headers)
├── rules/teamshared.mdc
├── hooks/                 # Agent Chat capture + postToolUse + postToolUseFailure + preCompact (Cursor)
├── clients/               # protocol + manual MCP examples for other harnesses
├── .agents/plugins/
│   └── marketplace.json   # Codex catalog: source ./plugins/teamshared
├── plugins/teamshared/    # Codex plugin (OAuth MCP + 1.30 protocol + capture hooks)
│   ├── .codex-plugin/plugin.json  # interface.logo + composerIcon
│   └── assets/logo.png / icon.png  # ChatGPT Sources + Codex directory
├── install/codex/         # Codex: mcp add + .codex/config.toml (tsk_ via env; do not mix)
├── assets/logo.png        # 512×512 brand mark (Cursor UI)
├── assets/logo.svg
├── README.md
├── AGENTS.md
├── CHANGELOG.md
└── LICENSE
```
