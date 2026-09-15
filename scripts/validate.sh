#!/usr/bin/env bash
# Structural checks for the Cursor plugin (MCP + recall rule + chat-capture hooks),
# Claude Code marketplace package (MCP + 1.29 skill + official capture hooks),
# and native Codex marketplace package (OAuth MCP + 1.29 skill + official capture hooks).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL=0

check() {
  if [[ -e "$1" ]]; then
    echo "ok  $1"
  else
    echo "MISSING  $1"
    FAIL=1
  fi
}

absent() {
  if [[ -e "$1" ]]; then
    echo "UNEXPECTED  $1"
    FAIL=1
  else
    echo "ok  absent  $1"
  fi
}

echo "Validating teamshared plugin at $ROOT"
check "$ROOT/.cursor-plugin/plugin.json"
check "$ROOT/.cursor-plugin/marketplace.json"
check "$ROOT/plugin.json"
check "$ROOT/.mcp.json"
check "$ROOT/mcp.json"
check "$ROOT/rules/teamshared.mdc"
check "$ROOT/install/codex/mcp.toml"
check "$ROOT/install/codex/README.md"
check "$ROOT/docs/d1-org-binding.md"
check "$ROOT/scripts/org_binding.py"
check "$ROOT/scripts/test_org_binding.py"
check "$ROOT/scripts/d1_harness_probe.sh"
check "$ROOT/claude/hooks/org_binding.py"
check "$ROOT/plugins/teamshared/hooks/org_binding.py"
check "$ROOT/install/pi/mcp.json"
check "$ROOT/install/hermes/mcp.yaml"
check "$ROOT/install/hermes/capture.py"
check "$ROOT/clients/protocol.md"
check "$ROOT/assets/logo.png"
check "$ROOT/assets/logo.svg"
check "$ROOT/LICENSE"
check "$ROOT/README.md"
check "$ROOT/CHANGELOG.md"
check "$ROOT/hooks/hooks.json"
check "$ROOT/hooks/capture.py"
check "$ROOT/hooks/post_tool_use.py"
check "$ROOT/hooks/pre_compact.py"
check "$ROOT/hooks/session_start.py"
check "$ROOT/hooks/before_submit_prompt.py"
check "$ROOT/hooks/after_agent_response.py"
check "$ROOT/hooks/stop.py"
check "$ROOT/hooks/session_end.py"
check "$ROOT/.claude-plugin/marketplace.json"
check "$ROOT/claude/.claude-plugin/plugin.json"
check "$ROOT/claude/.mcp.json"
check "$ROOT/claude/README.md"
check "$ROOT/claude/skills/teamshared-memory/SKILL.md"
check "$ROOT/claude/skills/status/SKILL.md"
check "$ROOT/claude/hooks/hooks.json"
check "$ROOT/claude/hooks/capture.py"
check "$ROOT/claude/hooks/session_start.py"
check "$ROOT/claude/hooks/user_prompt_submit.py"
check "$ROOT/claude/hooks/stop.py"
check "$ROOT/claude/hooks/stop_failure.py"
check "$ROOT/claude/hooks/session_end.py"
check "$ROOT/claude/hooks/post_tool_use_failure.py"
check "$ROOT/claude/hooks/pre_compact.py"
check "$ROOT/claude/hooks/test_capture.py"
check "$ROOT/.agents/plugins/marketplace.json"
check "$ROOT/plugins/teamshared/.codex-plugin/plugin.json"
check "$ROOT/plugins/teamshared/assets/logo.png"
check "$ROOT/plugins/teamshared/assets/icon.png"
check "$ROOT/plugins/teamshared/.mcp.json"
check "$ROOT/plugins/teamshared/README.md"
check "$ROOT/plugins/teamshared/skills/teamshared-memory/SKILL.md"
check "$ROOT/plugins/teamshared/skills/teamshared-memory/agents/openai.yaml"
check "$ROOT/plugins/teamshared/skills/status/SKILL.md"
check "$ROOT/plugins/teamshared/hooks/hooks.json"
check "$ROOT/plugins/teamshared/hooks/capture.py"
check "$ROOT/plugins/teamshared/hooks/session_start.py"
check "$ROOT/plugins/teamshared/hooks/user_prompt_submit.py"
check "$ROOT/plugins/teamshared/hooks/stop.py"
check "$ROOT/plugins/teamshared/hooks/session_end.py"
check "$ROOT/plugins/teamshared/hooks/post_tool_use.py"
check "$ROOT/plugins/teamshared/hooks/pre_compact.py"
check "$ROOT/plugins/teamshared/hooks/test_capture.py"
absent "$ROOT/plugins/teamshared/hooks/stop_failure.py"
absent "$ROOT/plugins/teamshared/hooks/post_tool_use_failure.py"
absent "$ROOT/skills"
absent "$ROOT/agents"
absent "$ROOT/commands"
absent "$ROOT/claude/agents"
absent "$ROOT/claude/commands"

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT/.cursor-plugin/plugin.json" "$ROOT/.cursor-plugin/marketplace.json" "$ROOT/mcp.json" "$ROOT/plugin.json" "$ROOT/.mcp.json" "$ROOT/hooks/hooks.json" "$ROOT/.claude-plugin/marketplace.json" "$ROOT/claude/.claude-plugin/plugin.json" "$ROOT/claude/.mcp.json" "$ROOT/claude/hooks/hooks.json" "$ROOT/claude/skills/teamshared-memory/SKILL.md" "$ROOT/claude/skills/status/SKILL.md"
import json, re, sys

