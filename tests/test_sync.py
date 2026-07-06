"""Incremental sync: add / change / remove detection and artifact cleanup."""

from __future__ import annotations

import json

import pytest

from okf_kit.config import STATE_DIRNAME, STATE_FILENAME
from okf_kit.crawl import build_bundle
from okf_kit.sync import sync_bundle, run_sync


def _state(bundle):
    return json.loads((bundle / STATE_DIRNAME / STATE_FILENAME).read_text())


def test_sync_no_changes(mutable_site, tmp_path):
    url, _ = mutable_site
    bundle = tmp_path / "b"
    build_bundle(url, output=str(bundle), max_pages=50)

    home = bundle / "pages" / "home.md"
    before_mtime = home.stat().st_mtime_ns

    import asyncio

    report = asyncio.run(run_sync(str(bundle)))
    assert (report["added"], report["changed"], report["removed"]) == (0, 0, 0)
    # unchanged concept file left byte-for-byte (timestamp preserved)
    assert home.stat().st_mtime_ns == before_mtime
    assert _state(bundle)["last_sync"]["added"] == 0


def test_sync_add_change_remove(mutable_site, tmp_path):
    url, site = mutable_site
    bundle = tmp_path / "b"
    build_bundle(url, output=str(bundle), max_pages=50)
    n_before = _state(bundle)["page_count"]

    # CHANGE: edit an existing page's body
    install = site / "docs" / "guide" / "install.html"
    install.write_text(install.read_text().replace("pip install acme-cli", "pip install acme-cli==2.0"))

    # ADD: a new page, linked from the home page so the crawler finds it
    (site / "docs" / "changelog.html").write_text(
        "<!doctype html><html><head><title>Changelog</title></head>"
        "<body><main><h1>Changelog</h1><p>Version 2.0 released.</p></main></body></html>"
    )
    index = site / "index.html"
    index.write_text(index.read_text().replace(
        '<a href="/docs/intro.html">Intro</a>',
        '<a href="/docs/intro.html">Intro</a> · <a href="/docs/changelog.html">Changelog</a>',
    ))

    # REMOVE: delete a page (its inbound link now 404s → treated as removed)
    (site / "docs" / "guide" / "config.html").unlink()

    import asyncio

    report = asyncio.run(run_sync(str(bundle)))
    assert report["added"] == 1, report
    assert report["changed"] == 1, report
    assert report["removed"] == 1, report

    # artifacts applied
    assert (bundle / "pages" / "docs" / "changelog.md").exists()
    assert not (bundle / "pages" / "docs" / "guide" / "config.md").exists()
    assert "acme-cli==2.0" in (bundle / "pages" / "docs" / "guide" / "install.md").read_text()
    assert _state(bundle)["page_count"] == n_before  # +1 -1


def test_sync_safety_valve(mutable_site, tmp_path):
    url, site = mutable_site
    bundle = tmp_path / "b"
    build_bundle(url, output=str(bundle), max_pages=50)

    # Gut the site so the re-crawl finds almost nothing.
    for p in site.rglob("*.html"):
        if p.name != "index.html":
            p.unlink()
    (site / "index.html").write_text(
        "<!doctype html><html><head><title>Home</title></head><body><p>gone</p></body></html>"
    )

    with pytest.raises(SystemExit):
        sync_bundle(str(bundle))
    # --force applies it
    import asyncio

    report = asyncio.run(run_sync(str(bundle), force=True))
    assert report["removed"] >= 1
