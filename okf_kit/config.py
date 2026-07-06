"""Paths and user config for okf-kit (~/.okf/)."""

from __future__ import annotations

import os
from pathlib import Path


def home_dir() -> Path:
    """The okf-kit home directory (override with OKF_HOME, e.g. in tests)."""
    root = Path(os.environ.get("OKF_HOME", Path.home() / ".okf"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def bundles_dir() -> Path:
    d = home_dir() / "bundles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chats_dir() -> Path:
    d = home_dir() / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Where a bundle stores its own crawl/sync state, inside the bundle directory.
STATE_DIRNAME = ".okf-kit"
STATE_FILENAME = "state.json"
