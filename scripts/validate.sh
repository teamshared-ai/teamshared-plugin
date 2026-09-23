#!/usr/bin/env bash
# Structural checks for the Cursor plugin (MCP + recall rule + chat-capture hooks),
# Claude Code marketplace package (MCP + 1.31 skill + official capture hooks),
# and native Codex marketplace package (OAuth MCP + 1.31 skill + official capture hooks).
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
check "$ROOT/AGENTS.md"
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
    "1.31.0",
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
    "org_list",
    "org_context_get",
    "org_bind",
    "org_unbind",
    "scope=conversation",
    "optional fallback",
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
if "1.31.0" not in status:
    print("FAIL  Claude status skill must mention protocol 1.31.0")
    sys.exit(1)
print("ok  Claude teamshared-memory 1.31.0 + status skill")

require_repo_mcp_url(PLUGIN_MCP_URL, "plugin default shape")
require_repo_mcp_url("https://teamshared.com/o/sapien/mcp", "bound org shape")
print("ok  MCP url shapes  plugin /mcp; repo /mcp or /o/{slug}/mcp")
PY
  python3 "$ROOT/hooks/test_capture.py" -q
  python3 "$ROOT/claude/hooks/test_capture.py" -q
  python3 "$ROOT/plugins/teamshared/hooks/test_capture.py" -q
  python3 "$ROOT/scripts/test_org_binding.py" -q
  python3 "$ROOT/scripts/test_org_bind_guidance.py" -q
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
  python3 - <<'PY' "$ROOT/.agents/plugins/marketplace.json" "$ROOT/plugins/teamshared/.codex-plugin/plugin.json" "$ROOT/plugins/teamshared/.mcp.json" "$ROOT/plugins/teamshared/skills/teamshared-memory/SKILL.md" "$ROOT/plugins/teamshared/skills/status/SKILL.md" "$ROOT/plugins/teamshared/hooks/hooks.json" "$ROOT/plugins/teamshared/skills/teamshared-memory/agents/openai.yaml"
import json, re, sys
from pathlib import Path

(
    market_path,
    plugin_path,
    mcp_path,
    skill_path,
    status_path,
    hooks_path,
    openai_yaml_path,
) = map(Path, sys.argv[1:])

with market_path.open() as f:
    market = json.load(f)
print(f"ok  JSON  {market_path}")
if market.get("name") != "teamshared":
    print(f"FAIL  Codex marketplace name must be 'teamshared', got {market.get('name')!r}")
    sys.exit(1)
if (market.get("interface") or {}).get("displayName") != "TeamShared":
    print("FAIL  Codex marketplace displayName must be 'TeamShared'")
    sys.exit(1)
entries = market.get("plugins") or []
if [entry.get("name") for entry in entries] != ["teamshared"]:
    print("FAIL  Codex marketplace must contain only the teamshared plugin")
    sys.exit(1)
entry = entries[0]
if (entry.get("source") or {}) != {"source": "local", "path": "./plugins/teamshared"}:
    print(f"FAIL  Codex marketplace source, got {entry.get('source')!r}")
    sys.exit(1)
if entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
    print(f"FAIL  Codex marketplace policy, got {entry.get('policy')!r}")
    sys.exit(1)
if entry.get("category") != "Productivity":
    print(f"FAIL  Codex marketplace category, got {entry.get('category')!r}")
    sys.exit(1)
print("ok  Codex marketplace  teamshared@teamshared source ./plugins/teamshared")

with plugin_path.open() as f:
    plugin = json.load(f)
print(f"ok  JSON  {plugin_path}")
if plugin.get("name") != "teamshared":
    print(f"FAIL  Codex plugin name, got {plugin.get('name')!r}")
    sys.exit(1)
if not re.match(r"^\d+\.\d+\.\d+$", str(plugin.get("version") or "")):
    print(f"FAIL  Codex plugin version must be semver, got {plugin.get('version')!r}")
    sys.exit(1)
if (plugin.get("author") or {}).get("name") != "Loreum Labs Ltd":
    print("FAIL  Codex plugin author.name must be 'Loreum Labs Ltd'")
    sys.exit(1)
if plugin.get("skills") != "./skills/" or plugin.get("mcpServers") != "./.mcp.json":
    print("FAIL  Codex plugin must declare ./skills/ and ./.mcp.json")
    sys.exit(1)
