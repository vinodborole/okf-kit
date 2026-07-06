"""validate / zip / sync / visualize accept a downloaded bundle *name*, not
just a directory path (regression: `okf visualize <name>` used to fail while
`okf chat <name>` worked)."""

from __future__ import annotations

from okf_kit.cli import main
from okf_kit.config import bundles_dir
from okf_kit.crawl import build_bundle


def _install_bundle(fixture_site) -> str:
    """Build a bundle into ~/.okf/bundles/acme (as `okf get` would), return its name."""
    build_bundle(fixture_site, output=str(bundles_dir() / "acme"), max_pages=50)
    return "acme"


def test_validate_by_name(fixture_site, okf_home):
    name = _install_bundle(fixture_site)
    assert main(["validate", name]) == 0            # resolves to the store, conformant
    assert main(["validate", "no-such-bundle"]) == 3  # nonexistent → not conformant


def test_zip_by_name(fixture_site, okf_home, tmp_path):
    name = _install_bundle(fixture_site)
    out = tmp_path / "acme.zip"
    assert main(["zip", name, "-o", str(out)]) == 0
    assert out.exists()


def test_visualize_by_name(fixture_site, okf_home, tmp_path):
    name = _install_bundle(fixture_site)
    out = tmp_path / "graph.html"
    assert main(["visualize", name, "-o", str(out)]) == 0
    assert out.exists() and out.read_text().startswith("<!doctype html>")


def test_sync_by_name(fixture_site, okf_home):
    name = _install_bundle(fixture_site)
    # sync re-crawls the still-running fixture site; nothing changed → rc 0
    assert main(["sync", name]) == 0


def test_path_still_works(fixture_site, tmp_path):
    """A plain directory path must keep working (no regression)."""
    out = tmp_path / "acme-okf"
    build_bundle(fixture_site, output=str(out), max_pages=50)
    assert main(["validate", str(out)]) == 0
    assert main(["visualize", str(out), "-o", str(tmp_path / "g.html")]) == 0
