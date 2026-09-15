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
