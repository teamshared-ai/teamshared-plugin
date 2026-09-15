#!/usr/bin/env python3
"""Canonical TeamShared repo org binding (D1).

D2 capture hooks and D3 ``org bind`` / ``org status`` must use this resolver
so every harness agrees on one file and one derived URL. This module does
not talk to MCP and does not write harness ``mcp.json`` / ``config.toml``.

Binding file: ``<repo>/.teamshared/org``

Accepted bodies:

* JSON ``{"v": 1, "slug": "sapien"}`` (``v`` optional, default 1)
* one-line slug ``sapien``
* ``slug=sapien`` (``#`` comments allowed)

Derived bound URL: ``https://teamshared.com/o/{slug}/mcp``
Unbound / fail-open URL: ``https://teamshared.com/mcp``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_MCP_URL = "https://teamshared.com/mcp"
ORG_MCP_URL_TEMPLATE = "https://teamshared.com/o/{slug}/mcp"
BINDING_RELATIVE = ".teamshared/org"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
MAX_BINDING_BYTES = 4096


class BindingError(ValueError):
    """Invalid binding contents. D3 bind should raise; D2 hooks fail open."""


@dataclass(frozen=True)
class OrgBinding:
    bound: bool
    slug: str | None
    url: str
    source: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def org_mcp_url(slug: str) -> str:
    normalized = normalize_slug(slug)
    return ORG_MCP_URL_TEMPLATE.format(slug=normalized)


def normalize_slug(raw: str) -> str:
    slug = raw.strip().lower()
    if not SLUG_RE.fullmatch(slug):
        raise BindingError(
            f"invalid org slug {raw!r}; expected {SLUG_RE.pattern}"
        )
    return slug


def parse_org_binding_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        raise BindingError("empty binding")

    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise BindingError(f"invalid binding JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise BindingError("binding JSON must be an object")
        extra = set(payload) - {"v", "slug"}
        if extra:
            raise BindingError(f"unknown binding keys: {sorted(extra)}")
        version = payload.get("v", 1)
        if version != 1:
            raise BindingError(f"unsupported binding version {version!r}")
        slug = payload.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            raise BindingError("binding JSON must include a non-empty slug")
        return normalize_slug(slug)

    slug_from_kv: str | None = None
    for line in stripped.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            raise BindingError("mixed JSON and text binding")
        if "=" in line:
            key, value = line.split("=", 1)
            if key.strip() != "slug":
                raise BindingError(f"unknown binding key {key.strip()!r}")
            if slug_from_kv is not None:
                raise BindingError("multiple slug lines")
            slug_from_kv = value
            continue
        if slug_from_kv is not None:
            raise BindingError("multiple slug lines")
        slug_from_kv = line
    if slug_from_kv is None:
        raise BindingError("no slug in binding")
    return normalize_slug(slug_from_kv)


def resolve_org_binding(
    repo_root: Path,
    *,
    strict: bool = False,
) -> OrgBinding:
    """Resolve ``.teamshared/org`` under ``repo_root``.

    ``strict=False`` (D2): missing or invalid → unbound ``/mcp``.
    ``strict=True`` (D3 bind/status on a file that should exist): raise
    ``BindingError`` for invalid contents. Missing file is still unbound.
    """
    root = Path(repo_root)
    path = root / BINDING_RELATIVE
    source = str(path)
    if not path.is_file():
        return OrgBinding(
            bound=False,
            slug=None,
            url=DEFAULT_MCP_URL,
            source=source,
            error=None,
        )
    try:
        data = path.read_bytes()
        if len(data) > MAX_BINDING_BYTES:
            raise BindingError(
                f"binding file exceeds {MAX_BINDING_BYTES} bytes"
            )
        slug = parse_org_binding_text(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, BindingError) as exc:
        if strict and path.is_file():
            raise BindingError(str(exc)) from exc
        return OrgBinding(
            bound=False,
            slug=None,
            url=DEFAULT_MCP_URL,
            source=source,
            error=str(exc),
        )
    return OrgBinding(
        bound=True,
        slug=slug,
        url=org_mcp_url(slug),
        source=source,
        error=None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve the TeamShared repo org binding (D1)."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Repository root that may contain .teamshared/org",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on an invalid binding file (D3). Default fail-open (D2).",
    )
    args = parser.parse_args(argv)
    try:
        binding = resolve_org_binding(Path(args.repo_root), strict=args.strict)
    except BindingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json.dump(binding.as_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
