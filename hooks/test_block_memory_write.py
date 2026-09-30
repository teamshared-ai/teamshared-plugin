#!/usr/bin/env python3
"""Unit tests for PreToolUse Write|Edit MEMORY.md block (#62)."""

from __future__ import annotations

import json
import unittest
from unittest import mock

import block_memory_write as bmw


class PathMatchTests(unittest.TestCase):
    def test_memory_md_blocked(self) -> None:
        for path in (
            "MEMORY.md",
            "docs/MEMORY.md",
            "/abs/repo/MEMORY.md",
            ".claude/MEMORY.md",
            ".claude/projects/x/MEMORY.md",
            ".cursor/MEMORY.md",
            ".cursor/rules/MEMORY.md",
        ):
            self.assertTrue(bmw.is_blocked_path(path), path)

    def test_claude_memory_dir_blocked(self) -> None:
        for path in (
            ".claude/memory/foo.md",
            ".claude/memory/notes.txt",
            "proj/.claude/memory/x.md",
            "/abs/.claude/memory/x",
            ".claude/memory",
        ):
            self.assertTrue(bmw.is_blocked_path(path), path)

    def test_ordinary_paths_allowed(self) -> None:
        for path in (
            "src/x.py",
            "README.md",
            "memory.md",  # case-sensitive: not MEMORY.md
            "MEMORY.MD",
            ".claude/settings.json",
            ".claude/memories/foo.md",  # not .claude/memory/
            "",
            None,
        ):
            self.assertFalse(bmw.is_blocked_path(path), path)  # type: ignore[arg-type]


class DecideTests(unittest.TestCase):
    def test_write_memory_denied_cursor(self) -> None:
        out, denied = bmw.decide(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "MEMORY.md", "content": "x"},
            }
        )
        self.assertTrue(denied)
        self.assertEqual(out.get("permission"), "deny")
        self.assertIn("memory_remember", out.get("agent_message", ""))

    def test_edit_claude_memory_denied(self) -> None:
        out, denied = bmw.decide(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": ".claude/memory/foo.md"},
            }
        )
        self.assertTrue(denied)
        hso = out.get("hookSpecificOutput") or {}
        self.assertEqual(hso.get("permissionDecision"), "deny")
        self.assertIn("memory_remember", hso.get("permissionDecisionReason", ""))

    def test_multiedit_blocked(self) -> None:
        out, denied = bmw.decide(
            {
                "tool_name": "MultiEdit",
                "tool_input": {"file_path": "lib/MEMORY.md", "edits": []},
            }
        )
        self.assertTrue(denied)
        self.assertEqual(out.get("permission"), "deny")

    def test_ordinary_write_allowed(self) -> None:
        out, denied = bmw.decide(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "src/x.py", "content": "x"},
            }
        )
        self.assertFalse(denied)
        self.assertEqual(out.get("permission"), "allow")

    def test_missing_path_allowed(self) -> None:
        out, denied = bmw.decide({"tool_name": "Write", "tool_input": {}})
        self.assertFalse(denied)
        self.assertEqual(out.get("permission"), "allow")

    def test_non_write_tool_allowed(self) -> None:
        out, denied = bmw.decide(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "MEMORY.md"},
            }
        )
        self.assertFalse(denied)

    def test_parse_garbage_fail_open(self) -> None:
        out, denied = bmw.decide(None)  # type: ignore[arg-type]
        self.assertFalse(denied)
        self.assertEqual(out, {})

    def test_path_key_variants(self) -> None:
        for key in ("file_path", "path", "target_file"):
            out, denied = bmw.decide(
                {"tool_name": "Write", "tool_input": {key: "MEMORY.md"}}
            )
            self.assertTrue(denied, key)


class MainFailOpenTests(unittest.TestCase):
    def test_invalid_json_stdin_allows(self) -> None:
        with mock.patch("sys.stdin") as stdin:
            stdin.read.return_value = "not-json{{"
            with mock.patch("sys.stdout") as stdout:
                code = bmw.main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
