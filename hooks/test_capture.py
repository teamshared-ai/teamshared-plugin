#!/usr/bin/env python3
"""Unit tests for Cursor TeamShared hooks. No network."""

from __future__ import annotations

import json
import os
import subprocess
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
    "postToolUseFailure",
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


class FailureRecallTests(unittest.TestCase):
    def test_query_is_tool_plus_truncated_error(self) -> None:
        long_err = ("ok line\n" * 80) + "AssertionError: expected 2 got 3\n"
        payload = {
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
            "error_message": long_err,
        }
        query = capture.failure_recall_query(payload)
        self.assertTrue(query.startswith("Shell "))
        self.assertIn("AssertionError", query)
        self.assertLessEqual(len(query), capture.MAX_FAILURE_RECALL_QUERY_CHARS)
        self.assertTrue(capture.is_post_tool_use_failure_event(payload))

    def test_query_strips_secrets_and_skips_empty(self) -> None:
        payload = {
            "tool_name": "Shell",
            "error_message": "boom Bearer leaked-token-value tsk_abcDEF12345678",
        }
        query = capture.failure_recall_query(payload)
        self.assertNotIn("leaked-token-value", query)
        self.assertNotIn("tsk_abcDEF12345678", query)
        self.assertIn("[redacted]", query)
        self.assertEqual(capture.failure_recall_query({"tool_name": "Read"}), "")

    def test_catalog_without_bug_fix_kind_uses_semantic_recall(self) -> None:
        self.assertIsNone(capture.failure_recall_filters())
        self.assertNotIn("bug_fix", capture._CATALOG_RECALL_KINDS)
        self.assertNotIn("anti_pattern", capture._CATALOG_RECALL_KINDS)

    def test_catalog_bug_fix_kind_sends_filter(self) -> None:
        with patch.object(
            capture, "_CATALOG_RECALL_KINDS", frozenset({"bug_fix", "fact"})
        ):
            self.assertEqual(capture.failure_recall_filters(), {"kind": "bug_fix"})
        calls: list[dict] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append(arguments)
            return {"records": [{"content": "pin the lockfile"}]}

        payload = {
            "tool_name": "Shell",
            "error_message": "ELIFECYCLE npm test",
            "cwd": str(Path.cwd()),
        }
        with patch.object(
            capture, "_CATALOG_RECALL_KINDS", frozenset({"bug_fix", "fact"})
        ):
            with patch.object(capture, "mcp_call", side_effect=fake_call):
                with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                    extra = capture.handle_post_tool_use_failure(payload)
        self.assertEqual(calls[0]["filters"], {"kind": "bug_fix"})
        self.assertIn("pin the lockfile", extra["additional_context"])

    def test_recall_injects_additional_context_and_never_writes(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {
                "records": [
                    {
                        "kind": "note",
                        "subject": "other",
                        "content": "unrelated note",
                    },
                    {
                        "kind": "bug_fix",
                        "subject": "npm test",
                        "content": "pin jest and clear cache. Bearer leaked-token-value",
                        "tags": ["bug_fix"],
                    },
                    {
                        "kind": "fact",
                        "subject": "decision",
                        "content": "use vitest in this repo",
                        "tags": ["decision"],
                    },
                ]
            }

        payload = {
            "hook_event_name": "postToolUseFailure",
            "tool_name": "Shell",
            "error_message": "FAIL src/add.test.ts Expected 2, got 3",
            "cwd": str(Path.cwd()),
        }
        with patch.object(capture, "mcp_call", side_effect=fake_call):
            with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                extra = capture.handle_post_tool_use_failure(payload)
        self.assertEqual([name for name, _ in calls], ["memory_recall"])
        args = calls[0][1]
        self.assertEqual(args["k"], 3)
        self.assertFalse(args["verbose"])
        self.assertIn("Shell", args["query"])
        self.assertIn("Expected 2", args["query"])
        self.assertNotIn("filters", args)
        self.assertNotIn("context_commit", [name for name, _ in calls])
        ctx = extra["additional_context"]
        self.assertIn("## Recalled", ctx)
        self.assertIn("npm test", ctx)
        self.assertIn("pin jest", ctx)
        self.assertNotIn("leaked-token-value", ctx)
        # Preferred bug_fix / decision-like hits come first.
        self.assertLess(ctx.index("npm test"), ctx.index("use vitest"))
        self.assertLess(ctx.index("use vitest"), ctx.index("unrelated note"))
        self.assertLessEqual(len(ctx), capture.MAX_FAILURE_RECALL_BLOCK_CHARS)

    def test_empty_or_unbound_skips_injection(self) -> None:
        payload = {
            "tool_name": "Shell",
            "error_message": "boom",
            "cwd": str(Path.cwd()),
        }
        with patch.object(capture, "resolve_token", return_value=None):
            with patch.object(capture, "mcp_call", side_effect=AssertionError("network")):
                self.assertEqual(capture.handle_post_tool_use_failure(payload), {})
        with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
            with patch.object(capture, "mcp_call", return_value=None):
                self.assertEqual(capture.handle_post_tool_use_failure(payload), {})
            with patch.object(capture, "mcp_call", return_value={"records": []}):
                self.assertEqual(capture.handle_post_tool_use_failure(payload), {})
        self.assertEqual(
            capture.handle_post_tool_use_failure(
                {"tool_name": "Shell", "is_interrupt": True, "error_message": "canceled"}
            ),
            {},
        )

    def test_failed_post_tool_use_recalls_without_replacing_write(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            if name == "memory_recall":
                return {"hits": [{"content": "prior fix: clear node_modules"}]}
            if name == "memory_session_ensure":
                return {"session_id": "sess-1"}
            return {"session_id": "sess-1"}

        payload = {
            "tool_name": "Shell",
            "tool_input": {"command": "npm test"},
            "tool_output": {
                "exitCode": 1,
                "stderr": "FAIL src/add.test.ts\nExpected 2, got 3\n",
            },
            "cwd": str(Path.cwd()),
            "conversation_id": "conv-fail",
        }
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_failed_post_tool_use_recall(payload)
                        capture.ingest(
                            "Cursor postToolUse: `npm test` exit 1.",
                            fact="Cursor postToolUse: `npm test` exit 1.\nFAIL",
                            payload=payload,
                            token="oauth-from-connect",
                        )
        names = [name for name, _ in calls]
        self.assertIn("memory_recall", names)
        self.assertIn("context_commit", names)
        self.assertEqual(names.count("memory_recall"), 1)
        self.assertIn("additional_context", extra)
        self.assertIn("prior fix", extra["additional_context"])
        self.assertEqual(
            capture.handle_failed_post_tool_use_recall(
                {
                    "tool_name": "Shell",
                    "tool_input": {"command": "npm test"},
                    "tool_output": {"exitCode": 0, "stdout": "ok"},
                }
            ),
            {},
        )

    def test_format_recall_hits_caps_and_skips_empty(self) -> None:
        body = "ranking uses RRF. " + ("x" * 4000)
        ctx = capture.format_recall_hits(
            {
                "records": [
                    {"subject": "retrieval", "content": body},
                    {"content": "second hit"},
                    {"content": "third hit"},
                    {"content": "dropped by k"},
                ]
            }
        )
        self.assertIn("## Recalled", ctx)
        self.assertIn("retrieval", ctx)
        self.assertNotIn("dropped by k", ctx)
        self.assertNotIn("x" * 500, ctx)
        self.assertLessEqual(len(ctx), capture.MAX_FAILURE_RECALL_BLOCK_CHARS)
        self.assertEqual(capture.format_recall_hits({"records": []}), "")
        self.assertEqual(capture.format_recall_hits(None), "")


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
        self.assertNotIn("auto_recall", calls[0][1])

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
        self.assertNotIn("additional_context", extra)
        self.assertTrue(calls[0][1]["fresh"])
        self.assertTrue(calls[0][1]["auto_recall"])
        self.assertNotIn("user", calls[0][1])

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
                        extra = capture.handle_session_start(payload)
                        self.assertNotIn("additional_context", extra)
                        self.assertEqual(extra["env"][capture.CONVERSATION_ENV], "conv-offline")
                        self.assertNotIn(capture.SESSION_ENV, extra["env"])
                        self.assertEqual(
                            capture.handle_before_submit_prompt(payload),
                            {"continue": True},
                        )
                        self.assertEqual(capture.handle_after_agent_response(payload), {})
                        self.assertEqual(capture.handle_session_end(payload), {})


class SessionStartContextTests(unittest.TestCase):
    def test_soul_present_includes_additional_context(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {
                "session_id": "ts-soul",
                "soul": "Prefers terse diffs and fail-open hooks.",
                "soul_linked": True,
            }

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_session_start(
                            {"session_id": "conv-soul", "cwd": str(Path.cwd())}
                        )
        self.assertEqual(extra["env"][capture.SESSION_ENV], "ts-soul")
        self.assertIn("additional_context", extra)
        self.assertIn("Prefers terse diffs", extra["additional_context"])
        self.assertIn("## Soul", extra["additional_context"])
        self.assertLessEqual(len(extra["additional_context"]), capture.MAX_BOOTSTRAP_CHARS)
        self.assertTrue(calls[0][1]["fresh"])

    def test_playbook_header_is_truncated_and_named(self) -> None:
        body = "Step one: recall first.\n" + ("x" * 4000)

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            return {
                "session_id": "ts-pb",
                "soul": "",
                "playbook": {
                    "name": "Recall first",
                    "slug": "recall-first",
                    "body_md": body,
                },
            }

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_session_start(
                            {"conversation_id": "conv-pb", "cwd": str(Path.cwd())}
                        )
        ctx = extra["additional_context"]
        self.assertIn("## Playbook: Recall first", ctx)
        self.assertIn("Step one: recall first.", ctx)
        self.assertLess(len(ctx), len(body))
        self.assertLessEqual(len(ctx), capture.MAX_BOOTSTRAP_CHARS)
        self.assertNotIn("x" * 2000, ctx)

    def test_empty_soul_and_no_playbook_omits_filler(self) -> None:
        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            return {
                "session_id": "ts-empty",
                "soul": "   ",
                "soul_linked": True,
                "playbook": {},
                "records": [{"content": "do-not-dump-recall"}],
                "skills": [{"name": "full-library"}],
                "turns": [{"role": "user", "content": "raw transcript"}],
            }

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_session_start(
                            {"conversation_id": "conv-empty", "cwd": str(Path.cwd())}
                        )
        self.assertEqual(extra["env"][capture.SESSION_ENV], "ts-empty")
        self.assertNotIn("additional_context", extra)
        self.assertEqual(
            capture.bootstrap_additional_context(
                {
                    "session_id": "ts-empty",
                    "soul": "",
                    "records": [{"content": "do-not-dump-recall"}],
                    "skills": [{"name": "full-library"}],
                    "turns": [{"role": "user", "content": "raw transcript"}],
                }
            ),
            "",
        )

    def test_mcp_failure_fail_open(self) -> None:
        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            return None

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_session_start(
                            {"session_id": "conv-fail", "cwd": str(Path.cwd())}
                        )
        self.assertNotIn("additional_context", extra)
        self.assertEqual(extra["env"][capture.CONVERSATION_ENV], "conv-fail")
        self.assertNotIn(capture.SESSION_ENV, extra["env"])

    def test_mcp_exception_fail_open(self) -> None:
        def boom(*_args, **_kwargs):
            raise RuntimeError("auth expired")

        payload = {"session_id": "conv-boom", "cwd": str(Path.cwd())}
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "ensure_session_payload", side_effect=boom):
                    extra = capture.handle_session_start(payload)
        self.assertEqual(extra["env"][capture.CONVERSATION_ENV], "conv-boom")
        self.assertNotIn("additional_context", extra)
        self.assertNotIn(capture.SESSION_ENV, extra["env"])

    def test_profile_included_when_present(self) -> None:
        ctx = capture.bootstrap_additional_context(
            {
                "session_id": "ts-profile",
                "soul": None,
                "profile": {"text": "Uses Connect; prefer keyword recall."},
            }
        )
        self.assertIn("## Profile", ctx)
        self.assertIn("Uses Connect", ctx)
        self.assertLessEqual(len(ctx), capture.MAX_BOOTSTRAP_CHARS)

    def test_bootstrap_unwraps_structured_content_and_redacts(self) -> None:
        ctx = capture.bootstrap_additional_context(
            {
                "structuredContent": {
                    "session_id": "ts-wrap",
                    "soul": "Keep secrets out. Bearer leaked-token-value",
                }
            }
        )
        self.assertIn("Keep secrets out", ctx)
        self.assertNotIn("leaked-token-value", ctx)
        self.assertIn("[redacted]", ctx)

    def test_bootstrap_respects_hard_cap(self) -> None:
        ctx = capture.bootstrap_additional_context({"soul": "A" * 8000})
        self.assertTrue(ctx)
        self.assertLessEqual(len(ctx), capture.MAX_BOOTSTRAP_CHARS)
        self.assertTrue(ctx.endswith("…"))

    def test_session_start_passes_title_and_prompt_anchors(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {"session_id": "ts-anchor"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        capture.handle_session_start(
                            {
                                "session_id": "conv-anchor",
                                "title": "Fix ranking",
                                "prompt": "why is RRF wrong in recall",
                                "cwd": str(Path.cwd()),
                            }
                        )
        self.assertTrue(calls[0][1]["auto_recall"])
        self.assertEqual(calls[0][1]["topic"], "Fix ranking")
        self.assertIn("why is RRF wrong", calls[0][1]["user"])

    def test_auto_recall_records_folded_into_additional_context(self) -> None:
        body = "ranking uses RRF then repo boost. " + ("x" * 4000)
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL):
            calls.append((name, arguments))
            return {
                "session_id": "ts-recall",
                "soul": "",
                "auto_recall": {
                    "skipped": False,
                    "records": [
                        {"subject": "retrieval", "content": body},
                        {"subject": "caps", "content": "k=5 on the server"},
                    ],
                },
            }

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="oauth-from-connect"):
                        extra = capture.handle_session_start(
                            {
                                "conversation_id": "conv-recall",
                                "title": "retrieval",
                                "cwd": str(Path.cwd()),
                            }
                        )
        ctx = extra["additional_context"]
        self.assertTrue(calls[0][1]["auto_recall"])
        self.assertEqual(calls[0][1]["topic"], "retrieval")
        self.assertIn("## Recalled", ctx)
        self.assertIn("retrieval", ctx)
        self.assertIn("RRF", ctx)
        self.assertIn("k=5", ctx)
        self.assertNotIn("x" * 500, ctx)
        self.assertLessEqual(len(ctx), capture.MAX_BOOTSTRAP_CHARS)

    def test_auto_recall_hits_key_and_skipped(self) -> None:
        self.assertIn(
            "compact hit",
            capture.format_auto_recall_hits(
                {"auto_recall": {"hits": [{"content": "compact hit"}]}}
            ),
        )
        self.assertEqual(
            capture.format_auto_recall_hits(
                {"auto_recall": {"skipped": True, "records": [{"content": "nope"}]}}
            ),
            "",
        )
        self.assertEqual(capture.format_auto_recall_hits({"session_id": "old"}), "")
        self.assertEqual(
            capture.bootstrap_additional_context(
                {
                    "session_id": "ts-empty",
                    "soul": "",
                    "auto_recall": {
                        "skipped": True,
                        "reason": "missing_query",
                        "records": [],
                    },
                }
            ),
            "",
        )


def _git_repo(body: str | None) -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    if body is not None:
        path = root / ".teamshared" / "org"
        path.parent.mkdir(parents=True)
        path.write_text(body, encoding="utf-8")
    return tmp, root


class OrgBindingCaptureTests(unittest.TestCase):
    def _ensure_url(self, repo: Path) -> str:
        calls: list[str | None] = []

        def fake_call(
            name: str, arguments: dict, token: str, url: str | None = None
        ):
            calls.append(url)
            return {"session_id": "sess-org"}

        payload = {"conversation_id": "conv-org", "cwd": str(repo)}
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = Path(cache_dir) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(
                        capture, "resolve_token", return_value="oauth-from-connect"
                    ):
                        sid = capture.ensure_session(
                            payload, fresh=True, token="oauth-from-connect"
                        )
        self.assertEqual(sid, "sess-org")
        self.assertEqual(len(calls), 1)
        return calls[0] or ""

    def test_bound_repo_captures_into_org(self) -> None:
        tmp, root = _git_repo('{"v": 1, "slug": "sapien"}')
        with tmp:
            self.assertEqual(
                capture.resolve_mcp_url({"cwd": str(root)}),
                "https://teamshared.com/o/sapien/mcp",
            )
            self.assertEqual(
                self._ensure_url(root), "https://teamshared.com/o/sapien/mcp"
            )

    def test_unbound_repo_captures_into_default_org(self) -> None:
        tmp, root = _git_repo(None)
        with tmp:
            self.assertEqual(
                capture.resolve_mcp_url({"cwd": str(root)}),
                "https://teamshared.com/mcp",
            )
            self.assertEqual(self._ensure_url(root), "https://teamshared.com/mcp")

    def test_invalid_binding_fail_open_to_default(self) -> None:
        tmp, root = _git_repo("not a slug!!")
        with tmp:
            self.assertEqual(
                capture.resolve_mcp_url({"cwd": str(root)}),
                "https://teamshared.com/mcp",
            )


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
            "post_tool_use_failure.py",
            "pre_compact.py",
        ):
            self.assertTrue((HERE / script).is_file(), script)
        self.assertEqual(len(hooks["hooks"]["postToolUseFailure"]), 1)
        self.assertTrue(hooks["hooks"]["postToolUseFailure"][0]["command"])


if __name__ == "__main__":
    unittest.main()
