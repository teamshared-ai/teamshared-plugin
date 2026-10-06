#!/usr/bin/env python3
"""Unit tests for Claude Code TeamShared hooks. No network."""

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
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "SessionEnd",
    "PostToolUseFailure",
    "PreCompact",
    "SubagentStart",
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
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test -- --runInBand"},
            "error": "Exit code 1\nFAIL src/add.test.ts\nExpected 2, got 3\n",
        }
        self.assertTrue(capture.is_shell_tool(payload))
        fact = capture.failed_tool_fact(payload)
        self.assertIn("npm test", fact)
        self.assertIn("exit 1", fact)
        self.assertIn("Expected 2, got 3", fact)
        self.assertTrue(fact.startswith("Claude PostToolUseFailure:"))
        self.assertLess(len(fact), 1200)

    def test_skips_non_shell_tools(self) -> None:
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "foo"},
            "error": "Exit code 1",
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
        self.assertTrue(fact.startswith("Claude PostToolUseFailure:"))


class PreCompactTests(unittest.TestCase):
    def test_short_summary(self) -> None:
        payload = {"trigger": "auto", "custom_instructions": None}
        summary = capture.precompact_summary(payload)
        self.assertIn("PreCompact", summary)
        self.assertIn("auto", summary)
        self.assertLess(len(summary), 400)


