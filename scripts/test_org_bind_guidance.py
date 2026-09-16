#!/usr/bin/env python3
"""Pins MCP-native org-bind guidance in harness skills and rules.

Candidate tool names come from teamshared-ai/teamshared#541
(``org_list`` / ``org_bind``). There is no shipped server contract yet —
do not invent extra names or arguments. CLI bind stays an optional fallback.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROTOCOL_FILES = (
    ROOT / "rules" / "teamshared.mdc",
    ROOT / "claude" / "skills" / "teamshared-memory" / "SKILL.md",
    ROOT / "plugins" / "teamshared" / "skills" / "teamshared-memory" / "SKILL.md",
)

STATUS_FILES = (
    ROOT / "claude" / "skills" / "status" / "SKILL.md",
    ROOT / "plugins" / "teamshared" / "skills" / "status" / "SKILL.md",
)

REQUIRED = (
    "org_list",
    "org_bind",
    "teamshared org bind <slug>",
    "optional fallback",
)

# CLI-only warning copy that #541 replaces for chat-first hosts.
LEGACY_CLI_ONLY = "(suggest `teamshared org bind <slug>`)"

# Issue #541 listed these as candidates; do not treat them as the contract.
INVENTED_CONTRACT = (
    "org_bind(slug, scope=",
    "org_unbind",
    "org_context_get",
)

NO_CLI_INSTALL = "Do not tell the user to install the TeamShared CLI"


def collapsed(text: str) -> str:
    return " ".join(text.split())


class OrgBindGuidanceTests(unittest.TestCase):
    def test_protocol_files_prefer_mcp_org_tools(self) -> None:
        for path in PROTOCOL_FILES:
            text = path.read_text(encoding="utf-8")
            flat = collapsed(text)
            for needle in REQUIRED:
                self.assertIn(needle, flat, f"{path} missing {needle!r}")
            self.assertIn(
                NO_CLI_INSTALL,
                flat,
                f"{path} must not send chat users to install the CLI",
            )
            self.assertNotIn(
                LEGACY_CLI_ONLY,
                text,
                f"{path} still has CLI-only warning copy",
            )
            for forbidden in INVENTED_CONTRACT:
                self.assertNotIn(
                    forbidden,
                    text,
                    f"{path} must not invent {forbidden!r} before the server PR",
                )

    def test_status_skills_prefer_mcp_org_tools(self) -> None:
        for path in STATUS_FILES:
            flat = collapsed(path.read_text(encoding="utf-8"))
            for needle in ("org_list", "org_bind", "optional fallback"):
                self.assertIn(needle, flat, f"{path} missing {needle!r}")
            self.assertIn("teamshared org bind <slug>", flat)

    def test_agents_md_mcp_first_cli_fallback(self) -> None:
        flat = collapsed((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("org_list", flat)
        self.assertIn("org_bind", flat)
        self.assertIn("optional fallback", flat)
        self.assertIn("teamshared org bind <slug>", flat)
        self.assertIn(NO_CLI_INSTALL, flat)


if __name__ == "__main__":
    unittest.main()
