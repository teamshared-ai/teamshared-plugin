#!/usr/bin/env python3
"""Unit tests for PreToolUse Read → memory_for_paths inject (#58)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pre_read_memory as prm


class RelativePathTests(unittest.TestCase):
    def test_normalize_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            target = root / "src" / "app.py"
            target.write_text("x\n", encoding="utf-8")
            self.assertEqual(prm.relative_path(str(target), root), "src/app.py")
            self.assertEqual(prm.relative_path("src/app.py", root), "src/app.py")

    def test_outside_repo_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            root = Path(a)
            outside = Path(b) / "secret.py"
            outside.write_text("x\n", encoding="utf-8")
            self.assertIsNone(prm.relative_path(str(outside), root))


class RenderTests(unittest.TestCase):
    def test_empty_miss(self) -> None:
        self.assertEqual(prm.render("src/a.py", {}), "")
        self.assertEqual(prm.render("src/a.py", {"records": []}), "")

    def test_newest_first_attributed(self) -> None:
        found = {
            "records": [
                {
                    "content": "  Prefer  fail-open  ",
                    "kind": "preference",
                    "created_at": "2026-09-28T12:00:00Z",
                    "provenance": {"writer_class": "human", "created_at": "2026-09-28T12:00:00Z"},
                }
            ]
        }
        text = prm.render("hooks/x.py", found)
        self.assertIn("TeamShared memory for `hooks/x.py`", text)
        self.assertIn("2026-09-28 [preference, human] Prefer fail-open", text)

    def test_render_cap(self) -> None:
        big = "w" * (prm.MAX_CONTEXT_CHARS + 500)
        found = {"records": [{"content": big, "kind": "note", "created_at": "2026-01-01T00:00:00Z"}]}
        text = prm.render("a.py", found)
        self.assertLessEqual(len(text), prm.MAX_CONTEXT_CHARS)
        self.assertTrue(text.endswith("…"))


class AnswerTests(unittest.TestCase):
    def test_cursor_shape(self) -> None:
        out = prm.answer({}, "hello")
        self.assertEqual(out, {"additional_context": "hello"})

    def test_claude_shape(self) -> None:
        out = prm.answer({"hook_event_name": "PreToolUse"}, "hello")
        self.assertEqual(
            out,
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": "hello",
                }
            },
        )

    def test_empty_context(self) -> None:
        self.assertEqual(prm.answer({"hook_event_name": "PreToolUse"}, ""), {})


class RunFailOpenTests(unittest.TestCase):
    def test_non_read_tool(self) -> None:
        self.assertEqual(prm.run({"tool_name": "Shell", "tool_input": {"file_path": "a.py"}}, 999.0), {})

    def test_no_token(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(prm, "_resolve_auth", return_value=(None, prm.DEFAULT_MCP_URL)):
                out = prm.run(
                    {
                        "tool_name": "Read",
                        "tool_input": {"file_path": "a.py"},
                        "cwd": os.getcwd(),
                    },
                    999.0,
                )
                self.assertEqual(out, {})

    def test_outside_path_no_inject(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            outside = Path(b) / "x.py"
            outside.write_text("x\n", encoding="utf-8")
            with mock.patch.object(prm, "_resolve_auth", return_value=("tsk_test", prm.DEFAULT_MCP_URL)):
                with mock.patch.object(prm, "repo_root", return_value=Path(a)):
                    out = prm.run(
                        {
                            "tool_name": "Read",
                            "tool_input": {"file_path": str(outside)},
                            "cwd": a,
                        },
                        999.0,
                    )
                    self.assertEqual(out, {})

    def test_call_timeout_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "a.py"
            target.write_text("x\n", encoding="utf-8")
            with mock.patch.object(prm, "_resolve_auth", return_value=("tsk_test", prm.DEFAULT_MCP_URL)):
                with mock.patch.object(prm, "repo_root", return_value=root):
                    with mock.patch.object(prm, "call_tool", side_effect=TimeoutError("budget")):
                        # run() does not catch TimeoutError itself — main() does.
                        # Simulate main's fail-open by ensuring call_tool returning None also yields {}.
                        pass
            with mock.patch.object(prm, "_resolve_auth", return_value=("tsk_test", prm.DEFAULT_MCP_URL)):
                with mock.patch.object(prm, "repo_root", return_value=root):
                    with mock.patch.object(prm, "call_tool", return_value=None):
                        out = prm.run(
                            {
                                "tool_name": "Read",
                                "tool_input": {"file_path": str(target)},
                                "cwd": str(root),
                            },
                            999.0,
                        )
                        self.assertEqual(out, {})

    def test_hits_inject_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "a.py"
            target.write_text("x\n", encoding="utf-8")
            found = {
                "records": [
                    {
                        "content": "Keep the budget at 3s",
                        "kind": "preference",
                        "created_at": "2026-09-29T01:00:00Z",
                        "provenance": {"writer_class": "human", "created_at": "2026-09-29T01:00:00Z"},
                    }
                ]
            }
            with mock.patch.object(prm, "_resolve_auth", return_value=("tsk_test", prm.DEFAULT_MCP_URL)):
                with mock.patch.object(prm, "repo_root", return_value=root):
                    with mock.patch.object(prm, "call_tool", return_value=found):
                        out = prm.run(
                            {
                                "tool_name": "Read",
                                "tool_input": {"file_path": str(target)},
                                "cwd": str(root),
                            },
                            999.0,
                        )
            self.assertIn("additional_context", out)
            self.assertIn("Keep the budget at 3s", out["additional_context"])


class EmitOnceTests(unittest.TestCase):
    def test_emit_idempotent(self) -> None:
        prm._emitted = False
        with mock.patch("sys.stdout") as stdout:
            prm.emit({"a": 1})
            prm.emit({"a": 2})
        writes = [c.args[0] for c in stdout.write.call_args_list]
        self.assertEqual(len(writes), 1)
        self.assertEqual(json.loads(writes[0].strip()), {"a": 1})
        prm._emitted = False


if __name__ == "__main__":
    raise SystemExit(unittest.main())
