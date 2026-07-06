"""Shared test fixtures: serve the static fixture site on a local port."""

from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path

import pytest

FIXTURE_SITE = Path(__file__).parent / "fixtures" / "site"


@pytest.fixture
def fixture_site():
    """Serve tests/fixtures/site/ on localhost; yields the base URL.

    Fully offline — no network. Directory requests resolve to index.html so
    "/" serves the site root the way a real docs site would.
    """
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(FIXTURE_SITE)
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
