# D1 evidence

Captured 2026-09-15 in Cloud Agent
[bc-5eb767c6-aea6-5529-98d8-f56c77044359](https://cursor.com/agents/bc-5eb767c6-aea6-5529-98d8-f56c77044359)
against production `https://teamshared.com`.

| File | What it proves |
| --- | --- |
| [c1-org-mcp.log](c1-org-mcp.log) | C1 org path is live; C2 org PRM is not |
| [probe-latest.log](probe-latest.log) | Re-run of `scripts/d1_harness_probe.sh` in this VM |
| [cursor-cloud-grok.md](cursor-cloud-grok.md) | This Grok/Cloud run inherited Connect; no repo `mcp.json` |
| [cursor-desktop.md](cursor-desktop.md) | Blocked + laptop verify steps |
| [claude-code.md](claude-code.md) | Blocked + `claude mcp list` verify steps |
| [codex.md](codex.md) | Blocked + `codex mcp list` verify steps |

Re-run the production probe (no secrets):

```bash
./scripts/d1_harness_probe.sh
```
