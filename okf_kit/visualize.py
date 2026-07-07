"""Render any OKF bundle as a self-contained, readable HTML explorer
(`okf visualize`).

A collapsible outline of the bundle's concepts (by path), with a detail pane
showing each concept's frontmatter, rendered body, the concepts it **links to**,
and the concepts that **cite** it (backlinks). No backend, no CDN, no okf-kit
state file required — it reads any OKF bundle via `bundle_reader`, so it works
on bundles produced by any tool.
"""

from __future__ import annotations

import json
from pathlib import Path

from .bundle_reader import read_bundle


def _tree(concepts: list[dict]) -> list[dict]:
    root: dict = {}
    for i, c in enumerate(concepts):
        parts = c["id"].split("/")
        cur = root
        for seg in parts[:-1]:
            cur = cur.setdefault(seg, {"_dir": {}})["_dir"]
        cur[parts[-1]] = {"_page": i}

    def conv(d: dict) -> list[dict]:
        items: list[dict] = []
        for name, node in d.items():
            if "_page" in node:
                i = node["_page"]
                items.append({"name": concepts[i]["title"], "page": i,
                              "deg": concepts[i]["_deg"]})
            else:
                kids = conv(node["_dir"])
                count = sum(k.get("count", 1) for k in kids)
                items.append({"name": name, "children": kids, "count": count})
        items.sort(key=lambda k: ("children" not in k, k["name"].lower()))
        return items

    return conv(root)


def _data(bundle_dir: Path) -> dict:
    b = read_bundle(bundle_dir)
    concepts = b["concepts"]
    idx = {c["id"]: i for i, c in enumerate(concepts)}
    links: list[list[int]] = [[] for _ in concepts]
    back: list[list[int]] = [[] for _ in concepts]
    for s, t in b["edges"]:
        si, ti = idx[s], idx[t]
        links[si].append(ti)
        back[ti].append(si)
    nodes = []
    for i, c in enumerate(concepts):
        c["_deg"] = len(set(links[i])) + len(set(back[i]))
        nodes.append({
            "id": c["id"], "title": c["title"], "type": c["type"],
            "tags": c["tags"], "resource": c["resource"], "description": c["description"],
            "body": c["body"][:12000],
            "links": sorted(set(links[i])), "back": sorted(set(back[i])),
        })
    return {"count": len(concepts), "tree": _tree(concepts), "nodes": nodes}


def visualize(directory, *, output: str | None = None) -> Path:
    bundle_dir = Path(directory)
    data = _data(bundle_dir)
    out = Path(output) if output else bundle_dir / "viz.html"
    out.write_text(_HTML.replace("__DATA__", json.dumps(data)), encoding="utf8")
    print(f"Wrote {out} ({data['count']} concepts)")
    return out


