---
name: teamshared-memory
description: Recall-first TeamShared memory protocol for Codex. Use on every turn when TeamShared MCP tools are available, and when recalling or storing team memory, past work, preferences, playbooks, projects, or durable repository context.
---

# TeamShared memory for Codex

The `teamshared` MCP server at `https://teamshared.com/mcp` is durable memory
across tasks and repositories. Authenticate through the plugin's OAuth Connect
flow. The server publishes MCP OAuth discovery metadata, so this package does
not store API keys or headers. Never store tokens, credentials, or login codes
in TeamShared memory.

For manual Codex TOML setup outside this plugin, follow
`install/codex/README.md` in the repository and use `TEAMSHARED_TOKEN`.

When unsure which tool fits an intent, call
`memory_tools_catalog(need="<intent>")`.

## Every turn

1. Call `memory_session_ensure(repo=..., topic=..., fresh=..., user=...)` to
   recover or rotate the session and append the substantive user request. Use
   `fresh=true` only on the first turn of a new task or after a clear pivot.
2. Call `memory_recall(...)` with a short keyword query. Retrieve named
   playbooks, skills, and entities with `memory_playbook_get`,
   `memory_skill_get`, and `memory_entity_view` instead of recall.
3. Do the user's work, grounding the result in relevant memory hits. If recall
   is empty, say so before relying on current context or general knowledge.
4. Make `context_commit(summary=..., facts=[...], repo=..., github=...,
   close=...)` the final TeamShared MCP call. Use `close=true` when the task is
   complete.

Do not append tool-call turns for TeamShared calls. If the MCP tools are
unavailable, continue the user's task without memory and briefly disclose that
TeamShared could not be used.

## Fetch

Default recall scope is durable: semantic, episodic, procedural, skill,
strategic, and work. Use `scope=["working"]` only for the current task's open
session turns. Start with one to three keywords, then broaden if results are
thin.

```text
memory_recall(
  query=<1-3 keyword tokens>,
  repo=<workspace-slug>,
  github=<owner/repo>,
  explain=true
)
```

## Store

| Need | Tool |
|---|---|
| Durable fact, preference, event, or note | `context_commit` `facts[]` or `memory_remember` |
| Atomic how-to | `memory_skill_set` |
| Composed flow | `memory_playbook_set` |
| Assignable task | `work_*` |
| Board or project | `project_*` |
| Person or organization | `memory_entity_view` and ontology tools |

Resolve `repo` from the workspace root as a slug without slashes. Resolve
`github` as `owner/repo` when a GitHub remote is available. Never call
`memory_forget` without the user's explicit request.
