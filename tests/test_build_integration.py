"""End-to-end: crawl the offline fixture site into a bundle and validate it."""

from __future__ import annotations

import json

from okf_kit.crawl import build_bundle
from okf_kit.config import STATE_DIRNAME, STATE_FILENAME


def test_build_produces_conformant_bundle(fixture_site, tmp_path):
    out = tmp_path / "acme-okf"
    rc = build_bundle(fixture_site, output=str(out), max_depth=3, max_pages=50)
    assert rc == 0

    # Reserved + hierarchy
    assert (out / "index.md").exists()
    assert (out / "log.md").exists()
    assert (out / "pages" / "home.md").exists()          # site root, dodged from index
    assert (out / "pages" / "docs" / "intro.md").exists()
    assert (out / "pages" / "docs" / "guide" / "install.md").exists()
    assert (out / "pages" / "docs" / "guide" / "config.md").exists()
    # Directory indexes for progressive disclosure
    assert (out / "pages" / "index.md").exists()
    assert (out / "pages" / "docs" / "guide" / "index.md").exists()


def test_concept_has_frontmatter_and_content(fixture_site, tmp_path):
    out = tmp_path / "acme-okf"
    build_bundle(fixture_site, output=str(out), max_depth=3, max_pages=50)

    install = (out / "pages" / "docs" / "guide" / "install.md").read_text()
    assert install.startswith("---\n")
    assert "type: Web Page" in install
    assert "resource:" in install
    # extraction fidelity: code fence + table survived
    assert "pip install acme-cli" in install
    assert "| OS | Status |" in install or "OS" in install
    assert "# Citations" in install


def test_external_links_not_followed(fixture_site, tmp_path):
    out = tmp_path / "acme-okf"
    build_bundle(fixture_site, output=str(out), max_depth=3, max_pages=50)
    # example.com/external must not appear as a page
    assert not (out / "pages" / "external.md").exists()
    md_files = [p for p in (out / "pages").rglob("*.md") if p.name != "index.md"]
    assert 5 <= len(md_files) <= 7  # home, intro, install, config, faq


def test_state_json_has_hashes(fixture_site, tmp_path):
    out = tmp_path / "acme-okf"
    build_bundle(fixture_site, output=str(out), max_depth=3, max_pages=50)
    state = json.loads((out / STATE_DIRNAME / STATE_FILENAME).read_text())
    assert state["generator"] == "okf-kit"
    assert state["page_count"] == len(state["pages"])
    assert all(len(p["hash"]) == 64 for p in state["pages"])
    assert state["root_url"].startswith("http://127.0.0.1")


def test_max_pages_respected(fixture_site, tmp_path):
    out = tmp_path / "capped"
    build_bundle(fixture_site, output=str(out), max_depth=3, max_pages=2)
    md = [p for p in (out / "pages").rglob("*.md") if p.name != "index.md"]
    assert len(md) <= 2
