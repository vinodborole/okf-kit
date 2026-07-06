"""Visualize: self-contained HTML graph from the bundle's link structure."""

from __future__ import annotations

import json

from okf_kit.config import STATE_DIRNAME, STATE_FILENAME
from okf_kit.visualize import visualize


def test_edges_recorded_in_state(built_bundle):
    state = json.loads((built_bundle / STATE_DIRNAME / STATE_FILENAME).read_text())
    assert "edges" in state
    # the fixture site is interlinked, so there should be at least one edge
    assert len(state["edges"]) >= 1
    paths = {p["path"] for p in state["pages"]}
    for s, t in state["edges"]:
        assert s in paths and t in paths


def test_visualize_self_contained(built_bundle, tmp_path):
    out = visualize(built_bundle, output=str(tmp_path / "g.html"))
    html = out.read_text()
    assert html.startswith("<!doctype html>")
    # no external requests — everything inlined
    assert "http://" not in html.split("<script>")[0] or "cdn" not in html.lower()
    assert "src=" not in html and "cdn" not in html.lower()
    # data embedded
    assert '"nodes"' in html and '"links"' in html
    assert "__DATA__" not in html  # placeholder replaced