_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>okf-kit — bundle explorer</title>
<style>
  :root{--ground:#F4F3EF;--card:#FBFBF9;--ink:#22262E;--muted:#6A727E;--line:#E3E2DC;
        --accent:#3B5CC4;--brass:#9A6B1F;--hover:#ECEBE5;--chip:#EDECE6}
  @media (prefers-color-scheme:dark){:root{--ground:#15171C;--card:#1C1F25;--ink:#E8E9E4;
        --muted:#98A0AB;--line:#2B2F37;--accent:#7C97F0;--brass:#C69749;--hover:#23272F;--chip:#262A31}}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.55 system-ui,-apple-system,sans-serif;background:var(--ground);color:var(--ink);
       height:100vh;display:flex;flex-direction:column}
  header{padding:13px 20px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:12px}
  header h1{margin:0;font-size:15px;font-weight:650;letter-spacing:.2px}
  header .c{margin-left:auto;color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
  .wrap{flex:1;display:grid;grid-template-columns:minmax(300px,1fr) minmax(340px,1.35fr);min-height:0}
  .col{display:flex;flex-direction:column;min-height:0}
  .search{padding:12px 16px 6px}
  input{width:100%;background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px 12px;
        color:var(--ink);font:inherit}
  .pane{overflow:auto;padding:8px 8px 40px 14px}
  #detail{border-left:1px solid var(--line);background:var(--card);padding:24px 26px 60px;overflow:auto}
  ul.tree,ul.tree ul{list-style:none;margin:0;padding:0}
  ul.tree ul{margin-left:13px;border-left:1px solid var(--line);padding-left:2px}
  .row{display:flex;align-items:center;gap:6px;padding:4px 8px;border-radius:7px;cursor:pointer;white-space:nowrap}
  .row:hover{background:var(--hover)}
  .row.sel{background:color-mix(in srgb,var(--accent) 18%,transparent)}
  .tw{width:13px;flex:none;color:var(--muted);font-size:10px;transition:transform .12s}
  .tw.open{transform:rotate(90deg)}
  .fold .nm{font-weight:600}
  .dot{width:6px;height:6px;border-radius:50%;background:var(--brass);opacity:.55;flex:none}
  .nm{overflow:hidden;text-overflow:ellipsis}
  .badge{margin-left:auto;color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums;padding-left:10px}
  .hidden{display:none}.hl{background:color-mix(in srgb,var(--brass) 34%,transparent);border-radius:3px}
  #detail h2{margin:0 0 6px;font-size:19px;line-height:1.25}
  .kv{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:4px}
  .type{font-size:11px;font-weight:600;color:var(--accent);background:color-mix(in srgb,var(--accent) 14%,transparent);
        padding:2px 9px;border-radius:20px}
  .cid{color:var(--muted);font-family:ui-monospace,monospace;font-size:11.5px;word-break:break-all}
  .res{display:inline-block;margin:2px 0 6px;font-size:12.5px}
  .tags{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0}
  .tag{font-size:11px;color:var(--muted);background:var(--chip);padding:2px 8px;border-radius:20px}
  .desc{color:var(--ink);margin:10px 0 4px}
  .body{border-top:1px solid var(--line);margin-top:16px;padding-top:8px;font-size:13.5px;overflow-wrap:anywhere}
  .body h2,.body h3,.body h4,.body h5{font-size:14px;margin:16px 0 6px}
  .body pre{background:var(--chip);border-radius:8px;padding:10px 12px;overflow:auto;font-size:12px}
  .body code{font-family:ui-monospace,monospace;font-size:12.5px}
  .body p code{background:var(--chip);padding:1px 5px;border-radius:4px}
  .body ul{padding-left:20px}.body a{color:var(--accent)}.body .mdlink{color:var(--brass)}
  h3.sec{font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);margin:22px 0 8px}
  .lk{display:flex;gap:8px;align-items:baseline;padding:5px 8px;border-radius:7px;cursor:pointer}
  .lk:hover{background:var(--hover)} .lk .sec2{color:var(--muted);font-size:11.5px;margin-left:auto;white-space:nowrap}
  .empty{color:var(--muted)}
</style></head><body>
<header><h1>okf-kit</h1><span class="c" id="count"></span></header>
<div class="wrap">
  <div class="col">
    <div class="search"><input id="q" placeholder="search concepts…" autocomplete="off"></div>
    <div class="pane"><ul class="tree" id="tree"></ul></div>
  </div>
  <div class="pane" id="detail"><p class="empty">Select a concept to see its content, links, and backlinks.</p></div>
</div>
<script>
const DATA=__DATA__, N=DATA.nodes;
document.getElementById('count').textContent=DATA.count+' concepts';
const treeEl=document.getElementById('tree'), detail=document.getElementById('detail');
let filter='', selRow=null; const rowFor=new Map();
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function markName(s){if(!filter)return esc(s);const i=s.toLowerCase().indexOf(filter);
  return i<0?esc(s):esc(s.slice(0,i))+'<span class="hl">'+esc(s.slice(i,i+filter.length))+'</span>'+esc(s.slice(i+filter.length));}
const secOf=id=>id.split('/').slice(0,-1).join('/');

function render(node, ul, depth){
  const li=document.createElement('li');
  const row=document.createElement('div');
  if(node.children){
    row.className='row fold';
    const tw=document.createElement('span');tw.className='tw'+(depth<1?' open':'');tw.textContent='▸';
    const nm=document.createElement('span');nm.className='nm';nm.textContent=node.name;
    const bd=document.createElement('span');bd.className='badge';bd.textContent=node.count;
    row.append(tw,nm,bd);li.appendChild(row);
    const kids=document.createElement('ul');if(depth>=1)kids.classList.add('hidden');
    node.children.forEach(c=>render(c,kids,depth+1));li.appendChild(kids);
    row.onclick=()=>{kids.classList.toggle('hidden');tw.classList.toggle('open');};
    node._row=row;node._kids=kids;node._tw=tw;
  } else {
    row.className='row leaf';
    const dot=document.createElement('span');dot.className='dot';
    const nm=document.createElement('span');nm.className='nm';nm.innerHTML=markName(node.name);
    const bd=document.createElement('span');bd.className='badge';bd.textContent=node.deg;
    row.append(dot,nm,bd);li.appendChild(row);
    row.onclick=()=>select(node.page);
    rowFor.set(node.page,{row,nm,name:node.name});
  }
  ul.appendChild(li);
}
DATA.tree.forEach(n=>render(n,treeEl,0));

function mdrender(src){
  const lines=src.split('\n');let html='',i=0,inList=false;
  const closeL=()=>{if(inList){html+='</ul>';inList=false;}};
  const inline=s=>s.replace(/`([^`]+)`/g,(m,x)=>'<code>'+x+'</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,(m,t,u)=>/\.md($|[#?])/.test(u)
      ?'<span class="mdlink">'+t+'</span>'
      :'<a href="'+u+'" target="_blank" rel="noopener">'+t+'</a>');
  while(i<lines.length){
    let ln=lines[i];
    if(ln.trimStart().startsWith('```')){closeL();let code='';i++;
      while(i<lines.length&&!lines[i].trimStart().startsWith('```')){code+=lines[i]+'\n';i++;}
      i++;html+='<pre><code>'+esc(code)+'</code></pre>';continue;}
    const h=ln.match(/^(#{1,5})\s+(.*)/);
    if(h){closeL();html+='<h'+(h[1].length+1)+'>'+inline(esc(h[2]))+'</h'+(h[1].length+1)+'>';i++;continue;}
    const li=ln.match(/^\s*[-*+]\s+(.*)/);
    if(li){if(!inList){html+='<ul>';inList=true;}html+='<li>'+inline(esc(li[1]))+'</li>';i++;continue;}
    if(ln.trim()===''){closeL();i++;continue;}
    closeL();html+='<p>'+inline(esc(ln))+'</p>';i++;
  }
  closeL();return html;
}

function linkList(ids){
  if(!ids.length)return '<p class="empty">None.</p>';
  return ids.map(j=>`<div class="lk" data-i="${j}"><span>${esc(N[j].title)}</span>`+
    `<span class="sec2">${esc(secOf(N[j].id))||'/'}</span></div>`).join('');
}
function select(i){
  const n=N[i];
  if(selRow)selRow.classList.remove('sel');
  const r=rowFor.get(i);if(r){selRow=r.row;r.row.classList.add('sel');r.row.scrollIntoView({block:'nearest'});}
  const res=n.resource?`<a class="res" href="${esc(n.resource)}" target="_blank" rel="noopener">${esc(n.resource)}</a>`:'';
  const tags=n.tags.length?`<div class="tags">${n.tags.map(t=>'<span class="tag">'+esc(t)+'</span>').join('')}</div>`:'';
  const desc=n.description?`<p class="desc">${esc(n.description)}</p>`:'';
  detail.innerHTML=
    `<h2>${esc(n.title)}</h2>`+
    `<div class="kv">${n.type?'<span class="type">'+esc(n.type)+'</span>':''}<span class="cid">${esc(n.id)}</span></div>`+
    res+tags+desc+
    `<div class="body">${mdrender(n.body)}</div>`+
    `<h3 class="sec">Links to · ${n.links.length}</h3>${linkList(n.links)}`+
    `<h3 class="sec">Cited by · ${n.back.length}</h3>${linkList(n.back)}`;
  detail.querySelectorAll('.lk').forEach(el=>el.onclick=()=>select(+el.dataset.i));
  detail.scrollTop=0;
}

function walk(node){
  if(!node.children){const r=rowFor.get(node.page);const hit=!filter||node.name.toLowerCase().includes(filter)
      ||N[node.page].id.toLowerCase().includes(filter);
    if(r){r.nm.innerHTML=markName(node.name);r.row.parentElement.classList.toggle('hidden',!hit);}return hit;}
  let any=false;node.children.forEach(c=>{any=walk(c)||any;});
  if(node._row){node._row.parentElement.classList.toggle('hidden',!!filter&&!any);
    if(filter){node._kids.classList.remove('hidden');node._tw.classList.add('open');}}
  return any;
}
document.getElementById('q').addEventListener('input',e=>{filter=e.target.value.toLowerCase().trim();
  DATA.tree.forEach(walk);});
</script></body></html>"""
