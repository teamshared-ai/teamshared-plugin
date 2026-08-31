# Changelog

## Unreleased

- **Rule 1.22.0:** copy the canonical memory rule from `xhad/teamshared`
  (live server `c98c737`, 1.22.0 after #110 / squash `b05b0f2`). Adds
  identity get-by-name routing (named playbook/skill/entity →
  `memory_playbook_get` / `memory_skill_get` / `memory_entity_view`, not
  recall; `soul` + `agent_memory`; `memory_agent_get`). No mcp.json,
  hooks, or marketplace submit changes.
- **Rule 1.19.0:** copy the canonical memory rule from `xhad/teamshared`
  (`7b524d5`, after #85). Adds Campaign CRM (Person / Organization /
  campaign-as-Project, `gtm-outreach`, `kind=outreach`). No mcp.json,
  hooks, or marketplace submit changes.
- **0.10.0 Cursor hooks:** two hooks only — `postToolUse` (failed)
  test/lint/shell → short episodic fact: command + error tail, secrets
  stripped) and `preCompact` (short session summary). Both append through
  `memory_session_ensure` + `context_commit` on the existing Connect
  session. No `tsk_` in `mcp.json`. Still no skills, agents, or commands.
- **cursor.directory copy:** install path is Add marketplace → this GitHub
  URL → `/add-plugin teamshared` → Settings → Tools & MCP → Connect. Cloud /
  Grok inherit. Listing paste block does not mention `mcp_auth` or `tsk_`.
- **Author:** `author.name` is **Loreum Labs Ltd** in `plugin.json` and
  `.cursor-plugin/plugin.json` (matches marketplace owner). `validate.sh`
  now asserts that name.
- **Setup story:** Cloud and Grok Bot inherit account-level Cursor Connect
  (Settings → Tools & MCP → teamshared → Connect). Do not treat `mcp_auth` as
  the primary path. Plugin `mcp.json` stays URL-only. Durable backup: one org
  `tsk_` on the MCP headers.
- **Rule 1.17.0:** same Connect inheritance copy; drop headless `mcp_auth` as
  the default auth path.

## 0.9.2 — 2026-08-18

- **Rule 1.15.0:** always-on protocol is a ~130-line fetch/store loop
  (`ensure(user=)` → keyword `memory_recall` → `context_commit` with `facts[]`
  and `close=true`). Dropped the duplicated tool encyclopedia / Quick chooser;
  routing stays on `memory_tools_catalog(need=...)`. Store table still names
  `file_upload_request` and `project_*`.

## 0.9.1 — 2026-08-15

- **Plugin logo:** `plugin.json` now uses the committed relative path
  `assets/logo.png` (512×512), matching `marketplace.json` and first-party
  Cursor plugins. The previous absolute URL (`https://teamshared.com/assets/logo.png`)
  500s, so Cursor had nothing to paint on tool turns.

## 0.9.0 — 2026-08-13

- **License / author:** Agentic Labs Ltd (copyright and plugin/marketplace author).
- **Slim plugin:** MCP tools + recall rule only. Removed skills, slash
  commands, the continual-learning stop hook, and the AGENTS.md updater agent.
  Cursor auto-discovers those folders, so they are gone from the bundle.

## 0.8.0 — 2026-08-13

- **Cursor plugin contract:** `mcp.json` registers `https://teamshared.com/mcp`
  (URL only; Cursor OAuth Connect, no bearer headers). Manifest `name` is
  kebab-case `teamshared`. `plugin.json` points `rules` at `teamshared.mdc` so
  the stale markdown twin is not also injected.
- **Commands:** `/teamshared-connect`, `/teamshared-recall`,
  `/teamshared-remember`, `/teamshared-think`, `/teamshared-probe`.
- **Onboarding:** install the plugin, then **Connect** — do not paste a URL or
  `tsk_*` token into `~/.cursor/mcp.json`.

## Unreleased

