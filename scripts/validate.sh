#!/usr/bin/env bash
# Structural checks for the Cursor plugin (MCP + recall rule + two hooks),
# Claude Code marketplace package, and native Codex marketplace package.
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
check "$ROOT/.claude-plugin/marketplace.json"
check "$ROOT/claude/.claude-plugin/plugin.json"
check "$ROOT/claude/.mcp.json"
check "$ROOT/claude/README.md"
check "$ROOT/claude/skills/teamshared-memory/SKILL.md"
check "$ROOT/.agents/plugins/marketplace.json"
check "$ROOT/plugins/teamshared/.codex-plugin/plugin.json"
check "$ROOT/plugins/teamshared/.mcp.json"
check "$ROOT/plugins/teamshared/README.md"
check "$ROOT/plugins/teamshared/skills/teamshared-memory/SKILL.md"
check "$ROOT/plugins/teamshared/skills/teamshared-memory/agents/openai.yaml"
absent "$ROOT/skills"
absent "$ROOT/agents"
absent "$ROOT/commands"
absent "$ROOT/claude/hooks"
absent "$ROOT/claude/agents"
absent "$ROOT/claude/commands"

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT/.cursor-plugin/plugin.json" "$ROOT/.cursor-plugin/marketplace.json" "$ROOT/mcp.json" "$ROOT/plugin.json" "$ROOT/.mcp.json" "$ROOT/hooks/hooks.json" "$ROOT/.claude-plugin/marketplace.json" "$ROOT/claude/.claude-plugin/plugin.json" "$ROOT/claude/.mcp.json"
import json, re, sys

kebab = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
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
if server.get("url") != "https://teamshared.com/mcp":
    print(f"FAIL  mcp.json teamshared.url must be https://teamshared.com/mcp, got {server.get('url')!r}")
    sys.exit(1)
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
if open_server.get("url") != "https://teamshared.com/mcp":
    print(f"FAIL  .mcp.json teamshared.url, got {open_server.get('url')!r}")
    sys.exit(1)
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
if set(events) != {"postToolUse", "preCompact"}:
    print(f"FAIL  hooks.json must register only postToolUse and preCompact, got {sorted(events)}")
    sys.exit(1)
if not events["postToolUse"] or not events["preCompact"]:
    print("FAIL  hooks.json postToolUse and preCompact must each have a command")
    sys.exit(1)
matcher = events["postToolUse"][0].get("matcher")
if matcher != "Shell":
    print(f"FAIL  postToolUse matcher must be Shell, got {matcher!r}")
    sys.exit(1)
if "tsk_" in json.dumps(hooks):
    print("FAIL  hooks.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  hooks  postToolUse + preCompact only")

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
if claude_plugin.get("hooks"):
    print("FAIL  Claude plugin.json must not declare hooks")
    sys.exit(1)
if (claude_plugin.get("author") or {}).get("name") != author_name:
    print("FAIL  Claude plugin.json author.name must match Cursor author.name")
    sys.exit(1)
print("ok  Claude plugin.json  no hooks")

with open(claude_mcp_path) as f:
    claude_mcp = json.load(f)
print(f"ok  JSON  {claude_mcp_path}")
claude_server = (claude_mcp.get("mcpServers") or {}).get("teamshared") or {}
if claude_server.get("url") != "https://teamshared.com/mcp":
    print(
        "FAIL  Claude .mcp.json url must be https://teamshared.com/mcp, "
        f"got {claude_server.get('url')!r}"
    )
    sys.exit(1)
if claude_server.get("type") not in ("http", "streamable-http"):
    print(
        "FAIL  Claude .mcp.json type must be http (or streamable-http), "
        f"got {claude_server.get('type')!r}"
    )
    sys.exit(1)
