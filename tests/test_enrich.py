"""Enrichment: frontmatter gains description + tags (fake enricher, no key)."""

from __future__ import annotations

import yaml

from okf_kit.enrich import enrich_bundle


def test_enrich_merges_frontmatter(built_bundle):
    def fake(title, body):
        return {"description": "A test page.", "tags": ["alpha", "beta"]}

    n = enrich_bundle(built_bundle, enricher=fake)
    assert n >= 5

    intro = (built_bundle / "pages" / "docs" / "intro.md").read_text()
    fm = yaml.safe_load(intro[4 : intro.index("\n---\n", 4)])
    assert fm["description"] == "A test page."
    assert fm["tags"] == ["alpha", "beta"]
    assert fm["type"] == "Web Page"  # existing fields preserved
    # body intact after rewrite
    assert "# Citations" in intro


def test_enrich_survives_one_failure(built_bundle):
    calls = {"n": 0}

    def flaky(title, body):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return {"description": "ok", "tags": ["x"]}

    n = enrich_bundle(built_bundle, enricher=flaky)
    assert n >= 4  # all but the one that failed
