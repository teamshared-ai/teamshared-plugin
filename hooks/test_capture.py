#!/usr/bin/env python3
"""Unit tests for Cursor TeamShared hooks. No network."""

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


REQUIRED_HOOKS = {
    "sessionStart",
    "beforeSubmitPrompt",
    "afterAgentResponse",
    "stop",
    "sessionEnd",
    "postToolUse",
    "preCompact",
}


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


class ConversationMappingTests(unittest.TestCase):
    def test_conversation_id_from_payload_and_session_alias(self) -> None:
        self.assertEqual(
            capture.conversation_id({"conversation_id": "conv-1"}),
            "conv-1",
        )
        self.assertEqual(capture.conversation_id({"session_id": "sess-cursor"}), "sess-cursor")
        self.assertEqual(capture.session_topic("conv-1"), "cursor:conv-1")
        self.assertEqual(capture.session_topic(None), "cursor")

    def test_maps_conversation_to_teamshared_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {"conversation_id": "conv-abc", "cwd": str(Path.cwd())}
            calls: list[tuple[str, dict]] = []

            def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
                calls.append((name, arguments))
                return {"session_id": "ts-sess-1"}

            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        sid = capture.ensure_session(payload, fresh=True, token="oauth-from-connect")
                self.assertEqual(sid, "ts-sess-1")
                self.assertEqual(calls[0][0], "memory_session_ensure")
                self.assertEqual(calls[0][1]["topic"], "cursor:conv-abc")
                self.assertTrue(calls[0][1]["fresh"])
                self.assertEqual(capture.mapped_session_id("conv-abc"), "ts-sess-1")

                calls.clear()
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    again = capture.ensure_session(payload, fresh=True, token="oauth-from-connect")
                self.assertEqual(again, "ts-sess-1")
                self.assertFalse(calls[0][1]["fresh"])


