#!/usr/bin/env python3
"""Unit tests for SessionStart / PreCompact constraints re-attach (#59)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import constraints_attach as ca
import capture


PLANTED = (
    "# TeamShared constraints\n"
    "- Prefer fail-open hooks with short timeouts\n"
    "- Never store secrets in mcp.json"
)


class ExtractTests(unittest.TestCase):
    def test_prompt_planted_preference(self) -> None:
        result = {
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": PLANTED},
                }
            ]
        }
        self.assertEqual(ca.extract_prompt_text(result), PLANTED)

    def test_prompt_empty_org(self) -> None:
        self.assertEqual(ca.extract_prompt_text({"messages": []}), "")
        self.assertEqual(ca.extract_prompt_text({}), "")
        self.assertEqual(ca.extract_prompt_text(None), "")

    def test_prompt_list_content(self) -> None:
        result = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": PLANTED}],
                }
            ]
        }
        self.assertEqual(ca.extract_prompt_text(result), PLANTED)

    def test_resource_json_body(self) -> None:
        body = json.dumps(
            {
                "text": PLANTED,
                "items": [{"content": "Prefer fail-open hooks with short timeouts"}],
                "empty": False,
                "count": 2,
            }
        )
        result = {"contents": [{"uri": ca.CONSTRAINTS_URI, "text": body}]}
        self.assertEqual(ca.extract_resource_text(result), PLANTED)

    def test_resource_empty_flag(self) -> None:
        body = json.dumps({"text": "", "items": [], "empty": True, "count": 0})
        result = {"contents": [{"uri": ca.CONSTRAINTS_URI, "text": body}]}
        self.assertEqual(ca.extract_resource_text(result), "")


class NormalizeTests(unittest.TestCase):
    def test_adds_heading_when_missing(self) -> None:
        out = ca.normalize_constraints_text("- Prefer fail-open")
        self.assertTrue(out.startswith(ca.CONSTRAINTS_HEADING))
        self.assertIn("- Prefer fail-open", out)

    def test_cap(self) -> None:
        big = ca.CONSTRAINTS_HEADING + "\n- " + ("w" * (ca.MAX_CONSTRAINTS_CHARS + 200))
        out = ca.normalize_constraints_text(big)
        self.assertLessEqual(len(out), ca.MAX_CONSTRAINTS_CHARS)
        self.assertTrue(out.endswith("…"))


class AppendAndHostShapeTests(unittest.TestCase):
    def test_append(self) -> None:
        self.assertEqual(ca.append_constraints("", ""), "")
        self.assertEqual(ca.append_constraints("", PLANTED), PLANTED)
        self.assertEqual(ca.append_constraints("# TeamShared\n\n## Soul\nx", ""), "# TeamShared\n\n## Soul\nx")
        merged = ca.append_constraints("# TeamShared\n\n## Soul\nx", PLANTED)
        self.assertIn("## Soul", merged)
        self.assertIn("# TeamShared constraints", merged)
        self.assertTrue(merged.index("## Soul") < merged.index("# TeamShared constraints"))

    def test_cursor_precompact_user_message(self) -> None:
        self.assertEqual(ca.cursor_precompact_extra(""), {})
        self.assertEqual(ca.cursor_precompact_extra(PLANTED), {"user_message": PLANTED})

    def test_claude_precompact_system_message(self) -> None:
        self.assertEqual(ca.claude_precompact_extra(""), {})
        self.assertEqual(ca.claude_precompact_extra(PLANTED), {"systemMessage": PLANTED})


class FetchFailOpenTests(unittest.TestCase):
    def test_auth_miss_no_throw(self) -> None:
        with mock.patch.object(ca, "_resolve_auth", return_value=(None, ca.DEFAULT_MCP_URL)):
            self.assertEqual(ca.fetch_constraints_text({"cwd": "/tmp"}), "")

    def test_rpc_timeout_fail_open(self) -> None:
        with mock.patch.object(ca, "_resolve_auth", return_value=("tsk_test", ca.DEFAULT_MCP_URL)):
            with mock.patch.object(ca, "mcp_rpc", side_effect=TimeoutError("budget")):
                self.assertEqual(ca.fetch_constraints_text({}), "")

    def test_empty_prompt_falls_back_to_resource(self) -> None:
        def fake_rpc(url, token, method, params, deadline, **kwargs):
            if method == "prompts/get":
                return {"messages": []}
            if method == "resources/read":
                return {
                    "contents": [
                        {
                            "uri": ca.CONSTRAINTS_URI,
                            "text": json.dumps({"text": PLANTED, "empty": False}),
                        }
                    ]
                }
            return None

        with mock.patch.object(ca, "_resolve_auth", return_value=("tsk_test", ca.DEFAULT_MCP_URL)):
            with mock.patch.object(ca, "mcp_rpc", side_effect=fake_rpc):
                self.assertEqual(ca.fetch_constraints_text({}), PLANTED)

    def test_planted_preference_from_prompt(self) -> None:
        def fake_rpc(url, token, method, params, deadline, **kwargs):
            self.assertEqual(method, "prompts/get")
            self.assertEqual(params.get("name"), "constraints")
            return {
                "messages": [
                    {"role": "user", "content": {"type": "text", "text": PLANTED}}
                ]
            }

        with mock.patch.object(ca, "_resolve_auth", return_value=("tsk_test", ca.DEFAULT_MCP_URL)):
            with mock.patch.object(ca, "mcp_rpc", side_effect=fake_rpc):
                self.assertEqual(ca.fetch_constraints_text({"cwd": "/tmp"}), PLANTED)


class SessionStartInjectTests(unittest.TestCase):
    def test_cursor_session_start_appends_constraints(self) -> None:
        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            return {
                "session_id": "ts-constraints",
                "soul": "Prefers terse diffs.",
            }

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with mock.patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with mock.patch.object(capture, "mcp_call", side_effect=fake_call):
                    with mock.patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        with mock.patch.object(capture, "fetch_constraints_text", return_value=PLANTED):
                            extra = capture.handle_session_start(
                                {"session_id": "conv-c", "cwd": str(Path.cwd())}
                            )
        ctx = extra["additional_context"]
        self.assertIn("Prefers terse diffs", ctx)
        self.assertIn("# TeamShared constraints", ctx)
        self.assertIn("Prefer fail-open hooks", ctx)

    def test_cursor_session_start_empty_org_no_block(self) -> None:
        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            return {"session_id": "ts-empty-c", "soul": "Prefers terse diffs."}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with mock.patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with mock.patch.object(capture, "mcp_call", side_effect=fake_call):
                    with mock.patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        with mock.patch.object(capture, "fetch_constraints_text", return_value=""):
                            extra = capture.handle_session_start(
                                {"session_id": "conv-empty-c", "cwd": str(Path.cwd())}
                            )
        self.assertIn("additional_context", extra)
        self.assertNotIn("# TeamShared constraints", extra["additional_context"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
