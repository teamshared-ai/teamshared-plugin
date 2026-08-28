#!/usr/bin/env python3
"""Unit tests for the two Cursor hooks. No network."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import capture  # noqa: E402


class StripSecretsTests(unittest.TestCase):
    def test_strips_tsk_and_bearer_and_url_password(self) -> None:
        raw = (
            "cmd tsk_abcDEF12345678 Authorization: Bearer supersecret "
            "https://user:hunter2@example.com/x sk-abcdefghijklmnopqrstuvwxyz "
            "api_key=shh-now ghp_abcdefghijklmnopqrstuvwxyz"
        )
        cleaned = capture.strip_secrets(raw)
        self.assertNotIn("tsk_abcDEF12345678", cleaned)
        self.assertNotIn("supersecret", cleaned)
        self.assertNotIn("hunter2", cleaned)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", cleaned)
        self.assertNotIn("shh-now", cleaned)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz", cleaned)
        self.assertIn("[redacted]", cleaned)


class FailedToolTests(unittest.TestCase):
    def test_skips_successful_shell(self) -> None:
        payload = {
            "tool_name": "Shell",
            "tool_input": {"command": "npm test"},
            "tool_output": json.dumps({"exitCode": 0, "stdout": "All tests passed"}),
        }
        self.assertFalse(capture.is_failed_test_lint_shell(payload))

    def test_skips_non_shell_tools(self) -> None:
        payload = {
            "tool_name": "Read",
            "tool_input": {"path": "foo"},
            "tool_output": json.dumps({"exitCode": 1}),
        }
        self.assertFalse(capture.is_failed_test_lint_shell(payload))

    def test_captures_failed_npm_test(self) -> None:
        payload = {
            "tool_name": "Shell",
            "tool_input": {"command": "npm test -- --runInBand"},
            "tool_output": {
                "exitCode": 1,
                "stderr": "FAIL src/add.test.ts\nExpected 2, got 3\n",
                "stdout": "Test Suites: 1 failed",
            },
        }
        self.assertTrue(capture.is_failed_test_lint_shell(payload))
        fact = capture.failed_tool_fact(payload)
        self.assertIn("npm test", fact)
        self.assertIn("exit 1", fact)
        self.assertIn("Expected 2, got 3", fact)
        self.assertLess(len(fact), 1200)

    def test_captures_failed_generic_shell(self) -> None:
        payload = {
            "tool_name": "Shell",
            "tool_input": {"command": "make build"},
            "tool_output": {"exitCode": 2, "stderr": "missing separator"},
        }
        self.assertTrue(capture.is_failed_test_lint_shell(payload))

    def test_fact_is_short_and_strips_secrets(self) -> None:
        long_log = ("ok\n" * 400) + "Authorization: Bearer leaked-token-value\nboom\n"
        payload = {
            "tool_name": "Shell",
            "tool_input": {"command": "pytest -q"},
            "tool_output": {"exitCode": 1, "stderr": long_log},
        }
        fact = capture.failed_tool_fact(payload)
        self.assertNotIn("leaked-token-value", fact)
        self.assertIn("[redacted]", fact)
        self.assertLessEqual(len(fact), capture.MAX_FACT_CHARS)
        self.assertLess(len(fact), len(long_log))
        self.assertTrue(fact.startswith("Cursor postToolUse:"))


class PreCompactTests(unittest.TestCase):
    def test_short_summary(self) -> None:
        payload = {
            "trigger": "auto",
            "context_usage_percent": 85,
            "context_tokens": 120000,
            "context_window_size": 128000,
            "message_count": 45,
            "is_first_compaction": True,
        }
        summary = capture.precompact_summary(payload)
        self.assertIn("preCompact", summary)
        self.assertIn("85%", summary)
        self.assertIn("45 messages", summary)
        self.assertLess(len(summary), 400)

    def test_does_not_embed_full_transcript(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".jsonl") as handle:
            for i in range(200):
                handle.write(
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {
                                "content": [{"type": "text", "text": f"paragraph {i} " + ("x" * 200)}]
                            },
                        }
                    )
                    + "\n"
                )
            path = handle.name
        try:
            summary = capture.precompact_summary({"trigger": "manual", "transcript_path": path})
        finally:
            os.unlink(path)
        self.assertLess(len(summary), capture.MAX_SUMMARY_CHARS + 1)
        self.assertNotIn("paragraph 0", summary)


class IngestTests(unittest.TestCase):
    def test_ingest_uses_ensure_then_commit_with_origin_agent(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            if name == "memory_session_ensure":
                return {"session_id": "sess-1"}
            return {"session_id": "sess-1", "turn_count": 2}

        with patch.object(capture, "mcp_call", side_effect=fake_call):
            with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                ok = capture.ingest(
                    "Cursor postToolUse: `npm test` exit 1.",
                    fact="Cursor postToolUse: `npm test` exit 1.\nFAIL",
                    payload={"cwd": str(Path.cwd())},
                    token="oauth-from-connect",
                )
        self.assertTrue(ok)
        names = [name for name, _ in calls]
        self.assertEqual(names, ["memory_session_ensure", "context_commit"])
        commit = calls[1][1]
        self.assertEqual(commit["session_id"], "sess-1")
        self.assertFalse(commit["close"])
        self.assertEqual(commit["facts"][0]["kind"], "event")
        self.assertIn("origin:agent", commit["facts"][0]["tags"])
        self.assertNotIn("tsk_", json.dumps(commit))

    def test_ingest_without_token_is_false(self) -> None:
        with patch.object(capture, "resolve_token", return_value=None):
            self.assertFalse(capture.ingest("hello", token=None))


class HooksManifestTests(unittest.TestCase):
    def test_only_two_cursor_hooks(self) -> None:
        hooks = json.loads((HERE / "hooks.json").read_text())
        events = set(hooks["hooks"])
        self.assertEqual(events, {"postToolUse", "preCompact"})
        self.assertEqual(len(hooks["hooks"]["postToolUse"]), 1)
        self.assertEqual(len(hooks["hooks"]["preCompact"]), 1)
        self.assertEqual(hooks["hooks"]["postToolUse"][0]["matcher"], "Shell")


if __name__ == "__main__":
    unittest.main()
