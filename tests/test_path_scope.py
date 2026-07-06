"""Path-scoping: a crawl stays within the seed's section unless told otherwise."""

from __future__ import annotations

import json

from okf_kit.config import STATE_DIRNAME, STATE_FILENAME
from okf_kit.crawl import build_bundle, scope_prefix_for
from okf_kit.sync import run_sync


def _state(bundle):
    return json.loads((bundle / STATE_DIRNAME / STATE_FILENAME).read_text())


def _concepts(bundle):
    return [p for p in (bundle / "pages").rglob("*.md") if p.name != "index.md"]


def test_scope_prefix_derivation():
    assert scope_prefix_for("https://x/") == "/"
    assert scope_prefix_for("https://x/book") == "/book/"          # section (normalized)
    assert scope_prefix_for("https://x/stable/book") == "/stable/book/"
    assert scope_prefix_for("https://x/docs/intro.html") == "/docs/"  # file → its dir


def test_auto_scope_excludes_parent(fixture_site, tmp_path):
    out = tmp_path / "b"
    # Seed inside /docs/ → auto scope /docs/ → the home page (/) is excluded.
    build_bundle(fixture_site + "/docs/intro.html", output=str(out), max_pages=50)
    assert not (out / "pages" / "home.md").exists()
    assert all("docs" in str(p.relative_to(out)) for p in _concepts(out))
    assert _state(out)["config"]["path_prefix"] == "/docs/"


def test_all_paths_reaches_parent(fixture_site, tmp_path):
    out = tmp_path / "b"
    build_bundle(fixture_site + "/docs/intro.html", output=str(out), max_pages=50, all_paths=True)
    assert (out / "pages" / "home.md").exists()  # reached via intro → /index.html
    assert _state(out)["config"]["path_prefix"] == "/"


def test_explicit_path_prefix(fixture_site, tmp_path):
    out = tmp_path / "b"
    build_bundle(fixture_site + "/", output=str(out), path_prefix="/docs/guide/", max_pages=50)
    # Only /docs/guide/* is followed; /docs/intro and /docs/faq are out of scope.
    assert (out / "pages" / "docs" / "guide" / "install.md").exists()
    assert (out / "pages" / "docs" / "guide" / "config.md").exists()
    assert not (out / "pages" / "docs" / "intro.md").exists()
    assert not (out / "pages" / "docs" / "faq.md").exists()
    assert _state(out)["config"]["path_prefix"] == "/docs/guide/"


def test_sync_preserves_scope(fixture_site, tmp_path):
    out = tmp_path / "b"
    build_bundle(fixture_site + "/docs/intro.html", output=str(out), max_pages=50)
    n_before = _state(out)["page_count"]

    import asyncio

    report = asyncio.run(run_sync(str(out)))
    # Re-crawl with the stored /docs/ scope → nothing new, home still excluded.
    assert (report["added"], report["changed"], report["removed"]) == (0, 0, 0)
    assert not (out / "pages" / "home.md").exists()
    assert _state(out)["page_count"] == n_before
