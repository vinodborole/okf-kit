"""Serve OKF bundles over MCP (`okf serve-mcp`) for Claude Code/Desktop, Cursor.

Exposes the bundle-navigation tools over stdio using the official `mcp`
package (okf-kit[mcp]). The tool logic is the same path-guarded primitives the
chat agent uses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .bundle_nav import list_directory, read_concept, search_bundle
from .config import bundles_dir
from .registry import resolve_bundle

_INSTALL_HINT = "MCP support needs the extra:  pip install 'okf-kit[mcp]'"


def _resolve_bundles(names: list[str], all_: bool) -> dict[str, Path]:
    if all_ or not names:
        found = {}
        for state in sorted(bundles_dir().glob("*/.okf-kit/state.json")):
            found[state.parent.parent.name] = state.parent.parent
        # also include an explicitly-passed local dir
        for n in names:
            p = Path(n)
            if (p / "index.md").exists():
                found[p.name] = p
        return found
    return {Path(resolve_bundle(n)).name: resolve_bundle(n) for n in names}


def serve_mcp(names: list[str], *, all_: bool = False) -> int:
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        raise SystemExit(_INSTALL_HINT) from None

    bundles = _resolve_bundles(names, all_)
    if not bundles:
        raise SystemExit("No bundles to serve. `okf get <name>` first, or pass a bundle directory.")

    server = Server("okf-kit")

    @server.list_tools()
    async def _tools() -> list["Tool"]:
        return [
            Tool(name="list_bundles", description="List available OKF bundles.",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="list_directory", description="List a directory inside a bundle.",
                 inputSchema={"type": "object", "properties": {
                     "bundle": {"type": "string"}, "path": {"type": "string"}},
                     "required": ["bundle", "path"]}),
            Tool(name="read_concept", description="Read a concept file from a bundle.",
                 inputSchema={"type": "object", "properties": {
                     "bundle": {"type": "string"}, "path": {"type": "string"}},
                     "required": ["bundle", "path"]}),
            Tool(name="search_bundle", description="Keyword search within a bundle.",
                 inputSchema={"type": "object", "properties": {
                     "bundle": {"type": "string"}, "query": {"type": "string"}},
                     "required": ["bundle", "query"]}),
        ]

    @server.call_tool()
    async def _call(name: str, arguments: dict) -> list["TextContent"]:
        return [TextContent(type="text", text=_dispatch(bundles, name, arguments))]

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    import asyncio

    # stdout is the JSON-RPC channel in a stdio MCP server — log to stderr only.
    print(
        f"okf serve-mcp: serving {len(bundles)} bundle(s): {', '.join(bundles)}",
        file=sys.stderr,
        flush=True,
    )
    asyncio.run(_run())
    return 0


def _dispatch(bundles: dict[str, Path], name: str, args: dict) -> str:
    """Tool dispatch, factored out so it's unit-testable without a live server."""
    if name == "list_bundles":
        return "\n".join(sorted(bundles)) or "(none)"
    bundle = args.get("bundle")
    if bundle not in bundles:
        return f"error: unknown bundle '{bundle}'. Available: {', '.join(sorted(bundles))}"
    d = bundles[bundle]
    if name == "list_directory":
        return list_directory(d, args.get("path", "/"))
    if name == "read_concept":
        return read_concept(d, args.get("path", "/index.md"))
    if name == "search_bundle":
        return json.dumps(search_bundle(d, args.get("query", ""), limit=5), indent=2)
    return f"error: unknown tool '{name}'"
