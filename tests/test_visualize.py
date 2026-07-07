"""Visualize: a self-contained, readable HTML explorer of any OKF bundle."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap

import pytest

from okf_kit.visualize import _HTML, visualize


def _embedded(html: str) -> dict:
    return json.loads(html.split("const DATA=", 1)[1].split(", N=DATA.nodes", 1)[0])


def test_self_contained(built_bundle, tmp_path):
    out = visualize(built_bundle, output=str(tmp_path / "viz.html"))
    html = out.read_text()
    assert html.startswith("<!doctype html>")
    assert "__DATA__" not in html                      # placeholder replaced
    assert "cdn" not in html.lower() and "src=" not in html   # no external assets
    data = _embedded(html)
    assert data["nodes"] and "tree" in data


def test_detail_has_links_and_backlinks(built_bundle, tmp_path):
    html = visualize(built_bundle, output=str(tmp_path / "v.html")).read_text()
    # the interlinked fixture site yields at least one edge → some concept
    # has an outbound link and its target has a backlink
    data = _embedded(html)
    assert any(n["links"] for n in data["nodes"])
    assert any(n["back"] for n in data["nodes"])
    # the detail pane renders both sections
    assert "Links to" in _HTML and "Cited by" in _HTML


_RENDER = textwrap.dedent(r"""
    const fs=require('fs'), vm=require('vm');
    const script=fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0];
    const mkEl=()=>{const e={children:[],className:'',style:{},dataset:{},
      set textContent(v){},set innerHTML(v){},append(...k){e.children.push(...k)},
      appendChild(k){e.children.push(k)},addEventListener(){},querySelectorAll(){return[]},
      scrollIntoView(){},classList:{toggle(){},add(){},remove(){}},get parentElement(){return mkEl();}};return e;};
    const doc={getElementById:()=>mkEl(),createElement:()=>mkEl()};
    const ctx={document:doc,Math,JSON,console,Object,Array,Map,Set,Number};
    vm.createContext(ctx); vm.runInContext(script,ctx,{timeout:8000});
""")


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_explorer_js_executes(built_bundle, tmp_path):
    out = visualize(built_bundle, output=str(tmp_path / "v.html"))
    h = tmp_path / "h.js"
    h.write_text(_RENDER)
    proc = subprocess.run(["node", str(h), str(out)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
