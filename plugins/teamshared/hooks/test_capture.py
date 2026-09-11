#!/usr/bin/env python3
"""Unit tests for Codex TeamShared hooks. No network."""

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
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "SessionEnd",
    "PostToolUse",
    "PreCompact",
}

CLAUDE_ONLY = {"StopFailure", "PostToolUseFailure"}
CURSOR_ONLY = {
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
    def test_captures_failed_bash_from_official_payload(self) -> None:
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test -- --runInBand"},
            "tool_response": {"exit_code": 1, "stderr": "FAIL src/add.test.ts\nExpected 2, got 3\n"},
        }
        self.assertTrue(capture.is_shell_tool(payload))
        self.assertTrue(capture.tool_failed(payload))
        fact = capture.failed_tool_fact(payload)
        self.assertIn("npm test", fact)
        self.assertIn("exit 1", fact)
        self.assertIn("Expected 2, got 3", fact)
        self.assertTrue(fact.startswith("Codex PostToolUse:"))
        self.assertLess(len(fact), 1200)

    def test_skips_successful_bash(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": {"exit_code": 0, "stdout": "ok\n"},
        }
        self.assertTrue(capture.is_shell_tool(payload))
        self.assertFalse(capture.tool_failed(payload))

    def test_skips_non_shell_tools(self) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {"command": "edit"},
            "tool_response": {"exit_code": 1},
        }
        self.assertFalse(capture.is_shell_tool(payload))

    def test_fact_is_short_and_strips_secrets(self) -> None:
        long_log = ("ok\n" * 400) + "Authorization: Bearer leaked-token-value\nboom\n"
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest -q"},
            "error": f"Exit code 1\n{long_log}",
        }
        fact = capture.failed_tool_fact(payload)
        self.assertNotIn("leaked-token-value", fact)
        self.assertIn("[redacted]", fact)
        self.assertLessEqual(len(fact), capture.MAX_FACT_CHARS)
        self.assertTrue(fact.startswith("Codex PostToolUse:"))


class PreCompactTests(unittest.TestCase):
    def test_short_summary(self) -> None:
        payload = {"trigger": "auto", "custom_instructions": None}
        summary = capture.precompact_summary(payload)
        self.assertIn("PreCompact", summary)
        self.assertIn("auto", summary)
        self.assertLess(len(summary), 400)


class ConversationMappingTests(unittest.TestCase):
    def test_conversation_id_from_codex_session(self) -> None:
        self.assertEqual(capture.conversation_id({"session_id": "thr_123"}), "thr_123")
        self.assertEqual(capture.session_topic("thr_123"), "codex:thr_123")
        self.assertEqual(capture.session_topic(None), "codex")

    def test_maps_conversation_to_teamshared_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {"session_id": "thr_abc", "cwd": str(Path.cwd())}
            calls: list[tuple[str, dict]] = []

            def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
                calls.append((name, arguments))
                return {"session_id": "ts-sess-1"}

            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        sid = capture.ensure_session(payload, fresh=True, token="tsk_testtoken")
                self.assertEqual(sid, "ts-sess-1")
                self.assertEqual(calls[0][0], "memory_session_ensure")
                self.assertEqual(calls[0][1]["topic"], "codex:thr_abc")
                self.assertTrue(calls[0][1]["fresh"])
                self.assertEqual(capture.mapped_session_id("thr_abc"), "ts-sess-1")

                calls.clear()
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    again = capture.ensure_session(payload, fresh=True, token="tsk_testtoken")
                self.assertEqual(again, "ts-sess-1")
                self.assertFalse(calls[0][1]["fresh"])