if plugin.get("hooks") != "./hooks/hooks.json":
    print(
        "FAIL  Codex plugin.json hooks must be './hooks/hooks.json', "
        f"got {plugin.get('hooks')!r}"
    )
    sys.exit(1)
interface = plugin.get("interface") or {}
for field in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "defaultPrompt"):
    if field not in interface:
        print(f"FAIL  Codex plugin interface missing {field}")
        sys.exit(1)
if interface.get("composerIcon") != "./assets/icon.png":
    print(
        "FAIL  Codex plugin.json interface.composerIcon must be './assets/icon.png', "
        f"got {interface.get('composerIcon')!r}"
    )
    sys.exit(1)
if interface.get("logo") != "./assets/logo.png":
    print(
        "FAIL  Codex plugin.json interface.logo must be './assets/logo.png', "
        f"got {interface.get('logo')!r}"
    )
    sys.exit(1)
if interface.get("logoDark") != "./assets/logo.png":
    print(
        "FAIL  Codex plugin.json interface.logoDark must be './assets/logo.png', "
        f"got {interface.get('logoDark')!r}"
    )
    sys.exit(1)
prompts = interface.get("defaultPrompt") or []
if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
    print("FAIL  Codex defaultPrompt must be 1-3 starter strings")
    sys.exit(1)
for prompt in prompts:
    if not isinstance(prompt, str) or len(prompt) > 128:
        print(f"FAIL  Codex defaultPrompt entry exceeds 128 chars: {prompt!r}")
        sys.exit(1)
print("ok  Codex plugin.json  MCP + skill + official hooks")

with mcp_path.open() as f:
    mcp = json.load(f)
print(f"ok  JSON  {mcp_path}")
if set(mcp) != {"mcpServers"}:
    print(f"FAIL  Codex .mcp.json top-level keys, got {sorted(mcp)}")
    sys.exit(1)
server = (mcp.get("mcpServers") or {}).get("teamshared") or {}
if server != {"type": "streamable-http", "url": "https://teamshared.com/mcp"}:
    print(f"FAIL  Codex MCP config, got {server!r}")
    sys.exit(1)
if server.get("headers"):
    print("FAIL  Codex .mcp.json must not include headers (OAuth discovery)")
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", json.dumps(mcp)):
    print("FAIL  Codex .mcp.json must not contain a tsk_ secret")
    sys.exit(1)
print("ok  Codex .mcp.json  OAuth-discovered streamable HTTP")

with hooks_path.open() as f:
    hooks = json.load(f)
print(f"ok  JSON  {hooks_path}")
events = hooks.get("hooks") or {}
required = {
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "SessionEnd",
    "PostToolUse",
    "PreCompact",
}
if set(events) != required:
    print(f"FAIL  Codex hooks.json must register {sorted(required)}, got {sorted(events)}")
    sys.exit(1)
forbidden = {
    "StopFailure",
    "PostToolUseFailure",
    "sessionStart",
    "beforeSubmitPrompt",
    "afterAgentResponse",
    "postToolUse",
    "preCompact",
}
if set(events) & forbidden:
    print(f"FAIL  Codex hooks.json includes unsupported events {sorted(set(events) & forbidden)}")
    sys.exit(1)
for name in required:
    group = events.get(name) or []
    handlers = (group[0].get("hooks") or []) if group else []
    command = handlers[0].get("command") if handlers else None
    if not command or "python3" not in command or "${PLUGIN_ROOT}/hooks/" not in command:
        print(f"FAIL  Codex hooks.json {name} must be python3 ${{PLUGIN_ROOT}}/hooks/...")
        sys.exit(1)
matcher = events["PostToolUse"][0].get("matcher")
if matcher != "Bash":
    print(f"FAIL  Codex PostToolUse matcher must be Bash, got {matcher!r}")
    sys.exit(1)
session_end_timeout = (events["SessionEnd"][0].get("hooks") or [{}])[0].get("timeout")
if not isinstance(session_end_timeout, (int, float)) or session_end_timeout > 3:
    print(f"FAIL  Codex SessionEnd timeout must be <= 3s, got {session_end_timeout!r}")
    sys.exit(1)
if "tsk_" in json.dumps(hooks):
    print("FAIL  Codex hooks.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  Codex hooks  official events + capture")

