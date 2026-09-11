---
name: teamshared-memory
description: Recall-first TeamShared memory protocol 1.27.0 for Claude Code. Use on every turn when TeamShared MCP tools are available, and when searching or storing team memory, past work, preferences, playbooks, soul, or agent memory.
---

# TeamShared memory (Claude Code)

<!-- teamshared-rule-version: 1.27.0 -->

The `teamshared` MCP server is your durable brain across sessions and repos.
Authenticated identity sets write attribution; do not pass `agent` unless you
intentionally override it or narrow a read filter. The MCP connection itself
uses Claude Code's own native OAuth flow — point the user at **`/mcp` →
teamshared → Authenticate** if it shows as needing authentication; that opens
a browser to the same email/OTP login as the web console and stores the token
for you. Never try to do this yourself. Do not call `mcp_auth` as the first
hop — it is a last-resort fallback after initialize when the host has no
token and `/mcp` isn't available.

The chat-capture **hooks** (below) are a separate subprocess with no access
to that OAuth token, so they authenticate independently with a `tsk_` bearer
from `TEAMSHARED_TOKEN` (`Authorization: Bearer tsk_…`), minted at
https://teamshared.com/app/keys. They're optional — unset, they simply don't
capture anything, and the MCP connection and every-turn workflow are
unaffected. Never store or print the token. Point humans at the console
(`/app`) for sign-in, wiki, people, and keys.

This skill is protocol **1.27.0** — the same fetch/store loop as
`rules/teamshared.mdc` in the teamshared-plugin repo, adapted for Claude Code
(OAuth MCP connection, `TEAMSHARED_TOKEN` hooks, Claude write path). SessionStart
also injects the every-turn loop.

Unsure which tool? Call `memory_tools_catalog(need="<intent>")` — do not scan
every MCP descriptor, and do not call `scope="memory", tier="core"` as the only
discovery path (that hides files and projects).

## Staying current

On the **first turn of a chat** (or when the user asks about teamshared
versions), call `version` with this skill's protocol version (`1.27.0`) as
`installed_rule_version`. Do not call `version` every turn. If
`update_available: true`, write the returned `rule_markdown` verbatim to
`~/.claude/rules/teamshared.md` (or `.claude/rules/teamshared.md` in a repo)
and tell the user the memory rule was updated. Never invent a version.

## Every turn

Run in order:

1. **`memory_session_ensure(repo=..., topic=..., fresh=<first turn>, user=<request>)`**
   — recovers or rotates the session and appends the substantive user request.
   `fresh=true` only on the first turn of a new chat (or a clear mid-chat pivot).
   Bound work (named work id, or `agent_run_*` context) → pass `work_id=`; else
   a named playbook → `playbook_slug=`. Omit both when unbound — never dump the
   playbook catalog. Adopt non-empty `soul` (private human), `agent_memory`
   (org-shared Agent), and `playbook` `{name, description, body_md, slug}` from
   the ensure payload.
2. **`memory_recall(...)`** for keyword search (architecture, debugging, past
   work). Named playbook/skill/entity → get-by-name, not recall. Resume handoff: `memory_changes_since(cursor=...)` for durable deltas (opaque cursor); still `memory_recall` for search.
3. **Do the work.**
4. **`context_commit(summary=..., facts=[...], repo=..., github=..., close=<done?>)`**
   — last MCP call of the turn. `close=true` when the task is done or the user
   says goodbye (queues distillation). Adopt `reopened: true` session ids.

Do not append `[tool]` turns for teamshared MCP calls. After bulky Bash/Read
output, `context_normalize` and reason over the trimmed `output`. Do not
re-normalize teamshared MCP responses.

## Fetch

Always pass `repo=` and `github=` (see **Code scope**). Default scope is durable
(semantic, episodic, procedural, skill, strategic, work) — **not** working.
`scope=["working"]` only when you need this chat's open session turns.

```text
memory_recall(
  query=<1-3 keyword tokens>,
  repo=<workspace-slug>,
  github=<owner/repo>,
  explain=true
)
```

1. Short keyword first (`"mex"`, `"Hivemind"`). If thin, broaden. Not a long conversational question.
2. Named playbook/skill/entity → `memory_playbook_get` / `memory_skill_get` / `memory_entity_view`.
3. Ground answers in hits; if empty, say so before answering from priors.
4. Prefer `metadata.matched_keyword: true`. `memory_think` only after hits, or
   for open strategic questions.

## Store

**Session (every turn):** `ensure(user=)` captures the request; `context_commit`
`summary` is a faithful assistant reply — not UI boilerplate. Truncate long
tool output. Never store secrets, tokens, or credentials.