kebab = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
PLUGIN_MCP_URL = "https://teamshared.com/mcp"
REPO_MCP_URL_RE = re.compile(
    r"^https://teamshared\.com(?:/o/[a-z0-9][a-z0-9-]{0,62})?/mcp$"
)


def require_plugin_mcp_url(url, where):
    if url != PLUGIN_MCP_URL:
        print(f"FAIL  {where} plugin default must stay {PLUGIN_MCP_URL}, got {url!r}")
        sys.exit(1)


def require_repo_mcp_url(url, where):
    if not isinstance(url, str) or not REPO_MCP_URL_RE.fullmatch(url):
        print(
            f"FAIL  {where} must be {PLUGIN_MCP_URL} or "
            f"https://teamshared.com/o/{{slug}}/mcp, got {url!r}"
        )
        sys.exit(1)


(
    plugin_path,
    market_path,
    mcp_path,
    open_plugin_path,
    open_mcp_path,
    hooks_path,
    claude_market_path,
    claude_plugin_path,
    claude_mcp_path,
    claude_hooks_path,
    claude_skill_path,
    claude_status_path,
) = sys.argv[1:]

with open(plugin_path) as f:
    plugin = json.load(f)
print(f"ok  JSON  {plugin_path}")

name = plugin.get("name", "")
if not kebab.match(name):
    print(f"FAIL  plugin.json name {name!r} must be lowercase kebab-case")
    sys.exit(1)
print(f"ok  name  {name}")

if plugin.get("homepage") != "https://teamshared.com":
    print(f"FAIL  plugin.json homepage, got {plugin.get('homepage')!r}")
    sys.exit(1)
if plugin.get("repository") != "https://github.com/teamshared-ai/teamshared-plugin":
    print(f"FAIL  plugin.json repository, got {plugin.get('repository')!r}")
    sys.exit(1)

if plugin.get("mcpServers") != "./mcp.json":
    print(f"FAIL  plugin.json mcpServers must be './mcp.json', got {plugin.get('mcpServers')!r}")
    sys.exit(1)
print("ok  mcpServers  ./mcp.json")

if plugin.get("rules") != "./rules/teamshared.mdc":
    print(f"FAIL  plugin.json rules must be './rules/teamshared.mdc', got {plugin.get('rules')!r}")
    sys.exit(1)
print("ok  rules  ./rules/teamshared.mdc")

if plugin.get("logo") != "assets/logo.png":
    print(f"FAIL  plugin.json logo must be 'assets/logo.png', got {plugin.get('logo')!r}")
    sys.exit(1)
print("ok  logo  assets/logo.png")

if plugin.get("hooks") != "./hooks/hooks.json":
    print(f"FAIL  plugin.json hooks must be './hooks/hooks.json', got {plugin.get('hooks')!r}")
    sys.exit(1)
print("ok  hooks  ./hooks/hooks.json")

for key in ("skills", "agents", "commands"):
    if key in plugin:
        print(f"FAIL  plugin.json must not declare {key}")
        sys.exit(1)
