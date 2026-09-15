# Cursor Cloud / Grok Bot — exercised in this run

**Run:** https://cursor.com/agents/bc-5eb767c6-aea6-5529-98d8-f56c77044359
**Model:** cursor-grok-4.6-high-fast (Grok Bot on Cursor Cloud)
**Repo:** github.com/teamshared-ai/teamshared-plugin
**Environment:** personal, no `environment.json` in the checkout
(`cursor-cloud-environment-info`: `environmentJsonPath` null,
`source=Personal`)

## What this session loaded

- TeamShared MCP tools are available (`work_get`, `file_get`,
  `memory_session_ensure`, …) under the `Teamshared` namespace.
- There is **no** `/workspace/.cursor/mcp.json`.
- There is **no** `~/.cursor/mcp.json`.
- Plugin sources in the checkout still point at `https://teamshared.com/mcp`
  (`mcp.json`, `.mcp.json`, `claude/.mcp.json`,
  `plugins/teamshared/.mcp.json`).
- Official Cloud MCP docs (cursor.com/docs/cloud-agent/capabilities):
  agents use MCP from the Agents dropdown and Team Integrations & MCP.
  HTTP MCP is proxied by the Cursor backend; it is not started from a
  repo file inside the VM.

## Finding

Cloud / Grok inherited the account-level TeamShared Connect to `/mcp`.
Repo `.cursor/mcp.json` is not how this harness picked up TeamShared.
Writing an org URL there would not replace that Connect; if Cloud later
loaded project MCP files, it would be a second server.

Hooks that run in the checkout can still read `.teamshared/org` (D2).

## How to re-verify

1. Start a Cloud / Grok agent on a repo **without** `.cursor/mcp.json`.
2. Confirm TeamShared tools exist (account Connect).
3. Optionally add `.cursor/mcp.json` with `https://teamshared.com/o/{slug}/mcp`
   in a throwaway repo. If a second TeamShared namespace appears, that
   confirms the duplicate. If it does not appear, Cloud is ignoring the
   repo file — also consistent with "do not use it as the bind path."
