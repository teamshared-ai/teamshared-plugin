# Decision: repo org binding without a duplicate TeamShared server

**Status:** proposed · D1 · 2026-09-15
**Issue:** [teamshared-plugin#36](https://github.com/teamshared-ai/teamshared-plugin/issues/36)
**Plan item:** D1 · Milestone M1 · [plan v6](https://teamshared.com/app/files/f78638c3-80db-4d8e-88e0-ba622373be61)
**Master:** [personal hub + personal and company orgs](https://teamshared.com/app/work/130df8db-4c2a-47e9-9d4f-c21466295ed5)
**Attached to master:** [Decision: repo org binding (D1)](https://teamshared.com/app/files/a1d7703d-f571-49e8-a47f-6546d830f0df)
**Depends:** C1 live on teamshared.com (`/o/{slug}/mcp`, [teamshared#417](https://github.com/teamshared-ai/teamshared/issues/417) / [PR #439](https://github.com/teamshared-ai/teamshared/pull/439))
**Out of scope here:** D2 hook resolver wiring, D3 `org bind` / `unbind` CLI

This is a spike. It chooses the binding format and records how each harness
can pick it up without loading a second TeamShared MCP server. It does not
ship bind/unbind or change capture hooks.

---

## 1. Decision

**Canonical binding is a committed repo file, not a per-harness MCP entry.**

```
.teamshared/org
```

Preferred contents (JSON, versioned):

```json
{
  "v": 1,
  "slug": "sapien"
}
```

Also accepted, so a human can write the file without JSON:

```
sapien
```

or

```
# TeamShared org binding
slug=sapien
```

**Derived URL** (never stored; never a secret):

```
https://teamshared.com/o/{slug}/mcp
```

**Unbound** (file missing, empty, or unreadable): `https://teamshared.com/mcp`.

Slug rules: trim, case-fold to lowercase, then
`^[a-z0-9][a-z0-9-]{0,62}$`. D3 bind must refuse an invalid slug. D2 hooks
fail open to `/mcp` (same as today's capture).

The executable contract lives in [`scripts/org_binding.py`](../scripts/org_binding.py).
D2 and D3 must import or copy that resolver. Do not invent a second format.

`teamshared org bind <slug>` (D3) writes only this file. It does **not** write
`.cursor/mcp.json`, a project `.mcp.json` `teamshared` server, or
`.codex/config.toml` `[mcp_servers.teamshared]`. Those files add a second
TeamShared server next to the plugin / Connect server.

---

## 2. Why not per-harness MCP config

The plan asked whether each harness can take a repo-level org URL from its
native config. The answer is: **the native config can express an org URL, but
it cannot replace the plugin/Connect server.** The result is two TeamShared
tool sets.

| Layer | What it registers | Same name `teamshared`? |
| --- | --- | --- |
| Cursor marketplace plugin `mcp.json` | Plugin-scoped HTTP server at `/mcp` + Connect | Separate namespace from project/user |
| Cursor `~/.cursor/mcp.json` | User-scoped server | Official help: project wins on name. Forum + `mcpService.knownServerIds`: `user-*` and `project-*` still both appear |
| Cursor `.cursor/mcp.json` | Project-scoped server | Does not disable the plugin server |
| Cursor Cloud / Grok Bot | Account Connect and/or Agents dashboard MCP | Official Cloud MCP source is the dashboard, not the checkout |
| Claude Code plugin `.mcp.json` | `plugin:teamshared:teamshared` | Dedup only when **command or URL is identical** |
| Claude Code project `.mcp.json` | Manual `teamshared` | Org URL ≠ `/mcp` → both load. Suppression of the plugin copy is shown in `/plugin`, not as an override |
| Codex plugin `.mcp.json` | Plugin HTTP server at `/mcp` | User/project `config.toml` can set `enabled`, not the URL |
| Codex `.codex/config.toml` | `[mcp_servers.teamshared]` | A second server unless the plugin one is disabled |

C2 (OAuth discovery for org URLs) is **not** live. A 401 on `/o/{slug}/mcp`
advertises the same `resource_metadata` as `/mcp`
(`https://teamshared.com/.well-known/oauth-protected-resource`, whose
`resource` is `https://teamshared.com/mcp`).
`/.well-known/oauth-protected-resource/o/{slug}/mcp` is 404. Pointing a
**new** Connect at the org path is not a supported product path until C2.

C1 **does** accept today's `/mcp` tokens on org paths (membership rebind).
Hooks and a later plugin shim can call `/o/{slug}/mcp` with the existing
Connect / OAuth token. That is the no-duplicate path.

---

## 3. How each harness picks up the bind

### Cursor Desktop

**Pickup:** one plugin HTTP server at `https://teamshared.com/mcp` (user
Connect). D2 reads `.teamshared/org` from the workspace and sends capture
to the derived org URL with that same Connect token.

**Do not write** `.cursor/mcp.json` with a second `teamshared` (or
`teamshared-sapien`) entry. Cursor loads plugin, user, and project sources
side by side. Official docs only say project overrides **user**
`~/.cursor/mcp.json` on the same name. They do not say a project file
replaces a marketplace plugin. Community reports show duplicate
`user-<name>` and `project-<name>` ids even for that narrower case.

`${env:NAME}` interpolation exists for Cursor `url` fields, but HTTP
servers have no `envFile`, so a per-repo env cannot retarget the installed
plugin `mcp.json` without launching the app from a custom environment.

**After C2 (follow-up, not D3):** either interpolate the **plugin**
`mcp.json` URL from a workspace-readable value, or ship a stdio shim in
the plugin that reads `.teamshared/org` and forwards with the Connect
token. Still one server.

**Proof in this VM:** blocked. No Cursor Desktop GUI. How to verify on a
laptop: Settings → Tools & MCP with the plugin connected, then add
`.cursor/mcp.json` pointing at `https://teamshared.com/o/{slug}/mcp`.
Expect two TeamShared servers. Remove the project file; expect one.

### Cursor Cloud / Grok Bot

**Pickup:** inherited account-level Connect to `/mcp`. This Cloud / Grok
run has a live `Teamshared` tool namespace and **no**
`/workspace/.cursor/mcp.json` and **no** `~/.cursor/mcp.json`. Official
Cloud MCP docs list the Agents MCP dropdown and Team Integrations & MCP,
not repo `.cursor/mcp.json`.

D2 hooks that run inside the checkout still read `.teamshared/org` and can
POST to the org URL with the inherited token (C1).

**Do not** treat repo `.cursor/mcp.json` as the Cloud bind path. It is not
the documented Cloud MCP source. If Cloud later started loading it, it
would sit next to inherited Connect — a duplicate.

Per-repo agent **tools** stay on the inherited `/mcp` org until a Cloud
environment MCP URL or a plugin shim exists. That is an honest Cloud gap,
not something D3 should paper over with a second server. D5 covers unbound
`/mcp` mis-writes.

**Proof in this VM:** this run. See
[`docs/d1-evidence/cursor-cloud-grok.md`](d1-evidence/cursor-cloud-grok.md).

### Claude Code

**Pickup:** one plugin server, `plugin:teamshared:teamshared`, from
`claude/.mcp.json` (`https://teamshared.com/mcp` + native `/mcp` OAuth).

Claude Code **does** expand `${VAR}` and `${VAR:-default}` in plugin
`url` fields, and project `.claude/settings.json` can set an `env` block
(after workspace trust). That is the clean retarget **after C2**:

```json
"url": "${TEAMSHARED_MCP_URL:-https://teamshared.com/mcp}"
```

plus a trusted project `env.TEAMSHARED_MCP_URL` derived from
`.teamshared/org`. Same plugin server, new URL, same OAuth account.

**Until C2:** do not change the plugin URL and do not add a project
`.mcp.json` `teamshared` entry. A different URL is **not** deduped
(changelog 2.1.71: skip plugin server only when command/URL match the
manual server). Result: `plugin:teamshared:teamshared` **and** project
`teamshared`. D2 hooks read `.teamshared/org`.

**Proof in this VM:** blocked. No `claude` binary. How to verify: install
`teamshared@teamshared`, add a project `.mcp.json` with
`https://teamshared.com/o/{slug}/mcp`, run `claude mcp list`. Expect both
servers. Confirm `/plugin` shows the plugin copy as suppressed only when
the URLs match.

### Codex

**Pickup:** native plugin `.mcp.json` stays `https://teamshared.com/mcp`.
Official Codex docs: plugin servers are launched from the plugin;
`config.toml` may set
`plugins."teamshared@teamshared".mcp_servers.teamshared.enabled` and tool
policy, **not** the transport URL.

Project `.codex/config.toml` `[mcp_servers.teamshared]` (trusted projects
only; user `~/.codex/config.toml` wins on conflicts) is a second server.
The documented way to keep one live server is disable the plugin MCP and
add a project table — that is a new OAuth or `tsk_` Connect, not "one
Connect."

**Until C2:** leave the plugin server on `/mcp`. D2 hooks read
`.teamshared/org`. The manual `install/codex/` `tsk_` path may use project
`config.toml` **or** the plugin, never both (already documented).

**Proof in this VM:** blocked. No `codex` binary. How to verify: with the
marketplace plugin installed, merge an org URL into `.codex/config.toml`
and run `codex mcp list`. Expect plugin + project servers unless the
plugin server is `enabled = false`.

---

## 4. Contract for D2 and D3

| Caller | Behavior |
| --- | --- |
| D2 hooks (`hooks/capture.py`, Claude/Codex capture) | `resolve_org_binding(repo_root)` → use `url`. Missing/invalid → `/mcp`. No second MCP server. |
| D3 `org bind <slug>` | Membership check (C1), then write `.teamshared/org`. Idempotent. |
| D3 `org status` | Print slug, derived URL, `bound`, and "harnesses: plugin/Connect still `/mcp`; hooks follow this file." |
| D3 `org unbind` | Remove `.teamshared/org`. |
| D4 docs | One Connect. Bind the repo file. Never "add a second TeamShared server." |
| D5 | Unbound `/mcp` warning for multi-org accounts, as planned. |

Resolver details: [`scripts/org_binding.py`](../scripts/org_binding.py).
Tests: [`scripts/test_org_binding.py`](../scripts/test_org_binding.py).

---

## 5. After C2 (not this PR)

C2 must publish protected-resource metadata for `/o/{slug}/mcp` and accept
the `/mcp` token audience on org resources (already partly true at the
middleware layer). Then:

1. Claude Code: plugin `url` interpolation + D3 may also write
   `.claude/settings.json` `env.TEAMSHARED_MCP_URL` so the **plugin**
   server retargets.
2. Cursor Desktop / Cloud: plugin shim or first-party URL override so the
   **existing** Connect is reused on the org path. Still no project
   `mcp.json` twin.
3. Codex: only if plugin `.mcp.json` gains interpolation; otherwise keep
   disable-plugin + project table as a documented escape hatch for `tsk_`
   bots, not the default.

Revisit only if a harness ships a real "replace plugin URL" API.

---

## 6. Rejected alternatives

| Alternative | Why not |
| --- | --- |
| `.cursor/mcp.json` / project `.mcp.json` / `.codex/config.toml` as source of truth | Second TeamShared server. This plugin repo already gitignores `.cursor/mcp.json` and `.codex/`. |
| `${workspaceFolderBasename}` as the slug | Folder name is not the org slug. |
| Env-only `TEAMSHARED_ORG` | Not per-repo, not shared with teammates, Cloud/Grok inherit Connect not a shell env. |
| Disable plugin MCP and use only project config | Breaks one-Connect and Cloud inheritance. |
| Wait to bind until every harness can retarget tools | Hooks can follow the file today (C1 token reuse). D5 covers leftover `/mcp` tool writes. |

---

## 7. Evidence index

| Harness | Result | Artifact |
| --- | --- | --- |
| C1 (prerequisite) | Live. `/mcp` and `/o/sapien/mcp` both 401 `missing_bearer_token` with the same `www-authenticate` metadata URL. Path-specific PRM is 404 (C2). | [`d1-evidence/c1-org-mcp.log`](d1-evidence/c1-org-mcp.log) |
| Cursor Cloud / Grok Bot | Exercised. Inherited Connect; no repo/user `mcp.json`. | [`d1-evidence/cursor-cloud-grok.md`](d1-evidence/cursor-cloud-grok.md) |
| Cursor Desktop | Blocked in this VM (no Desktop). Verify steps in §3. | [`d1-evidence/cursor-desktop.md`](d1-evidence/cursor-desktop.md) |
| Claude Code | Blocked in this VM (no `claude`). Verify steps in §3. | [`d1-evidence/claude-code.md`](d1-evidence/claude-code.md) |
| Codex | Blocked in this VM (no `codex`). Verify steps in §3. | [`d1-evidence/codex.md`](d1-evidence/codex.md) |

Re-run the live C1 probe:

```bash
./scripts/d1_harness_probe.sh
```