auth = ((claude_server.get("headers") or {}).get("Authorization") or "")
if auth != "Bearer ${TEAMSHARED_TOKEN}":
    print(
        "FAIL  Claude .mcp.json Authorization must be "
        "'Bearer ${TEAMSHARED_TOKEN}', "
        f"got {auth!r}"
    )
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", json.dumps(claude_mcp)):
    print("FAIL  Claude .mcp.json must not contain a real tsk_ secret")
    sys.exit(1)
print("ok  Claude .mcp.json  remote MCP + TEAMSHARED_TOKEN")
PY
  python3 "$ROOT/hooks/test_capture.py" -q
  python3 - <<'PY' "$ROOT/.agents/plugins/marketplace.json" "$ROOT/plugins/teamshared/.codex-plugin/plugin.json" "$ROOT/plugins/teamshared/.mcp.json" "$ROOT/plugins/teamshared/skills/teamshared-memory/SKILL.md" "$ROOT/.cursor-plugin/plugin.json"
import json, re, sys
from pathlib import Path

market_path, plugin_path, mcp_path, skill_path, cursor_plugin_path = map(Path, sys.argv[1:])

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
with cursor_plugin_path.open() as f:
    cursor_plugin = json.load(f)
print(f"ok  JSON  {plugin_path}")
if plugin.get("name") != "teamshared":
    print(f"FAIL  Codex plugin name, got {plugin.get('name')!r}")
    sys.exit(1)
if plugin.get("version") != cursor_plugin.get("version"):
    print("FAIL  Codex plugin version must match Cursor plugin version")
    sys.exit(1)
if (plugin.get("author") or {}).get("name") != "Loreum Labs Ltd":
    print("FAIL  Codex plugin author.name must be 'Loreum Labs Ltd'")
    sys.exit(1)
if plugin.get("skills") != "./skills/" or plugin.get("mcpServers") != "./.mcp.json":
    print("FAIL  Codex plugin must declare ./skills/ and ./.mcp.json")
    sys.exit(1)
interface = plugin.get("interface") or {}
for field in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "defaultPrompt"):
    if field not in interface:
        print(f"FAIL  Codex plugin interface missing {field}")
        sys.exit(1)
print("ok  Codex plugin.json  MCP + teamshared-memory skill")

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
if re.search(r"tsk_[A-Za-z0-9]", json.dumps(mcp)):
    print("FAIL  Codex .mcp.json must not contain a tsk_ secret")
    sys.exit(1)
print("ok  Codex .mcp.json  OAuth-discovered streamable HTTP")

skill = skill_path.read_text()
if "name: teamshared-memory" not in skill or "description:" not in skill:
    print("FAIL  Codex skill frontmatter is incomplete")
    sys.exit(1)
if "[TODO:" in skill or "## Every turn" not in skill:
    print("FAIL  Codex skill must be complete and include the every-turn workflow")
    sys.exit(1)
if re.search(r"tsk_[A-Za-z0-9]", skill):
    print("FAIL  Codex skill must not contain a tsk_ secret")
    sys.exit(1)
print("ok  Codex teamshared-memory skill")
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
    echo "ok  docs  $(basename "$doc") two hooks, no skills"
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

if ! grep -q "install/codex/README.md" "$ROOT/clients/README.md"; then
  echo "FAIL  clients/README.md must link to install/codex/README.md"
  FAIL=1
else
  echo "ok  docs  clients/README Codex link"
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
elif ! grep -q 'TEAMSHARED_TOKEN' "$ROOT/README.md" || ! grep -q 'TEAMSHARED_TOKEN' "$ROOT/claude/.mcp.json"; then
  echo "FAIL  README.md and claude/.mcp.json must document TEAMSHARED_TOKEN"
  FAIL=1
elif ! grep -q 'does not inherit Cursor Connect' "$ROOT/README.md"; then
  echo "FAIL  README.md must say Claude Code does not inherit Cursor Connect"
  FAIL=1
else
  echo "ok  docs  Claude Code marketplace + TEAMSHARED_TOKEN"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "Validation failed."
  exit 1
fi

echo "All checks passed."
