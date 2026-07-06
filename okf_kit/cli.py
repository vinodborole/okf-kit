"""Command-line interface for okf-kit.

    okf build <url>       crawl a site into an OKF bundle
    okf validate <dir>    OKF v0.1 conformance check
    okf zip <dir>         package a bundle for hand-off
    okf sync <dir>        incrementally update a bundle            (M2)
    okf list / get        registry                                 (M3)
    okf chat / visualize / serve-mcp   consume a bundle            (M3)
"""

from __future__ import annotations

import argparse
import sys

from . import __version__

_LATER: dict[str, str] = {}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okf",
        description="Turn any website into a portable, agent-ready OKF bundle.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    build = sub.add_parser("build", help="Crawl a site into an OKF bundle")
    build.add_argument("url", help="Root URL, e.g. https://docs.example.com")
    build.add_argument("-o", "--output", metavar="DIR", help="Bundle directory (default: ./<host>-okf)")
    build.add_argument("--max-depth", type=int, default=3, help="Max crawl depth (default: 3)")
    build.add_argument("--max-pages", type=int, default=200, help="Max pages (default: 200)")
    build.add_argument("--js", action="store_true", help="Render JavaScript (needs okf-kit[js])")
    build.add_argument("--no-robots", action="store_true", help="Ignore robots.txt")
    build.add_argument(
        "--path-prefix", metavar="PATH",
        help="Only crawl URLs under this path (default: auto — the seed's section)",
    )
    build.add_argument(
        "--all-paths", action="store_true",
        help="Crawl the whole host, not just the seed's path section",
    )
    build.add_argument(
        "--enrich", action="store_true",
        help="Add LLM descriptions + tags to frontmatter (needs okf-kit[enrich] + OPENAI_API_KEY)",
    )
    build.add_argument("--enrich-model", default="gpt-4o-mini", help="Model for --enrich")
    build.add_argument("-v", "--verbose", action="store_true")

    validate = sub.add_parser("validate", help="Check OKF v0.1 conformance")
    validate.add_argument("directory", help="Bundle directory")
    validate.add_argument("--quiet", action="store_true", help="No output; exit code only")

    zipc = sub.add_parser("zip", help="Package a bundle as a zip")
    zipc.add_argument("directory", help="Bundle directory")
    zipc.add_argument("-o", "--output", metavar="FILE", help="Zip path (default: <name>.zip)")

    syncp = sub.add_parser("sync", help="Re-crawl and update only what changed")
    syncp.add_argument("directory", help="Bundle directory")
    syncp.add_argument("--max-depth", type=int, default=None, help="Override crawl depth")
    syncp.add_argument("--max-pages", type=int, default=None, help="Override page cap")
    syncp.add_argument(
        "--force", action="store_true",
        help="Apply even if the re-crawl found under half the previous pages",
    )

    listp = sub.add_parser("list", help="List local bundles (or --remote registry)")
    listp.add_argument("--remote", action="store_true", help="List the registry catalog")
    listp.add_argument("--registry", help="registry.yaml URL or path")

    getp = sub.add_parser("get", help="Download a bundle from the registry")
    getp.add_argument("name", help="Bundle name from the registry")
    getp.add_argument("--registry", help="registry.yaml URL or path")
    getp.add_argument("--yes", "-y", action="store_true", help="Skip the download confirmation")

    chatp = sub.add_parser("chat", help="Chat with a bundle")
    chatp.add_argument("bundle", help="Bundle name or directory")
    chatp.add_argument("--provider", help="openai | ollama | openrouter | anthropic | custom")
    chatp.add_argument("--model", help="Model name")
    chatp.add_argument("--base-url", help="Custom OpenAI-compatible endpoint")
    chatp.add_argument("--trace", action="store_true", help="Show the navigation trace")
    chatp.add_argument("--resume", action="store_true", help="Resume the latest session")
    chatp.add_argument("--history", action="store_true", help="List saved sessions and exit")

    vizp = sub.add_parser("visualize", help="Export an interactive HTML graph")
    vizp.add_argument("directory", help="Bundle directory")
    vizp.add_argument("-o", "--output", metavar="FILE", help="HTML path (default: <bundle>/graph.html)")

    mcpp = sub.add_parser("serve-mcp", help="Serve bundles over MCP (stdio)")
    mcpp.add_argument("names", nargs="*", help="Bundle names/dirs (default: all local)")
    mcpp.add_argument("--all", action="store_true", help="Serve all local bundles")

    for name, milestone in _LATER.items():
        p = sub.add_parser(name, help=f"[{milestone}] see docs")
        p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cmd = args.command

    if cmd in _LATER:
        print(
            f"`okf {cmd}` lands in milestone {_LATER[cmd]} and isn't wired up yet.",
            file=sys.stderr,
        )
        return 2

    if cmd == "build":
        from .crawl import build_bundle

        rc = build_bundle(
            args.url,
            output=args.output,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            js=args.js,
            respect_robots=not args.no_robots,
            path_prefix=args.path_prefix,
            all_paths=args.all_paths,
            verbose=args.verbose,
        )
        if rc == 0 and args.enrich:
            from .enrich import enrich_bundle
            from .crawl import _default_output
            from .mapper import normalize_url

            target = args.output or str(_default_output(normalize_url(args.url)))
            enrich_bundle(target, model=args.enrich_model)
        return rc
    if cmd == "validate":
        from .okf import validate_bundle
        from .registry import bundle_dir_arg

        return 0 if validate_bundle(bundle_dir_arg(args.directory), quiet=args.quiet) else 3
    if cmd == "zip":
        from .okf import zip_bundle
        from .registry import bundle_dir_arg

        zip_bundle(bundle_dir_arg(args.directory), output=args.output)
        return 0
    if cmd == "sync":
        from .registry import bundle_dir_arg
        from .sync import sync_bundle

        return sync_bundle(
            str(bundle_dir_arg(args.directory)),
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            force=args.force,
        )
    if cmd == "list":
        from .registry import cmd_list

        return cmd_list(remote=args.remote, registry=args.registry)
    if cmd == "get":
        from .registry import cmd_get

        return cmd_get(args.name, registry=args.registry, yes=args.yes)
    if cmd == "chat":
        from .chat.repl import run_chat

        return run_chat(
            args.bundle,
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            trace=args.trace,
            resume=args.resume,
            show_history=args.history,
        )
    if cmd == "visualize":
        from .registry import bundle_dir_arg
        from .visualize import visualize

        visualize(bundle_dir_arg(args.directory), output=args.output)
        return 0
    if cmd == "serve-mcp":
        from .mcp import serve_mcp

        return serve_mcp(args.names, all_=args.all)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