- **Own repo:** plugin lives at [`teamshared-ai/teamshared-plugin`](https://github.com/teamshared-ai/teamshared-plugin)
  (this repository; moved from `xhad/teamshared-cursor`). Add marketplace
  `https://github.com/teamshared-ai/teamshared-plugin`, then `/add-plugin teamshared`.
  The MCP server remains [`xhad/teamshared`](https://github.com/xhad/teamshared).
- **Folder marketplace:** `.cursor-plugin/marketplace.json` with `"source": "./"`
  so Cursor **Add plugins from folder** accepts this repo root.
- **Rule 1.14.0:** every-turn `memory_session_ensure(..., user=request)` (no
  separate append); `memory_tools_catalog(need=...)` is the conversation
  router; Quick chooser covers projects and ontology.
- **Landing + onboarding:** public `/` restyled; curl `install.sh` retired
  (`/install` → `/#connect`; `.sh` routes return 410). Cursor connects via
  MCP OAuth in Settings, not inline `mcp.json`.
- **MCP OAuth (Cursor):** Connect uses browser email/OTP
  (same as `/app`). `tsk_*` API keys remain for CI and other harnesses.
  Migration: `042_mcp_oauth.sql`. Rule **1.13.0**.
- **Rule 1.9.0:** private per-person **soul** memory (org + account scoped).
  Tiny compressed identity block returned on `memory_session_ensure` and
  injected by `context_prepare` / the LLM gateway. Tools: `memory_soul_get`,
  `memory_soul_set`. Preferences absorb into the soul. API keys must be minted
  from the console while signed in so `created_by` links to the human account.
  Migration: `034_soul.sql`.

## 0.5.0 — 2026-07-11

- **Server 0.5.0:** `memory_session_ensure` and `context_commit` for one-call
  session bootstrap and turn-end logging; self-healing `memory_session_append`;
  compression middleware fix; `work_list(mine=true)` for agents; FTS recall
  score normalization; graph neighbor dedup; tool param aliases; optional chat
  gateway; migration 033 (`memory:delete` for agent tokens); API key page
  install URL pinned to `teamshared.com`.
- **Rule 1.8.0:** session logging now uses `memory_session_ensure` and
  `context_commit`; `memory_session_append` self-heals expired sessions
  (`reopened: true`).
- **Rule 1.7.1:** align governance guidance with the active-write implementation;
  remove references to retired approvals and capture-consent console surfaces.

## Unreleased

## 0.7.0 — 2026-06-29

- **Rule 1.7.0:** retrieval playbook — durable default scope (exclude working),
  keyword-anchor-then-broaden queries, recall-before-think for entity/competitor
  questions, no `[tool]` appends for teamshared MCP calls, dense summary guidance
  on `memory_remember`.
- **Server:** `DEFAULT_RECALL_SCOPES` and `memory_think` default recall omit
  working; MCP tool descriptions and server instructions updated to match.
- **Installer:** Pi coding agent harness (`pi`) — project-local `./.mcp.json`.

## 0.6.0 — 2026-06-25

- **Rule 1.6.0:** removed the agent-execution surface — cloud/background agent
  runs (`agent_run_*`), the workflow engine (`workflow_*`), and agent assignees
  (`assignee_agent`). Work items assign to **people** only; API keys are
  org-bound and carry a free-text attribution label. Dropped all "Cloud Agents"
  references.

## 0.5.0 — 2026-06-19

- **Install consolidation:** all curl-install templates live under `install/` in
  this plugin bundle; repo-root `install_assets/` removed. Server resolves assets
  via `teamshared.clients.install_assets` (aliases: rule → `rules/`, protocol →
  `clients/protocol.md`).
- **Rule 1.5.0:** context compression via MCP (`context_prepare`, `context_normalize`,
  `context_compress`, `context_retrieve`); MCP middleware auto-normalizes teamshared
  tool responses; removed Cursor compression hooks (`beforeSubmitPrompt`, `postToolUse`).
- **Rule 1.5.0:** `memory_think` + recall `explain`; skills vs playbooks decision
  tree; tiered every-turn checklist; approval matrix; graph autolink + Postgres
  fallback; slim tool reference (delegate to `memory_tools_catalog`); fix
  `work_create` active-immediately guidance; bundled rituals documented as skills.

## 0.4.0 — 2026-06-08

- **Rule 1.3.0:** log every chat via `memory_session_*` (open on first turn,
  append user/assistant each round, close on done/pivot). State key:
  `conversation/active-session`.
- Removed the Cursor `conversation-capture-stop` transcript hook; NL capture is
  agent-driven through MCP instead of `POST /sessions/turns`.
- Continual-learning stop hook unchanged.
- **Rule 1.4.0:** every-turn checklist (ordered steps), mid-thread pivot handling,
  append-failure recovery, always resolve `repo=`, consent clarification, aligned
  starter procedures.

## 0.3.0 — 2026-06-01

- Rule + skill now point teammates to the **web console** (`/app`) for human
  actions: self-service OTP sign-in, multi-tenant orgs (own org on first login,
  create/switch, add members), the browsable memory wiki, and managing agents,
  API keys, approvals, and consent.
- Onboarding (README + MARKETPLACE) updated: mint a bearer token from the console
  **API Keys** page (self-service) in addition to `/get-token` / invite links.
- `health` tool description corrected to reflect the full component set.

## 0.2.0 — 2026-05-28

- Unified `teamshared-memory` and continual-learning into one **teamshared** plugin.
- Continual-learning hook stores cadence + transcript index on teamshared (`/state` API).
- MCP server key standardized to `teamshared`.
- Rule file renamed to `teamshared.mdc`.

## 0.1.0

- Initial `teamshared-memory` plugin: MCP wiring, recall-first rule, client snippets.
