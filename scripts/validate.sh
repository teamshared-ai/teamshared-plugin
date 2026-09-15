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