print("ok  no skills/agents/commands in manifest")

with open(market_path) as f:
    market = json.load(f)
print(f"ok  JSON  {market_path}")
names = [p.get("name") for p in market.get("plugins", [])]
if names != ["teamshared"]:
    print(f"FAIL  marketplace.json plugins must be [teamshared], got {names}")
    sys.exit(1)
if market["plugins"][0].get("source") != "./":
    print(
        "FAIL  marketplace.json source must be './', "
        f"got {market['plugins'][0].get('source')!r}"
    )
    sys.exit(1)
if market["plugins"][0].get("logo") != "assets/logo.png":
    print(
        "FAIL  marketplace.json logo must be 'assets/logo.png', "
        f"got {market['plugins'][0].get('logo')!r}"
    )
    sys.exit(1)
print("ok  marketplace  source ./")

with open(mcp_path) as f:
    mcp = json.load(f)
print(f"ok  JSON  {mcp_path}")
server = (mcp.get("mcpServers") or {}).get("teamshared") or {}
require_plugin_mcp_url(server.get("url"), "mcp.json teamshared.url")
if server.get("headers"):
    print("FAIL  mcp.json must not include headers (Cursor uses OAuth Connect)")
    sys.exit(1)
if "tsk_" in json.dumps(mcp):
    print("FAIL  mcp.json must not contain a tsk_ key")
    sys.exit(1)
if server.get("type") != "http":
    print(f"FAIL  mcp.json teamshared.type must stay 'http' for Cursor, got {server.get('type')!r}")
    sys.exit(1)
print("ok  mcp.json  url-only OAuth")

OPEN_PLUGIN_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
}
with open(open_plugin_path) as f:
    open_plugin = json.load(f)
print(f"ok  JSON  {open_plugin_path}")
extra = set(open_plugin) - OPEN_PLUGIN_FIELDS
if extra:
    print(f"FAIL  root plugin.json extra fields {sorted(extra)}")
    sys.exit(1)
if open_plugin.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
    print(f"FAIL  root plugin.json $schema, got {open_plugin.get('$schema')!r}")
    sys.exit(1)
if not kebab.match(open_plugin.get("name", "")):
    print(f"FAIL  root plugin.json name {open_plugin.get('name')!r} must be lowercase kebab-case")
    sys.exit(1)
for key in ("version", "description", "homepage", "repository", "license", "keywords"):
    if open_plugin.get(key) != plugin.get(key):
        print(f"FAIL  root plugin.json {key} must match .cursor-plugin/plugin.json")
        sys.exit(1)
if open_plugin.get("author") != plugin.get("author"):
    print("FAIL  root plugin.json author must match .cursor-plugin/plugin.json")
    sys.exit(1)
author_name = (plugin.get("author") or {}).get("name")
if author_name != "Loreum Labs Ltd":
    print(f"FAIL  author.name must be 'Loreum Labs Ltd', got {author_name!r}")
    sys.exit(1)
print("ok  author  Loreum Labs Ltd")
if (market.get("owner") or {}).get("name") != author_name:
    print(
        "FAIL  marketplace.json owner.name must match author.name, "
        f"got {(market.get('owner') or {}).get('name')!r}"
    )
    sys.exit(1)
print("ok  marketplace owner  Loreum Labs Ltd")
print("ok  root plugin.json  Agent Plugins 1.0.0")

with open(open_mcp_path) as f:
    open_mcp = json.load(f)
print(f"ok  JSON  {open_mcp_path}")
if set(open_mcp) != {"$schema", "mcpServers"}:
    print(f"FAIL  .mcp.json top-level keys must be $schema + mcpServers, got {sorted(open_mcp)}")
    sys.exit(1)
if open_mcp.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json":
    print(f"FAIL  .mcp.json $schema, got {open_mcp.get('$schema')!r}")
    sys.exit(1)
open_server = (open_mcp.get("mcpServers") or {}).get("teamshared") or {}
if open_server.get("type") != "streamable-http":
    print(f"FAIL  .mcp.json teamshared.type must be 'streamable-http', got {open_server.get('type')!r}")
    sys.exit(1)