skill = skill_path.read_text()
status = status_path.read_text()
openai_yaml = openai_yaml_path.read_text()
for needle in (
    "1.31.0",
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
    "~/.codex/AGENTS.md",
    "SessionStart",
    "UserPromptSubmit",
    "StopFailure",
    "PostToolUseFailure",
    "OAuth",
    "org_list",
    "org_context_get",
    "org_bind",
    "org_unbind",
    "scope=conversation",
    "optional fallback",
):
    if needle not in skill:
        print(f"FAIL  Codex teamshared-memory skill must mention {needle!r}")
        sys.exit(1)
if "[TODO:" in skill or "## Every turn" not in skill:
    print("FAIL  Codex skill must be complete and include the every-turn workflow")
    sys.exit(1)
if "even when the user does not name TeamShared" not in skill:
    print("FAIL  Codex skill description must trigger without the user naming TeamShared")
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", skill) or re.search(r"tsk_[A-Za-z0-9]", status):
    print("FAIL  Codex skills must not contain a tsk_ secret")
    sys.exit(1)
if "name: status" not in status or "health" not in status:
    print("FAIL  Codex $status skill is incomplete")
    sys.exit(1)
if "1.31.0" not in status:
    print("FAIL  Codex status skill must mention protocol 1.31.0")
    sys.exit(1)
if "allow_implicit_invocation: true" not in openai_yaml:
    print("FAIL  Codex openai.yaml must allow implicit skill invocation")
    sys.exit(1)
print("ok  Codex teamshared-memory 1.31.0 + status skill")
PY
else
  echo "skip JSON parse (python3 not found)"
fi

for doc in "$ROOT/README.md" "$ROOT/MARKETPLACE.md"; do
  if ! grep -q "postToolUse" "$doc" || ! grep -q "preCompact" "$doc"; then
    echo "FAIL  $doc must mention postToolUse and preCompact"
    FAIL=1
  elif ! grep -Eqi "no skills|still no skills" "$doc"; then
    echo "FAIL  $doc must say the plugin still has no skills/agents/commands"
    FAIL=1
  else
    echo "ok  docs  $(basename "$doc") hooks + no skills"
  fi
done

if ! grep -q "codex mcp add" "$ROOT/README.md" \
  || ! grep -q "TEAMSHARED_TOKEN" "$ROOT/README.md" \
  || ! grep -q "/app/keys" "$ROOT/README.md" \
  || ! grep -q "install/codex/README.md" "$ROOT/README.md"; then
  echo "FAIL  README.md must document Codex mcp add, TEAMSHARED_TOKEN, /app/keys, and install/codex/README.md"
  FAIL=1
else
  echo "ok  docs  README Codex section"
fi

if ! grep -q "codex plugin marketplace add teamshared-ai/teamshared-plugin" "$ROOT/README.md" \
  || ! grep -q "codex plugin add teamshared@teamshared" "$ROOT/README.md" \
  || ! grep -q "MCP OAuth" "$ROOT/README.md" \
  || ! grep -q "codex plugin marketplace add teamshared-ai/teamshared-plugin" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "codex plugin add teamshared@teamshared" "$ROOT/plugins/teamshared/README.md"; then
  echo "FAIL  README files must document the native Codex marketplace, install command, and OAuth"
  FAIL=1
else
  echo "ok  docs  native Codex marketplace + OAuth"
fi

if ! grep -q "/oauth/authorize" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "@Browser" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "oauth_loopback.html" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "TEAMSHARED_TOKEN" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "force in-app browser" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "/oauth/authorize" "$ROOT/README.md" \
  || ! grep -q "@Browser" "$ROOT/README.md" \
  || ! grep -q "Skip the OAuth browser" "$ROOT/install/codex/README.md" \
  || ! grep -q "TEAMSHARED_TOKEN" "$ROOT/install/codex/README.md" \
  || ! grep -q "oauth_loopback.html" "$ROOT/install/codex/README.md"; then
  echo "FAIL  Codex OAuth docs must name host-owned first open, /oauth/authorize, @Browser ≠ Authenticate, TEAMSHARED_TOKEN workaround, and oauth_loopback.html"
  FAIL=1
else
  echo "ok  docs  Codex OAuth browser reality + TEAMSHARED_TOKEN workaround"
fi

if ! grep -q "SessionStart" "$ROOT/README.md" \
  || ! grep -q "StopFailure" "$ROOT/README.md" \
  || ! grep -q "PostToolUseFailure" "$ROOT/README.md" \
  || ! grep -q "SessionStart" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "UserPromptSubmit" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "PostToolUse" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "StopFailure" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "keyring" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "/hooks" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q "1.31.0" "$ROOT/plugins/teamshared/README.md" \
  || ! grep -q '~/.codex/AGENTS.md' "$ROOT/plugins/teamshared/README.md"; then
  echo "FAIL  README files must document Codex SessionStart, capture vs Claude, /hooks trust, and AGENTS.md"
  FAIL=1
