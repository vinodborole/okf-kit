"""Reading an arbitrary OKF bundle (not just okf-kit's own) into concepts+edges."""

from __future__ import annotations

from okf_kit.bundle_reader import _target_id, read_bundle


def test_target_id_resolution():
    assert _target_id("events_.md", "tables/x") == "tables/events_"
    assert _target_id("../refs/m.md", "tables/x") == "refs/m"
    assert _target_id("/datasets/d.md", "tables/x") == "datasets/d"
    assert _target_id("d.md#section", "a/b") == "a/d"
    assert _target_id("https://example.com", "a/b") is None    # external, not a concept
    assert _target_id("../../escape.md", "a/b") is None        # escapes the bundle


def _write(dir, rel, frontmatter, body):
    p = dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    fm = "".join(f"{k}: {v}\n" for k, v in frontmatter.items())
    p.write_text(f"---\n{fm}---\n\n{body}\n", encoding="utf8")


def test_reads_google_style_bundle_from_markdown_links(tmp_path):
    # A bundle with no okf-kit state.json — edges must come from body links.
    b = tmp_path / "bundle"
    _write(b, "index.md", {}, "# ignored reserved listing")            # reserved → skipped
    _write(b, "tables/events.md", {"type": "Table", "title": "Events"},
           "See the [day count](../metrics/day_count.md) metric.")
    _write(b, "metrics/day_count.md", {"type": "Metric", "title": "Day count"},
           "Number of days.")

    data = read_bundle(b)
    ids = {c["id"] for c in data["concepts"]}
    assert ids == {"tables/events", "metrics/day_count"}              # index.md excluded
    assert ["tables/events", "metrics/day_count"] in data["edges"]    # link → edge
    events = next(c for c in data["concepts"] if c["id"] == "tables/events")
    assert events["type"] == "Table" and events["title"] == "Events"


def test_okf_kit_state_edges_included(built_bundle):
    # okf-kit's own bundle: bodies keep web links, edges come from state.json.
    data = read_bundle(built_bundle)
    assert data["concepts"] and data["edges"]