require_plugin_mcp_url(open_server.get("url"), ".mcp.json teamshared.url")
if open_server.get("headers"):
    print("FAIL  .mcp.json must not include headers")
    sys.exit(1)
if "tsk_" in json.dumps(open_mcp):
    print("FAIL  .mcp.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  .mcp.json  streamable-http")

with open(hooks_path) as f:
    hooks = json.load(f)
print(f"ok  JSON  {hooks_path}")
events = hooks.get("hooks") or {}
required = {
    "sessionStart",
    "beforeSubmitPrompt",
    "afterAgentResponse",
    "stop",
    "sessionEnd",
    "postToolUse",
    "preCompact",
}
if set(events) != required:
    print(f"FAIL  hooks.json must register {sorted(required)}, got {sorted(events)}")
    sys.exit(1)
for name in required:
    if not events.get(name) or not events[name][0].get("command"):
        print(f"FAIL  hooks.json {name} must have a command")
        sys.exit(1)
matcher = events["postToolUse"][0].get("matcher")
if matcher != "Shell":
    print(f"FAIL  postToolUse matcher must be Shell, got {matcher!r}")
    sys.exit(1)
if "tsk_" in json.dumps(hooks):
    print("FAIL  hooks.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  hooks  chat capture + postToolUse + preCompact")

with open(claude_market_path) as f:
    claude_market = json.load(f)
print(f"ok  JSON  {claude_market_path}")
if claude_market.get("name") != "teamshared":
    print(f"FAIL  Claude marketplace name must be 'teamshared', got {claude_market.get('name')!r}")
    sys.exit(1)
if (claude_market.get("owner") or {}).get("name") != author_name:
    print(
        "FAIL  Claude marketplace owner.name must match author.name, "
        f"got {(claude_market.get('owner') or {}).get('name')!r}"
    )
    sys.exit(1)
claude_plugins = claude_market.get("plugins") or []
if [p.get("name") for p in claude_plugins] != ["teamshared"]:
    print(
        "FAIL  Claude marketplace plugins must be [teamshared], "
        f"got {[p.get('name') for p in claude_plugins]}"
    )
    sys.exit(1)
if claude_plugins[0].get("source") != "./claude":
    print(
        "FAIL  Claude marketplace source must be './claude', "
        f"got {claude_plugins[0].get('source')!r}"
    )
    sys.exit(1)
print("ok  Claude marketplace  teamshared@teamshared source ./claude")

with open(claude_plugin_path) as f:
    claude_plugin = json.load(f)
print(f"ok  JSON  {claude_plugin_path}")
if claude_plugin.get("name") != "teamshared":
    print(f"FAIL  Claude plugin.json name must be 'teamshared', got {claude_plugin.get('name')!r}")
    sys.exit(1)
if claude_plugin.get("mcpServers") != "./.mcp.json":
    print(
        "FAIL  Claude plugin.json mcpServers must be './.mcp.json', "
        f"got {claude_plugin.get('mcpServers')!r}"
    )
    sys.exit(1)
if claude_plugin.get("hooks") != "./hooks/hooks.json":
    print(
        "FAIL  Claude plugin.json hooks must be './hooks/hooks.json', "
        f"got {claude_plugin.get('hooks')!r}"
    )
    sys.exit(1)
if (claude_plugin.get("author") or {}).get("name") != author_name:
    print("FAIL  Claude plugin.json author.name must match Cursor author.name")
    sys.exit(1)
print("ok  Claude plugin.json  MCP + hooks")

with open(claude_mcp_path) as f:
    claude_mcp = json.load(f)
print(f"ok  JSON  {claude_mcp_path}")
claude_server = (claude_mcp.get("mcpServers") or {}).get("teamshared") or {}
require_plugin_mcp_url(claude_server.get("url"), "Claude .mcp.json url")
if claude_server.get("type") not in ("http", "streamable-http"):
    print(
        "FAIL  Claude .mcp.json type must be http (or streamable-http), "
        f"got {claude_server.get('type')!r}"
    )
    sys.exit(1)
if claude_server.get("headers"):
    print(
        "FAIL  Claude .mcp.json must not include headers "
        "(Claude Code's native /mcp OAuth flow handles auth), "
        f"got {claude_server.get('headers')!r}"
    )
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", json.dumps(claude_mcp)):
    print("FAIL  Claude .mcp.json must not contain a real tsk_ secret")
    sys.exit(1)
