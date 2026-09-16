#!/usr/bin/env python3
"""Pins MCP-native org-bind guidance to the shipped server contract.

Authoritative contract: teamshared-ai/teamshared#542 (Fixes #541), protocol
1.31.0. ``rules/teamshared.mdc`` must stay a verbatim copy of
``src/teamshared/clients/teamshared.mdc``. Claude/Codex skills document the
four tools, scope, and precedence. CLI bind is an optional fallback only.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MDC = ROOT / "rules" / "teamshared.mdc"

SKILL_FILES = (
    ROOT / "claude" / "skills" / "teamshared-memory" / "SKILL.md",
    ROOT / "plugins" / "teamshared" / "skills" / "teamshared-memory" / "SKILL.md",
)

STATUS_FILES = (
    ROOT / "claude" / "skills" / "status" / "SKILL.md",
    ROOT / "plugins" / "teamshared" / "skills" / "status" / "SKILL.md",
)

# Server client mdc (lean lockstep copy).
MDC_REQUIRED = (
    "1.31.0",
    "org_list",
    "org_bind(slug=...)",
    "bound_scope",
    "teamshared org bind",
    "is optional",
)

# Full shipped contract for harness skills.
SKILL_REQUIRED = (
    "1.31.0",
    "org_list",
    "org_context_get",
    "org_bind",
    "org_unbind",
    "scope=conversation",
    "workspace",
    "Mcp-Session-Id",
    "no_session",
    "teamshared org bind <slug>",
    "optional fallback",
)

STATUS_REQUIRED = (
    "1.31.0",
    "org_list",
    "org_context_get",
    "org_bind",
    "org_unbind",
    "optional fallback",
    "teamshared org bind <slug>",
)

LEGACY_CLI_ONLY = "(suggest `teamshared org bind <slug>`)"
NO_CLI_INSTALL = "Do not tell the user to install the TeamShared CLI"
PRECEDENCE = "path `/o/{slug}/mcp` > conversation"
BLOCKED_OR_CANDIDATE = (
    "when those tools exist",
    "blocked on server",
    "candidate names",
    "Do not invent org-tool",
    "There is no shipped server contract",
)


def collapsed(text: str) -> str:
    return " ".join(text.split())


class OrgBindGuidanceTests(unittest.TestCase):
    def test_mdc_matches_server_org_bind_copy(self) -> None:
        text = MDC.read_text(encoding="utf-8")
        flat = collapsed(text)
        for needle in MDC_REQUIRED:
            self.assertIn(needle, flat, f"{MDC} missing {needle!r}")
        self.assertNotIn(LEGACY_CLI_ONLY, text)
        for forbidden in BLOCKED_OR_CANDIDATE:
            self.assertNotIn(forbidden, text, f"{MDC} still has {forbidden!r}")

    def test_protocol_skills_document_shipped_contract(self) -> None:
        for path in SKILL_FILES:
            text = path.read_text(encoding="utf-8")
            flat = collapsed(text)
            for needle in SKILL_REQUIRED:
                self.assertIn(needle, flat, f"{path} missing {needle!r}")
            self.assertIn(NO_CLI_INSTALL, flat, f"{path} must not send chat users to install the CLI")
            self.assertIn(PRECEDENCE, flat, f"{path} missing precedence")
            self.assertNotIn(LEGACY_CLI_ONLY, text)
            for forbidden in BLOCKED_OR_CANDIDATE:
                self.assertNotIn(forbidden, text, f"{path} still has {forbidden!r}")

    def test_status_skills_document_shipped_contract(self) -> None:
        for path in STATUS_FILES:
            text = path.read_text(encoding="utf-8")
            flat = collapsed(text)
            for needle in STATUS_REQUIRED:
                self.assertIn(needle, flat, f"{path} missing {needle!r}")
            self.assertNotIn("when those tools exist", text)

    def test_agents_md_mcp_first_cli_fallback(self) -> None:
        flat = collapsed((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        for needle in (
            "org_list",
            "org_context_get",
            "org_bind",
            "org_unbind",
            "scope=conversation",
            "optional fallback",
            "teamshared org bind <slug>",
            NO_CLI_INSTALL,
        ):
            self.assertIn(needle, flat, f"AGENTS.md missing {needle!r}")
        self.assertNotIn("when those tools exist", flat)


if __name__ == "__main__":
    unittest.main()
