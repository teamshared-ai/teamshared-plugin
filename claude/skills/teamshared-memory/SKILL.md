---
name: teamshared-memory
description: Recall-first TeamShared memory protocol for Claude Code. Use when searching or storing team memory, past work, preferences, playbooks, or when TeamShared MCP tools are available.
---

# TeamShared memory (Claude Code)

The `teamshared` MCP server (`https://teamshared.com/mcp`) is durable memory
across sessions and repos. Auth is a `tsk_` bearer from `TEAMSHARED_TOKEN`
(`Authorization: Bearer tsk_…`). Claude Code does not inherit Cursor Connect.
Do not call `mcp_auth` as the first hop. Mint keys at
https://teamshared.com/app/keys. Never store the token.

This skill is a Claude-shaped pointer to the same fetch/store loop as
`rules/teamshared.mdc` in this repo. It does not install Cursor hooks.

Unsure which tool? Call `memory_tools_catalog(need="<intent>")`.

## Every turn

1. **`memory_session_ensure(repo=..., topic=..., fresh=<first turn>, user=<request>)`**
   — recovers or rotates the session and appends the substantive user request.
   `fresh=true` only on the first turn of a new chat (or a clear mid-chat pivot).
2. **`memory_recall(...)`** for keyword search. Named playbook/skill/entity →
   `memory_playbook_get` / `memory_skill_get` / `memory_entity_view`, not recall.
3. **Do the work.**
4. **`context_commit(summary=..., facts=[...], repo=..., github=..., close=<done?>)`**
   — last MCP call of the turn. `close=true` when the task is done.

Do not append `[tool]` turns for TeamShared MCP calls. Never store secrets,
tokens, or credentials.

## Fetch

Default scope is durable (semantic, episodic, procedural, skill, strategic,
work) — **not** working. Short keyword first; if thin, broaden.

```text
memory_recall(query=<1-3 keyword tokens>, repo=<workspace-slug>, github=<owner/repo>, explain=true)
```

Ground answers in hits; if empty, say so before answering from priors.

## Store

| Want | Tool |
|---|---|
| Durable fact / preference / event | `context_commit` `facts[]` or `memory_remember` |
| Atomic how-to | `memory_skill_set` |
| Composed flow | `memory_playbook_set` |
| Assignable task | `work_*` |
| Board / project | `project_*` |

Resolve `repo=` from the workspace slug (no slashes) and `github=` as
`owner/repo` when available.
