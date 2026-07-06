"""Shared test fixtures: serve the static fixture site on a local port."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from serve_util import serve as _serve

FIXTURE_SITE = Path(__file__).parent / "fixtures" / "site"


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
def built_bundle(fixture_site, tmp_path):
    """A ready-made bundle crawled from the fixture site."""
    from okf_kit.crawl import build_bundle

    out = tmp_path / "acme-okf"
    build_bundle(fixture_site, output=str(out), max_pages=50)
    return out


@pytest.fixture
def okf_home(tmp_path, monkeypatch):
    """Point ~/.okf at a tmp dir so bundle store / chat history are isolated."""
    home = tmp_path / "okfhome"
    monkeypatch.setenv("OKF_HOME", str(home))
    return home


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
