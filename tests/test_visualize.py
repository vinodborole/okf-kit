"""Visualize: self-contained HTML graph from the bundle's link structure."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap

import pytest

from okf_kit.config import STATE_DIRNAME, STATE_FILENAME
from okf_kit.visualize import _HTML, visualize


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


def test_interaction_state_declared_before_loop():
    """`hover`/`drag` (read by tick/draw) must be declared before loop() runs,
    or the first frame throws a temporal-dead-zone ReferenceError → blank page."""
    assert _HTML.index("let hover=null,drag=null;") < _HTML.index("loop();")


def test_layout_cools_and_freezes():
    """The force sim must anneal: `alpha` decays and the tick early-returns when
    settled, or the graph jitters forever ("out of control"). Structural guard —
    the physics is verified numerically in the standalone check."""
    assert "let alpha=1;" in _HTML
    assert "alpha*COOL" in _HTML          # cooling each frame
    assert "if(alpha<ALPHA_MIN && !drag) return;" in _HTML  # freeze when settled


# Node stubs for document/canvas/raf so the embedded script can run headless.
_RENDER_HARNESS = textwrap.dedent(r"""
    const fs=require('fs'), vm=require('vm');
    const html=fs.readFileSync(process.argv[1],'utf8');
    const script=html.split('<script>')[1].split('</script>')[0];
    const any=()=>new Proxy(function(){},{get:(t,k)=>k in t?t[k]:any(),set:()=>true,apply:()=>any()});
    const el={addEventListener(){},set textContent(v){},style:{},value:'',getContext(){return any();}};
    const ctx={document:{getElementById:()=>el,documentElement:{}},
      getComputedStyle:()=>({getPropertyValue:()=>'#000'}),
      innerWidth:1200,innerHeight:800,addEventListener(){},requestAnimationFrame(){},
      Math,JSON,console,Object,Array};
    vm.runInNewContext(script,ctx,{timeout:3000});  // throws on any runtime error
""")


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_generated_graph_executes(built_bundle, tmp_path):
    """The generated page's JS runs its first frame without error (real render)."""
    out = visualize(built_bundle, output=str(tmp_path / "g.html"))
    harness = tmp_path / "h.js"
    harness.write_text(_RENDER_HARNESS)
    proc = subprocess.run(
        ["node", str(harness), str(out)], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0, f"graph JS failed to run:\n{proc.stderr}"
