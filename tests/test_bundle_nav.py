"""Bundle navigation primitives + path-traversal guard."""

from __future__ import annotations

from okf_kit.bundle_nav import list_directory, read_concept, search_bundle


def test_list_and_read(built_bundle):
    root = list_directory(built_bundle, "/")
    assert "dir:  pages" in root
    pages = list_directory(built_bundle, "/pages")
    assert "home.md" in pages
    concept = read_concept(built_bundle, "/pages/docs/intro.md")
    assert "type: Web Page" in concept


def test_read_errors_gracefully(built_bundle):
    assert read_concept(built_bundle, "/pages/nope.md").startswith("error:")
    assert list_directory(built_bundle, "/nope").startswith("error:")


def test_traversal_guarded(built_bundle):
    assert read_concept(built_bundle, "/../../etc/passwd").startswith("error:")
    assert list_directory(built_bundle, "/..").startswith("error:") or \
        "dir:" not in list_directory(built_bundle, "/../../")


def test_search(built_bundle):
    hits = search_bundle(built_bundle, "installation pip", limit=3)
    assert hits and any("install" in h["path"] for h in hits)
    assert all("score" in h and h["score"] > 0 for h in hits)