else
  echo "ok  docs  Codex SessionStart + capture gaps vs Claude"
fi

if ! grep -q "install/codex/README.md" "$ROOT/clients/README.md"; then
  echo "FAIL  clients/README.md must link to install/codex/README.md"
  FAIL=1
else
  echo "ok  docs  clients/README Codex link"
fi

if ! grep -q "Authorization: Bearer tsk_" "$ROOT/clients/hermes.config.yaml" \
  || ! grep -q "Sign in to MCP" "$ROOT/clients/hermes.config.yaml" \
  || ! grep -q "redirect_uri not allowed" "$ROOT/clients/hermes.config.yaml" \
  || ! grep -q "teamshared token mint" "$ROOT/clients/hermes.config.yaml" \
  || ! grep -q "Authorization: Bearer tsk_" "$ROOT/install/hermes/mcp.yaml" \
  || ! grep -q "Sign in to MCP" "$ROOT/install/hermes/mcp.yaml" \
  || ! grep -q "redirect_uri not allowed" "$ROOT/install/hermes/mcp.yaml" \
  || ! grep -q "teamshared token mint" "$ROOT/install/hermes/mcp.yaml" \
  || ! grep -q "Sign in to MCP" "$ROOT/clients/README.md" \
  || ! grep -q "redirect_uri not allowed" "$ROOT/clients/README.md" \
  || ! grep -Fq "*.up.railway.app" "$ROOT/clients/README.md" \
  || ! grep -q "teamshared token mint" "$ROOT/clients/README.md" \
  || ! grep -q "Authorization: Bearer tsk_" "$ROOT/clients/protocol.md" \
  || ! grep -q "Sign in to MCP" "$ROOT/clients/protocol.md" \
  || ! grep -q "redirect_uri not allowed" "$ROOT/clients/protocol.md" \
  || ! grep -q "teamshared token mint" "$ROOT/clients/protocol.md"; then
  echo "FAIL  Hermes docs must lead with bearer tsk_, ban Sign in to MCP / OAuth on hosted Railway, and name redirect_uri not allowed + token mint"
  FAIL=1
else
  echo "ok  docs  Hermes bearer tsk_ (not hosted OAuth)"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT/install/codex/mcp.toml" "$ROOT/install/codex/README.md"
import re, sys
from pathlib import Path

toml_path, readme_path = map(Path, sys.argv[1:])
toml = toml_path.read_text()
readme = readme_path.read_text()

if 'url = "https://teamshared.com/mcp"' not in toml:
    print("FAIL  install/codex/mcp.toml url must be https://teamshared.com/mcp")
    sys.exit(1)
if 'bearer_token_env_var = "TEAMSHARED_TOKEN"' not in toml:
    print("FAIL  install/codex/mcp.toml must use bearer_token_env_var = TEAMSHARED_TOKEN")
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", toml):
    print("FAIL  install/codex/mcp.toml must not contain a tsk_ secret")
    sys.exit(1)
if "__TEAMSHARED_TOKEN__" in toml or "__MCP_URL__" in toml:
    print("FAIL  install/codex/mcp.toml must use the hosted URL and env var, not curl-installer placeholders")
    sys.exit(1)
print("ok  install/codex/mcp.toml  hosted URL + env bearer")

for needle in (
    "codex mcp add",
    "TEAMSHARED_TOKEN",
    "/app/keys",
    ".codex/config.toml",
    "Authorization: Bearer",
    "https://teamshared.com/mcp",
):
    if needle not in readme:
        print(f"FAIL  install/codex/README.md must mention {needle!r}")
        sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", readme):
    print("FAIL  install/codex/README.md must not contain a tsk_ secret")
    sys.exit(1)
print("ok  install/codex/README.md  few-step Codex setup")
PY
else
  echo "skip Codex TOML parse (python3 not found)"
fi

if ! grep -q '/plugin marketplace add teamshared-ai/teamshared-plugin' "$ROOT/README.md"; then
  echo "FAIL  README.md must document Claude Code marketplace add"
  FAIL=1
elif ! grep -q '/plugin install teamshared@teamshared' "$ROOT/README.md"; then
  echo "FAIL  README.md must document /plugin install teamshared@teamshared"
  FAIL=1
