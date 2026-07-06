"""Render a bundle as a self-contained interactive HTML graph (`okf visualize`).

Single file, no backend, no CDN — works from file://. Nodes are concept
pages (colored by top-level section), edges are internal links. Canvas
force-directed layout in vanilla JS (no d3), with search and hover. Styled in
the calknowledge Ink & Index palette.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import STATE_DIRNAME, STATE_FILENAME


def _graph_data(bundle_dir: Path) -> dict:
    state = json.loads((bundle_dir / STATE_DIRNAME / STATE_FILENAME).read_text(encoding="utf8"))
    pages = state.get("pages", [])
    index = {p["path"]: i for i, p in enumerate(pages)}

    def section(path: str) -> str:
        parts = path.split("/")  # pages/<section>/...
        return parts[1] if len(parts) > 2 else "root"

    nodes = [
        {"id": i, "path": p["path"], "title": p.get("title") or p["path"].split("/")[-1],
         "section": section(p["path"])}
        for i, p in enumerate(pages)
    ]
    links = [
        {"source": index[s], "target": index[t]}
        for s, t in state.get("edges", [])
        if s in index and t in index
    ]
    return {"root_url": state.get("root_url"), "nodes": nodes, "links": links}


def visualize(directory, *, output: str | None = None) -> Path:
    bundle_dir = Path(directory)
    if not (bundle_dir / STATE_DIRNAME / STATE_FILENAME).exists():
        raise SystemExit(f"{directory} is not an okf-kit bundle (no state.json)")
    data = _graph_data(bundle_dir)
    out = Path(output) if output else bundle_dir / "graph.html"
    out.write_text(_HTML.replace("__DATA__", json.dumps(data)), encoding="utf8")
    print(f"Wrote {out} ({len(data['nodes'])} nodes, {len(data['links'])} links)")
    return out


_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>okf-kit — knowledge graph</title>
<style>
  :root{--ground:#F2F2EF;--ink:#1F242C;--muted:#5C6572;--line:#DCDDD8;
        --accent:#3B5CC4;--brass:#9A6B1F;--surface:#FBFBFC}
  @media (prefers-color-scheme:dark){:root{--ground:#14161B;--ink:#E7E8E3;
        --muted:#9AA1AC;--line:#31353D;--accent:#5F7BDE;--brass:#AA8033;--surface:#1D2026}}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 system-ui,sans-serif;background:var(--ground);color:var(--ink);overflow:hidden}
  header{position:fixed;top:0;left:0;right:0;padding:12px 18px;display:flex;gap:14px;align-items:center;
         background:var(--surface);border-bottom:1px solid var(--line);z-index:2}
  header b{font-size:15px}
  header .u{color:var(--muted);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  input{margin-left:auto;background:var(--ground);border:1px solid var(--line);border-radius:7px;
        padding:7px 12px;color:var(--ink);font:inherit;width:220px}
  canvas{display:block}
  #tip{position:fixed;pointer-events:none;background:var(--surface);border:1px solid var(--line);
       border-radius:8px;padding:8px 12px;font-size:12px;max-width:320px;display:none;z-index:3;
       box-shadow:0 6px 20px rgba(0,0,0,.15)}
  #tip .p{color:var(--muted);font-family:ui-monospace,monospace;font-size:10.5px;margin-top:3px;word-break:break-all}
</style></head><body>
<header><b>okf-kit</b><span class="u" id="root"></span>
  <input id="q" placeholder="filter concepts…" autocomplete="off"></header>
<canvas id="c"></canvas><div id="tip"></div>
<script>
const DATA = __DATA__;
const canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
const tip = document.getElementById('tip');
document.getElementById('root').textContent = DATA.root_url || '';
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const PALETTE = {};
function colorFor(section){
  if(section in PALETTE) return PALETTE[section];
  const base = [css('--accent'), css('--brass'), '#2E7D4F', '#B3372E', '#7E5717', '#2C459E'];
  const c = base[Object.keys(PALETTE).length % base.length];
  return PALETTE[section] = c;
}
let W,H;
function resize(){W=canvas.width=innerWidth;H=canvas.height=innerHeight;}
addEventListener('resize',resize); resize();

const nodes = DATA.nodes.map(n=>({...n,x:W/2+(Math.random()-.5)*300,y:H/2+(Math.random()-.5)*300,vx:0,vy:0}));
const links = DATA.links.map(l=>({s:nodes[l.source],t:nodes[l.target]}));
const deg = new Array(nodes.length).fill(0);
links.forEach(l=>{deg[l.s.id]++;deg[l.t.id]++;});

let filter='';
document.getElementById('q').addEventListener('input',e=>{filter=e.target.value.toLowerCase();});
function dim(n){return filter && !(n.title.toLowerCase().includes(filter)||n.path.toLowerCase().includes(filter));}

// interaction state — declared before the loop starts (tick/draw read them)
let hover=null,drag=null;

// force sim
function tick(){
  for(let i=0;i<nodes.length;i++){
    const a=nodes[i];
    for(let j=i+1;j<nodes.length;j++){
      const b=nodes[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01;
      const f=1400/d2;const d=Math.sqrt(d2);
      a.vx+=f*dx/d;a.vy+=f*dy/d;b.vx-=f*dx/d;b.vy-=f*dy/d;
    }
    a.vx+=(W/2-a.x)*0.001;a.vy+=(H/2-a.y)*0.001;
  }
  links.forEach(l=>{
    let dx=l.t.x-l.s.x,dy=l.t.y-l.s.y,d=Math.sqrt(dx*dx+dy*dy)||1;const f=(d-90)*0.01;
    l.s.vx+=f*dx/d;l.s.vy+=f*dy/d;l.t.vx-=f*dx/d;l.t.vy-=f*dy/d;
  });
  nodes.forEach(n=>{if(n===drag)return;n.x+=n.vx*=.85;n.y+=n.vy*=.85;});
}
function draw(){
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle=css('--line');ctx.lineWidth=1;
  links.forEach(l=>{if(dim(l.s)&&dim(l.t))return;ctx.beginPath();ctx.moveTo(l.s.x,l.s.y);ctx.lineTo(l.t.x,l.t.y);ctx.stroke();});
  nodes.forEach(n=>{
    const r=5+Math.min(deg[n.id],8);ctx.globalAlpha=dim(n)?.15:1;
    ctx.beginPath();ctx.arc(n.x,n.y,r,0,7);ctx.fillStyle=colorFor(n.section);ctx.fill();
    ctx.strokeStyle=css('--surface');ctx.lineWidth=1.5;ctx.stroke();
    if(deg[n.id]>=4||n===hover){ctx.globalAlpha=dim(n)?.15:1;ctx.fillStyle=css('--ink');
      ctx.font='11px system-ui';ctx.fillText(n.title.slice(0,28),n.x+r+3,n.y+3);}
  });
  ctx.globalAlpha=1;
}
function loop(){tick();draw();requestAnimationFrame(loop);}loop();

canvas.addEventListener('mousemove',e=>{
  const m=nearest(e.clientX,e.clientY);hover=m;
  if(m){tip.style.display='block';tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+14)+'px';
    tip.innerHTML='<div>'+esc(m.title)+'</div><div class="p">'+esc(m.path)+'</div>';}
  else tip.style.display='none';
  if(drag){drag.x=e.clientX;drag.y=e.clientY;drag.vx=drag.vy=0;}
});
canvas.addEventListener('mousedown',e=>{drag=nearest(e.clientX,e.clientY);});
addEventListener('mouseup',()=>{drag=null;});
function nearest(x,y){let best=null,bd=225;nodes.forEach(n=>{const d=(n.x-x)**2+(n.y-y)**2;if(d<bd){bd=d;best=n;}});return best;}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
</script></body></html>"""
