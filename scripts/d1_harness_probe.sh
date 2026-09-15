#!/usr/bin/env bash
# Live C1 + local-source probe for the D1 org-binding spike.
# Does not install or launch Cursor Desktop, Claude Code, or Codex.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${TEAMSHARED_HOST:-https://teamshared.com}"

echo "# D1 harness probe"
echo "host=$HOST"
echo "repo=$ROOT"
echo

echo "## Local MCP / bind sources"
for path in \
  "$ROOT/.teamshared/org" \
  "$ROOT/.cursor/mcp.json" \
  "$HOME/.cursor/mcp.json" \
  "$ROOT/.mcp.json" \
  "$ROOT/mcp.json" \
  "$ROOT/claude/.mcp.json" \
  "$ROOT/plugins/teamshared/.mcp.json" \
  "$ROOT/.codex/config.toml" \
  "$HOME/.codex/config.toml"; do
  if [[ -e "$path" ]]; then
    echo "present  $path"
  else
    echo "absent   $path"
  fi
done
echo

echo "## Harness CLIs"
for cmd in claude codex cursor; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "present  $cmd -> $(command -v "$cmd")"
  else
    echo "absent   $cmd"
  fi
done
echo

echo "## C1 org MCP (unauthenticated)"
probe() {
  local path="$1"
  local tmp
  tmp="$(mktemp)"
  local code
  code="$(curl -sS -D - -o "$tmp" "${HOST}${path}" | awk 'BEGIN{IGNORECASE=1} /^HTTP/{print $2} /^www-authenticate:/{print}' | tr '\n' ' ')"
  local body
  body="$(tr -d '\n' < "$tmp")"
  rm -f "$tmp"
  echo "GET ${path}"
  echo "  ${code}"
  echo "  body=${body}"
}

probe "/mcp"
probe "/o/sapien/mcp"
probe "/o/does-not-exist-xyz/mcp"
echo

echo "## C2 org protected-resource metadata"
for path in \
  "/.well-known/oauth-protected-resource" \
  "/.well-known/oauth-protected-resource/mcp" \
  "/.well-known/oauth-protected-resource/o/sapien/mcp"; do
  code="$(curl -sS -o /tmp/d1-prm.json -w '%{http_code}' "${HOST}${path}")"
  echo "GET ${path} -> ${code}"
  python3 - "$code" <<'PY'
import json, sys
code = sys.argv[1]
try:
    data = json.load(open("/tmp/d1-prm.json"))
except Exception:
    print("  (non-JSON)")
    raise SystemExit
if isinstance(data, dict):
    print(f"  resource={data.get('resource')}")
    print(f"  authorization_servers={data.get('authorization_servers')}")
PY
done
echo

echo "## Resolver (this repo)"
python3 "$ROOT/scripts/org_binding.py" "$ROOT"
echo
echo "done"