elif ! grep -q '/mcp' "$ROOT/README.md" || ! grep -Eqi 'Authenticate' "$ROOT/README.md"; then
  echo "FAIL  README.md must document the /mcp OAuth Authenticate step for Claude Code"
  FAIL=1
elif ! grep -q 'TEAMSHARED_TOKEN' "$ROOT/README.md"; then
  echo "FAIL  README.md must document TEAMSHARED_TOKEN (needed for the capture hooks)"
  FAIL=1
elif grep -q 'does not inherit Cursor Connect' "$ROOT/README.md"; then
  echo "FAIL  README.md must not claim Claude Code has no OAuth-equivalent login (it has its own native /mcp flow)"
  FAIL=1
elif ! grep -q 'SessionStart' "$ROOT/README.md" || ! grep -q '/teamshared:status' "$ROOT/README.md"; then
  echo "FAIL  README.md must document Claude SessionStart and /teamshared:status"
  FAIL=1
else
  echo "ok  docs  Claude Code marketplace + OAuth + TEAMSHARED_TOKEN for hooks"
fi

if ! grep -q 'SessionStart' "$ROOT/claude/README.md" \
  || ! grep -q 'UserPromptSubmit' "$ROOT/claude/README.md" \
  || ! grep -q 'PostToolUseFailure' "$ROOT/claude/README.md" \
  || ! grep -q '1.31.0' "$ROOT/claude/README.md" \
  || ! grep -q '/teamshared:status' "$ROOT/claude/README.md" \
  || ! grep -q '~/.claude/rules/teamshared.md' "$ROOT/claude/README.md"; then
  echo "FAIL  claude/README.md must document official hooks, 1.31.0, status, and the Claude write path"
  FAIL=1
else
  echo "ok  docs  claude/README hooks + 1.31.0"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT/rules/teamshared.mdc" "$ROOT/hooks/capture.py" "$ROOT/claude/hooks/capture.py" "$ROOT/plugins/teamshared/hooks/capture.py"
import re, sys
from pathlib import Path

rule_path, *capture_paths = map(Path, sys.argv[1:])
rule = rule_path.read_text()
front = re.search(r"^version:\s*(\d+\.\d+\.\d+)\s*$", rule, re.M)
comment = re.search(r"teamshared-rule-version:\s*(\d+\.\d+\.\d+)", rule)
if not front or not comment:
    print("FAIL  rules/teamshared.mdc must declare frontmatter + HTML comment versions")
    sys.exit(1)
if front.group(1) != comment.group(1):
    print(
        f"FAIL  rules/teamshared.mdc frontmatter {front.group(1)} "
        f"!= comment {comment.group(1)}"
    )
    sys.exit(1)
rule_version = front.group(1)
if rule_version != "1.31.0":
    print(f"FAIL  rules/teamshared.mdc must be protocol 1.31.0, got {rule_version}")
    sys.exit(1)
if "two Cursor hooks" in rule:
    print("FAIL  rules/teamshared.mdc must not copy the 1.26.0 two-hooks paragraph")
    sys.exit(1)
for needle in (
    "memory_changes_since",
    "degraded: true",
    "errors_by_pillar",
    "sessionStart",
    "beforeSubmitPrompt",
    "afterAgentResponse",
    "sessionEnd",
    "postToolUse",
    "preCompact",
    "org_list",
    "org_bind",
    "bound_scope",
):
    if needle not in rule:
        print(f"FAIL  rules/teamshared.mdc must mention {needle!r}")
        sys.exit(1)
print(f"ok  rules/teamshared.mdc  protocol {rule_version} + capture hooks")

const_re = re.compile(r'^PROTOCOL_VERSION\s*=\s*"(\d+\.\d+\.\d+)"\s*$', re.M)
for path in capture_paths:
    text = path.read_text()
    match = const_re.search(text)
    if not match:
        print(f"FAIL  {path} must define PROTOCOL_VERSION")
        sys.exit(1)
    if match.group(1) != rule_version:
        print(
            f"FAIL  {path} PROTOCOL_VERSION {match.group(1)} "
            f"!= rules/teamshared.mdc {rule_version}"
        )
        sys.exit(1)
    if "resolve_org_binding" not in text or "def resolve_mcp_url" not in text:
        print(f"FAIL  {path} must resolve MCP URL from .teamshared/org")
        sys.exit(1)
    if re.search(r'^MCP_URL\s*=\s*"https://teamshared.com/mcp"', text, re.M):
        print(f"FAIL  {path} must not hardcode MCP_URL; use the D1 resolver")
        sys.exit(1)
    print(f"ok  PROTOCOL_VERSION  {path} == {rule_version}")
    print(f"ok  org binding resolver  {path}")