class TurnCaptureTests(unittest.TestCase):
    def test_user_prompt_redacts_secrets_and_notes_attachments(self) -> None:
        text = capture.user_prompt_text(
            {
                "prompt": "deploy with Bearer leaked-token-value please",
                "attachments": [{"type": "file", "file_path": "/tmp/secret.env"}],
            }
        )
        self.assertNotIn("leaked-token-value", text)
        self.assertIn("[redacted]", text)
        self.assertIn("secret.env", text)

    def test_assistant_text_falls_back_to_transcript(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".jsonl") as handle:
            handle.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]},
                    }
                )
                + "\n"
            )
            handle.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "hello tsk_abcDEF12345678"}],
                        },
                    }
                )
                + "\n"
            )
            path = handle.name
        try:
            text = capture.assistant_response_text({"transcript_path": path})
        finally:
            os.unlink(path)
        self.assertIn("hello", text)
        self.assertNotIn("tsk_abcDEF12345678", text)

    def test_before_submit_prompt_ensures_with_user(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {
                "conversation_id": "conv-9",
                "prompt": "fix the flaky test tsk_abcDEF12345678",
                "cwd": str(Path.cwd()),
            }
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_before_submit_prompt(payload)
        self.assertEqual(extra, {"continue": True})
        self.assertEqual(calls[0][0], "memory_session_ensure")
        self.assertIn("fix the flaky test", calls[0][1]["user"])
        self.assertNotIn("tsk_abcDEF12345678", calls[0][1]["user"])
        self.assertFalse(calls[0][1]["fresh"])
        self.assertEqual(calls[0][1]["topic"], "cursor:conv-9")

    def test_after_agent_response_appends_assistant(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            if name == "memory_session_ensure":
                return {"session_id": "sess-1"}
            return {"session_id": "sess-1", "turn_count": 2}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {
                "conversation_id": "conv-9",
                "text": "I patched the test. Bearer leaked-token-value",
                "cwd": str(Path.cwd()),
            }
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        capture.handle_after_agent_response(payload)
        names = [name for name, _ in calls]
        self.assertIn("memory_session_append", names)
        append = next(args for name, args in calls if name == "memory_session_append")
        self.assertEqual(append["role"], "assistant")
        self.assertIn("I patched the test", append["content"])
        self.assertNotIn("leaked-token-value", append["content"])
        self.assertEqual(append["session_id"], "sess-1")

    def test_session_start_sets_env_and_ensures(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {"session_id": "ts-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_session_start(
                            {"session_id": "conv-new", "cwd": str(Path.cwd())}
                        )
        self.assertEqual(extra["env"][capture.SESSION_ENV], "ts-1")
        self.assertEqual(extra["env"][capture.CONVERSATION_ENV], "conv-new")
        self.assertTrue(calls[0][1]["fresh"])

    def test_stop_completed_does_not_close(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with patch.object(capture, "mcp_call", side_effect=fake_call):
            with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                extra = capture.handle_stop({"status": "completed", "loop_count": 0})
        self.assertEqual(extra, {})
        self.assertEqual(calls, [])

    def test_stop_aborted_appends_system_note(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        capture.handle_stop(
                            {
                                "status": "aborted",
                                "conversation_id": "conv-9",
                                "cwd": str(Path.cwd()),
                            }
                        )
        names = [name for name, _ in calls]
        self.assertIn("memory_session_append", names)
        self.assertNotIn("memory_session_close", names)
        append = next(args for name, args in calls if name == "memory_session_append")
        self.assertEqual(append["role"], "system")
        self.assertIn("aborted", append["content"])

    def test_session_end_closes_and_distills(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            cache.write_text(json.dumps({"conversations": {"conv-9": {"session_id": "sess-1"}}}))
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        capture.handle_session_end(
                            {
                                "session_id": "conv-9",
                                "reason": "user_close",
                                "cwd": str(Path.cwd()),
                            }
                        )
                self.assertIsNone(capture.mapped_session_id("conv-9"))
        names = [name for name, _ in calls]
        self.assertIn("memory_session_close", names)
        close = next(args for name, args in calls if name == "memory_session_close")
        self.assertEqual(close["session_id"], "sess-1")
        self.assertTrue(close["distill"])


class IngestTests(unittest.TestCase):
    def test_ingest_uses_ensure_then_commit_with_origin_agent(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            if name == "memory_session_ensure":
                return {"session_id": "sess-1"}
            return {"session_id": "sess-1", "turn_count": 2}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        ok = capture.ingest(
                            "Cursor postToolUse: `npm test` exit 1.",
                            fact="Cursor postToolUse: `npm test` exit 1.\nFAIL",
                            payload={"cwd": str(Path.cwd()), "conversation_id": "conv-tool"},
                            token="oauth-from-connect",
                        )
        self.assertTrue(ok)
        names = [name for name, _ in calls]
        self.assertEqual(names, ["memory_session_ensure", "context_commit"])
        self.assertEqual(calls[0][1]["topic"], "cursor:conv-tool")
        commit = calls[1][1]
        self.assertEqual(commit["session_id"], "sess-1")
        self.assertFalse(commit["close"])
        self.assertEqual(commit["facts"][0]["kind"], "event")
        self.assertIn("origin:agent", commit["facts"][0]["tags"])
        self.assertNotIn("tsk_", json.dumps(commit))

    def test_ingest_without_token_is_false(self) -> None:
        with patch.object(capture, "resolve_token", return_value=None):
            self.assertFalse(capture.ingest("hello", token=None))

    def test_handlers_without_token_do_not_touch_network(self) -> None:
        def boom(*_args, **_kwargs):
            raise AssertionError("network")

        payload = {
            "conversation_id": "conv-offline",
            "prompt": "hello",
            "text": "world",
            "cwd": str(Path.cwd()),
        }
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "resolve_token", return_value=None):
                    with patch.object(capture.urllib.request, "urlopen", side_effect=boom):
                        self.assertFalse(capture.ensure_session(payload, token=None))
                        self.assertEqual(
                            capture.handle_before_submit_prompt(payload),
                            {"continue": True},
                        )
                        self.assertEqual(capture.handle_after_agent_response(payload), {})
                        self.assertEqual(capture.handle_session_end(payload), {})


class HooksManifestTests(unittest.TestCase):
    def test_registers_chat_capture_and_existing_hooks(self) -> None:
        hooks = json.loads((HERE / "hooks.json").read_text())
        events = set(hooks["hooks"])
        self.assertEqual(events, REQUIRED_HOOKS)
        self.assertEqual(len(hooks["hooks"]["postToolUse"]), 1)
        self.assertEqual(len(hooks["hooks"]["preCompact"]), 1)
        self.assertEqual(hooks["hooks"]["postToolUse"][0]["matcher"], "Shell")
        for name in REQUIRED_HOOKS:
            self.assertTrue(hooks["hooks"][name][0]["command"])
        self.assertNotIn("tsk_", json.dumps(hooks))
        for script in (
            "session_start.py",
            "before_submit_prompt.py",
            "after_agent_response.py",
            "stop.py",
            "session_end.py",
            "post_tool_use.py",
            "pre_compact.py",
        ):
            self.assertTrue((HERE / script).is_file(), script)


if __name__ == "__main__":
    unittest.main()
