"""Shared test fixtures: serve the static fixture site on a local port."""

from __future__ import annotations

import functools
import http.server
import shutil
import threading
from pathlib import Path

import pytest

FIXTURE_SITE = Path(__file__).parent / "fixtures" / "site"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):  # silence request logging in tests
        pass


def _serve(directory: Path):
    handler = functools.partial(_QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture
def fixture_site():
    """Serve the read-only fixture site; yields the base URL. Fully offline."""
    server, url = _serve(FIXTURE_SITE)
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def mutable_site(tmp_path):
    """Serve a writable *copy* of the fixture site so a test can add/edit/delete
    pages between build and sync. Yields (base_url, site_dir)."""
    site_dir = tmp_path / "site"
    shutil.copytree(FIXTURE_SITE, site_dir)
    server, url = _serve(site_dir)
    try:
        yield url, site_dir
    finally:
        server.shutdown()
        server.server_close()
