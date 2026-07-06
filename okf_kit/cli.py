"""Command-line interface for okf-kit.

    okf build <url>       crawl a site into an OKF bundle          (M1)
    okf validate <dir>    OKF v0.1 conformance check               (M1)
    okf zip <dir>         package a bundle for hand-off            (M1)
    okf sync <dir>        incrementally update a bundle            (M2)
    okf list / get        registry                                 (M3)
    okf chat / visualize / serve-mcp   consume a bundle            (M3)
"""

from __future__ import annotations

import argparse
import sys

from . import __version__

# Milestone each command lands in; used until the handler is wired up.
_MILESTONE = {
    "build": "M1",
    "validate": "M1",
    "zip": "M1",
    "sync": "M2",
    "list": "M3",
    "get": "M3",
    "chat": "M3",
    "visualize": "M3",
    "serve-mcp": "M3",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okf",
        description="Turn any website into a portable, agent-ready OKF bundle.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    for name, milestone in _MILESTONE.items():
        p = sub.add_parser(name, help=f"[{milestone}] see docs")
        p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    print(
        f"`okf {args.command}` lands in milestone {_MILESTONE[args.command]} "
        f"and isn't implemented yet.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
