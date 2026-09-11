#!/usr/bin/env bash
# Structural checks for both plugins in this repo:
# - Cursor plugin (.cursor-plugin/): MCP + recall rule + two hooks
# - Claude Code plugin (.claude-plugin/): MCP + teamshared skill + two hooks
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
check "$ROOT/install/pi/mcp.json"
check "$ROOT/install/hermes/mcp.yaml"
check "$ROOT/install/hermes/capture.py"
check "$ROOT/clients/protocol.md"
check "$ROOT/assets/logo.png"
check "$ROOT/assets/logo.svg"
check "$ROOT/LICENSE"
check "$ROOT/README.md"
check "$ROOT/CHANGELOG.md"
check "$ROOT/hooks/hooks.cursor.json"
check "$ROOT/hooks/capture.py"
check "$ROOT/hooks/post_tool_use.py"
check "$ROOT/hooks/pre_compact.py"
absent "$ROOT/agents"
absent "$ROOT/commands"

check "$ROOT/.claude-plugin/plugin.json"
check "$ROOT/.claude-plugin/marketplace.json"
check "$ROOT/skills/teamshared/SKILL.md"
check "$ROOT/hooks/hooks.claude.json"

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' "$ROOT/.cursor-plugin/plugin.json" "$ROOT/.cursor-plugin/marketplace.json" "$ROOT/mcp.json" "$ROOT/plugin.json" "$ROOT/.mcp.json" "$ROOT/hooks/hooks.cursor.json" "$ROOT/.claude-plugin/plugin.json" "$ROOT/.claude-plugin/marketplace.json" "$ROOT/hooks/hooks.claude.json" "$ROOT/skills/teamshared/SKILL.md"
import json, re, sys

kebab = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
(
    plugin_path, market_path, mcp_path, open_plugin_path, open_mcp_path,
    hooks_path, claude_plugin_path, claude_market_path, claude_hooks_path,
    claude_skill_path,
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

if plugin.get("hooks") != "./hooks/hooks.cursor.json":
    print(f"FAIL  plugin.json hooks must be './hooks/hooks.cursor.json', got {plugin.get('hooks')!r}")
    sys.exit(1)
print("ok  hooks  ./hooks/hooks.cursor.json")

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
    print(f"FAIL  hooks.cursor.json must register only postToolUse and preCompact, got {sorted(events)}")
    sys.exit(1)
if not events["postToolUse"] or not events["preCompact"]:
    print("FAIL  hooks.cursor.json postToolUse and preCompact must each have a command")
    sys.exit(1)
matcher = events["postToolUse"][0].get("matcher")
if matcher != "Shell":
    print(f"FAIL  postToolUse matcher must be Shell, got {matcher!r}")
    sys.exit(1)
if "tsk_" in json.dumps(hooks):
    print("FAIL  hooks.cursor.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  hooks  postToolUse + preCompact only")

with open(claude_plugin_path) as f:
    claude_plugin = json.load(f)
print(f"ok  JSON  {claude_plugin_path}")
if claude_plugin.get("name") != "teamshared":
    print(f"FAIL  .claude-plugin/plugin.json name must be 'teamshared', got {claude_plugin.get('name')!r}")
    sys.exit(1)
if claude_plugin.get("author") != plugin.get("author"):
    print("FAIL  .claude-plugin/plugin.json author must match .cursor-plugin/plugin.json")
    sys.exit(1)
if claude_plugin.get("mcpServers") != "./mcp.json":
    print(f"FAIL  .claude-plugin/plugin.json mcpServers must be './mcp.json', got {claude_plugin.get('mcpServers')!r}")
    sys.exit(1)
if claude_plugin.get("skills") != "./skills/":
    print(f"FAIL  .claude-plugin/plugin.json skills must be './skills/', got {claude_plugin.get('skills')!r}")
    sys.exit(1)
if claude_plugin.get("hooks") != "./hooks/hooks.claude.json":
    print(f"FAIL  .claude-plugin/plugin.json hooks must be './hooks/hooks.claude.json', got {claude_plugin.get('hooks')!r}")
    sys.exit(1)
print("ok  .claude-plugin/plugin.json  mcp + skill + hooks")

with open(claude_market_path) as f:
    claude_market = json.load(f)
print(f"ok  JSON  {claude_market_path}")
claude_names = [p.get("name") for p in claude_market.get("plugins", [])]
if claude_names != ["teamshared"]:
    print(f"FAIL  .claude-plugin/marketplace.json plugins must be [teamshared], got {claude_names}")
    sys.exit(1)
if claude_market["plugins"][0].get("source") != "./":
    print(
        "FAIL  .claude-plugin/marketplace.json source must be './', "
        f"got {claude_market['plugins'][0].get('source')!r}"
    )
    sys.exit(1)
if (claude_market.get("owner") or {}).get("name") != author_name:
    print(
        "FAIL  .claude-plugin/marketplace.json owner.name must match author.name, "
        f"got {(claude_market.get('owner') or {}).get('name')!r}"
    )
    sys.exit(1)
print("ok  .claude-plugin/marketplace.json  source ./, owner Loreum Labs Ltd")

with open(claude_hooks_path) as f:
    claude_hooks = json.load(f)
print(f"ok  JSON  {claude_hooks_path}")
claude_events = claude_hooks.get("hooks") or {}
if set(claude_events) != {"PostToolUse", "PreCompact"}:
    print(f"FAIL  hooks.claude.json must register only PostToolUse and PreCompact, got {sorted(claude_events)}")
    sys.exit(1)
claude_matcher = claude_events["PostToolUse"][0].get("matcher")
if claude_matcher != "Bash":
    print(f"FAIL  hooks.claude.json PostToolUse matcher must be Bash, got {claude_matcher!r}")
    sys.exit(1)
if "tsk_" in json.dumps(claude_hooks):
    print("FAIL  hooks.claude.json must not contain a tsk_ key")
    sys.exit(1)
print("ok  hooks.claude.json  PostToolUse + PreCompact only")

skill_text = open(claude_skill_path).read()
if not skill_text.startswith("---\n"):
    print(f"FAIL  {claude_skill_path} must start with YAML frontmatter")
    sys.exit(1)
if "name: teamshared" not in skill_text.splitlines()[1]:
    print(f"FAIL  {claude_skill_path} frontmatter name must be teamshared")
    sys.exit(1)
print("ok  skills/teamshared/SKILL.md  frontmatter present")
PY
  python3 "$ROOT/hooks/test_capture.py" -q
else
  echo "skip JSON parse (python3 not found)"
fi

for doc in "$ROOT/README.md" "$ROOT/MARKETPLACE.md"; do
  if ! grep -iq "postToolUse\|PostToolUse" "$doc" || ! grep -iq "preCompact" "$doc"; then
    echo "FAIL  $doc must mention postToolUse/PostToolUse and preCompact"
    FAIL=1
  else
    echo "ok  docs  $(basename "$doc") mentions both hooks"
  fi
done

if ! grep -q "Claude Code" "$ROOT/README.md"; then
  echo "FAIL  README.md must document the Claude Code plugin"
  FAIL=1
else
  echo "ok  docs  README.md documents the Claude Code plugin"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "Validation failed."
  exit 1
fi

echo "All checks passed."
