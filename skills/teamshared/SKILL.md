---
name: teamshared
description: Use the teamshared MCP server as persistent, cross-session, cross-repo team memory — recalling past decisions, architecture, debugging history, and team preferences, and capturing durable facts and session summaries as you work. Use for any non-trivial coding or work request, not just explicit "remember this" asks.
when_to_use: Triggered by "what did we decide about...", "how do we usually...", "remember this", "did we run into this before", starting a new coding session, or wrapping one up.
license: MIT
---

# teamshared Memory Protocol

<!-- teamshared-skill-version: 1.18.0 -->

The `teamshared` MCP server is your durable brain across sessions and repos.
Authenticated identity sets write attribution; do not pass `agent` unless you
intentionally override it or narrow a read filter.

## First-time auth

Claude Code auto-detects that `teamshared` needs OAuth and shows it as
"Needs authentication" in `/mcp`. Point the user at **`/mcp` → teamshared →
Authenticate** — that opens a browser to the same email/OTP login as the web
console and stores the token in the system keychain, same as Cursor's
Connect. This is the normal path; do not try to do it yourself.

Only fall back to calling `authenticate` (with the user's email) then
`complete_authentication` (with the one-time code they receive) yourself if a
`teamshared` call fails as unauthenticated and `/mcp` isn't available in the
current context (e.g. a non-interactive run). Never invent or guess a code.
Durable backup for non-interactive contexts (CI, hooks): one org `tsk_` key
on the MCP headers (`Authorization: Bearer tsk_…`) — mint it under
`/app/keys`, not in this plugin's `mcp.json`. Point humans at the console
(`/app`) for sign-in, wiki, people, and keys.

Unsure which tool? Call `memory_tools_catalog(need="<intent>")` — do not scan
every MCP descriptor, and do not call `scope="memory", tier="core"` as the only
discovery path (that hides files and projects).

## Every turn

Run in order:

1. **`memory_session_ensure(repo=..., topic=..., fresh=<first turn>, user=<request>)`**
   — recovers or rotates the session and appends the substantive user request.
   `fresh=true` only on the first turn of a new chat (or a clear mid-chat pivot).
   Adopt a non-empty `soul` as always-on identity for the rest of the chat.
2. **`memory_recall(...)`** for non-trivial work (architecture, debugging, past
   work, "how do we…"). Skip only true one-liner acknowledgments.
3. **Do the work.**
4. **`context_commit(summary=..., facts=[...], repo=..., github=..., close=<done?>)`**
   — last MCP call of the turn. `close=true` when the task is done or the user
   says goodbye (queues distillation). Adopt `reopened: true` session ids.

Do not append `[tool]` turns for teamshared MCP calls. After bulky Bash/Grep/Read
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

1. Short keyword first (`"mex"`, `"Hivemind"`). If thin, broaden.
2. Do not start with only a long conversational question.
3. Ground answers in hits; if empty, say so before answering from priors.
4. Prefer `metadata.matched_keyword: true`. `memory_think` only after hits, or
   for open strategic questions.

## Store

**Session (every turn):** `ensure(user=)` captures the request; `context_commit`
`summary` is a faithful assistant reply — not UI boilerplate. Truncate long
tool output. Never store secrets, tokens, or credentials.

This plugin also ships **two Claude Code hooks** (no others): `PostToolUse`
writes a short episodic fact when a Bash test/lint/command fails; `PreCompact`
writes a short session summary. Both use the same ingest path (`context_commit`)
and reuse an org `tsk_` key from the environment when one is configured. Do not
duplicate that write in the same turn.

**Durable `facts[]`** (still true next week; one dense paragraph; `subject` +
tags). `[[Entity]]` wikilinks autolink. Code-scoped facts take `repo=` /
`github=`.

| Signal | `kind` |
|---|---|
| "I prefer / always / never …" | `preference` |
| Stable repo/org fact | `fact` |
| One-off event worth logging | `event` |
| Misc working note | `note` |

Do **not** put skills, playbooks, tasks, or strategic vision in `facts[]` /
`memory_remember`:

| Want | Tool |
|---|---|
| Atomic how-to | `memory_skill_set` |
| Composed flow (`tool_recipe.skills`) | `memory_playbook_set` |
| Assignable task | `work_*` (comments for progress) |
| Board / project | `project_*` |
| Large local file upload | `file_upload_request` |
| Other shared files | `file_*` |
| Vision / OKRs | `memory_strategic_*` |

`close=true` distills the session into durable memory.

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

## Never

- `memory_forget` without an explicit user request
- `memory_session_open` after `memory_session_ensure` already returned a session_id
- `memory_remember` for skills, playbooks, tasks, or strategic vision
- Appending `[tool]` turns for teamshared MCP calls
- Probing `TEAMSHARED_*` env vars in the shell — call `health`
- Storing secrets, tokens, credentials, or login/OTP codes