PY
else
  echo "skip protocol drift check (python3 not found)"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT/README.md"
import re
import sys
from pathlib import Path

readme = Path(sys.argv[1]).read_text(encoding="utf-8")
private = re.compile(r"github\.com/teamshared-ai/teamshared(?!-plugin)")
if private.search(readme):
    print("FAIL  README.md must not link github.com/teamshared-ai/teamshared (private 404)")
    sys.exit(1)
for needle in (
    "https://teamshared.com/#connect",
    "https://github.com/teamshared-ai/teamshared-plugin",
    "https://teamshared.com/mcp",
):
    if needle not in readme:
        print(f"FAIL  README.md must name canonical public URL {needle!r}")
        sys.exit(1)
print("ok  docs  README public install/source URLs")
PY
else
  echo "skip README public URL check (python3 not found)"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT"
import sys
from pathlib import Path

root = Path(sys.argv[1])
docs = {
    "README.md": root / "README.md",
    "AGENTS.md": root / "AGENTS.md",
    "install/README.md": root / "install" / "README.md",
    "install/codex/README.md": root / "install" / "codex" / "README.md",
    "claude/README.md": root / "claude" / "README.md",
    "plugins/teamshared/README.md": root / "plugins" / "teamshared" / "README.md",
    "MARKETPLACE.md": root / "MARKETPLACE.md",
}
required_everywhere = (
    "teamshared org bind",
    "Do not add a second TeamShared server",
    "Unbound `/mcp` keeps working",
    "teamshared token mint",
    ".teamshared/org",
)
readme_harnesses = (
    "Cursor Cloud",
    "Claude Code",
    "Codex",
    "teamshared org status",
    "teamshared org unbind",
)
agents_harnesses = (
    "### Cursor",
    "### Cursor Cloud",
    "### Claude Code",
    "### Codex",
)

for label, path in docs.items():
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in required_everywhere if needle not in text]
    if missing:
        print(f"FAIL  {label} D4 install docs missing {missing}")
        sys.exit(1)
    if "add a second TeamShared server" in text and "Do not add a second TeamShared server" not in text:
        print(f"FAIL  {label} must not advise adding a second TeamShared server")
        sys.exit(1)
    print(f"ok  docs  D4 one-Connect + bind  {label}")

readme = docs["README.md"].read_text(encoding="utf-8")
for needle in readme_harnesses:
    if needle not in readme:
        print(f"FAIL  README.md must cover {needle!r}")
        sys.exit(1)
print("ok  docs  README Cursor Cloud + Claude Code + Codex + bind CLI")

agents = docs["AGENTS.md"].read_text(encoding="utf-8")
for needle in agents_harnesses:
    if needle not in agents:
        print(f"FAIL  AGENTS.md must have section {needle!r}")
        sys.exit(1)
print("ok  docs  AGENTS.md Cursor / Claude Code / Codex / Cursor Cloud")
PY
else
  echo "skip D4 install-doc check (python3 not found)"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT"
import json, re, sys
from pathlib import Path

root = Path(sys.argv[1])
PLUGIN_MCP_URL = "https://teamshared.com/mcp"
REPO_MCP_URL_RE = re.compile(
    r"^https://teamshared\.com(?:/o/[a-z0-9][a-z0-9-]{0,62})?/mcp$"
)

# Optional repo-level MCP configs (not plugin defaults) may use /o/{slug}/mcp.
optional = [
    root / ".cursor" / "mcp.json",
    root / ".teamshared" / "mcp.json",
]
for path in optional:
    if not path.is_file():
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        print(f"FAIL  {path} is not valid JSON")
        sys.exit(1)
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        continue
    for name, server in servers.items():
        if not isinstance(server, dict):
            continue
        url = server.get("url")
        if url is None:
            continue
        if not REPO_MCP_URL_RE.fullmatch(url):
            print(
                f"FAIL  {path} {name}.url must be {PLUGIN_MCP_URL} or "
                f"/o/{{slug}}/mcp, got {url!r}"
            )
            sys.exit(1)
print("ok  repo MCP configs  /mcp or /o/{slug}/mcp allowed")
PY
else
  echo "skip repo MCP url check (python3 not found)"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "Validation failed."
  exit 1
fi

echo "All checks passed."
