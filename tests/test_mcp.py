"""MCP tool dispatch (server transport not exercised — needs the mcp extra)."""

from __future__ import annotations

import json

from okf_kit.mcp import _dispatch


def test_dispatch_tools(built_bundle):
    bundles = {"acme": built_bundle}
    assert "acme" in _dispatch(bundles, "list_bundles", {})
    listing = _dispatch(bundles, "list_directory", {"bundle": "acme", "path": "/pages"})
    assert "home.md" in listing
    concept = _dispatch(bundles, "read_concept", {"bundle": "acme", "path": "/pages/docs/intro.md"})
    assert "type: Web Page" in concept
    hits = json.loads(_dispatch(bundles, "search_bundle", {"bundle": "acme", "query": "install"}))
    assert hits and "path" in hits[0]


def test_dispatch_unknown_bundle(built_bundle):
    out = _dispatch({"acme": built_bundle}, "read_concept", {"bundle": "nope", "path": "/x"})
    assert out.startswith("error:")
