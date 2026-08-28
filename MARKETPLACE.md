# Marketplace install & publish

How to install **teamshared** from this repo, and how to submit to the
[Cursor Marketplace](https://cursor.com/marketplace).

The plugin is **MCP + the recall rule + two Cursor hooks**
(`postToolUse` and `preCompact`). Still no skills, agents, or commands.

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
   a key in the plugin `mcp.json`.

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
Durable backup: one org `tsk_` on the MCP headers (`Authorization: Bearer tsk_…`)
— not in the plugin `mcp.json`. Mint keys under `/app/keys`.

## Publish to Cursor Marketplace (official listing)

Cursor reviews all marketplace plugins manually. Checklist before submitting at
[cursor.com/marketplace/publish](https://cursor.com/marketplace/publish):

- [ ] Repository is **public** and open source (MIT)
- [ ] `.cursor-plugin/marketplace.json` lists `teamshared` with `"source": "./"`
- [ ] `.cursor-plugin/plugin.json` is valid JSON with kebab-case `name`, `version`, `description`, `author`, `license`, `logo`, `mcpServers`
- [ ] `mcp.json` registers `https://teamshared.com/mcp` with no `headers`
- [ ] Plugin ships `rules/teamshared.mdc` and two hooks in `hooks/` (`postToolUse`, `preCompact` only; no `skills/`, `agents/`, `commands/`, or extra hooks)
- [ ] `README.md` covers install, MCP config, and what the plugin does
- [ ] `LICENSE` and `CHANGELOG.md` present
- [ ] Logo committed at `assets/logo.png` (512×512 brand mark) and `assets/logo.svg`; both `plugin.json` and `marketplace.json` reference `assets/logo.png` (relative path, not a remote URL)
- [ ] Test locally: symlink to `~/.cursor/plugins/local/teamshared`, reload, verify MCP + rule

### Validate locally

```bash
./scripts/validate.sh
```

### Submission notes

- Manifest `author.name` is **Teamshared Labs** in both `plugin.json` and
  `.cursor-plugin/plugin.json`. Marketplace `owner.name` matches.
- In the submission description, mention: requires the hosted teamshared MCP
  (`https://teamshared.com/mcp`) and email/OTP Connect (no API key in the
  plugin). Cloud / Grok Bot inherit that account-level Connect. Ships the
  recall-first rule plus two hooks (`postToolUse`, `preCompact`) — no
  skills, agents, or commands. Do not mention a `tsk_` key or `mcp_auth`
  in the marketplace description.
- Alternative first step: list on [cursor.directory](https://cursor.directory/plugins/new) while waiting for official marketplace review. Submit `https://github.com/teamshared-ai/teamshared-plugin` (not the old `xhad/teamshared-cursor` redirect). Root `plugin.json` and `.mcp.json` are the Open Plugins / Agent Plugins discovery files; Cursor install still uses `.cursor-plugin/` and `mcp.json`.

### Ready-to-paste marketplace description

Use this on [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).
Do not add a `tsk_` key or `mcp_auth` steps.

```
TeamShared registers the hosted TeamShared MCP (https://teamshared.com/mcp)
and ships the recall-first memory rule plus two Cursor hooks: postToolUse
(failed test/lint/shell) and preCompact (short session summary). Still no
skills, slash commands, or extra agents.

After install, connect with email and a one-time code under Settings →
Tools & MCP → teamshared → Connect (same as the web console). Cloud and
Grok Bot agents inherit that account-level Connect. The hooks reuse that
Connect session — do not paste a key into the plugin.
```

## Repo layout

```
teamshared-plugin/
├── .cursor-plugin/
│   ├── marketplace.json   # git marketplace + folder picker: source ./
│   └── plugin.json
├── plugin.json            # Agent Plugins 1.0.0 / cursor.directory discovery
├── .mcp.json              # Open Plugins MCP config (streamable-http)
├── mcp.json               # Cursor-native HTTP MCP (OAuth Connect, no headers)
├── rules/teamshared.mdc
├── hooks/                 # postToolUse + preCompact only
├── clients/               # protocol + manual MCP examples for other harnesses
├── assets/logo.png        # 512×512 brand mark (Cursor UI)
├── assets/logo.svg
├── README.md
├── CHANGELOG.md
└── LICENSE
```