class ConversationMappingTests(unittest.TestCase):
    def test_conversation_id_from_claude_session(self) -> None:
        self.assertEqual(capture.conversation_id({"session_id": "claude-sess"}), "claude-sess")
        self.assertEqual(capture.session_topic("claude-sess"), "claude:claude-sess")
        self.assertEqual(capture.session_topic(None), "claude")

    def test_maps_conversation_to_teamshared_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            payload = {"session_id": "claude-abc", "cwd": str(Path.cwd())}
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
                self.assertEqual(calls[0][1]["topic"], "claude:claude-abc")
                self.assertTrue(calls[0][1]["fresh"])
                self.assertEqual(capture.mapped_session_id("claude-abc"), "ts-sess-1")

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
                "session_id": "claude-9",
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
        self.assertEqual(calls[0][1]["topic"], "claude:claude-9")
        self.assertNotIn("auto_recall", calls[0][1])

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
                "session_id": "claude-9",
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
                                "session_id": "claude-new",
                                "source": "startup",
                                "cwd": str(Path.cwd()),
                            }
                        )
        output = extra["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("1.31.0", output["additionalContext"])
        self.assertIn("memory_changes_since", output["additionalContext"])
        self.assertIn("memory_session_ensure", output["additionalContext"])
        self.assertIn("work_id", output["additionalContext"])
        self.assertTrue(calls[0][1]["fresh"])
        self.assertTrue(calls[0][1]["auto_recall"])
        self.assertNotIn("user", calls[0][1])
        self.assertLess(len(output["additionalContext"]), 10000)

    def test_session_start_passes_title_and_prompt_anchors(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "ts-anchor"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        capture.handle_session_start(
                            {
                                "session_id": "claude-anchor",
                                "source": "startup",
                                "title": "Fix ranking",
                                "prompt": "why is RRF wrong in recall",
                                "cwd": str(Path.cwd()),
                            }
                        )
        self.assertTrue(calls[0][1]["auto_recall"])
        self.assertEqual(calls[0][1]["topic"], "Fix ranking")
        self.assertIn("why is RRF wrong", calls[0][1]["user"])

    def test_session_start_folds_auto_recall_hits(self) -> None:
        body = "ranking uses RRF then repo boost. " + ("x" * 4000)

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            return {
                "session_id": "ts-recall",
                "auto_recall": {
                    "skipped": False,
                    "records": [
                        {"subject": "retrieval", "content": body},
                    ],
                },
            }

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        extra = capture.handle_session_start(
                            {
                                "session_id": "claude-recall",
                                "source": "startup",
                                "title": "retrieval",
                                "cwd": str(Path.cwd()),
                            }
                        )
        ctx = extra["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1.31.0", ctx)
        self.assertIn("## Recalled", ctx)
        self.assertIn("retrieval", ctx)
        self.assertIn("RRF", ctx)
        self.assertNotIn("x" * 500, ctx)
        self.assertLess(len(ctx), 10000)

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

    def test_stop_failure_appends_system_note(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        capture.handle_stop_failure(
                            {
                                "session_id": "claude-9",
                                "error": "rate_limit",
                                "error_details": "429 Too Many Requests",
                                "cwd": str(Path.cwd()),
                            }
                        )
        names = [name for name, _ in calls]
        self.assertIn("memory_session_append", names)
        self.assertNotIn("memory_session_close", names)
        append = next(args for name, args in calls if name == "memory_session_append")
        self.assertEqual(append["role"], "system")
        self.assertIn("rate_limit", append["content"])

    def test_session_end_closes_and_distills(self) -> None:
        calls: list[tuple[str, dict]] = []

        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            calls.append((name, arguments))
            return {"session_id": "sess-1"}

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            cache.write_text(json.dumps({"conversations": {"claude-9": {"session_id": "sess-1"}}}))
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                        capture.handle_session_end(
                            {
                                "session_id": "claude-9",
                                "reason": "other",
                                "cwd": str(Path.cwd()),
                            }
                        )
                self.assertIsNone(capture.mapped_session_id("claude-9"))
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
                            "Claude PostToolUseFailure: `npm test` exit 1.",
                            fact="Claude PostToolUseFailure: `npm test` exit 1.\nFAIL",
                            payload={"cwd": str(Path.cwd()), "session_id": "claude-tool"},
                            token="tsk_testtoken",
                        )
        self.assertTrue(ok)
        names = [name for name, _ in calls]
        self.assertEqual(names, ["memory_session_ensure", "context_commit"])
        commit = calls[1][1]
        self.assertEqual(commit["facts"][0]["kind"], "event")
        self.assertIn("claude", commit["facts"][0]["tags"])
        self.assertNotIn("tsk_", json.dumps(commit))

    def test_handlers_without_token_do_not_touch_network(self) -> None:
        def boom(*_args, **_kwargs):
            raise AssertionError("network")

        payload = {
            "session_id": "claude-offline",
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

    def test_resolve_token_ignores_cursor_store(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(capture.resolve_token())
        with patch.dict(os.environ, {"TEAMSHARED_TOKEN": "tsk_fromenv"}, clear=True):
            self.assertEqual(capture.resolve_token(), "tsk_fromenv")


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
            name: str,
            arguments: dict,
            token: str,
            url: str | None = None,
            timeout: float = 6,
        ):
            calls.append(url)
            return {"session_id": "sess-org"}

        payload = {"session_id": "claude-org", "cwd": str(repo)}
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = Path(cache_dir) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                with patch.object(capture, "mcp_call", side_effect=fake_call):
                    with patch.object(
                        capture, "resolve_token", return_value="tsk_testtoken"
                    ):
                        sid = capture.ensure_session(
                            payload, fresh=True, token="tsk_testtoken"
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


def _no_network(*_args, **_kwargs):
    raise AssertionError("SubagentStart must not touch the network")


class SubagentStartTests(unittest.TestCase):
    """#66: SubagentStart injects protocol + parent's cached recall, offline."""

    def _session_start_with_recall(self, cid: str, records: list[dict]) -> None:
        def fake_call(name: str, arguments: dict, token: str, url: str = capture.MCP_URL, timeout: float = 6):
            return {
                "session_id": "ts-parent",
                "auto_recall": {"skipped": False, "records": records},
            }

        with patch.object(capture, "mcp_call", side_effect=fake_call):
            with patch.object(capture, "resolve_token", return_value="tsk_testtoken"):
                capture.handle_session_start(
                    {"session_id": cid, "source": "startup", "cwd": str(Path.cwd())}
                )

    def _subagent(self, cid: str | None) -> str:
        payload = {
            "hook_event_name": "SubagentStart",
            "agent_id": "agent-1",
            "agent_type": "Explore",
            "cwd": str(Path.cwd()),
        }
        if cid:
            payload["session_id"] = cid
        with patch.object(capture, "mcp_call", side_effect=_no_network):
            with patch.object(capture.urllib.request, "urlopen", side_effect=_no_network):
                with patch.object(capture, "resolve_token", side_effect=_no_network):
                    extra = capture.handle_subagent_start(payload)
        out = extra["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SubagentStart")
        return out["additionalContext"]

    def test_protocol_plus_cached_recall_for_known_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                self._session_start_with_recall(
                    "claude-parent",
                    [{"subject": "deploys", "content": "staging deploys run from main via Railway"}],
                )
                ctx = self._subagent("claude-parent")
                # Parent mapping untouched; no new TeamShared session.
                self.assertEqual(capture.mapped_session_id("claude-parent"), "ts-parent")
        self.assertTrue(ctx.startswith(capture.PROTOCOL_CONTEXT.rstrip()))
        self.assertIn("1.31.0", ctx)
        self.assertIn("## Subagent", ctx)
        self.assertIn("fresh=false", ctx)
        self.assertIn("## Recalled", ctx)
        self.assertIn("staging deploys run from main", ctx)
        self.assertLess(len(ctx), 10000)

    def test_protocol_only_when_no_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                ctx = self._subagent("claude-unknown")
                ctx_no_id = self._subagent(None)
                self.assertFalse(cache.exists())
        self.assertEqual(ctx, capture.subagent_base_context())
        self.assertEqual(ctx_no_id, capture.subagent_base_context())
        self.assertIn(capture.PROTOCOL_CONTEXT.rstrip(), ctx)
        self.assertNotIn("## Recalled", ctx)

    def test_other_session_recall_does_not_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                self._session_start_with_recall(
                    "claude-a", [{"subject": "a-only", "content": "fact for session A"}]
                )
                ctx = self._subagent("claude-b")
        self.assertNotIn("fact for session A", ctx)

    def test_oversized_recall_trimmed_protocol_intact(self) -> None:
        huge = "## Recalled\n" + "\n".join(f"- hit {i}: " + ("y" * 120) for i in range(400))
        self.assertGreater(len(huge), 20000)
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                capture.store_recall_block("claude-big", huge)
                ctx = self._subagent("claude-big")
        self.assertLess(len(ctx), 10000)
        self.assertLessEqual(len(ctx), capture.MAX_ADDITIONAL_CONTEXT_CHARS)
        self.assertTrue(ctx.startswith(capture.subagent_base_context()))
        self.assertIn("## Recalled", ctx)
        self.assertIn("- hit 0:", ctx)
        self.assertTrue(ctx.endswith("…"))

    def test_fit_never_trims_protocol(self) -> None:
        base = "P" * 9600
        self.assertEqual(capture.fit_additional_context(base, "extra"), base)

    def test_cache_exception_falls_back_to_protocol(self) -> None:
        with patch.object(capture, "cached_recall_block", side_effect=RuntimeError("boom")):
            ctx = self._subagent("claude-parent")
        self.assertEqual(ctx, capture.subagent_base_context())

    def test_corrupt_cache_falls_back_to_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            cache.write_text("{not json", encoding="utf-8")
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                ctx = self._subagent("claude-parent")
            cache.write_text(json.dumps({"recall": {"claude-parent": 42}}), encoding="utf-8")
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                ctx2 = self._subagent("claude-parent")
        self.assertEqual(ctx, capture.subagent_base_context())
        self.assertEqual(ctx2, capture.subagent_base_context())

    def test_failed_session_start_keeps_last_good_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                self._session_start_with_recall(
                    "claude-resume", [{"subject": "kept", "content": "still here"}]
                )
                with patch.object(capture, "mcp_call", return_value=None):
                    with patch.object(capture, "resolve_token", return_value=None):
                        capture.handle_session_start(
                            {"session_id": "claude-resume", "source": "resume"}
                        )
                ctx = self._subagent("claude-resume")
        self.assertIn("still here", ctx)

    def test_session_end_drops_cached_recall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                capture.store_recall_block("claude-end", "## Recalled\n- x")
                self.assertTrue(capture.cached_recall_block("claude-end"))
                capture.drop_mapped_session("claude-end")
                self.assertEqual(capture.cached_recall_block("claude-end"), "")

    def test_recall_cache_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            with patch.dict(os.environ, {capture.HOOK_CACHE_ENV: str(cache)}, clear=False):
                for i in range(capture.MAX_CACHED_RECALL_SESSIONS + 5):
                    capture.store_recall_block(f"c{i}", f"## Recalled\n- {i}")
                data = json.loads(cache.read_text())
        self.assertEqual(len(data["recall"]), capture.MAX_CACHED_RECALL_SESSIONS)
        self.assertNotIn("c0", data["recall"])

    def test_script_exits_zero_on_bad_input_and_corrupt_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "sessions.json"
            cache.write_text("garbage", encoding="utf-8")
            env = dict(os.environ)
            env[capture.HOOK_CACHE_ENV] = str(cache)
            env.pop("TEAMSHARED_TOKEN", None)
            env.pop("TEAMSHARED_STATE_TOKEN", None)
            for stdin in ("not json", json.dumps({"session_id": "x", "agent_type": "Plan"}), ""):
                proc = subprocess.run(
                    [sys.executable, str(HERE / "subagent_start.py")],
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                out = json.loads(proc.stdout)
                ctx = out["hookSpecificOutput"]["additionalContext"]
                self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SubagentStart")
                self.assertIn("1.31.0", ctx)
                self.assertLess(len(ctx), 10000)

    def test_handler_exception_still_exits_zero(self) -> None:
        import io

        buf = io.StringIO()
        with patch.object(capture, "subagent_base_context", side_effect=RuntimeError("boom")):
            with patch.object(capture.sys, "stdin", io.StringIO("{}")):
                with patch.object(capture.sys, "stdout", buf):
                    code = capture.run_hook(capture.handle_subagent_start)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {})


class HooksManifestTests(unittest.TestCase):
    def test_registers_official_claude_events(self) -> None:
        hooks = json.loads((HERE / "hooks.json").read_text())
        events = set(hooks["hooks"])
        self.assertEqual(events, REQUIRED_HOOKS)
        matcher = hooks["hooks"]["PostToolUseFailure"][0]["matcher"]
        self.assertEqual(matcher, "Bash|PowerShell")
        self.assertNotIn("tsk_", json.dumps(hooks))
        for name in REQUIRED_HOOKS:
            handler = hooks["hooks"][name][0]["hooks"][0]
            self.assertEqual(handler["type"], "command")
            self.assertEqual(handler["command"], "python3")
            self.assertTrue(handler["args"][0].endswith(".py"))
            self.assertIn("CLAUDE_PLUGIN_ROOT", handler["args"][0])
        for script in (
            "session_start.py",
            "user_prompt_submit.py",
            "stop.py",
            "stop_failure.py",
            "session_end.py",
            "post_tool_use_failure.py",
            "pre_compact.py",
            "subagent_start.py",
        ):
            self.assertTrue((HERE / script).is_file(), script)
        subagent = hooks["hooks"]["SubagentStart"][0]
        self.assertNotIn("matcher", subagent)
        self.assertEqual(subagent["hooks"][0]["timeout"], 10)
        self.assertTrue(subagent["hooks"][0]["args"][0].endswith("/subagent_start.py"))
        self.assertEqual(capture.PROTOCOL_VERSION, "1.31.0")
        self.assertIn("1.31.0", capture.PROTOCOL_CONTEXT)
        self.assertIn("memory_changes_since", capture.PROTOCOL_CONTEXT)
        self.assertIn("org_list", capture.PROTOCOL_CONTEXT)
        self.assertIn("org_context_get", capture.PROTOCOL_CONTEXT)
        self.assertIn("org_bind", capture.PROTOCOL_CONTEXT)
        self.assertIn("org_unbind", capture.PROTOCOL_CONTEXT)
        self.assertIn("scope=conversation", capture.PROTOCOL_CONTEXT)
        self.assertIn("optional fallback", capture.PROTOCOL_CONTEXT)
        self.assertLess(len(capture.PROTOCOL_CONTEXT), 10000)


if __name__ == "__main__":
    unittest.main()
