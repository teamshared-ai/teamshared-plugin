# Cursor Desktop — blocked in this VM

This Cloud VM has no Cursor Desktop GUI and no user
`~/.cursor/mcp.json`. Plugin cache under `~/.cursor/plugins/cache/` is
the Cloud plugin set, not a Desktop marketplace install we can toggle.

## Docs used

- https://cursor.com/docs/mcp — project `.cursor/mcp.json` and user
  `~/.cursor/mcp.json`; `${env:NAME}` interpolation on `url`; `envFile`
  is STDIO-only.
- https://cursor.com/help/customization/mcp — both files merge; same
  name: project takes priority over **user** (not stated for plugins).
- https://forum.cursor.com/t/duplicate-mcp-servers-in-cursor-settings/151971
  — `user-<name>` and `project-<name>` both stored; duplicates in the UI.
- This repo `.gitignore` already ignores `.cursor/mcp.json`.

## How to verify on a laptop

1. Install the TeamShared marketplace plugin and Connect to
   `https://teamshared.com/mcp`.
2. Confirm Settings → Tools & MCP shows one `teamshared`.
3. Write `.cursor/mcp.json`:

   ```json
   {
     "mcpServers": {
       "teamshared": {
         "type": "http",
         "url": "https://teamshared.com/o/YOUR_SLUG/mcp"
       }
     }
   }
   ```

4. Reload the window. Expect **two** TeamShared servers (plugin Connect
   + project). Screenshot that panel.
5. Remove the project file. Expect one server again.

Do not leave the project file in place. That is the duplicate D1 rejects.
