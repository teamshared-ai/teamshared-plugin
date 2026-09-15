# Codex — blocked in this VM

`command -v codex` is absent. We cannot run `codex mcp list`.

## Docs used

- https://developers.openai.com/codex/config-reference
  - User `~/.codex/config.toml`; project `.codex/config.toml` only when
    trusted; closest project file wins; user file wins on conflicts.
  - `plugins.<id>.mcp_servers.<name>.enabled` can disable a plugin
    server. There is no key to change the plugin transport URL.
- https://developers.openai.com/codex/mcp
  - "Those servers are launched from the plugin, so user config doesn't
    set their transport command."
- This repo `install/codex/README.md` already warns: native plugin **or**
  manual TOML, not both. `.gitignore` ignores `.codex/`.

## How to verify

1. `codex plugin add teamshared@teamshared` and complete OAuth.
2. `codex mcp list` — one TeamShared from the plugin.
3. Merge into trusted `.codex/config.toml`:

   ```toml
   [mcp_servers.teamshared]
   url = "https://teamshared.com/o/YOUR_SLUG/mcp"
   enabled = true
   ```

4. `codex mcp list` — expect plugin + project servers.
5. Set
   `[plugins."teamshared@teamshared".mcp_servers.teamshared] enabled = false`
   to leave only the project server (new Connect / `tsk_`, not one
   reused OAuth). That is the escape hatch, not the default bind.