This plugin also ships Claude Code hooks that capture the chat into TeamShared
working memory (`TEAMSHARED_TOKEN` only, fail-open): `SessionStart` injects
this protocol and maps `session_id` → `memory_session_ensure`;
`UserPromptSubmit` appends the redacted user prompt; `Stop` appends the
redacted assistant text (`last_assistant_message`); `StopFailure` notes API
errors; `SessionEnd` closes and distills; `PostToolUseFailure` writes a short
episodic fact when Bash/PowerShell fails; `PreCompact` writes a short session
summary. Hooks store the transcript; you still recall first and may
`context_commit` curated facts. Do not re-append the same user/assistant text
in the same turn.

**Durable `facts[]`** (still true next week; one dense paragraph; `subject` +
tags). `[[Entity]]` wikilinks autolink. Code-scoped facts take `repo=` /
`github=`.

| Signal | `kind` |
|---|---|
| "I prefer / always / never …" | `preference` |
| Stable repo/org fact | `fact` |
| One-off event worth logging | `event` |
| Outreach send (mentions Person + Campaign) | `outreach` |
| Misc working note | `note` |

Do **not** put skills, playbooks, tasks, or strategic vision in `facts[]` /
`memory_remember`:

| Want | Tool |
|---|---|
| Atomic how-to | `memory_skill_set` |
| Composed flow (`tool_recipe.skills`) | `memory_playbook_set` |
| Assignable task / outreach beat | `work_*` (`part_of=` a campaign Project) |
| Person / campaign CRM | `account_brief` / `memory_entity_view` (`gtm-outreach`) |
| Another agent's profile | `memory_agent_get` (`slug` / `cursor_agent_id`) |
| Board / project | `project_*` |
| Spawn Cursor coding worker | `agent_run_start` (`github=owner/repo`) |
| Follow / status / cancel cloud agent | `agent_run_followup` / `_status` / `_cancel` |
| Large local file upload | `file_upload_request` |
| Other shared files | `file_*` (`work_id=` hangs a file on a task; `project_id=` on a project) |
| Vision / OKRs | `memory_strategic_*` |

`close=true` distills the session into durable memory.

## Campaign CRM

Use the seeded ontology. Do **not** invent Contact or Deal kinds. Gmail /
Telegram send skills live on the Grok Bot — do not ingest inbox into
TeamShared.

| Need | Use |
|---|---|
| Contact | `Person` (`memory_ontology_propose_entity`). Properties: email, name, telegram, role, stage |
| Company | `Organization`. `Person --works_at--> Organization` (`works_for` is an alias of `works_at`) |
| Campaign | `Project` (`status` = active / paused / done). People and bots `works_on` it |
| Beat | `work_create(..., part_of=<campaign>)`; `assigned_to` a Person or Agent |
| After send | `memory_remember(kind="outreach")` mentioning Person and Campaign |

Playbook `gtm-outreach`: `memory_entity_view` → draft + approval child;
human / Grok card sends. That Person view is the CRM record.

## Code scope

Resolve `repo=` every chat, not only git tasks:

1. Workspace slug — `git rev-parse --show-toplevel` (else the project root);
   strip leading `/`, replace `/` with `-`. Never use `owner/repo` as `repo=`
   (slashes are invalid).
2. GitHub — `gh repo view --json nameWithOwner` → `github=<owner/repo>` (stored
   as `github:<owner>/<repo>`). If an MCP call fails on `repo`, omit it and
   retry with `github=` and/or tags.

Reads are the shared brain (all agents) unless you pass `agent=` to narrow.
Writes attribute to the authenticated identity.

`memory_recall` may return hits **and** `degraded: true` when
`errors_by_pillar` is non-empty (a pillar timed out or was unavailable).
Treat that as partial — do not conclude "nothing known" from a thin result.
Error values are stable codes (`unavailable`, `timeout`, `permission_denied`),
not exception text. `GET /metrics` is unauthenticated and strips `org=` UUID
labels; use `health` for connectivity, not metrics as a tenant-debug scrape.

## Never

- `memory_forget` without an explicit user request
- `memory_session_open` after `memory_session_ensure` already returned a session_id
- `memory_remember` for skills, playbooks, tasks, or strategic vision
- Inventing Contact or Deal kinds — use Person / Organization / Project / WorkItem
- Appending `[tool]` turns for teamshared MCP calls
- Probing `TEAMSHARED_*` env vars in the shell — call `health`
- Storing secrets, tokens, credentials, or the `mcp_auth` login code
- Printing or committing `TEAMSHARED_TOKEN`
