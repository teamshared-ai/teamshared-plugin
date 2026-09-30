#!/usr/bin/env python3
"""Unit tests for PreCompact durable-facts nudge (#63)."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import durable_facts_nudge as dfn


class NudgeTextTests(unittest.TestCase):
    def test_under_cap_and_mentions_remember(self) -> None:
        text = dfn.nudge_text()
        self.assertLessEqual(len(text), dfn.MAX_NUDGE_CHARS)
        self.assertIn("memory_remember", text)
        self.assertIn("0–3", text)
        self.assertIn("constraints", text.lower())


class EmitGateTests(unittest.TestCase):
    def test_unbound_no_token(self) -> None:
        self.assertFalse(dfn.should_emit_nudge(token=None))
        self.assertFalse(dfn.should_emit_nudge(token=""))
        self.assertFalse(dfn.should_emit_nudge(token="   "))

    def test_bound_with_token(self) -> None:
        self.assertTrue(dfn.should_emit_nudge(token="tsk_test"))


class ComposeTests(unittest.TestCase):
    def test_cursor_nudge_only(self) -> None:
        out = dfn.precompact_extra("cursor", dfn.nudge_text())
        self.assertIn("user_message", out)
        self.assertNotIn("systemMessage", out)
        self.assertLessEqual(len(out["user_message"]), dfn.MAX_NUDGE_CHARS)

    def test_claude_nudge_only(self) -> None:
        out = dfn.precompact_extra("claude", dfn.nudge_text())
        self.assertIn("systemMessage", out)
        self.assertNotIn("user_message", out)

    def test_compose_with_constraints(self) -> None:
        constraints = "# TeamShared constraints\n- Prefer fail-open"
        out = dfn.precompact_extra("cursor", constraints, dfn.nudge_text())
        msg = out["user_message"]
        self.assertIn("# TeamShared constraints", msg)
        self.assertIn("memory_remember", msg)
        self.assertLess(msg.index("constraints"), msg.index("durable facts"))

    def test_empty(self) -> None:
        self.assertEqual(dfn.precompact_extra("cursor", "", ""), {})


class BuildExtraTests(unittest.TestCase):
    def test_unbound_no_nudge(self) -> None:
        out = dfn.build_precompact_extra("cursor", {}, token=None)
        self.assertEqual(out, {})

    def test_bound_nudge_under_cap(self) -> None:
        out = dfn.build_precompact_extra("cursor", {}, token="tok")
        self.assertIn("user_message", out)
        self.assertLessEqual(len(out["user_message"]), dfn.MAX_NUDGE_CHARS)
        self.assertIn("memory_remember", out["user_message"])

    def test_bound_composes_constraints(self) -> None:
        out = dfn.build_precompact_extra(
            "claude",
            {},
            token="tok",
            constraints="# TeamShared constraints\n- x",
        )
        msg = out["systemMessage"]
        self.assertIn("# TeamShared constraints", msg)
        self.assertIn("memory_remember", msg)


class RunIngestTests(unittest.TestCase):
    def test_summary_ingest_still_attempted(self) -> None:
        ingest_calls: list[object] = []

        class FakeCapture:
            @staticmethod
            def read_stdin_json():
                return {"trigger": "manual"}

            @staticmethod
            def precompact_summary(payload):
                return "session summary for ingest"

            @staticmethod
            def ingest(summary, payload=None):
                ingest_calls.append((summary, payload))

            @staticmethod
            def emit_ok(extra=None):
                FakeCapture.last_extra = extra or {}

            @staticmethod
            def resolve_token():
                return "tok"

        with mock.patch.dict("sys.modules", {"capture": FakeCapture}):
            # Re-import path uses import capture inside the function
            code = dfn.run_precompact_with_nudge(host="cursor")
        self.assertEqual(code, 0)
        self.assertEqual(len(ingest_calls), 1)
        self.assertEqual(ingest_calls[0][0], "session summary for ingest")
        self.assertIn("user_message", FakeCapture.last_extra)
        self.assertIn("memory_remember", FakeCapture.last_extra["user_message"])

    def test_unbound_skips_nudge_still_ingests(self) -> None:
        ingest_calls: list[object] = []

        class FakeCapture:
            @staticmethod
            def read_stdin_json():
                return {}

            @staticmethod
            def precompact_summary(payload):
                return "sum"

            @staticmethod
            def ingest(summary, payload=None):
                ingest_calls.append(summary)

            @staticmethod
            def emit_ok(extra=None):
                FakeCapture.last_extra = extra or {}

            @staticmethod
            def resolve_token():
                return None

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.dict("sys.modules", {"capture": FakeCapture}):
                code = dfn.run_precompact_with_nudge(host="claude")
        self.assertEqual(code, 0)
        self.assertEqual(ingest_calls, ["sum"])
        self.assertEqual(FakeCapture.last_extra, {})


if __name__ == "__main__":
    unittest.main()