print("ok  Claude .mcp.json  remote MCP + OAuth (no headers)")

with open(claude_hooks_path) as f:
    claude_hooks = json.load(f)
print(f"ok  JSON  {claude_hooks_path}")
claude_events = claude_hooks.get("hooks") or {}
claude_required = {
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "SessionEnd",
    "PostToolUseFailure",
    "PreCompact",
}
if set(claude_events) != claude_required:
    print(
        f"FAIL  Claude hooks.json must register {sorted(claude_required)}, "
        f"got {sorted(claude_events)}"
    )
    sys.exit(1)
for name in claude_required:
    group = claude_events.get(name) or []
    handlers = (group[0].get("hooks") or []) if group else []
    command = handlers[0].get("command") if handlers else None
    args = handlers[0].get("args") if handlers else None
    if command != "python3" or not args:
        print(f"FAIL  Claude hooks.json {name} must be python3 + args")
        sys.exit(1)
    if "${CLAUDE_PLUGIN_ROOT}/hooks/" not in args[0]:
        print(f"FAIL  Claude hooks.json {name} args must use CLAUDE_PLUGIN_ROOT")
        sys.exit(1)
matcher = claude_events["PostToolUseFailure"][0].get("matcher")
if matcher != "Bash|PowerShell":
    print(f"FAIL  PostToolUseFailure matcher must be Bash|PowerShell, got {matcher!r}")
    sys.exit(1)
if "tsk_" in json.dumps(claude_hooks):
    print("FAIL  Claude hooks.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  Claude hooks  official events + capture")

from pathlib import Path
skill = Path(claude_skill_path).read_text()
status = Path(claude_status_path).read_text()
for needle in (
    "1.29.0",
    "work_id",
    "playbook_slug",
    "soul",
    "agent_memory",
    "memory_playbook_get",
    "memory_skill_get",
    "memory_entity_view",
    "memory_changes_since",
    "degraded",
    "installed_rule_version",
    "~/.claude/rules/teamshared.md",
    "TEAMSHARED_TOKEN",
    "SessionStart",
    "UserPromptSubmit",
):
    if needle not in skill:
        print(f"FAIL  Claude teamshared-memory skill must mention {needle!r}")
        sys.exit(1)
if "[TODO:" in skill or "## Every turn" not in skill:
    print("FAIL  Claude skill must be complete and include the every-turn workflow")
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", skill) or re.search(r"tsk_[A-Za-z0-9]", status):
    print("FAIL  Claude skills must not contain a tsk_ secret")
    sys.exit(1)
if "name: status" not in status or "health" not in status:
    print("FAIL  Claude /teamshared:status skill is incomplete")
    sys.exit(1)
if "1.29.0" not in status:
    print("FAIL  Claude status skill must mention protocol 1.29.0")
    sys.exit(1)
print("ok  Claude teamshared-memory 1.29.0 + status skill")

require_repo_mcp_url(PLUGIN_MCP_URL, "plugin default shape")
require_repo_mcp_url("https://teamshared.com/o/sapien/mcp", "bound org shape")
print("ok  MCP url shapes  plugin /mcp; repo /mcp or /o/{slug}/mcp")
PY
  python3 "$ROOT/hooks/test_capture.py" -q
  python3 "$ROOT/claude/hooks/test_capture.py" -q
  python3 "$ROOT/plugins/teamshared/hooks/test_capture.py" -q
  python3 "$ROOT/scripts/test_org_binding.py" -q
  if ! cmp -s "$ROOT/scripts/org_binding.py" "$ROOT/claude/hooks/org_binding.py"; then
    echo "FAIL  claude/hooks/org_binding.py must match scripts/org_binding.py"
    FAIL=1
  else
    echo "ok  claude/hooks/org_binding.py  matches D1 resolver"
  fi
  if ! cmp -s "$ROOT/scripts/org_binding.py" "$ROOT/plugins/teamshared/hooks/org_binding.py"; then
    echo "FAIL  plugins/teamshared/hooks/org_binding.py must match scripts/org_binding.py"
    FAIL=1
  else
    echo "ok  plugins/teamshared/hooks/org_binding.py  matches D1 resolver"
  fi
