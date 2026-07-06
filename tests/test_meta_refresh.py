"""A meta-refresh redirect stub (e.g. a /docs/ section root that bounces to a
first page) is followed, not treated as an empty dead-end."""

from __future__ import annotations

from okf_kit.crawl import build_bundle


def test_meta_refresh_is_followed(fixture_site, tmp_path):
    out = tmp_path / "b"
    # redirect.html has no content and no <a> links — only a meta-refresh to
    # /docs/intro.html. The crawl must follow it and reach the real pages.
    build_bundle(fixture_site + "/redirect.html", output=str(out), max_pages=50)

    assert (out / "pages" / "docs" / "intro.md").exists()      # followed the refresh
    assert not (out / "pages" / "redirect.md").exists()        # empty stub not written