class TurnCaptureTests(unittest.TestCase):
    def test_user_prompt_redacts_secrets(self) -> None:
        text = capture.user_prompt_text(
            {"prompt": "deploy with Bearer leaked-token-value please"}
        )
        self.assertNotIn("leaked-token-value", text)
        self.assertIn("[redacted]", text)

    def test_assistant_prefers_last_assistant_message(self) -> None:
        text = capture.assistant_response_text(
            {"last_assistant_message": "hello tsk_abcDEF12345678"}
        )
        self.assertIn("hello", text)
        self.assertNotIn("tsk_abcDEF12345678", text)

    def test_user_prompt_submit_ensures_with_user(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {
                "session_id": "thr_9",
                "prompt": "fix the flaky test tsk_abcDEF12345678",
                "cwd": str(Path.cwd()),
            }
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        extra = capture.handle_user_prompt_submit(payload)
        self.assertEqual(extra, {})
        self.assertEqual(calls[0][0], "memory_session_ensure")
        self.assertIn("fix the flaky test", calls[0][1]["user"])
        self.assertNotIn("tsk_abcDEF12345678", calls[0][1]["user"])
        self.assertFalse(calls[0][1]["fresh"])
        self.assertEqual(calls[0][1]["topic"], "codex:thr_9")

    def test_stop_appends_assistant(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            if name == "memory_session_ensure":
                return {"session_id": "sess-1"}
            return {"session_id": "sess-1", "turn_count": 2}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {
                "session_id": "thr_9",
                "last_assistant_message": "I patched the test. Bearer leaked-token-value",
                "cwd": str(Path.cwd()),
            }
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        extra = capture.handle_stop(payload)
        self.assertEqual(extra, {})
        names = [name for name, _ in calls]
        self.assertIn("memory_session_append", names)
        append = next(args for name, args in calls if name == "memory_session_append")
        self.assertEqual(append["role"], "assistant")
        self.assertIn("I patched the test", append["content"])
        self.assertNotIn("leaked-token-value", append["content"])

    def test_session_start_injects_protocol_and_ensures(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "ts-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        extra = capture.handle_session_start(
                            {
                                "session_id": "thr_new",
                                "source": "startup",
                                "cwd": str(Path.cwd()),
                            }
                        )
        output = extra["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("1.27.0", output["additionalContext"])
        self.assertIn("memory_changes_since", output["additionalContext"])
        self.assertIn("memory_session_ensure", output["additionalContext"])
        self.assertIn("work_id", output["additionalContext"])
        self.assertIn("OAuth", output["additionalContext"])
        self.assertIn("no `StopFailure`", output["additionalContext"])
        self.assertTrue(calls[0][1]["fresh"])
        self.assertLess(len(output["additionalContext"]), 10000)

    def test_session_start_resume_is_not_fresh(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "ts-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        capture.handle_session_start(
                            {
                                "session_id": "thr_resume",
                                "source": "resume",
                                "cwd": str(Path.cwd()),
                            }
                        )
        self.assertFalse(calls[0][1]["fresh"])

    def test_session_end_closes_and_distills(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            cache.write_text(json.dumps({"conversations": {"thr_9": {"session_id": "sess-1"}}}))
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        capture.handle_session_end(
                            {
                                "session_id": "thr_9",
                                "reason": "other",
                                "cwd": str(Path.cwd()),
                            }
                        )
                self.assertIsNone(capture.mapped_session_id("thr_9"))
        names = [name for name, _ in calls]
        self.assertIn("memory_session_close", names)
        close = next(args for name, args in calls if name == "memory_session_close")
        self.assertEqual(close["session_id"], "sess-1")
        self.assertTrue(close["distill"])


class IngestTests(unittest.TestCase):
    def test_ingest_uses_ensure_then_commit(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            if name == "memory_session_ensure":
                return {"session_id": "sess-1"}
            return {"session_id": "sess-1", "turn_count": 2}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        ok = capture.ingest(
                            "Codex PostToolUse: `npm test` exit 1.",
                            fact="Codex PostToolUse: `npm test` exit 1.\nFAIL",
                            payload={"cwd": str(Path.cwd()), "session_id": "thr_tool"},
                            token="tsk_testtoken",
                        )
        self.assertTrue(ok)
        names = [name for name, _ in calls]
        self.assertEqual(names, ["memory_session_ensure", "context_commit"])
        commit = calls[1][1]
        self.assertEqual(commit["facts"][0]["kind"], "event")
        self.assertIn("codex", commit["facts"][0]["tags"])
        self.assertNotIn("tsk_", json.dumps(commit))

    def test_handlers_without_token_do_not_touch_network(self) -> None:
        def boom(*_args, **_kwargs):
            raise AssertionError("network")

        payload = {
            "session_id": "thr_offline",
            "prompt": "hello",
            "last_assistant_message": "world",
            "cwd": str(Path.cwd()),
        }
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "resolve_token", return_value=None):
                    with patch.object(capture.urllib.request, "urlopen", side_effect=boom):
                        self.assertFalse(capture.ensure_session(payload, token=None))
                        extra = capture.handle_session_start(payload)
                        self.assertEqual(
                            extra["hookSpecificOutput"]["hookEventName"],
                            "SessionStart",
                        )
                        self.assertEqual(capture.handle_user_prompt_submit(payload), {})
                        self.assertEqual(capture.handle_stop(payload), {})
                        self.assertEqual(capture.handle_session_end(payload), {})


class TokenResolutionTests(unittest.TestCase):
    def test_oauth_file_store_wins_over_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex"
            home.mkdir()
            (home / ".credentials.json").write_text(
                json.dumps(
                    {
                        "teamshared|abc": {
                            "server_name": "teamshared",
                            "server_url": "https://teamshared.com/mcp",
                            "access_token": "oauth-access-token-value",
                        }
                    }
                )
            )
            with patch.dict(
                os.environ,
                {capture.CODEX_HOME_ENV: str(home), "TEAMSHARED_TOKEN": "tsk_fromenv"},
                clear=False,
            ):
                self.assertEqual(capture.resolve_token(), "oauth-access-token-value")

    def test_env_is_last_resort_when_oauth_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "empty-codex"
            home.mkdir()
            with patch.dict(
                os.environ,
                {capture.CODEX_HOME_ENV: str(home), "TEAMSHARED_TOKEN": "tsk_fromenv"},
                clear=True,
            ):
                self.assertEqual(capture.resolve_token(), "tsk_fromenv")

    def test_expired_oauth_token_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "codex"
            home.mkdir()
            (home / ".credentials.json").write_text(
                json.dumps(
                    {
                        "teamshared|abc": {
                            "server_name": "teamshared",
                            "server_url": "https://teamshared.com/mcp",
                            "access_token": "expired-oauth-token-value",
                            "expires_at": 1,
                        }
                    }
                )
            )
            with patch.dict(os.environ, {capture.CODEX_HOME_ENV: str(home)}, clear=True):
                self.assertIsNone(capture.resolve_token())

    def test_no_cursor_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "empty-codex"
            home.mkdir()
            with patch.dict(os.environ, {capture.CODEX_HOME_ENV: str(home)}, clear=True):
                self.assertIsNone(capture.resolve_token())
        self.assertFalse(hasattr(capture, "_token_from_cursor_store"))


class HooksManifestTests(unittest.TestCase):
    def test_registers_official_codex_events_only(self) -> None:
        hooks = json.loads((HERE / "hooks.json").read_text())
        events = set(hooks["hooks"])
        self.assertEqual(events, REQUIRED_HOOKS)
        self.assertTrue(events.isdisjoint(CLAUDE_ONLY))
        self.assertTrue(events.isdisjoint(CURSOR_ONLY))
        matcher = hooks["hooks"]["PostToolUse"][0]["matcher"]
        self.assertEqual(matcher, "Bash")
        session_end_timeout = hooks["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"]
        self.assertLessEqual(session_end_timeout, 3)
        self.assertNotIn("tsk_", json.dumps(hooks))
        for name in REQUIRED_HOOKS:
            handler = hooks["hooks"][name][0]["hooks"][0]
            self.assertEqual(handler["type"], "command")
            self.assertIn("PLUGIN_ROOT", handler["command"])
            self.assertTrue(handler["command"].endswith(".py"))
        for script in (
            "session_start.py",
            "user_prompt_submit.py",
            "stop.py",
            "session_end.py",
            "post_tool_use.py",
            "pre_compact.py",
        ):
            self.assertTrue((HERE / script).is_file(), script)
        self.assertFalse((HERE / "stop_failure.py").exists())
        self.assertFalse((HERE / "post_tool_use_failure.py").exists())
        self.assertEqual(capture.PROTOCOL_VERSION, "1.27.0")
        self.assertIn("1.27.0", capture.PROTOCOL_CONTEXT)
        self.assertIn("memory_changes_since", capture.PROTOCOL_CONTEXT)
        self.assertIn("OAuth", capture.PROTOCOL_CONTEXT)
        self.assertLess(len(capture.PROTOCOL_CONTEXT), 10000)


if __name__ == "__main__":
    unittest.main()
