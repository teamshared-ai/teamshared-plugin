# Marketplace install & publish

How to install **teamshared** from this repo, and how to submit to the
[Cursor Marketplace](https://cursor.com/marketplace).

The plugin is **MCP + the recall rule only**.

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
- [ ] Plugin ships only `rules/teamshared.mdc` (no `skills/`, `agents/`, `commands/`, `hooks/`)
- [ ] `README.md` covers install, MCP config, and what the plugin does
- [ ] `LICENSE` and `CHANGELOG.md` present
- [ ] Logo committed at `assets/logo.png` (512×512 brand mark) and `assets/logo.svg`; both `plugin.json` and `marketplace.json` reference `assets/logo.png` (relative path, not a remote URL)
- [ ] Test locally: symlink to `~/.cursor/plugins/local/teamshared`, reload, verify MCP + rule

### Validate locally

```bash
./scripts/validate.sh
```

### Submission notes

- Put **Agentic Labs Ltd** in the manifest `author.name` field (company name).
- In the submission description, mention: requires the hosted teamshared MCP
  (`https://teamshared.com/mcp`) and email/OTP Connect (no API key in the
  plugin). Cloud / Grok Bot inherit that account-level Connect. Ships the
  recall-first rule only — no hooks or skills.
- Alternative first step: list on [cursor.directory](https://cursor.directory/plugins/new) while waiting for official marketplace review. Submit `https://github.com/teamshared-ai/teamshared-plugin` (not the old `xhad/teamshared-cursor` redirect). Root `plugin.json` and `.mcp.json` are the Open Plugins / Agent Plugins discovery files; Cursor install still uses `.cursor-plugin/` and `mcp.json`.

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
├── clients/               # protocol + manual MCP examples for other harnesses
├── assets/logo.png        # 512×512 brand mark (Cursor UI)
├── assets/logo.svg
├── README.md
├── CHANGELOG.md
└── LICENSE
```
