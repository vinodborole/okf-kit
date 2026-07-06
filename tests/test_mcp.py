"""MCP tool dispatch + stdio hygiene."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from okf_kit.mcp import _dispatch

try:
    import mcp  # noqa: F401

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


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


@pytest.mark.skipif(not HAS_MCP, reason="needs the mcp extra")
def test_serve_mcp_keeps_stdout_clean(fixture_site, okf_home):
    """The startup banner must go to stderr — stdout is the JSON-RPC channel,
    so any non-JSON byte on it corrupts the protocol stream."""
    from okf_kit.config import bundles_dir
    from okf_kit.crawl import build_bundle

    build_bundle(fixture_site, output=str(bundles_dir() / "acme"), max_pages=50)
    proc = subprocess.Popen(
        [sys.executable, "-c", "from okf_kit.cli import main; import sys; sys.exit(main())",
         "serve-mcp", "acme"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        # empty stdin → EOF ends the stdio read loop and the server exits
        out, err = proc.communicate(input="", timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
    assert "serving" in err          # banner on stderr
    assert "serving" not in out      # stdout reserved for JSON-RPC
