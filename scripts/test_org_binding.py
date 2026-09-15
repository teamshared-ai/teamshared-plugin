#!/usr/bin/env python3
"""Unit tests for the D1 org-binding contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from org_binding import (
    BINDING_RELATIVE,
    DEFAULT_MCP_URL,
    BindingError,
    org_mcp_url,
    parse_org_binding_text,
    resolve_org_binding,
)


class ParseTests(unittest.TestCase):
    def test_json_preferred(self) -> None:
        self.assertEqual(
            parse_org_binding_text('{"v": 1, "slug": "Sapien"}'),
            "sapien",
        )

    def test_json_default_version(self) -> None:
        self.assertEqual(parse_org_binding_text('{"slug": "acme"}'), "acme")

    def test_plaintext_slug(self) -> None:
        self.assertEqual(parse_org_binding_text("  Sapien \n"), "sapien")

    def test_key_value_with_comment(self) -> None:
        text = "# bind this repo\nslug=my-org\n"
        self.assertEqual(parse_org_binding_text(text), "my-org")

    def test_rejects_unknown_json_key(self) -> None:
        with self.assertRaises(BindingError):
            parse_org_binding_text('{"slug": "sapien", "url": "https://x"}')

    def test_rejects_bad_slug(self) -> None:
        for raw in ("", "SAP IEN", "../x", "https://teamshared.com/o/a/mcp"):
            with self.subTest(raw=raw):
                with self.assertRaises(BindingError):
                    parse_org_binding_text(raw)

    def test_rejects_unsupported_version(self) -> None:
        with self.assertRaises(BindingError):
            parse_org_binding_text('{"v": 2, "slug": "sapien"}')


class ResolveTests(unittest.TestCase):
    def _repo(self, body: str | None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        if body is not None:
            path = root / BINDING_RELATIVE
            path.parent.mkdir(parents=True)
            path.write_text(body, encoding="utf-8")
        return root

    def test_missing_is_unbound(self) -> None:
        binding = resolve_org_binding(self._repo(None))
        self.assertFalse(binding.bound)
        self.assertIsNone(binding.slug)
        self.assertEqual(binding.url, DEFAULT_MCP_URL)
        self.assertIsNone(binding.error)

    def test_json_file_binds(self) -> None:
        binding = resolve_org_binding(
            self._repo(json.dumps({"v": 1, "slug": "sapien"}))
        )
        self.assertTrue(binding.bound)
        self.assertEqual(binding.slug, "sapien")
        self.assertEqual(binding.url, org_mcp_url("sapien"))
        self.assertIsNone(binding.error)

    def test_invalid_fail_open(self) -> None:
        binding = resolve_org_binding(self._repo("not a slug!!"))
        self.assertFalse(binding.bound)
        self.assertEqual(binding.url, DEFAULT_MCP_URL)
        self.assertIsNotNone(binding.error)

    def test_invalid_strict_raises(self) -> None:
        root = self._repo("not a slug!!")
        with self.assertRaises(BindingError):
            resolve_org_binding(root, strict=True)

    def test_derived_url_shape(self) -> None:
        self.assertEqual(
            org_mcp_url("sapien"),
            "https://teamshared.com/o/sapien/mcp",
        )


if __name__ == "__main__":
    unittest.main()
