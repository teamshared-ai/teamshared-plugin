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
